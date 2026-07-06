from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import db
from config import settings
from bot.keyboards import get_terms_keyboard, get_main_menu_keyboard
from aiogram.filters import Command

router = Router()

WELCOME_TEXT = (
    "🔐 <b>just1kbot</b>\n\n"
    "Привет! 👋\n\n"
    "Я помогу тебе получить быстрый и безопасный доступ к интернету через защищённые серверы.\n\n"
    "Перед началом необходимо принять пользовательское соглашение."
)

TERMS_TEXT = (
    "📄 <b>Пользовательское соглашение</b>\n\n"
    "Сервис выдаёт персональные VPN-профили для ваших устройств. "
    "Не передавайте конфиги третьим лицам, соблюдайте законы вашей страны и правила сервиса. "
    "Администратор может ограничить доступ при нарушениях или окончании подписки."
)

MENU_TEXT = "🔐 <b>just1kbot</b>\n\nГлавное меню"


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    await db.add_or_update_user(user_id, username, settings.DEFAULT_DEVICE_LIMIT)

    user = await db.get_user(user_id)
    if not user or user['is_accepted_terms'] == 0:
        await message.answer(WELCOME_TEXT, reply_markup=get_terms_keyboard(), parse_mode="HTML")
    else:
        await message.answer(MENU_TEXT, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "read_terms")
async def callback_read_terms(callback: CallbackQuery):
    await callback.message.answer(TERMS_TEXT, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "accept_terms")
async def callback_accept_terms(callback: CallbackQuery):
    await db.accept_terms(callback.from_user.id)
    await callback.message.edit_text(MENU_TEXT, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback.answer("Готово")


@router.callback_query(F.data == "help_menu")
async def callback_help(callback: CallbackQuery):
    await callback.message.answer(
        "📖 <b>Помощь</b>\n\n"
        "1. Купите подписку.\n"
        "2. Откройте Mini App.\n"
        "3. Создайте устройство, выберите сервер и скачайте конфиг.\n\n"
        "Если Telegram недоступен, создайте временную ссылку на устройство — она живёт 1 час.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "tg_proxy")
async def callback_tg_proxy(callback: CallbackQuery):
    await callback.message.answer("🌐 Telegram Proxy будет добавлен после подключения MTProxy-инфраструктуры.")
    await callback.answer()
