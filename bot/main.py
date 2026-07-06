import asyncio
import datetime
import logging
import contextlib
from aiogram import Bot, Dispatcher
from config import settings
from database import db
from bot.handlers.start import router as start_router
from bot.handlers.billing import router as billing_router
from bot.handlers.admin import router as admin_router
from amnezia_client import AmneziaClient

logger = logging.getLogger(__name__)

async def sub_checker_worker():
    logger.info("Фоновый воркер проверки подписок успешно запущен.")
    while True:
        await asyncio.sleep(3600)
        try:
            cutoff_time = (datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(hours=12)).isoformat()
            cursor = await db.connection.execute('''
                SELECT * FROM users WHERE subscription_expires_at IS NOT NULL AND subscription_expires_at < ?
            ''', (cutoff_time,))
            users = await cursor.fetchall()

            if not users:
                continue

            logger.info("Найдено просроченных подписок: %d. Начинаю очистку профилей...", len(users))
            client_cache = {}

            for user in users:
                devices = await db.get_user_devices(user['id'])
                for device in devices:
                    try:
                        server_id = device['server_id']
                        if server_id not in client_cache:
                            server = await db.get_server(server_id)
                            if not server:
                                logger.warning("Сервер ID %s не найден для устройства %s", server_id, device['id'])
                                continue
                            client_cache[server_id] = AmneziaClient(server['api_url'], server['api_key'])
                        
                        client = client_cache[server_id]
                        logger.info("Удаляю просроченный профиль %s для пользователя %s на сервере %s", 
                                    device['amnezia_client_id'], user['id'], server_id)
                        
                        await client.delete_vpn_profile(device['amnezia_client_id'])
                        await db.delete_device(device['id'])
                    except Exception as device_error:
                        logger.error("Ошибка при удалении устройства %s пользователя %s: %s", 
                                     device['id'], user['id'], device_error)

            for client in client_cache.values():
                if client._session and not client._session.closed:
                    await client._session.close()

        except Exception as worker_error:
            logger.error("Критическая ошибка в цикле воркера проверки подписок: %s", worker_error)

async def main():
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await db.connect()
    await db.init_db()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(billing_router)
    dp.include_router(admin_router)

    checker_task = asyncio.create_task(sub_checker_worker())

    try:
        await dp.start_polling(bot)
    finally:
        checker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await checker_task
        await bot.session.close()
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
