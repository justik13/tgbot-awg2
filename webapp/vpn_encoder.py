import zlib
import base64
import json
import struct

def encode_amnezia_config(config_text: str) -> str:
    # 1. Формируем структуру JSON, которую ожидает AmneziaVPN (обычно это обертка над текстом)
    config_json = {"config": config_text}
    json_str = json.dumps(config_json, separators=(',', ':'))
    data_bytes = json_str.encode('utf-8')
    
    # 2. Заголовок: 4 байта (длина данных)
    header = struct.pack('>I', len(data_bytes))
    
    # 3. Сжатие DEFLATE
    compressed = zlib.compress(data_bytes)
    
    # 4. Сборка пакета
    payload = header + compressed
    
    # 5. Base64URL
    b64 = base64.urlsafe_b64encode(payload).decode('utf-8').replace('=', '')
    return f"vpn://{b64}"
