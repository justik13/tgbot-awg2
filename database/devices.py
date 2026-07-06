from typing import Optional, List
import datetime


class DevicesMixin:
    async def add_device(self, user_id: int, server_id: int, name: str, amnezia_client_id: str, config_text: str) -> int:
        encrypted_config_text = self._encrypt(config_text)
        created_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        cursor = await self.connection.execute('''
            INSERT INTO devices (user_id, server_id, name, amnezia_client_id, config_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, server_id, name, amnezia_client_id, encrypted_config_text, created_at))
        await self.connection.commit()
        return cursor.lastrowid

    async def _device_from_row(self, row) -> dict:
        device = dict(row)
        device['config_text'] = self._decrypt(device['config_text'])
        return device

    async def get_device(self, device_id: int) -> Optional[dict]:
        cursor = await self.connection.execute('''
            SELECT d.*, s.name AS server_name, s.flag AS server_flag, s.bandwidth_label AS server_bandwidth
            FROM devices d
            LEFT JOIN servers s ON s.id = d.server_id
            WHERE d.id = ?
        ''', (device_id,))
        row = await cursor.fetchone()
        return await self._device_from_row(row) if row else None

    async def get_user_devices(self, user_id: int) -> List[dict]:
        cursor = await self.connection.execute('''
            SELECT d.*, s.name AS server_name, s.flag AS server_flag, s.bandwidth_label AS server_bandwidth
            FROM devices d
            LEFT JOIN servers s ON s.id = d.server_id
            WHERE d.user_id = ?
            ORDER BY d.created_at DESC
        ''', (user_id,))
        rows = await cursor.fetchall()
        return [await self._device_from_row(row) for row in rows]

    async def get_user_devices_count(self, user_id: int) -> int:
        cursor = await self.connection.execute('SELECT COUNT(*) FROM devices WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def rename_device(self, device_id: int, name: str):
        await self.connection.execute('UPDATE devices SET name = ? WHERE id = ?', (name, device_id))
        await self.connection.commit()

    async def delete_device(self, device_id: int):
        await self.connection.execute('DELETE FROM devices WHERE id = ?', (device_id,))
        await self.connection.commit()

    async def create_temporary_link(self, device_id: int, token: str, expires_at: str):
        await self.connection.execute('DELETE FROM temporary_links WHERE device_id = ? OR expires_at <= ?', (device_id, datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()))
        await self.connection.execute('''
            INSERT INTO temporary_links (device_id, token, expires_at)
            VALUES (?, ?, ?)
        ''', (device_id, token, expires_at))
        await self.connection.commit()

    async def get_device_by_temporary_token(self, token: str) -> Optional[dict]:
        cursor = await self.connection.execute('SELECT * FROM temporary_links WHERE token = ?', (token,))
        row = await cursor.fetchone()
        if not row:
            return None
        expires_at = datetime.datetime.fromisoformat(row['expires_at'])
        if expires_at <= datetime.datetime.now(datetime.UTC).replace(tzinfo=None):
            return None
        return await self.get_device(row['device_id'])
