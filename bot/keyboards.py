from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from config import settings


def get_terms_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📄 Прочитать соглашение", callback_data="read_terms")
    keyboard.button(text="✅ Принять и продолжить", callback_data="accept_terms")
    return keyboard.adjust(1).as_markup()


def get_main_menu_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🌐 Telegram Proxy", callback_data="tg_proxy")
    keyboard.button(text="💳 Купить подписку", callback_data="buy_subscription")
    keyboard.button(text="📖 Помощь", callback_data="help_menu")
    keyboard.button(text="🚀 Открыть приложение", web_app=WebAppInfo(url=settings.MINIAPP_URL))
    return keyboard.adjust(1).as_markup()


def get_tariffs_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="7 дней — 25 руб / 21 ⭐️", callback_data="tariff_7")
    keyboard.button(text="1 мес — 90 руб / 70 ⭐️", callback_data="tariff_30")
    keyboard.button(text="3 мес — 250 руб / 190 ⭐️", callback_data="tariff_90")
    keyboard.button(text="← Назад", callback_data="back_to_menu")
    return keyboard.adjust(1).as_markup()


def get_payment_methods_keyboard(tariff_days: int):
    rub_amounts = {7: 25, 30: 90, 90: 250}
    stars_amounts = {7: 21, 30: 70, 90: 190}
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=f"⭐️ Telegram Stars — {stars_amounts[tariff_days]} ⭐️", callback_data=f"pay_stars_{tariff_days}")
    keyboard.button(text=f"💳 Карта RUB — {rub_amounts[tariff_days]} руб", callback_data=f"pay_rub_{tariff_days}")
    keyboard.button(text="← Назад к тарифам", callback_data="buy_subscription")
    return keyboard.adjust(1).as_markup()
