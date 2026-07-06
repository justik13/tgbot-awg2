from typing import Optional, List


class ServersMixin:
    async def add_server(self, name: str, api_url: str, api_key: str, country_code: str = '', flag: str = '🌐', bandwidth_label: str = ''):
        encrypted_api_key = self._encrypt(api_key)
        await self.connection.execute('''
            INSERT INTO servers (name, api_url, api_key, country_code, flag, bandwidth_label, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (name, api_url, encrypted_api_key, country_code, flag, bandwidth_label))
        await self.connection.commit()

    def _server_from_row(self, row) -> dict:
        server = dict(row)
        server['api_key'] = self._decrypt(server['api_key'])
        return server

    async def get_server(self, server_id: int) -> Optional[dict]:
        cursor = await self.connection.execute('SELECT * FROM servers WHERE id = ?', (server_id,))
        row = await cursor.fetchone()
        return self._server_from_row(row) if row else None

    async def get_active_servers(self) -> List[dict]:
        cursor = await self.connection.execute('SELECT * FROM servers WHERE is_active = 1 ORDER BY name')
        rows = await cursor.fetchall()
        return [self._server_from_row(row) for row in rows]

    async def get_all_servers(self) -> List[dict]:
        cursor = await self.connection.execute('SELECT * FROM servers ORDER BY name')
        rows = await cursor.fetchall()
        return [self._server_from_row(row) for row in rows]

    async def toggle_server_status(self, server_id: int, is_active: int):
        await self.connection.execute('UPDATE servers SET is_active = ? WHERE id = ?', (is_active, server_id))
        await self.connection.commit()

    async def delete_server(self, server_id: int):
        await self.connection.execute('DELETE FROM servers WHERE id = ?', (server_id,))
        await self.connection.commit()
