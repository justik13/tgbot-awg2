import asyncio
from aiogram import Bot, Dispatcher
from config import settings
from database import db
from bot.handlers.start import router

async def main():
    await db.connect()
    await db.init_db()
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    try:
        await dp.start_polling(bot)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
