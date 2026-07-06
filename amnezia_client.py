import aiohttp
from typing import Dict, Optional

class AmneziaClient:
    def __init__(self, api_url: str, api_key: str):
        if api_url.endswith('/'):
            api_url = api_url[:-1]
        self.api_url = api_url
        self.api_key = api_key

    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def check_status(self) -> Dict[str, object]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/api/v1/status", headers=self._get_headers()) as response:
                    if response.status == 200:
                        return {"online": True, "metrics": await response.json()}
        except Exception:
            pass
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/status", headers=self._get_headers()) as response:
                    if response.status == 200:
                        return {"online": True, "metrics": await response.json()}
        except Exception:
            pass
        return {"online": False, "metrics": {}}

    async def create_vpn_profile(self, client_id: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/api/v1/client", headers=self._get_headers(), json={"client_id": client_id}) as response:
                    if response.status == 200:
                        return await response.text()
        except Exception:
            pass
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/clients", headers=self._get_headers(), json={"client_id": client_id}) as response:
                    if response.status == 200:
                        return await response.text()
        except Exception:
            pass
        return None

    async def delete_vpn_profile(self, client_id: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(f"{self.api_url}/api/v1/client/{client_id}", headers=self._get_headers()) as response:
                    if response.status in (200, 204):
                        return True
        except Exception:
            pass
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(f"{self.api_url}/clients/{client_id}", headers=self._get_headers()) as response:
                    if response.status in (200, 204):
                        return True
        except Exception:
            pass
        return False
