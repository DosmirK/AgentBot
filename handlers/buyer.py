from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import *
from states import BuyerState, OrderState, ProfileEdit
from database import *

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


router = Router()


# ---------------- ВСПОМОГАТЕЛЬНЫЕ ----------------

def product_text_buyer(p):
    return (
        f"🛒 <b>{p['name']}</b>\n\n"
        f"📦 Фасовка: {p['amount']}\n"
        f"💰 Цена: {p['price']} сом\n"
        f"📊 Остаток: {p['stock']} шт"
    )


async def show_products_for_buyer(message, products, title="📦 Товары:"):

    if not products:
        await message.answer("📦 Нет товаров")
        return

    await message.answer(title)

    for p in products:

        text = product_text_buyer(p)

        kb = InlineKeyboardMarkup(inline_keyboard=[[

            InlineKeyboardButton(
                text="✅ Выбрать",
                callback_data=f"product_{p['id']}"
            )

        ]])

        try:
            await message.answer_photo(
                photo=p["image"],
                caption=text,
                parse_mode="HTML",
                reply_markup=kb
            )
        except:
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=kb
            )


# ---------------- ПОКУПАТЕЛЬ ----------------

@router.message(F.text == "🛒 Магазин")
async def buyer_register(message: Message, state: FSMContext):
    buyer = get_buyer(message.from_user.id)
    if buyer:
        await message.answer(
            f"Добро пожаловать в ваш магазин, <b>{buyer['shop_name']}</b>!",
            parse_mode="HTML",
            reply_markup=buyer_menu_kb()
        )
        return

    await state.set_state(BuyerState.register_name)
    await message.answer("Введите название вашего магазина:")


@router.message(BuyerState.register_name)
async def buyer_enter_name(message: Message, state: FSMContext):
    shop_name = message.text.strip()
    if len(shop_name) < 2:
        await message.answer("Название слишком короткое, введите снова:")
        return

    await state.update_data(shop_name=shop_name)
    await state.set_state(BuyerState.register_address)
    await message.answer("Введите адрес вашего магазина:")


@router.message(BuyerState.register_address)
async def buyer_enter_address(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Адрес слишком короткий, введите снова:")
        return

    data = await state.get_data()
    shop_name = data.get("shop_name")

    add_buyer(message.from_user.id, shop_name, address)

    await message.answer(
        f"✅ Ваш магазин зарегистрирован:\n<b>{shop_name}</b>\n📍 {address}",
        parse_mode="HTML",
        reply_markup=buyer_menu_kb()
    )

    await state.clear()


@router.message(F.text == "📋 Список фирм")
async def show_shops(message: Message):

    shops = get_all_shops()

    if not shops:
        await message.answer("❌ Фирм нет")
        return

    await message.answer(
        "🏪 Выберите магазин:",
        reply_markup=shops_kb(shops)
    )


@router.message(F.text == "📥 Мои заказы")
async def buyer_orders(message: Message):

    buyer = get_buyer(message.from_user.id)

    if not buyer:
        await message.answer("❌ Сначала зарегистрируйтесь")
        return

    orders = get_buyer_orders(message.from_user.id)

    if not orders:
        await message.answer("❌ У вас пока нет заказов.")
        return

    orders_dict = {}

    for o in orders:
        oid = o["order_id"]

        if oid not in orders_dict:
            seller = get_seller_by_id(o["seller_id"])
            seller_name = seller["shop_name"] if seller else "Неизвестно"

            orders_dict[oid] = {
                "status": o["status"],
                "address": o["address"],
                "total_amount": o["total_amount"],
                "created_at": o["created_at"],
                "seller_name": seller_name,
                "items": []
            }

        orders_dict[oid]["items"].append(o)

    text = "📥 Мои заказы:\n\n"

    for order_id, data in orders_dict.items():

        text += f"🆔 Заказ #{order_id}\n"
        text += f"🏪 Фирма: {data['seller_name']}\n"
        text += f"📅 Дата: {data['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
        text += f"📍 Адрес: {data['address']}\n"
        text += f"💵 Итого: {data['total_amount']} сом\n"
        text += f"📌 Статус: {data['status']}\n"
        text += "📦 Товары:\n"

        for item in data["items"]:
            product = get_product(item["product_id"])
            packaging = product["amount"] if product else "Не указано"

            text += (
                f"  • {item['product_name']}\n"
                f"    Фасовка: {packaging}\n"
                f"    Кол-во: {item['quantity']} шт\n"
                f"    Цена: {item['price']} сом\n"
                f"    Сумма: {item['total_price']} сом\n"
            )

        text += "\n"

    await message.answer(text)


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):

    buyer = get_buyer(message.from_user.id)

    if not buyer:
        await message.answer("❌ Сначала зарегистрируйтесь")
        return

    text = (
        "👤 Ваш профиль\n\n"
        f"🏪 Название: {buyer['shop_name']}\n"
        f"📍 Адрес: {buyer['address']}\n"
    )

    await message.answer(text, reply_markup=profile_kb())


