
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
        order_id = int(call.data.split("_")[2])
    except:
        await call.answer("❌ Ошибка ID заказа")
        return

    result = accept_order_atomic(order_id)

    if result == "not_enough_stock":
        await call.answer("❌ Недостаточно товара")
        return

    if not result:
        await call.answer("⚠️ Заказ уже обработан")
        return

    items = get_order_items(order_id)

    total_text = "📦 Состав заказа:\n\n"
    total_sum = 0

    for item in items:
        total_sum += float(item["total_price"])

        total_text += (
            f"📦 {item['product_name']}\n"
            f"📦 Фасовка: {item['amount']}\n"
            f"🔢 {item['quantity']} × {item['price']} = {item['total_price']} сом\n\n"
        )

    total_text += f"💵 Итого: {result['total_amount']} сом\n"
    total_text += f"📍 Адрес: {result['address']}\n"

    buyer_id = result["buyer_tg"]

    await call.bot.send_message(
        buyer_id,
        "✅ Ваш заказ принят продавцом\n\n" + total_text
    )

    admin_text = (
        f"📝 Заказ #{order_id} принят продавцом\n\n"
        f"🏪 Продавец: {result['seller_shop']}\n"
        f"👤 Покупатель: {result['buyer_shop']}\n\n"
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
    order_id = data.get("order_id")

    if not order_id:
        await message.answer("Ошибка заказа")
        await state.clear()
        return

    reason = message.text.strip()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT * FROM orders
            WHERE id=%s
            FOR UPDATE
        """, (order_id,))

        order = cur.fetchone()

        if not order or order["status"] != "new":
            await message.answer("Заказ уже обработан")
            return

        cur.execute("""
            UPDATE orders
            SET status='отклоненный'
            WHERE id=%s
        """, (order_id,))

        conn.commit()

        buyer_id = order["buyer_tg"]

        await message.bot.send_message(
            buyer_id,
            f"❌ Ваш заказ #{order_id} отклонён\n\nПричина: {reason}"
        )

        await message.answer("✅ Отказ отправлен")

    except Exception as e:
        conn.rollback()
        logging.error(f"❌ decline_order: {e}")
        await message.answer("Ошибка")

    finally:
        cur.close()
        release_connection(conn)
        await state.clear()