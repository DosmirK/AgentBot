import asyncio
import logging
from functools import wraps

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, TOKEN
from db import *
from keyboards import *
from states import SellerRegister, AddProduct, OrderState, DeclineState 

# ---------------- ЛОГИ ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------- INIT ----------------
bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------------- ПРОВЕРКА ПРОДАВЦА ----------------
def is_active_seller(tg_id: int) -> bool:
    seller = get_seller(tg_id)
    return seller and seller[3] == 1

def seller_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, state: FSMContext, *args, **kwargs):
        if not is_active_seller(message.from_user.id):
            await message.answer("⛔ Ваша подписка не активна.")
            return
        return await handler(message, state, *args, **kwargs)
    return wrapper

# ---------------- АДМИН ----------------
@dp.message(Command("allow"))
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
        await bot.send_message(tg_id, "✅ Вам открыт доступ продавца.\nНажмите «🏪 Продавец»")
    except Exception as e:
        logging.error(f"allow error: {e}")

@dp.message(Command("ban"))
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
        await bot.send_message(tg_id, "⛔ Ваша подписка отключена")
    except:
        pass

# ---------------- START ----------------
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Кто вы?", reply_markup=role_kb())

# ---------------- ПОКУПАТЕЛЬ ----------------
@dp.message(F.text == "🛒 Покупатель")
async def buyer_start(message: Message):
    await message.answer("Выберите магазин:", reply_markup=buyer_menu_kb())

@dp.message(F.text == "📋 Список магазинов")
async def show_shops(message: Message):
    shops = get_all_shops()
    if not shops:
        await message.answer("❌ Магазинов нет")
        return
    await message.answer("🏪 Выберите магазин:", reply_markup=shops_kb(shops))

@dp.callback_query(F.data.startswith("shop_"))
async def choose_shop(call: CallbackQuery):
    try:
        shop_id = int(call.data.split("_")[1])
    except:
        await call.answer("Ошибка")
        return

    products = get_products_by_shop(shop_id)
    if not products:
        await call.message.answer("❌ Нет товаров")
        await call.answer()
        return

    await call.message.answer("📦 Выберите товар:", reply_markup=products_kb(products))
    await call.answer()

@dp.callback_query(F.data.startswith("product_"))
async def choose_product(call: CallbackQuery, state: FSMContext):
    try:
        product_id = int(call.data.split("_")[1])
    except:
        await call.answer("Ошибка")
        return

    await state.update_data(product_id=product_id)
    await call.message.answer("Введите количество:")
    await state.set_state(OrderState.amount)
    await call.answer()

# ---------------- ЗАКАЗ ----------------
@dp.message(OrderState.amount)
async def order_amount(message: Message, state: FSMContext):
    text = message.text.replace(",", ".")
    try:
        amount = float(text)
    except:
        await message.answer("Введите число")
        return
    if amount <= 0:
        await message.answer("Количество должно быть больше 0")
        return
    await state.update_data(amount=amount)
    await message.answer("Введите адрес:")
    await state.set_state(OrderState.address)