@router.message(F.text == "✏️ Изменить название")
async def edit_name_start(message: Message, state: FSMContext):
    await message.answer("Введите новое название магазина:")
    await state.set_state(ProfileEdit.waiting_for_name)


@router.message(ProfileEdit.waiting_for_name)
async def save_new_name(message: Message, state: FSMContext):
    update_buyer_name(message.from_user.id, message.text)

    await message.answer("✅ Название обновлено")
    await state.clear()

    await show_profile(message)


@router.message(F.text == "📍 Изменить адрес")
async def edit_address_start(message: Message, state: FSMContext):
    await message.answer("Введите новый адрес:")
    await state.set_state(ProfileEdit.waiting_for_address)


@router.message(ProfileEdit.waiting_for_address)
async def save_new_address(message: Message, state: FSMContext):
    update_buyer_address(message.from_user.id, message.text)

    await message.answer("✅ Адрес обновлён")
    await state.clear()

    await show_profile(message)


@router.message(ProfileEdit.waiting_for_name, F.text == "⬅️ Назад")
@router.message(ProfileEdit.waiting_for_address, F.text == "⬅️ Назад")
async def cancel_edit(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Редактирование отменено.",
        reply_markup=buyer_menu_kb()
    )


@router.message(F.text == "⬅️ Назад")
async def back_general(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏠 Главное меню",
        reply_markup=buyer_menu_kb()
    )


# ---------------- ВЫБОР МАГАЗИНА ----------------

@router.callback_query(F.data.startswith("shop_"))
async def choose_shop(call: CallbackQuery, state: FSMContext):

    try:
        seller_id = int(call.data.split("_")[1])
    except:
        await call.answer("Ошибка")
        return

    categories = get_categories(seller_id)

    if not categories:
        await call.message.answer("❌ В фирме нет категорий")
        await call.answer()
        return

    await state.update_data(
        seller_id=seller_id,
        cart=[]
    )

    kb = categories_kb_buy(categories, "buycat_")

    await call.message.answer(
        "📂 Выберите категорию:",
        reply_markup=kb
    )

    await call.answer()


# ---------------- ВЫБОР КАТЕГОРИИ ----------------

@router.callback_query(F.data.startswith("buycat_"))
async def buyer_choose_category(call: CallbackQuery, state: FSMContext):

    cat_id = int(call.data.split("_")[1])

    data = await state.get_data()
    seller_id = data.get("seller_id")

    if not seller_id:
        await call.answer("Ошибка фирмы")
        return

    products = get_products_full_by_seller(seller_id)

    products = [
        p for p in products
        if p["category_id"] == cat_id and p["stock"] > 0
    ]

    await show_products_for_buyer(
        call.message,
        products,
        "📦 Выберите товар:"
    )

    await state.set_state(BuyerState.search)

    await call.answer()


# ---------------- ПОИСК ----------------

@router.message(
    BuyerState.search,
    ~F.text.in_([
        "➕ Добавить ещё",
        "📦 Оформить заказ",
        "❌ Очистить корзину"
    ])
)
async def search_product(message: Message, state: FSMContext):

    text = message.text.strip()

    data = await state.get_data()
    seller_id = data.get("seller_id")

    if not seller_id:
        await message.answer("Сначала выберите фирму 👇")
        await state.clear()
        return

    if not text:
        await message.answer("Введите название товара")
        return

    products = search_products_by_name(seller_id, text)

    if not products:
        await message.answer("❌ Товар не найден")
        return

    await show_products_for_buyer(
        message,
        products,
        "🔍 Найдено:"
    )


# ---------------- ВЫБОР ТОВАРА ----------------

@router.callback_query(F.data.startswith("product_"))
async def choose_product(call: CallbackQuery, state: FSMContext):

    try:
        product_id = int(call.data.split("_")[1])
    except:
        await call.answer("Ошибка товара")
        return

    await state.update_data(
        product_id=product_id
    )

    await call.message.answer("Введите количество:")

    await state.set_state(OrderState.amount)

    await call.answer()


# ---------------- КОЛИЧЕСТВО → В КОРЗИНУ ----------------

@router.message(OrderState.amount)
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

    print("FSM DATA:", await state.get_data())
    product_id = data.get("product_id")

    if not product_id:
        await message.answer("❗ Сначала выберите товар")
        await state.set_state(BuyerState.search)
        return

    cart = data.get("cart", [])

    product = get_product(product_id)

    if not product:
        await message.answer("❌ Товар не найден в базе")
        await state.clear()
        return

    stock = product["stock"]

    if amount > stock:
        await message.answer(
            f"❌ В наличии только {stock} шт.\nВведите другое количество:"
        )
        return

    cart.append({
        "product_id": product_id,
        "amount": amount
    })

    await state.update_data(
        cart=cart,
        product_id=None  
    )

    await message.answer(
        f"✅ Добавлено в корзину\n\n"
        f"🛒 В корзине: {len(cart)} товаров",
        reply_markup=cart_menu_kb()
    )

    await state.set_state(BuyerState.search)


