from flask import Flask, request, jsonify
import uuid
import datetime
from config import settings
from database import db
from amnezia_client import AmneziaClient

app = Flask(__name__)

def get_tg_user_id(req):
    user_id = req.headers.get('X-TG-User-Id')
    if not user_id:
        user_id = request.args.get('user_id')
    return int(user_id) if user_id else None

@app.before_request
async def before_request():
    if not db.connection:
        await db.connect()

@app.route('/api/dashboard', methods=['GET'])
async def get_dashboard():
    user_id = get_tg_user_id(request)
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    user = await db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    devices = await db.get_user_devices(user_id)
    
    return jsonify({
        "subscription_status": user['subscription_expires_at'],
        "device_limit": user['device_limit'],
        "devices": devices
    })

@app.route('/api/servers', methods=['GET'])
async def get_servers():
    servers = await db.get_active_servers()
    masked_servers = [{"id": server['id'], "name": server['name']} for server in servers]
    return jsonify(masked_servers)

@app.route('/api/devices', methods=['POST'])
async def create_device():
    user_id = get_tg_user_id(request)
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    data = request.get_json()
    server_id = data.get('server_id')
    name = data.get('name')
    
    if not server_id or not name:
        return jsonify({"error": "Server ID and device name are required"}), 400
    
    user_devices_count = await db.get_user_devices_count(user_id)
    user = await db.get_user(user_id)
    
    if user_devices_count >= user['device_limit']:
        return jsonify({"error": "Device limit exceeded"}), 400
    
    server = await db.get_server(server_id)
    if not server:
        return jsonify({"error": "Server not found"}), 404
    
    amnezia_client_id = f"tg_{uuid.uuid4().hex[:8]}"
    client = AmneziaClient(server['api_url'], server['api_key'])
    config_text = await client.create_vpn_profile(amnezia_client_id)
    
    if not config_text:
        return jsonify({"error": "Failed to create VPN profile"}), 500
    
    await db.add_device(user_id, server_id, name, amnezia_client_id, config_text)
    return jsonify({"status": "Device created successfully"})

@app.route('/api/devices/<int:device_id>', methods=['DELETE'])
async def delete_device(device_id):
    user_id = get_tg_user_id(request)
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    device = await db.get_device(device_id)
    if not device or device['user_id'] != user_id:
        return jsonify({"error": "Device not found or does not belong to the user"}), 404
    
    server = await db.get_server(device['server_id'])
    client = AmneziaClient(server['api_url'], server['api_key'])
    await client.delete_vpn_profile(device['amnezia_client_id'])
    
    await db.delete_device(device_id)
    return jsonify({"status": "Device deleted successfully"})

@app.route('/api/devices/<int:device_id>/share', methods=['POST'])
async def share_device(device_id):
    user_id = get_tg_user_id(request)
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    device = await db.get_device(device_id)
    if not device or device['user_id'] != user_id:
        return jsonify({"error": "Device not found or does not belong to the user"}), 404
    
    token = str(uuid.uuid4())
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
    
    await db.create_temporary_link(device_id, token, expires_at)
    return jsonify({"share_url": f"{settings.MINIAPP_URL}/share/{token}"})

@app.route('/share/<string:token>', methods=['GET'])
async def download_config(token):
    device = await db.get_device_by_temporary_token(token)
    if not device:
        return "Ссылка истекла или недействительна", 404
    
    config_text = device['config_text']
    response = app.response_class(
        response=config_text,
        status=200,
        mimetype='text/plain'
    )
    response.headers["Content-Disposition"] = f"attachment; filename=device_config.conf"
    return response

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
