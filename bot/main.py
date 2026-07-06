import asyncio
from aiogram import Bot, Dispatcher
from config import settings
from database import db
from bot.handlers.start import router as start_router
from bot.handlers.billing import router as billing_router

async def main():
    await db.connect()
    await db.init_db()
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(billing_router)
    
    try:
        await dp.start_polling(bot)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
