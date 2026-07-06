import aiosqlite
from cryptography.fernet import Fernet


class DatabaseCore:
    def __init__(self, db_path: str, encryption_key: str):
        self.db_path = db_path
        self.encryption_key = encryption_key.encode('utf-8')
        self.cipher_suite = Fernet(self.encryption_key)
        self.connection = None

    def _encrypt(self, text: str) -> str:
        if not text:
            return text
        return self.cipher_suite.encrypt(text.encode('utf-8')).decode('utf-8')

    def _decrypt(self, text: str) -> str:
        if not text:
            return text
        return self.cipher_suite.decrypt(text.encode('utf-8')).decode('utf-8')

    async def connect(self):
        self.connection = await aiosqlite.connect(self.db_path)
        await self.connection.execute("PRAGMA foreign_keys = ON;")
        await self.connection.execute("PRAGMA journal_mode=WAL;")
        await self.connection.execute("PRAGMA synchronous=NORMAL;")
        self.connection.row_factory = aiosqlite.Row

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

    async def init_db(self):
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                is_accepted_terms INTEGER DEFAULT 0,
                subscription_expires_at TEXT DEFAULT NULL,
                device_limit INTEGER,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                api_url TEXT,
                api_key TEXT,
                country_code TEXT DEFAULT '',
                flag TEXT DEFAULT '🌐',
                bandwidth_label TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1
            )
        ''')
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                server_id INTEGER,
                name TEXT,
                amnezia_client_id TEXT,
                config_text TEXT,
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE
            )
        ''')
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS temporary_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                token TEXT UNIQUE,
                expires_at TEXT,
                FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
            )
        ''')
        await self._ensure_column("servers", "country_code", "TEXT DEFAULT ''")
        await self._ensure_column("servers", "flag", "TEXT DEFAULT '🌐'")
        await self._ensure_column("servers", "bandwidth_label", "TEXT DEFAULT ''")
        await self.connection.commit()

    async def _ensure_column(self, table: str, column: str, definition: str):
        cursor = await self.connection.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in await cursor.fetchall()]
        if column not in columns:
            await self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