@dp.message(OrderState.address)
async def order_address(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Адрес слишком короткий")
        return

    await state.update_data(address=address)
    data = await state.get_data()
    product = get_product(data["product_id"])
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return

    seller = get_seller_by_id(product[1])
    seller_name = seller[2] if seller else "Неизвестно"
    total = float(product[4]) * data["amount"]

    text = f""" 
📝 Проверьте заказ: 
🏪 Магазин: {seller_name} 
📦 Товар: {product[2]} 
📊 Фасовка: {product[3]} 
🔢 Кол-во: {int(data['amount'])}
📍 Адрес: {address} 
💰 Цена: {product[4]} сом 
💵 Итого: {total} сом """
    await message.answer(text, reply_markup=order_confirm_buyer_kb())
    await state.set_state(OrderState.confirm)

@dp.callback_query(F.data == "buyer_confirm_yes", OrderState.confirm)
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product = get_product(data["product_id"])
    if not product:
        await call.message.answer("❌ Ошибка товара")
        await state.clear()
        return

    order_id = create_order(
        call.from_user.id,
        product[1],
        product[0],
        data["amount"],
        data["address"]
    )

    if not order_id:
        await call.message.answer("❌ Ошибка заказа")
        return

    seller = get_seller_by_id(product[1])
    seller_name = seller[2] if seller else "Неизвестно"

    if seller:
        total = float(product[4]) * data["amount"]
        text = f""" 
📥 Новый заказ #{order_id} 
🏪 Магазин: {seller_name} 
📦 Товар: {product[2]} 
📊 фасовка: {product[3]} 
🔢 Кол-во: {int(data['amount'])}
📍 Адрес доставки: {data['address']} 
💰 Цена: {product[4]} сом 
💵 Итого: {total} сом 
👤 Покупатель: {call.from_user.full_name} """
        await bot.send_message(seller[1], text, reply_markup=order_confirm_kb(order_id))

    await call.message.answer(f"✅ Заказ #{order_id} отправлен")
    await state.clear()
    await call.answer()

@dp.callback_query(F.data == "buyer_confirm_no", OrderState.confirm)
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("❌ Заказ отменён")
    await state.clear()
    await call.answer()

# ---------------- ПРОДАВЕЦ ----------------
@dp.message(F.text == "🏪 Продавец")
async def seller_start(message: Message, state: FSMContext):
    await state.clear()
    seller = get_seller(message.from_user.id)

    if not seller:
        add_seller(message.from_user.id)
        await message.answer("🔒 Доступ платный")
        await bot.send_message(ADMIN_ID, f"Запрос: {message.from_user.id}")
        return

    if seller[3] == 0:
        await message.answer("⛔ Подписка не активна")
        return

    if not seller[2]:
        await message.answer("Введите название магазина:")
        await state.set_state(SellerRegister.shop_name)
        return

    await message.answer("Меню:", reply_markup=seller_menu())

@dp.message(SellerRegister.shop_name)
async def save_shop(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Слишком короткое")
        return
    set_shop_name(message.from_user.id, name)
    await message.answer("✅ Готово. Магазин создан!", reply_markup=seller_menu())
    await state.clear()

# ---------------- ТОВАРЫ ----------------
@dp.message(F.text == "➕ Добавить товар")
@seller_only
async def add_product_start(message: Message, state: FSMContext):
    await message.answer("Название товара:")
    await state.set_state(AddProduct.name)

@dp.message(AddProduct.name)
@seller_only
async def product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Фасовка/упаковка:")
    await state.set_state(AddProduct.amount)

@dp.message(AddProduct.amount)
@seller_only
async def product_amount(message: Message, state: FSMContext):
    await state.update_data(amount=message.text.strip())
    await message.answer("Цена:")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
@seller_only
async def product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
    except:
        await message.answer("Введите число")
        return
    data = await state.get_data()
    seller = get_seller(message.from_user.id)
    add_product(seller[0], data["name"], data["amount"], price)
    await message.answer("✅ Добавлено", reply_markup=seller_menu())
    await state.clear()

@dp.message(F.text == "📦 Мои товары")
@seller_only
async def my_products(message: Message, state: FSMContext):
    seller = get_seller(message.from_user.id)
    products = get_products(seller[0])
    if not products:
        await message.answer("Нет товаров")
        return
    text = "📦 Ваши товары:\n\n"
    for p in products:
        text += f"{p[0]}# | {p[1]} | {p[2]} | {p[3]} сом\n"
    await message.answer(text)

@dp.message(F.text == "🗑 Удалить товар")
@seller_only
async def delete_product_menu(message: Message, state: FSMContext):
    seller = get_seller(message.from_user.id)
    products = get_products(seller[0])
    if not products:
        await message.answer("Нет товаров")
        return
    await message.answer("Выберите товар:", reply_markup=delete_products_kb(products))

@dp.callback_query(F.data.startswith("delprod_"))
async def delete_product(call: CallbackQuery):
    try:
        pid = int(call.data.split("_")[1])
    except:
        await call.answer("Ошибка")
        return
    delete_product_by_id(pid)
    await call.message.edit_text("✅ Удалено")
    await call.answer()

# ---------------- ЗАКАЗЫ ----------------
@dp.message(F.text == "📥 Заказы")
@seller_only
async def seller_orders(message: Message, state: FSMContext):
    seller = get_seller(message.from_user.id)
    orders = get_seller_orders(seller[0])

    if not orders:
        await message.answer("❌ Заказов нет.")
        return

    text = "📥 Заказы:\n\n"

    for o in orders:
        order_id = o[0]
        product_name = o[1]
        status = o[3]

        try:
            amount = int(float(o[2]))
        except (TypeError, ValueError):
            amount = 0

        product = get_product_by_name_and_seller(product_name, seller[0])
        packaging = product[3] if product else "Не указано"

        text += (
            f"🆔 Заказ #{order_id}\n"
            f"📦 Товар: {product_name}\n"
            f"📊 Фасовка: {packaging}\n"
            f"🔢 Кол-во: {amount}\n"
            f"📌 Статус: {status}\n\n"
        )

    await message.answer(text)

# ---------------- ПОДТВЕРЖДЕНИЕ ----------------
@dp.callback_query(F.data.startswith("order_ok_"))
async def order_accept(call: CallbackQuery):
    try:
        order_id = int(call.data.split("_")[2])
    except:
        await call.answer("Ошибка")
        return
    update_order_status(order_id, "принятый")
    buyer = get_buyer_by_order(order_id)
    if buyer:
        await bot.send_message(buyer[0], "✅ Заказ принят")
    await call.message.edit_text(call.message.text + "\n✅ Принято")
    await call.answer()

@dp.callback_query(F.data.startswith("order_no_"))
async def order_decline(call: CallbackQuery, state: FSMContext):
    try:
        order_id = int(call.data.split("_")[2])
    except:
        await call.answer("Ошибка")
        return
    await state.update_data(order_id=order_id)
    await call.message.answer("Причина:")
    await state.set_state(DeclineState.reason)
    await call.answer()

@dp.message(DeclineState.reason)
@seller_only
async def save_decline(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    reason = message.text.strip()
    update_order_status(order_id, "отклонён")
    buyer = get_buyer_by_order(order_id)
    if buyer:
        await bot.send_message(buyer[0], f"❌ Заказ #{order_id}\nПричина: {reason}")
    await message.answer("Отправлено")
    await state.clear()

# ---------------- FALLBACK ----------------
@dp.message()
async def unknown(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Используйте кнопки 👇")

# ---------------- MAIN ----------------
async def main():
    create_tables()
    logging.info("🤖 Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())