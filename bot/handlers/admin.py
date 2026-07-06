from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from database import db
from config import settings
from amnezia_client import AmneziaClient
from aiogram.filters.command import Command
import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(Command("admin"))
async def cmd_admin(message: Message, bot: Bot):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("У вас нет доступа к админке.")
        return

    cursor = await db.connection.execute('SELECT COUNT(*) FROM users')
    row = await cursor.fetchone()
    user_count = row[0] if row else 0

    cursor = await db.connection.execute('''
        SELECT COUNT(*) FROM users WHERE subscription_expires_at IS NOT NULL AND subscription_expires_at > ?
    ''', (datetime.datetime.now().isoformat(),))
    row = await cursor.fetchone()
    active_subscriptions_count = row[0] if row else 0

    cursor = await db.connection.execute('SELECT COUNT(*) FROM devices')
    row = await cursor.fetchone()
    total_devices_count = row[0] if row else 0

    admin_text = (
        f"Админка\n"
        f"Количество пользователей: {user_count}\n"
        f"Количество активных подписок: {active_subscriptions_count}\n"
        f"Общее количество устройств: {total_devices_count}"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🖥 Управление серверами", callback_data="admin_servers")
    await message.answer(admin_text, reply_markup=keyboard.as_markup())

@router.callback_query(F.data == "admin_servers")
async def callback_admin_servers(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("У вас нет доступа к админке.")
        return
    
    servers = await db.get_all_servers()
    keyboard = InlineKeyboardBuilder()
    
    for server in servers:
        server_status = await AmneziaClient(server['api_url'], server['api_key']).check_status()
        status = "online" if server_status['online'] else "offline"
        keyboard.button(text=f"{server['name']} ({status})", callback_data=f"admin_server_{server['id']}")
    
    keyboard.button(text="➕ Добавить сервер", callback_data="add_server")
    await callback.message.edit_text("Управление серверами", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("admin_server_"))
async def callback_admin_server(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("У вас нет доступа к админке.")
        return
    
    server_id = int(callback.data.split('_')[2])
    server = await db.get_server(server_id)
    
    server_status = await AmneziaClient(server['api_url'], server['api_key']).check_status()
    status = "online" if server_status['online'] else "offline"
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Вкл/Выкл", callback_data=f"toggle_server_{server_id}")
    keyboard.button(text="Удалить", callback_data=f"delete_server_{server_id}")
    
    await callback.message.edit_text(f"{server['name']} ({status})", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("toggle_server_"))
async def callback_toggle_server(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("У вас нет доступа к админке.")
        return
    
    server_id = int(callback.data.split('_')[2])
    server = await db.get_server(server_id)
    is_active = 1 - server['is_active']
    await db.toggle_server_status(server_id, is_active)
    
    await callback.message.answer("Статус сервера изменен.")

@router.callback_query(F.data.startswith("delete_server_"))
async def callback_delete_server(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("У вас нет доступа к админке.")
        return
    
    server_id = int(callback.data.split('_')[2])
    await db.delete_server(server_id)
    
    await callback.message.answer("Сервер удален.")

@router.callback_query(F.data == "add_server")
async def callback_add_server(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("У вас нет доступа к админке.")
        return
    
    await callback.message.answer("Введите данные сервера в формате: Имя|API_URL|API_KEY|Флаг|Канал (последние два поля можно не указывать)")

@router.message(F.text)
async def handle_add_server(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("У вас нет доступа к админке.")
        return
    
    parts = message.text.split('|')
    if len(parts) not in (3, 5):
        await message.answer("Неверный формат. Попробуйте снова.")
        return

    name, api_url, api_key = [part.strip() for part in parts[:3]]
    flag = parts[3].strip() if len(parts) == 5 else '🌐'
    bandwidth_label = parts[4].strip() if len(parts) == 5 else ''
    await db.add_server(name, api_url, api_key, flag=flag, bandwidth_label=bandwidth_label)
    
    await message.answer("Сервер успешно добавлен!")
