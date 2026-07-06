from typing import Optional, List

class ServersMixin:
    async def add_server(self, name: str, api_url: str, api_key: str):
        encrypted_api_key = self._encrypt(api_key)
        await self.connection.execute('''
            INSERT INTO servers (name, api_url, api_key, is_active)
            VALUES (?, ?, ?, 1)
        ''', (name, api_url, encrypted_api_key))
        await self.connection.commit()

    async def get_server(self, server_id: int) -> Optional[dict]:
        cursor = await self.connection.execute('SELECT * FROM servers WHERE id = ?', (server_id,))
        row = await cursor.fetchone()
        if row:
            decrypted_api_key = self._decrypt(row['api_key'])
            return {**row, 'api_key': decrypted_api_key}
        return None

    async def get_active_servers(self) -> List[dict]:
        servers = []
        cursor = await self.connection.execute('SELECT * FROM servers WHERE is_active = 1')
        rows = await cursor.fetchall()
        for row in rows:
            decrypted_api_key = self._decrypt(row['api_key'])
            servers.append({**row, 'api_key': decrypted_api_key})
        return servers

    async def get_all_servers(self) -> List[dict]:
        servers = []
        cursor = await self.connection.execute('SELECT * FROM servers')
        rows = await cursor.fetchall()
        for row in rows:
            decrypted_api_key = self._decrypt(row['api_key'])
            servers.append({**row, 'api_key': decrypted_api_key})
        return servers

    async def toggle_server_status(self, server_id: int, is_active: int):
        await self.connection.execute('''
            UPDATE servers
            SET is_active = ?
            WHERE id = ?
        ''', (is_active, server_id))
        await self.connection.commit()

    async def delete_server(self, server_id: int):
        await self.connection.execute('''
            DELETE FROM servers
            WHERE id = ?
        ''', (server_id,))
        await self.connection.commit()
