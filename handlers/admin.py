import logging

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_ID

from database import (
    get_seller,
    add_seller,
    activate_seller,
    deactivate_seller,
    get_all_sellers,
    get_all_buyers,
    delete_seller_full,
    restore_seller
)


router = Router()


# ---------------- ALLOW ----------------

@router.message(Command("allow"))
async def allow_seller(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        tg_id = int(message.text.split()[1])
    except:
        await message.answer("Пример: /allow 123456789")
        return

    try:

        if not get_seller(tg_id):
            add_seller(tg_id)

        activate_seller(tg_id)

        await message.answer("✅ Доступ выдан")

        await message.bot.send_message(
            tg_id,
            "✅ Вам открыт доступ продавца.\nНажмите «🏪 Фирма»"
        )

    except Exception as e:
        logging.error(f"allow error: {e}")


# ---------------- BAN ----------------

@router.message(Command("ban"))
async def ban_seller(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        tg_id = int(message.text.split()[1])
    except:
        await message.answer("Пример: /ban 123456789")
        return

    deactivate_seller(tg_id)

    await message.answer("⛔ Доступ отключён")

    try:
        await message.bot.send_message(
            tg_id,
            "⛔ Ваша подписка отключена"
        )
    except:
        pass


# ---------------- SELLERS ----------------

@router.message(Command("sellers"))
async def admin_sellers(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sellers = get_all_sellers()

    if not sellers:
        await message.answer("❌ Продавцов нет")
        return

    text = "🏪 Фирмы:\n\n"

    for s in sellers:

        tg_id = s["tg_id"]
        name = s["shop_name"]
        active = "✅" if s["is_active"] == 1 else "⛔"

        text += (
            f"{active} {name}\n"
            f"ID: {tg_id}\n\n"
        )

    await message.answer(text)


# ---------------- DELETE SELLER ----------------

@router.message(Command("delete_seller"))
async def delete_seller_command(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        tg_id = int(message.text.split()[1])
    except:
        await message.answer("Пример: /delete_seller 123456789")
        return

    success = delete_seller_full(tg_id)

    if not success:
        await message.answer("❌ Фирма не найдена или ошибка")
        return

    await message.answer("🗑 Фирма и все её данные удалены")

    try:
        await message.bot.send_message(
            tg_id,
            "🗑 Ваша фирма была удалена администратором"
        )
    except:
        pass


@router.message(Command("restore_seller"))
async def restore_seller_command(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        tg_id = int(message.text.split()[1])
    except:
        await message.answer("Пример: /restore_seller 123456789")
        return

    success = restore_seller(tg_id)

    if not success:
        await message.answer("❌ Фирма не найдена или ошибка")
        return

    await message.answer("✅ Фирма восстановлена")

    try:
        await message.bot.send_message(
            tg_id,
            "✅ Ваша фирма была восстановлена администратором"
        )
    except:
        pass

# ---------------- BUYERS ----------------

@router.message(Command("buyers"))
async def admin_buyers(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    buyers = get_all_buyers()

    if not buyers:
        await message.answer("❌ Покупателей нет")
        return

    text = "🛒 Покупатели:\n\n"

    for b in buyers:
        text += (
            f"👤 {b['shop_name']}\n"
            f"🆔 {b['tg_id']}\n"
            f"📍 {b['address']}\n\n"
        )

    await message.answer(text)