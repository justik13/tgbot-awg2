import logging
import asyncio
from typing import Optional, Any, Dict
import aiohttp

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)
MAX_RETRIES = 3
RETRY_DELAY = 1.5

class AmneziaClient:
    def __init__(self, base_url: str, api_key: str, protocol: str = "amneziawg2"):
        self.base_url = base_url.rstrip("/")
        self.api_key  = api_key
        self.protocol = protocol
        self._session = None

    def _get_headers(self) -> dict:
        return {
            "X-API-Key":    self.api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        loop_mismatch = False
        if self._session and not self._session.closed:
            session_loop = getattr(self._session, '_loop', None)
            if session_loop and (session_loop.is_closed() or session_loop != current_loop):
                loop_mismatch = True

        if self._session is None or self._session.closed or loop_mismatch:
            connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(
                headers=self._get_headers(),
                timeout=REQUEST_TIMEOUT,
                connector=connector,
            )
        return self._session

    async def _request(self, method: str, path: str, **kwargs) -> Optional[Any]:
        url = f"{self.base_url}{path}"
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                session = await self._get_session()
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status in (200, 201, 204):
                        if method == "DELETE" or resp.status == 204:
                            return True
                        ct = resp.headers.get("Content-Type", "")
                        return await resp.json() if "application/json" in ct else await resp.read()
                    
                    text = await resp.text()
                    logger.warning("API %s %s → %d: %s (попытка %d/%d)",
                                   method, path, resp.status, text[:300], attempt, MAX_RETRIES)
                    if resp.status < 500:
                        return None
            except aiohttp.ClientConnectorError as e:
                logger.error("Не удалось подключиться: %s (попытка %d/%d)", e, attempt, MAX_RETRIES)
            except asyncio.TimeoutError:
                logger.error("Таймаут (попытка %d/%d)", attempt, MAX_RETRIES)
            except Exception as e:
                logger.error("Ошибка API: %s (попытка %d/%d)", e, attempt, MAX_RETRIES)

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
        return None

    async def get_all_clients(self) -> Optional[dict]:
        return await self._request("GET", "/clients")

    async def create_user(self, client_name: str) -> Optional[dict]:
        payload = {"clientName": client_name, "protocol": self.protocol}
        logger.info("Создаю клиента: %s (%s)", client_name, self.protocol)
        result = await self._request("POST", "/clients", json=payload)
        return result

    async def update_user(self, client_id: str, **kwargs) -> bool:
        payload = {"clientId": client_id, **kwargs}
        result  = await self._request("PATCH", "/clients", json=payload)
        return result is not None

    async def delete_user(self, client_id: str) -> bool:
        payload = {"clientId": client_id, "protocol": self.protocol}
        result  = await self._request("DELETE", "/clients", json=payload)
        return result is not None

    async def get_client_config(self, username_or_id: str) -> Optional[str]:
        clients = await self.get_all_clients()
        if clients and isinstance(clients, dict):
            for item in clients.get("items", []):
                if item.get("username") == username_or_id or item.get("id") == username_or_id:
                    for peer in item.get("peers", []):
                        if peer.get("config"):
                            return peer["config"]

        session = await self._get_session()
        for path in (f"/clients/{username_or_id}/config", f"/clients/{username_or_id}"):
            try:
                async with session.get(f"{self.base_url}{path}") as resp:
                    if resp.status == 200:
                        ct = resp.headers.get("Content-Type", "")
                        if "application/json" in ct:
                            data = await resp.json()
                            return data.get("config") or data.get("client", {}).get("config")
                        raw_data = await resp.read()
                        return raw_data.decode("utf-8", errors="replace")
            except Exception as e:
                logger.debug("Fallback %s: %s", path, e)
        return None

    async def get_server_info(self) -> Optional[dict]:
        return await self._request("GET", "/server")

    async def get_server_load(self) -> Optional[dict]:
        return await self._request("GET", "/server/load")

    async def check_status(self) -> Dict[str, object]:
        info = await self.get_server_info()
        if info is not None:
            return {"online": True, "metrics": info if isinstance(info, dict) else {}}
        load = await self.get_server_load()
        if load is not None:
            return {"online": True, "metrics": load if isinstance(load, dict) else {}}
        return {"online": False, "metrics": {}}

    async def create_vpn_profile(self, client_id: str) -> Optional[str]:
        res = await self.create_user(client_id)
        if not res:
            return None
        if isinstance(res, dict):
            if "config" in res:
                return res["config"]
            if "client" in res and "config" in res["client"]:
                return res["client"]["config"]
        return await self.get_client_config(client_id)

    async def delete_vpn_profile(self, client_id: str) -> bool:
        return await self.delete_user(client_id)

    async def get_native_qr(self, config_text: str) -> Optional[dict]:
        logger.info("Запрашиваю официальную серию QR-кодов у amnezia-api")
        return await self._request("POST", "/clients/qr", json={"config": config_text})
