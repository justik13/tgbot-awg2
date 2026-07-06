from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from config import settings

def get_terms_keyboard() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📄 Прочитать соглашение", callback_data="read_terms")
    keyboard.button(text="✅ Принять и продолжить", callback_data="accept_terms")
    return keyboard.as_markup()

def get_main_menu_keyboard() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🌐 Telegram Proxy", callback_data="tg_proxy")
    keyboard.button(text="💳 Купить подписку", callback_data="buy_subscription")
    keyboard.button(text="📖 Помощь", callback_data="help_menu")
    keyboard.button(text="🚀 Открыть приложение", web_app=WebAppInfo(url=settings.MINIAPP_URL))
    return keyboard.as_markup()