# ---------------- КОРЗИНА ----------------

@router.message(F.text == "➕ Добавить ещё")
async def cart_add_more(message: Message, state: FSMContext):

    data = await state.get_data()
    seller_id = data.get("seller_id")

    if not seller_id:
        await message.answer("Сначала выберите магазин")
        return

    categories = get_categories(seller_id)

    await message.answer(
        "📂 Выберите категорию:",
        reply_markup=categories_kb_buy(categories, "buycat_")
    )

    await state.set_state(BuyerState.search)


@router.message(F.text == "❌ Очистить корзину")
async def cart_clear(message: Message, state: FSMContext):

    await state.update_data(cart=[])

    await message.answer(
        "🗑 Корзина очищена",
        reply_markup=buyer_menu_kb()
    )

    await state.clear()


@router.message(F.text == "📦 Оформить заказ")
async def cart_checkout(message: Message, state: FSMContext):

    data = await state.get_data()
    cart = data.get("cart", [])

    if not cart:
        await message.answer("❌ Корзина пустая")
        return

    await message.answer(
        "📝 Переходим к оформлению...",
        reply_markup=buyer_menu_kb()
    )

    buyer = get_buyer(message.from_user.id)

    if buyer and buyer["address"]:
        await state.update_data(address=buyer["address"])

        await show_order_preview(message, state)

    else:
        await message.answer("Введите адрес доставки:")
        await state.set_state(OrderState.address)


async def show_order_preview(message: Message, state: FSMContext):

    data = await state.get_data()
    cart = data.get("cart", [])
    address = data.get("address")

    text = "📝 Ваш заказ:\n\n"
    total_sum = 0

    for item in cart:
        product = get_product(item["product_id"])

        name = product["name"]
        packaging = product.get("amount", "Не указано")
        price = float(product["price"])
        amount = item["amount"]

        cost = price * amount
        total_sum += cost

        text += (
            f"📦 {name}\n"
            f"📦 Фасовка: {packaging}\n"
            f"🔢 {amount} × {price} = {cost} сом\n\n"
        )

    text += f"💵 Итого: {total_sum} сом\n"
    text += f"📍 Адрес: {address}"

    await message.answer(
        text,
        reply_markup=order_confirm_buyer_kb()
    )

    await state.set_state(OrderState.confirm)


# ---------------- АДРЕС ----------------

@router.message(OrderState.address)
async def order_address(message: Message, state: FSMContext):

    address = message.text.strip()

    if len(address) < 5:
        await message.answer("Адрес слишком короткий")
        return

    await state.update_data(address=address)

    update_buyer_address(message.from_user.id, address)

    await show_order_preview(message, state)


# ---------------- ПОДТВЕРЖДЕНИЕ ----------------

@router.callback_query(F.data == "buyer_confirm_yes", OrderState.confirm)
async def confirm_order(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    cart = data.get("cart", [])
    address = data.get("address")
    seller_id = data.get("seller_id")

    if not cart:
        await call.message.answer("❌ Корзина пуста")
        await state.clear()
        return

    if not seller_id:
        await call.message.answer("❌ Ошибка магазина")
        await state.clear()
        return

    order_id = create_order_full(
        call.from_user.id,
        seller_id,
        cart,
        address
    )

    if not order_id:
        await call.message.answer("❌ Ошибка создания заказа")
        await state.clear()
        return

    seller = get_seller_by_id(seller_id)

    if not seller:
        await call.message.answer("❌ Продавец не найден")
        await state.clear()
        return

    buyer = get_buyer(call.from_user.id)

    items = get_order_items(order_id)

    text = "📥 Новый заказ\n\n"
    total_sum = 0

    for item in items:
        total_sum += float(item["total_price"])

        text += (
            f"📦 {item['product_name']}\n"
            f"📦 Фасовка: {item['amount']}\n"
            f"🔢 {item['quantity']} × {item['price']} = {item['total_price']} сом\n\n"
        )

    text += f"📍 Адрес: {address}\n"
    text += f"💵 Итого: {total_sum} сом\n\n"
    text += f"🏪 Магазин: {buyer['shop_name']}"

    await call.bot.send_message(
        seller["tg_id"],
        text,
        reply_markup=order_confirm_kb(str(order_id))
    )

    await call.message.answer(
        f"✅ Заказ оформлен (№{order_id})"
    )

    await state.clear()
    await call.answer()


@router.callback_query(F.data == "buyer_confirm_no", OrderState.confirm)
async def cancel_order(call: CallbackQuery, state: FSMContext):

    await call.message.edit_text("❌ Заказ отменён")

    await state.clear()

    await call.answer()