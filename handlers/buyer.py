from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import *
from states import BuyerState, OrderState, ProfileEdit, OrdersView, BuyerStockState
from database import *

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from datetime import datetime
from data import DAY_MAP

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


def can_order_today(schedule):

    today_eng = datetime.now().strftime("%A").lower()

    today = DAY_MAP[today_eng]

    order_days = schedule["order_days"].split(",")

    return today in order_days

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
        await message.answer("Название слишком короткое")
        return

    await state.update_data(shop_name=shop_name)

    await state.set_state(BuyerState.register_district)

    await message.answer(
        "Выберите ваш район:",
        reply_markup=district_kb()
    )


@router.message(BuyerState.register_district)
async def buyer_enter_district(message: Message, state: FSMContext):

    district = message.text.strip()

    if district not in DISTRICTS:
        await message.answer("Выберите район кнопкой")
        return

    await state.update_data(district=district)

    await state.set_state(BuyerState.register_address)

    await message.answer(
        "Введите адрес вашего магазина:",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(BuyerState.register_address)
async def buyer_enter_address(message: Message, state: FSMContext):

    address = message.text.strip()

    if len(address) < 5:
        await message.answer(
            "Адрес слишком короткий, введите снова:"
        )
        return

    await state.update_data(
        address=address
    )

    await state.set_state(
        BuyerState.register_phone
    )

    await message.answer(
        "Введите номер телефона:"
    )


@router.message(BuyerState.register_phone)
async def buyer_enter_phone(
    message: Message,
    state: FSMContext
):

    phone = message.text.strip()

    if len(phone) < 8:
        await message.answer(
            "Введите корректный номер телефона"
        )
        return

    data = await state.get_data()

    shop_name = data.get("shop_name")
    district = data.get("district")
    address = data.get("address")

    add_buyer(
        message.from_user.id,
        shop_name,
        address,
        district,
        phone
    )

    await message.answer(
        f"✅ Магазин зарегистрирован\n\n"
        f"🏪 {shop_name}\n"
        f"🗺 Район: {district}\n"
        f"📍 {address}\n"
        f"📞 {phone}",
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

@router.message(F.text == "📦 Склад")
async def buyer_stock(message: Message, state: FSMContext):

    await state.set_state(
        BuyerStockState.page
    )

    await state.update_data(
        page=0
    )

    await send_stock_page(message, state, message.from_user.id)

async def send_stock_page(message, state, user_id):

    buyer = get_buyer(user_id)

    if not buyer:
        await message.answer(
            "❌ Сначала зарегистрируйтесь"
        )
        return

    stock = get_buyer_stock(
        buyer["id"]
    )

    if not stock:
        await message.answer(
            "📦 Склад пока пуст"
        )
        return

    data = await state.get_data()

    page = data.get("page", 0)

    start = page * 1
    end = start + 1

    current_items = stock[start:end]

    text = "📦 Ваш склад\n\n"

    for item in current_items:

        text += (
            f"📦 {item['name']}\n"
            f"📏 Фасовка: {item['amount']}\n"
            f"📊 Остаток: {item['quantity']}\n\n"
        )

    total_pages = (len(stock) - 1) // 1

    await message.answer(
        text,
        reply_markup=stock_pagination_kb(
            page,
            total_pages
        )
    )

@router.callback_query(F.data == "stock_next")
async def stock_next(
    call: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    page = data.get("page", 0)

    await state.update_data(
        page=page + 1
    )

    await call.message.delete()

    await send_stock_page(call.message, state, call.from_user.id)

    await call.answer()

@router.callback_query(F.data == "stock_prev")
async def stock_prev(
    call: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    page = data.get("page", 0)

    await state.update_data(
        page=max(page - 1, 0)
    )

    await call.message.delete()

    await send_stock_page(call.message, state, call.from_user.id)

    await call.answer()

@router.message(F.text == "📥 Мои заказы")
async def buyer_orders(message: Message, state: FSMContext):

    await state.set_state(OrdersView.page)
    await state.update_data(page=0)

    await send_orders_page(
        message,
        state,
        message.from_user.id
    )


async def send_orders_page(message, state, user_id):

    buyer = get_buyer(user_id)

    if not buyer:
        await message.answer("❌ Сначала зарегистрируйтесь")
        return

    orders = get_buyer_orders(user_id)

    if not orders:
        await message.answer("❌ У вас пока нет заказов.")
        return

    orders_dict = {}

    for o in orders:

        oid = o["order_id"]

        if oid not in orders_dict:

            seller = get_seller_by_id(o["seller_id"])

            orders_dict[oid] = {
                "seller_name": seller["shop_name"] if seller else "Неизвестно",
                "status": o["status"],
                "address": o["address"],
                "total_amount": o["total_amount"],
                "created_at": o["created_at"],
                "items": []
            }

        orders_dict[oid]["items"].append(o)

    orders_list = list(orders_dict.items())

    data = await state.get_data()
    page = data.get("page", 0)

    start = page * 3
    end = start + 3

    current_orders = orders_list[start:end]

    for order_id, order_data in current_orders:

        text = (
            f"🆔 Заказ #{order_id}\n"
            f"🏪 Фирма: {order_data['seller_name']}\n"
            f"📅 Дата: {order_data['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 Адрес: {order_data['address']}\n"
            f"💵 Итого: {order_data['total_amount']} сом\n"
            f"📌 Статус: {order_data['status']}\n\n"
        )

        text += "📦 Товары:\n"

        for item in order_data["items"]:

            product = get_product(item["product_id"])

            packaging = (
                product["amount"]
                if product else "Не указано"
            )

            text += (
                f"• {item['product_name']}\n"
                f"Фасовка: {packaging}\n"
                f"Кол-во: {item['quantity']}\n"
                f"Цена: {item['price']} сом\n\n"
            )

        await message.answer(
            text,
            reply_markup=repeat_order_kb(order_id)
        )

    total_pages = (len(orders_list) - 1) // 3

    if total_pages > 0:

        await message.answer(
            f"Страница {page + 1} из {total_pages + 1}",
            reply_markup=orders_pagination_kb(
                page,
                total_pages
            )
        )


@router.callback_query(F.data == "orders_next")
async def orders_next(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    page = data.get("page", 0)

    await state.update_data(
        page=page + 1
    )

    await call.message.delete()

    await send_orders_page(
        call.message,
        state,
        call.from_user.id
    )

    await call.answer()


@router.callback_query(F.data == "orders_prev")
async def orders_prev(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    page = data.get("page", 0)

    await state.update_data(
        page=max(page - 1, 0)
    )

    await call.message.delete()

    await send_orders_page(
        call.message,
        state,
        call.from_user.id
    )

    await call.answer()


@router.callback_query(F.data.startswith("repeat_order_"))
async def repeat_order(
    call: CallbackQuery,
    state: FSMContext
):

    order_id = int(
        call.data.replace(
            "repeat_order_",
            ""
        )
    )

    order = get_order(order_id)

    if not order:

        await call.answer(
            "Заказ не найден"
        )

        return

    items = get_order_items(order_id)

    cart = []

    problems = []

    for item in items:

        product = get_product(
            item["product_id"]
        )

        if not product:

            problems.append(
                f"❌ {item['product_name']} удалён"
            )

            continue

        if product["stock"] <= 0:

            problems.append(
                f"❌ {product['name']} отсутствует"
            )

            continue

        amount = float(item["quantity"])

        stock = float(product["stock"])

        if amount > stock:

            problems.append(
                f"⚠️ {product['name']} "
                f"доступно только {stock}"
            )

            amount = stock

        cart.append({
            "product_id": product["id"],
            "amount": amount
        })

    if not cart:

        await call.message.answer(
            "❌ Нет доступных товаров для повторного заказа"
        )

        await call.answer()

        return

    await state.update_data(
        seller_id=order["seller_id"],
        address=order["address"],
        cart=cart
    )

    if problems:

        await call.message.answer(
            "⚠️ Заказ был обновлён:\n\n"
            + "\n".join(problems)
        )

    await show_order_preview(
        call.message,
        state
    )

    await call.answer()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):

    buyer = get_buyer(message.from_user.id)

    if not buyer:
        await message.answer("❌ Сначала зарегистрируйтесь")
        return

    text = (
        "👤 Ваш профиль\n\n"
        f"🏪 Название: {buyer['shop_name']}\n"
        f"🗺 Район: {buyer['district']}\n"
        f"📍 Адрес: {buyer['address']}\n"
        f"📞 Телефон: {buyer['phone']}\n"
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


@router.message(F.text == "🗺 Изменить район")
async def edit_district_start(
    message: Message,
    state: FSMContext
):
    await message.answer(
        "Выберите новый район:",
        reply_markup=district_kb()
    )

    await state.set_state(
        ProfileEdit.waiting_for_district
    )


@router.message(ProfileEdit.waiting_for_district)
async def save_new_district(
    message: Message,
    state: FSMContext
):

    district = message.text.strip()

    if district not in DISTRICTS:
        await message.answer(
            "Выберите район кнопкой"
        )
        return

    update_buyer_district(
        message.from_user.id,
        district
    )

    await message.answer(
        "✅ Район обновлён"
    )

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


@router.message(F.text == "📞 Изменить телефон")
async def edit_phone_start(
    message: Message,
    state: FSMContext
):

    await message.answer(
        "Введите новый номер:"
    )

    await state.set_state(
        ProfileEdit.waiting_for_phone
    )


@router.message(ProfileEdit.waiting_for_phone)
async def save_phone(
    message: Message,
    state: FSMContext
):

    phone = message.text.strip()

    update_buyer_phone(
        message.from_user.id,
        phone
    )

    await message.answer(
        "✅ Телефон обновлён"
    )

    await state.clear()

    await show_profile(message)


@router.message(ProfileEdit.waiting_for_phone, F.text == "⬅️ Назад")
@router.message(ProfileEdit.waiting_for_district, F.text == "⬅️ Назад")
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

    buyer = get_buyer(call.from_user.id)

    if not buyer:
        await call.message.answer("❌ Сначала зарегистрируйтесь")
        return

    district = buyer["district"]

    schedule = get_seller_schedule(
        seller_id,
        district
    )

    if not schedule:
        await call.message.answer(
            "❌ Поставщик не работает с вашим районом"
        )
        return

    if not can_order_today(schedule):

        await call.message.answer(
            f"⛔ Сегодня поставщик не принимает "
            f"заказы из района {district}\n\n"
            f"Дни приёма заказов: "
            f"{schedule['order_days']}"
        )

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
        f"✅ Поставщик принимает заказы\n"
        f"🚚 Доставка: {schedule['delivery_day']}\n\n"
        f"📂 Выберите категорию:",
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

    buyer = get_buyer(call.from_user.id)

    schedule = get_seller_schedule(
        seller_id,
        buyer["district"]
    )

    if not schedule:
        await call.message.answer(
            "❌ Поставщик не работает с вашим районом"
        )
        await state.clear()
        return

    if not can_order_today(schedule):

        await call.message.answer(
            "❌ Сегодня поставщик не принимает "
            "заказы из вашего района"
        )

        await state.clear()
        return

    if not cart:
        await call.message.answer("❌ Корзина пуста")
        await state.clear()
        return

    if not seller_id:
        await call.message.answer("❌ Ошибка магазина")
        await state.clear()
        return
    
    prepayment = get_seller_prepayment(
    seller_id
    )

    if prepayment:
        await state.update_data(
        cart=cart,
        address=address,
        seller_id=seller_id
        )

        caption = (
        f"💰 Для оформления заказа требуется предоплата\n\n"
        f"Сумма: {prepayment['amount']} сом\n\n"
        f"Реквизиты:\n"
        f"{prepayment['payment_details']}"
        )

        if prepayment["qr_photo"]:

            await call.message.answer_photo(
            photo=prepayment["qr_photo"],
            caption=caption,
            reply_markup=prepayment_confirm_kb()
            )

        else:

            await call.message.answer(
            caption,
            reply_markup=prepayment_confirm_kb()
            )

        await call.answer()
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

    text += (
        f"🏪 Магазин: {buyer['shop_name']}\n"
        f"📞 Телефон: {buyer['phone']}\n"
        f"🗺 Район: {buyer['district']}\n"
        f"📍 Адрес: {address}\n\n"
        f"💵 Итого: {total_sum} сом"
    )

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

# ---------------- ПРЕДОПЛАТА ----------------

@router.callback_query(F.data == "prepayment_done")
async def prepayment_done(call: CallbackQuery, state: FSMContext):

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

    text += (
        f"🏪 Магазин: {buyer['shop_name']}\n"
        f"📞 Телефон: {buyer['phone']}\n"
        f"🗺 Район: {buyer['district']}\n"
        f"📍 Адрес: {address}\n\n"
        f"💵 Итого: {total_sum} сом"
    )

    await call.bot.send_message(
        seller["tg_id"],
        text,
        reply_markup=order_confirm_kb(str(order_id))
    )

    await call.message.answer(
        "✅ Информация об оплате получена.\n"
        "Заявка отправлена поставщику."
    )

    await state.clear()
    await call.answer()


@router.callback_query(F.data == "prepayment_cancel")
async def cancel_order_(call: CallbackQuery, state: FSMContext):

    await call.message.delete()
    await call.message.answer("❌ Заказ отменён")

    await state.clear()
    await call.answer()