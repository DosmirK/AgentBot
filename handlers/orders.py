
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID 
from states import DeclineState
from database import *


router = Router()


# ---------------- ПРИНЯТЬ ЗАКАЗ ----------------

@router.callback_query(F.data.startswith("order_ok_"))
async def order_accept(call: CallbackQuery):

    try:
        ids_part = call.data.split("_")[2]
        order_ids = [int(x) for x in ids_part.split(",")]
    except:
        await call.answer("❌ Ошибка ID заказа")
        return

    total_text = "📦 Состав заказа:\n\n"
    buyer_id = None
    seller_id = None
    address = None
    total_sum = 0

    for order_id in order_ids:

        order = get_order(order_id)
        if not order:
            continue

        if order["status"] != "new":
            await call.answer("⚠️ Заказ уже обработан")
            return

        buyer_id = order["buyer_tg"]
        seller_id = order["seller_id"]
        product_id = order["product_id"]
        amount = int(order["amount"])
        address = order["address"]

        product = get_product(product_id)
        if not product:
            continue

        current_stock = int(product["stock"])
        if current_stock < amount:
            await call.bot.send_message(
                buyer_id,
                f"❌ Недостаточно товара:\n"
                f"{product['name']}\n\n"
                f"Доступно: {current_stock} шт"
            )

            update_order_status(order_id, "declined")
            continue

        price = float(product["price"])
        cost = price * amount
        total_sum += cost

        updated = decrease_stock(product_id, amount)

        if updated:
            new_stock = int(updated["stock"])
            product_name = updated["name"]

            if new_stock <= 5:
                warning_text = (
                    f"⚠️ Товар заканчивается!\n\n"
                    f"📦 {product_name}\n"
                    f"📊 Остаток: {new_stock} шт"
                )

                await call.bot.send_message(
                    seller_id,  
                    warning_text
                )

        update_order_status(order_id, "accepted")

        total_text += (
            f"📦 {product['name']}\n"
            f"🔢 {amount} × {price} = {cost} сом\n\n"
        )

    if total_sum == 0:
        await call.answer("❌ Заказ не может быть обработан")
        return

    total_text += f"💵 Итого: {total_sum} сом\n"
    total_text += f"📍 Адрес: {address}\n"

    # ------------------ ПОКУПАТЕЛЬ ------------------

    if buyer_id:
        await call.bot.send_message(
            buyer_id,
            "✅ Ваш заказ принят продавцом\n\n" + total_text
        )

    # ------------------ АДМИН ------------------

    if seller_id:
        admin_text = (
            f"📝 Заказ принят продавцом\n\n"
            f"🏪 Продавец: {seller_id}\n"
            f"👤 Покупатель: {buyer_id}\n\n"
            + total_text
        )

        await call.bot.send_message(
            ADMIN_ID,
            admin_text
        )

    await call.message.edit_reply_markup(reply_markup=None)

    await call.message.edit_text(
        call.message.text + "\n\n✅ Заказ принят"
    )

    await call.answer("Принято ✅")


# ---------------- ОТКЛОНЕНИЕ ----------------

@router.callback_query(F.data.startswith("order_no_"))
async def order_decline(call: CallbackQuery, state: FSMContext):

    try:
        order_id = int(call.data.split("_")[2])
    except:
        await call.answer("Ошибка")
        return

    await state.update_data(order_id=order_id)

    await call.message.answer("Причина отказа:")

    await state.set_state(DeclineState.reason)

    await call.answer()


@router.message(DeclineState.reason)
async def save_decline(message: Message, state: FSMContext):

    data = await state.get_data()

    order_id = data["order_id"]

    reason = message.text.strip()

    update_order_status(order_id, "declined")

    buyer = get_buyer_by_order(order_id)

    if buyer:

        await message.bot.send_message(
            buyer[0],
            f"❌ Ваш заказ #{order_id} отклонён\nПричина: {reason}"
        )

    await message.answer("✅ Отказ отправлен")

    await state.clear()