from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import db
from config import settings
from bot.keyboards import get_terms_keyboard, get_main_menu_keyboard
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    await db.add_or_update_user(user_id, username, settings.DEFAULT_DEVICE_LIMIT)
    
    user = await db.get_user(user_id)
    if not user or user['is_accepted_terms'] == 0:
        await message.answer(
            "Я помогу тебе получить быстрый и безопасный доступ... Перед началом необходимо принять соглашение.",
            reply_markup=get_terms_keyboard()
        )
    else:
        await message.answer("Главное меню", reply_markup=get_main_menu_keyboard())

@router.callback_query(F.data == "read_terms")
async def callback_read_terms(callback: CallbackQuery):
    await callback.message.answer(
        "Текст пользовательского соглашения..."
    )

@router.callback_query(F.data == "accept_terms")
async def callback_accept_terms(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.accept_terms(user_id)
    await callback.message.edit_text("Главное меню", reply_markup=get_main_menu_keyboard())
