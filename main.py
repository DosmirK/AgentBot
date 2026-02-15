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
from states import SellerRegister, AddProduct, OrderState, DeclineState, BuyerState, EditProduct

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


@dp.message(Command("sellers"))
async def admin_sellers(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sellers = get_all_sellers()   # функция из db

    if not sellers:
        await message.answer("❌ Продавцов нет")
        return

    text = "🏪 Продавцы:\n\n"

    for s in sellers:
        sid = s[0]
        tg_id = s[1]
        name = s[2]
        active = "✅" if s[3] == 1 else "⛔"

        text += (
            f"{active} {name}\n"
            f"ID: {tg_id}\n\n"
        )

    await message.answer(text)


@dp.message(Command("buyers"))
async def admin_buyers(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    buyers = get_all_buyers()

    if not buyers:
        await message.answer("❌ Покупателей нет")
        return

    text = "🛒 Покупатели:\n\n"

    for b in buyers:
        uid = b[0]
        name = b[1] if len(b) > 1 else "—"

        text += f"👤 {name}\n🆔 {uid}\n\n"

    await message.answer(text)


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
async def choose_shop(call: CallbackQuery, state: FSMContext):

    logging.info(f"[SHOP] Callback data: {call.data}")

    try:
        seller_id = int(call.data.split("_")[1])
    except Exception as e:
        logging.error(f"[SHOP] Parse error: {e}")
        await call.answer("Ошибка")
        return

    logging.info(f"[SHOP] Selected seller_id = {seller_id}")

    products = get_products(seller_id)

    logging.info(f"[SHOP] Products count = {len(products)}")

    if not products:
        await call.message.answer("❌ Нет товаров")
        await call.answer()
        return

    # Сохраняем seller_id
    await state.update_data(seller_id=seller_id)

    data = await state.get_data()
    logging.info(f"[SHOP] FSM data after save: {data}")

    await state.set_state(BuyerState.search)

    await call.message.answer(
        "📦 Выберите товар или напишите название:",
        reply_markup=products_kb(products)
    )

    await call.answer()


@dp.callback_query(F.data.startswith("product_"))
async def choose_product(call: CallbackQuery, state: FSMContext):
    try:
        product_id = int(call.data.split("_")[1])
    except:
        await call.answer("Ошибка")
        return

    await state.update_data(product_id=product_id)
    await state.update_data(shop_id=None)
    await call.message.answer("Введите количество:")
    await state.set_state(OrderState.amount)
    await call.answer()

@dp.message(BuyerState.search)
async def search_or_choose_product(message: Message, state: FSMContext):

    logging.info(f"[SEARCH] Message: {message.text}")

    data = await state.get_data()
    logging.info(f"[SEARCH] FSM data: {data}")

    shop_id = data.get("seller_id")

    if not shop_id:
        logging.warning("[SEARCH] seller_id not found in FSM")
        await message.answer("Сначала выберите магазин 👇")
        await state.clear()
        return

    logging.info(f"[SEARCH] Using seller_id = {shop_id}")

    query = message.text.strip()

    if not query:
        logging.warning("[SEARCH] Empty query")
        await message.answer("Введите название товара")
        return

    logging.info(f"[SEARCH] Query = '{query}'")

    matched_products = search_products_by_name(shop_id, query)

    logging.info(f"[SEARCH] Found products: {matched_products}")

    if not matched_products:
        logging.warning("[SEARCH] No products found")
        await message.answer("❌ Товар не найден. Попробуйте другое название:")
        return

    await message.answer(
        "Найдены совпадения:",
        reply_markup=search_products_kb(matched_products)
    )


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

    data = await state.get_data()
    product_id = data["product_id"]

    product = get_product(product_id)

    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return

    stock = product[5]   # ← ВАЖНО: индекс склада (если не так — скажи)

    # Проверка остатков
    if amount > stock:
        await message.answer(
            f"❌ В наличии только {stock} шт.\n"
            f"Введите другое количество:"
        )
        return

    # Всё ок
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
    """
    Покупатель подтверждает заказ.
    Теперь просто создаём заказ в базе, но склад ещё не уменьшаем.
    """
    data = await state.get_data()
    product = get_product(data["product_id"])
    if not product:
        await call.message.answer("❌ Ошибка товара")
        await state.clear()
        return

    amount = int(data["amount"])

    # Создаём заказ с начальным статусом "ожидает принятия"
    order_id = create_order(
        call.from_user.id,
        product[1],      # seller_id
        product[0],      # product_id
        amount,
        data["address"]
    )

    if not order_id:
        await call.message.answer("❌ Ошибка заказа")
        return

    seller = get_seller_by_id(product[1])
    seller_name = seller[2] if seller else "Неизвестно"

    if seller:
        total = float(product[4]) * amount
        text = f""" 
📥 Новый заказ #{order_id} 
🏪 Магазин: {seller_name} 
📦 Товар: {product[2]} 
📊 фасовка: {product[3]} 
🔢 Кол-во: {amount}
📍 Адрес доставки: {data['address']} 
💰 Цена: {product[4]} сом 
💵 Итого: {total} сом 
👤 Покупатель: {call.from_user.full_name} """
        await bot.send_message(seller[1], text, reply_markup=order_confirm_kb(order_id))

    await call.message.answer(f"✅ Заказ #{order_id} создан и отправлен продавцу")
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
        user = message.from_user
        username = f"@{user.username}" if user.username else "без username"
        full_name = user.full_name

        text = (
            "📩 Запрос на доступ продавца\n\n"
            f"👤 Имя: {full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: {user.id}"
        )

        await bot.send_message(ADMIN_ID, text)
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

    seller = get_seller(message.from_user.id)

    await state.update_data(seller_id=seller[0])

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
async def get_price(message: Message, state: FSMContext):

    try:
        price = float(message.text.replace(",", "."))
    except:
        await message.answer("Введите число (например: 150 или 150.5)")
        return

    if price <= 0:
        await message.answer("Цена должна быть больше 0")
        return

    await state.update_data(price=price)

    await message.answer("Введите количество на складе:")
    await state.set_state(AddProduct.stock)

@dp.message(AddProduct.stock)
@seller_only
async def get_stock(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число!")
        return

    stock = int(message.text)

    data = await state.get_data()

    add_product(
        seller_id=data["seller_id"],
        name=data["name"],
        amount=data["amount"],
        price=data["price"],
        stock=stock
    )

    await state.clear()

    await message.answer("✅ Товар добавлен")

@dp.message(F.text == "📦 Мои товары")
@seller_only
async def my_products(message: Message, state: FSMContext):

    seller = get_seller(message.from_user.id)
    products = get_products(seller[0])

    if not products:
        await message.answer("Нет товаров")
        return

    max_len = 3500   # запас до лимита
    text = "📦 Ваши товары:\n\n"

    for p in products:
        pid = p[0]
        name = p[1]
        pack = p[2]
        price = p[3]
        stock = p[4]

        block = (
            f"🆔 {pid}\n"
            f"📦 {name}\n"
            f"📊 {pack}\n"
            f"💰 {price} сом\n"
            f"📦 Остаток: {stock}\n\n"
        )

        # Если текст стал слишком длинным — отправляем и начинаем заново
        if len(text) + len(block) > max_len:
            await message.answer(text)
            text = ""

        text += block

    # Отправляем остаток
    if text:
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

@dp.message(F.text == "✏️ Изменить товар")
@seller_only
async def edit_product_menu(message: Message, state: FSMContext):

    seller = get_seller(message.from_user.id)
    products = get_products(seller[0])

    if not products:
        await message.answer("Нет товаров")
        return

    await message.answer(
        "Выберите товар для изменения:",
        reply_markup=edit_products_kb(products)
    )

    await state.set_state(EditProduct.choose)

@dp.callback_query(F.data.startswith("editprod_"), EditProduct.choose)
async def choose_edit_product(call: CallbackQuery, state: FSMContext):

    pid = int(call.data.split("_")[1])

    await state.update_data(product_id=pid)

    await call.message.edit_text(
        "Что изменить?",
        reply_markup=edit_fields_kb()
    )

    await state.set_state(EditProduct.field)
    await call.answer()

@dp.callback_query(F.data.startswith("edit_"), EditProduct.field)
async def choose_edit_field(call: CallbackQuery, state: FSMContext):

    field = call.data.replace("edit_", "")

    if field == "cancel":
        await call.message.edit_text("❌ Отменено")
        await state.clear()
        return

    await state.update_data(field=field)

    text_map = {
        "name": "Введите новое название:",
        "amount": "Введите новую фасовку:",
        "price": "Введите новую цену:",
        "stock": "Введите новый остаток:"
    }

    await call.message.answer(text_map[field])

    await state.set_state(EditProduct.value)
    await call.answer()

@dp.message(EditProduct.value)
@seller_only
async def save_edit_value(message: Message, state: FSMContext):

    data = await state.get_data()

    pid = data["product_id"]
    field = data["field"]
    value = message.text.strip()

    # Валидация
    if field in ["price", "stock"]:
        try:
            value = float(value) if field == "price" else int(value)
        except:
            await message.answer("Введите число")
            return

    update_product_field(pid, field, value)

    await message.answer("✅ Товар обновлён")

    await state.clear()

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
    """
    Продавец принимает заказ:
    - уменьшаем склад
    - проверяем остаток
    - меняем статус
    - уведомляем покупателя
    - уведомляем админа
    """

    # Получаем order_id
    try:
        order_id = int(call.data.split("_")[2])
    except Exception:
        await call.answer("❌ Ошибка ID заказа")
        return

    # Получаем заказ
    order = get_order(order_id)
    if not order:
        await call.answer("❌ Заказ не найден")
        return

    buyer_tg = order[1]
    seller_id = order[2]
    product_id = order[3]
    amount = int(order[4])


    # Получаем товар
    product = get_product(product_id)
    if not product:
        await call.answer("❌ Товар не найден")
        return

    product_name = product[2]
    price = float(product[4])

    # Получаем продавца
    seller = get_seller_by_id(seller_id)
    seller_name = seller[2] if seller else "Неизвестный магазин"
    seller_chat = seller[1] if seller else None

    # Уменьшаем склад
    decrease_stock(product_id, amount)

    # Проверяем остаток
    product_after = get_product(product_id)

    if product_after and product_after[5] <= 5:
        if seller_chat:
            await bot.send_message(
                seller_chat,
                f"⚠️ Остаток товара «{product_after[2]}» низкий: {product_after[5]} шт."
            )

    # Меняем статус заказа
    update_order_status(order_id, "принятый")

    # Получаем покупателя
    buyer = get_buyer_by_order(order_id)

    buyer_id = buyer[0] if buyer else None

    # Уведомляем покупателя
    if buyer_id:
        await bot.send_message(
            buyer_id,
            f"✅ Ваш заказ #{order_id} принят продавцом"
        )

    # Считаем сумму
    total = price * amount

    # Сообщение админу (ТОЛЬКО после принятия)
    admin_text = (
        f"📊 Принятый заказ\n\n"
        f"🆔 #{order_id}\n"
        f"🏪 Магазин: {seller_name}\n"
        f"📦 Товар: {product_name}\n"
        f"📊 Фасовка: {product[3]}\n"
        f"🔢 Кол-во: {amount}\n"
        f"💰 Цена: {price} сом\n"
        f"💵 Итого: {total} сом\n"
        f"👤 Покупатель: {buyer_tg}\n"
        f"🆔 ID: {buyer_id if buyer_id else '—'}"
    )

    await bot.send_message(ADMIN_ID, admin_text)

    # Обновляем сообщение продавцу
    await call.message.edit_text(
        call.message.text + "\n\n✅ Заказ принят"
    )

    await call.answer("Заказ подтверждён ✅")

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