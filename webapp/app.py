from flask import Flask, request, jsonify, render_template
import uuid
import datetime
from config import settings
from database import db
from amnezia_client import AmneziaClient
from webapp.security import telegram_auth_required

AMNEZIA_CLIENTS = {}

def get_amnezia_client(server: dict) -> AmneziaClient:
    server_id = server['id']
    if server_id not in AMNEZIA_CLIENTS:
        AMNEZIA_CLIENTS[server_id] = AmneziaClient(server['api_url'], server['api_key'])
    return AMNEZIA_CLIENTS[server_id]

app = Flask(__name__)


def get_tg_user_id(req):
    user_id = req.headers.get('X-TG-User-Id') or req.args.get('user_id')
    return int(user_id) if user_id else None


def is_subscription_active(user: dict) -> bool:
    value = user.get('subscription_expires_at')
    return bool(value and datetime.datetime.fromisoformat(value) > datetime.datetime.now())


@app.before_request
async def before_request():
    if not db.connection:
        await db.connect()
        await db.init_db()


@app.route('/api/dashboard', methods=['GET'])
@telegram_auth_required
async def get_dashboard():
    user_id = get_tg_user_id(request)
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    user = await db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    devices = await db.get_user_devices(user_id)
    return jsonify({
        "subscription_expires_at": user['subscription_expires_at'],
        "subscription_active": is_subscription_active(user),
        "device_limit": user['device_limit'],
        "devices": devices,
    })


@app.route('/api/servers', methods=['GET'])
@telegram_auth_required
async def get_servers():
    servers = await db.get_active_servers()
    payload = []
    for server in servers:
        client = get_amnezia_client(server)
        status = await client.check_status()
        payload.append({
            "id": server['id'],
            "name": server['name'],
            "flag": server.get('flag') or '🌐',
            "bandwidth_label": server.get('bandwidth_label') or '',
            "online": status['online'],
            "metrics": status.get('metrics', {}),
        })
    return jsonify(payload)


@app.route('/api/devices', methods=['POST'])
@telegram_auth_required
async def create_device():
    user_id = get_tg_user_id(request)
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    user = await db.get_user(user_id)
    if not user or not is_subscription_active(user):
        return jsonify({"error": "Active subscription is required"}), 402

    data = request.get_json(silent=True) or {}
    server_id = data.get('server_id')
    name = (data.get('name') or '').strip()[:48]
    if not server_id or not name:
        return jsonify({"error": "Server ID and device name are required"}), 400

    if await db.get_user_devices_count(user_id) >= user['device_limit']:
        return jsonify({"error": "Device limit exceeded"}), 400

    server = await db.get_server(int(server_id))
    if not server or not server['is_active']:
        return jsonify({"error": "Server not found"}), 404

    amnezia_client_id = f"tg_{user_id}_{uuid.uuid4().hex[:8]}"
    client = get_amnezia_client(server)
    config_text = await client.create_vpn_profile(amnezia_client_id)
    if not config_text:
        return jsonify({"error": "Failed to create VPN profile"}), 500

    from webapp.vpn_encoder import encode_amnezia_config
    device_id = await db.add_device(user_id, server['id'], name, amnezia_client_id, config_text)
    device = await db.get_device(device_id)
    # Добавляем упакованный QR-код в ответ
    device['amnezia_qr'] = encode_amnezia_config(device['config_text'])
    return jsonify({"status": "Device created successfully", "device": device}), 201


@app.route('/api/devices/<int:device_id>', methods=['PATCH'])
@telegram_auth_required
async def rename_device(device_id):
    user_id = get_tg_user_id(request)
    device = await db.get_device(device_id)
    if not user_id or not device or device['user_id'] != user_id:
        return jsonify({"error": "Device not found"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()[:48]
    if not name:
        return jsonify({"error": "Device name is required"}), 400
    await db.rename_device(device_id, name)
    return jsonify({"status": "Device renamed", "device": await db.get_device(device_id)})


@app.route('/api/devices/<int:device_id>', methods=['DELETE'])
@telegram_auth_required
async def delete_device(device_id):
    user_id = get_tg_user_id(request)
    device = await db.get_device(device_id)
    if not user_id or not device or device['user_id'] != user_id:
        return jsonify({"error": "Device not found"}), 404

    server = await db.get_server(device['server_id'])
    if server:
        client = get_amnezia_client(server)
        await client.delete_vpn_profile(device['amnezia_client_id'])
    await db.delete_device(device_id)
    return jsonify({"status": "Device deleted successfully"})


@app.route('/api/devices/<int:device_id>/share', methods=['POST'])
@telegram_auth_required
async def share_device(device_id):
    user_id = get_tg_user_id(request)
    device = await db.get_device(device_id)
    if not user_id or not device or device['user_id'] != user_id:
        return jsonify({"error": "Device not found"}), 404

    token = uuid.uuid4().hex
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
    await db.create_temporary_link(device_id, token, expires_at)
    return jsonify({"share_url": f"{settings.MINIAPP_URL}/share/{token}", "expires_at": expires_at})


@app.route('/share/<string:token>', methods=['GET'])
async def shared_device(token):
    device = await db.get_device_by_temporary_token(token)
    if not device:
        return "Ссылка истекла или недействительна", 404
    return render_template('share.html', device=device)


@app.route('/share/<string:token>/download', methods=['GET'])
async def download_config(token):
    device = await db.get_device_by_temporary_token(token)
    if not device:
        return "Ссылка истекла или недействительна", 404
    response = app.response_class(response=device['config_text'], status=200, mimetype='text/plain')
    response.headers["Content-Disposition"] = f"attachment; filename={device['name']}.conf"
    return response


@app.route('/')
async def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
