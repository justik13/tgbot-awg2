from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from database import db
from bot.keyboards import get_tariffs_keyboard, get_payment_methods_keyboard, get_main_menu_keyboard

router = Router()

@router.callback_query(F.data == "buy_subscription")
async def callback_buy_subscription(callback: CallbackQuery):
    await callback.message.edit_text("💳 Выберите тариф:", reply_markup=get_tariffs_keyboard())

@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню", reply_markup=get_main_menu_keyboard())

@router.callback_query(F.data.startswith("tariff_"))
async def callback_choose_tariff(callback: CallbackQuery):
    tariff_days = int(callback.data.split("_")[1])
    await callback.message.edit_text(f"Вы выбрали тариф на {tariff_days} дней. Выберите метод оплаты:", reply_markup=get_payment_methods_keyboard(tariff_days))

@router.callback_query(F.data.startswith("pay_stars_"))
async def callback_pay_stars(callback: CallbackQuery):
    tariff_days = int(callback.data.split("_")[2])
    stars_amounts = {7: 21, 30: 70, 90: 190}
    stars_amount = stars_amounts.get(tariff_days, 0)
    
    await callback.message.answer_invoice(
        title="Подписка VPN",
        description=f"Продление подписки на {tariff_days} дней",
        payload=f"sub_{tariff_days}_{callback.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="⭐️", amount=stars_amount * 100)],
        provider_token=""
    )

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
    subscription_expires_at = updated_user['subscription_expires_at']
    
    await message.answer(
        f"Подписка успешно активирована до {subscription_expires_at}.",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data.startswith("pay_rub_"))
async def callback_pay_rub(callback: CallbackQuery):
    await callback.message.answer("Оплата картой через внешнюю платежку находится в разработке. Используйте Telegram Stars!")
