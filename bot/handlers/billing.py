import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from database import db
from bot.keyboards import get_tariffs_keyboard, get_payment_methods_keyboard, get_main_menu_keyboard
from config import settings

router = Router()

TARIFFS = {
    7: {"label": "7 дней", "rub": 25, "stars": 21},
    30: {"label": "1 месяц", "rub": 90, "stars": 70},
    90: {"label": "3 месяца", "rub": 250, "stars": 190},
}


def format_expiry(value: str | None) -> str:
    if not value:
        return "—"
    return datetime.datetime.fromisoformat(value).strftime("%d.%m.%Y")


@router.callback_query(F.data == "buy_subscription")
async def callback_buy_subscription(callback: CallbackQuery):
    await callback.message.edit_text(
        "💳 <b>Выберите тариф</b>\n\n"
        "7 дней — 25 руб / 21 ⭐️\n"
        "1 месяц — 90 руб / 70 ⭐️\n"
        "3 месяца — 250 руб / 190 ⭐️",
        reply_markup=get_tariffs_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("🔐 <b>just1kbot</b>\n\nГлавное меню", reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_"))
async def callback_choose_tariff(callback: CallbackQuery):
    tariff_days = int(callback.data.split("_")[1])
    tariff = TARIFFS[tariff_days]
    await callback.message.edit_text(
        f"🧾 <b>Ваш заказ</b>\n\n"
        f"Тариф: {tariff['label']}\n"
        f"Стоимость: {tariff['rub']} руб или {tariff['stars']} ⭐️\n\n"
        f"Итого: {tariff['rub']} руб",
        reply_markup=get_payment_methods_keyboard(tariff_days),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars_"))
async def callback_pay_stars(callback: CallbackQuery):
    tariff_days = int(callback.data.split("_")[2])
    tariff = TARIFFS[tariff_days]
    await callback.message.answer_invoice(
        title="Подписка just1kbot",
        description=f"Продление подписки: {tariff['label']}",
        payload=f"sub_{tariff_days}_{callback.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Telegram Stars", amount=tariff["stars"])],
        provider_token="",
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    days = int(payload.split("_")[1])
    user_id = int(payload.split("_")[2])

    await db.update_subscription(user_id, days)
    updated_user = await db.get_user(user_id)
    subscription_expires_at = format_expiry(updated_user['subscription_expires_at'])
    tariff = TARIFFS[days]

    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"Подписка активна до: {subscription_expires_at}\n"
        f"Тариф: {tariff['label']}\n\n"
        "Теперь вы можете создавать профили для ваших устройств на разных серверах.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("pay_rub_"))
async def callback_pay_rub(callback: CallbackQuery):
    if callback.from_user.id in settings.ADMIN_IDS:
        days = int(callback.data.split("_")[2])
        await db.update_subscription(callback.from_user.id, days)
        user = await db.get_user(callback.from_user.id)
        await callback.message.edit_text(
            f"✅ Тестовая RUB-оплата зачтена. Подписка активна до: {format_expiry(user['subscription_expires_at'])}",
            reply_markup=get_main_menu_keyboard(),
        )
    else:
        await callback.message.answer("💳 Оплата картой через Platega/эквайринг будет подключена после выдачи боевых ключей. Сейчас используйте Telegram Stars.")
    await callback.answer()
