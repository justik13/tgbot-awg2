import datetime
from typing import Optional
from config import settings

class UsersMixin:
    async def add_or_update_user(self, user_id: int, username: str, default_limit: int, is_admin: int = 0):
        if user_id in settings.ADMIN_IDS:
            is_admin = 1
        await self.connection.execute('''
            INSERT OR IGNORE INTO users (id, username, device_limit, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, default_limit, is_admin))
        await self.connection.execute('''
            UPDATE users
            SET username = ?
            WHERE id = ?
        ''', (username, user_id))
        await self.connection.commit()

    async def get_user(self, user_id: int) -> Optional[dict]:
        cursor = await self.connection.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def accept_terms(self, user_id: int):
        await self.connection.execute('''
            UPDATE users
            SET is_accepted_terms = 1
            WHERE id = ?
        ''', (user_id,))
        await self.connection.commit()

    async def update_subscription(self, user_id: int, days: int):
        cursor = await self.connection.execute('SELECT subscription_expires_at FROM users WHERE id = ?', (user_id,))
        row = await cursor.fetchone()
        if row and row['subscription_expires_at']:
            current_date = datetime.datetime.fromisoformat(row['subscription_expires_at'])
        else:
            current_date = datetime.datetime.now()

        new_expiry_date = current_date + datetime.timedelta(days=days)
        await self.connection.execute('''
            UPDATE users
            SET subscription_expires_at = ?
            WHERE id = ?
        ''', (new_expiry_date.isoformat(), user_id))
        await self.connection.commit()

    async def set_custom_device_limit(self, user_id: int, new_limit: int):
        if user_id in settings.ADMIN_IDS:
            await self.connection.execute('''
                UPDATE users
                SET device_limit = ?
                WHERE id = ?
            ''', (new_limit, user_id))
            await self.connection.commit()
