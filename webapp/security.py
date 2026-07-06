import hashlib
import hmac
import json
import time
from functools import wraps
from urllib.parse import parse_qsl

from flask import g, jsonify, request

from config import settings

MAX_INIT_DATA_AGE_SECONDS = 24 * 60 * 60


def parse_telegram_init_data(init_data: str) -> dict | None:
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        auth_date = int(parsed_data.get("auth_date", "0"))
        if auth_date <= 0 or time.time() - auth_date > MAX_INIT_DATA_AGE_SECONDS:
            return None

        user_raw = parsed_data.get("user")
        if user_raw:
            parsed_data["user"] = json.loads(user_raw)
        return parsed_data
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify_telegram_init_data(init_data: str) -> bool:
    return parse_telegram_init_data(init_data) is not None


def telegram_auth_required(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data")
        auth_data = parse_telegram_init_data(init_data) if init_data else None
        user = auth_data.get("user") if auth_data else None
        if not isinstance(user, dict) or not user.get("id"):
            return jsonify({"error": "Unauthorized", "message": "Invalid Telegram InitData"}), 403
        g.telegram_user = user
        g.telegram_init_data = auth_data
        return await f(*args, **kwargs)

    return decorated
