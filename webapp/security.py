import hmac
import hashlib
from urllib.parse import parse_qsl
from functools import wraps
from flask import request, jsonify
# Импортируем настройки из твоего существующего конфига (поправь путь, если он другой)
from config import settings 

def verify_telegram_init_data(init_data: str) -> bool:
    try:
        # Декодируем строку запроса Telegram в словарь
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return False
        
        received_hash = parsed_data.pop("hash")
        
        # Сортируем ключи по алфавиту и соединяем их через символ переноса строки
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # Официальный алгоритм Telegram: ключ генерируется через HMAC от строки "WebAppData"
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(computed_hash, received_hash)
    except Exception:
        return False

def telegram_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Ожидаем строку авторизации в заголовке X-Telegram-Init-Data
        init_data = request.headers.get("X-Telegram-Init-Data")
        if not init_data or not verify_telegram_init_data(init_data):
            return jsonify({"error": "Unauthorized", "message": "Invalid Telegram InitData"}), 403
        return f(*args, **kwargs)
    return decorated
