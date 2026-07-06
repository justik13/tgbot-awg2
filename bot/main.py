import asyncio
from aiogram import Bot, Dispatcher
from config import settings
from database import db
from bot.handlers.start import router as start_router
from bot.handlers.billing import router as billing_router
from bot.handlers.admin import router as admin_router
import datetime
from amnezia_client import AmneziaClient

async def sub_checker_worker():
    while True:
        await asyncio.sleep(3600)
        
        cursor = await db.connection.execute('''
            SELECT * FROM users WHERE subscription_expires_at IS NOT NULL AND subscription_expires_at < ?
        ''', ((datetime.datetime.now() - datetime.timedelta(hours=12)).isoformat(),))
        users = await cursor.fetchall()
        
        for user in users:
            devices = await db.get_user_devices(user['id'])
            for device in devices:
                server = await db.get_server(device['server_id'])
                client = AmneziaClient(server['api_url'], server['api_key'])
                await client.delete_vpn_profile(device['amnezia_client_id'])
                await db.delete_device(device['id'])

async def main():
    await db.connect()
    await db.init_db()
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(billing_router)
    dp.include_router(admin_router)
    
    asyncio.create_task(sub_checker_worker())
    
    try:
        await dp.start_polling(bot)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
