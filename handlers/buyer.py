from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import *
from states import BuyerState, OrderState
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

@router.message(F.text == "🛒 Покупатель")
async def buyer_start(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "Выберите магазин:",
        reply_markup=buyer_menu_kb()
    )


@router.message(F.text == "📋 Список магазинов")
async def show_shops(message: Message):

    shops = get_all_shops()

    if not shops:
        await message.answer("❌ Магазинов нет")
        return

    await message.answer(
        "🏪 Выберите магазин:",
        reply_markup=shops_kb(shops)
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
        await call.message.answer("❌ В магазине нет категорий")
        await call.answer()
        return

    # 👉 Инициализация корзины
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
        await call.answer("Ошибка магазина")
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
        await message.answer("Сначала выберите магазин 👇")
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

    # ✅ СОХРАНЯЕМ ID
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

    # ✅ ГЛАВНАЯ ЗАЩИТА
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

    # ➕ В корзину
    cart.append({
        "product_id": product_id,
        "amount": amount
    })

    await state.update_data(
        cart=cart,
        product_id=None   # ✅ очищаем
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
    "Введите адрес доставки:",
    reply_markup=buyer_menu_kb()
)

    await state.set_state(OrderState.address)


# ---------------- АДРЕС ----------------

@router.message(OrderState.address)
async def order_address(message: Message, state: FSMContext):

    address = message.text.strip()

    if len(address) < 5:
        await message.answer("Адрес слишком короткий")
        return

    await state.update_data(address=address)

    data = await state.get_data()
    cart = data.get("cart", [])

    text = "📝 Ваш заказ:\n\n"

    total_sum = 0

    for item in cart:

        product = get_product(item["product_id"])

        name = product["name"]
        price = float(product["price"])
        amount = item["amount"]

        cost = price * amount
        total_sum += cost

        text += (
            f"📦 {name}\n"
            f"🔢 {amount} × {price} = {cost} сом\n\n"
        )

    text += f"💵 Итого: {total_sum} сом\n"
    text += f"📍 Адрес: {address}"

    await message.answer(
        text,
        reply_markup=order_confirm_buyer_kb()
    )

    await state.set_state(OrderState.confirm)


# ---------------- ПОДТВЕРЖДЕНИЕ ----------------

@router.callback_query(F.data == "buyer_confirm_yes", OrderState.confirm)
async def confirm_order(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    cart = data.get("cart", [])
    address = data.get("address")

    if not cart:
        await call.message.answer("❌ Корзина пуста")
        await state.clear()
        return

    first_product = get_product(cart[0]["product_id"])

    if not first_product:
        await call.message.answer("❌ Ошибка товара")
        await state.clear()
        return

    seller = get_seller_by_id(first_product["seller_id"])

    if not seller:
        await call.message.answer("❌ Продавец не найден")
        await state.clear()
        return

    text = "📥 Новый заказ\n\n"
    total_sum = 0
    order_ids = []

    for item in cart:

        product = get_product(item["product_id"])

        if not product:
            continue

        amount = int(item["amount"])
        price = float(product["price"])
        cost = amount * price

        order_id = create_order(
            call.from_user.id,
            product["seller_id"],
            product["id"],
            amount,
            address
        )

        if order_id:
            order_ids.append(order_id)

        total_sum += cost

        text += (
            f"📦 {product['name']}\n"
            f"🔢 {amount} × {price} = {cost} сом\n\n"
        )

    text += f"📍 Адрес: {address}\n"
    text += f"💵 Итого: {total_sum} сом\n\n"
    text += f"👤 Покупатель: {call.from_user.full_name}"

    await call.bot.send_message(
        seller["tg_id"],
        text,
        reply_markup=order_confirm_kb(",".join(map(str, order_ids))) 
    )

    await call.message.answer(
        f"✅ Заказ оформлен ({len(cart)} товаров)"
    )

    await state.clear()
    await call.answer()


@router.callback_query(F.data == "buyer_confirm_no", OrderState.confirm)
async def cancel_order(call: CallbackQuery, state: FSMContext):

    await call.message.edit_text("❌ Заказ отменён")

    await state.clear()

    await call.answer()