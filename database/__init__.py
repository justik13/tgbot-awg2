from config import settings
from .core import DatabaseCore
from .users import UsersMixin
from .servers import ServersMixin
from .devices import DevicesMixin

class Database(DatabaseCore, UsersMixin, ServersMixin, DevicesMixin):
    pass

db = Database(db_path=settings.DB_PATH, encryption_key=settings.DB_ENCRYPTION_KEY)
