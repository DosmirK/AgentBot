import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID

from keyboards import (
    seller_menu, edit_fields_kb, week_days_kb, district_kb, seller_schedule_districts_kb, 
    delivery_day_kb, prepayment_edit_kb, prepayment_setup_kb)

from data import DISTRICTS, WEEK_DAYS
from states import SellerRegister, AddProduct, DeleteProduct, EditProduct, SellerSchedule, SellerPrepayment

from database import (
    get_seller,
    add_seller,
    set_shop_name,
    get_categories,
    add_category,
    add_product_full,
    get_products_full_by_seller,
    delete_product_by_id,
    update_product_field,
    delete_category,
    get_product,
    get_seller_orders,
    save_seller_schedule,
    get_seller_schedule,
    delete_seller_schedule,
    get_seller_prepayment,
    save_seller_prepayment,
    delete_seller_prepayment
)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


router = Router()

# ================= ВСПОМОГАТЕЛЬНЫЕ ===================

def product_text(p):

    return (
        f"🛒 <b>{p['name']}</b>\n\n"
        f"📦 Фасовка: {p['amount']}\n"
        f"💰 Цена: {p['price']} сом\n"
        f"📊 Остаток: {p['stock']} шт"
    )


def categories_kb(categories, prefix):

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for c in categories:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=c["name"],
                callback_data=f"{prefix}{c['id']}"
            )
        ])

    return kb


async def show_products_with_action(
    message,
    products,
    action_prefix=None,
    title="Выберите товар:"
):

    if not products:
        await message.answer("📦 Нет товаров")
        return

    await message.answer(title)

    for p in products:

        text = product_text(p)

        kb = None

        if action_prefix:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ Выбрать",
                    callback_data=f"{action_prefix}{p['id']}"
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


def check_seller(user_id):

    seller = get_seller(user_id)

    if not seller:
        return None

    if seller["is_active"] == 0:
        return False

    return seller

# ================= ПРОДАВЕЦ ==========================

@router.message(F.text == "🏪 Фирма")
async def seller_start(message: Message, state: FSMContext):

    await state.clear()

    seller = get_seller(message.from_user.id)

    if not seller:

        add_seller(message.from_user.id)

        await message.answer(
            "🔒 Доступ платный.\nЗапрос отправлен администратору."
        )

        user = message.from_user

        username = f"@{user.username}" if user.username else "без username"

        text = (
            "📩 Запрос продавца\n\n"
            f"👤 {user.full_name}\n"
            f"🔗 {username}\n"
            f"🆔 {user.id}"
        )

        try:
            await message.bot.send_message(ADMIN_ID, text)
        except Exception as e:
            logging.error(e)

        return

    if seller["is_active"] == 0:
        await message.answer("⛔ Подписка не активна")
        return

    if not seller["shop_name"]:
        await message.answer("Введите название фирмы:")
        await state.set_state(SellerRegister.shop_name)
        return

    await message.answer("Меню продавца:", reply_markup=seller_menu())

# ================= РЕГИСТРАЦИЯ =======================

@router.message(SellerRegister.shop_name)
async def save_shop_name(message: Message, state: FSMContext):

    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Слишком короткое название")
        return

    set_shop_name(message.from_user.id, name)

    await message.answer(
        "Выберите район для настройки графика:",
        reply_markup=district_kb()
    )

    await state.set_state(SellerRegister.schedule_district)


@router.message(SellerRegister.schedule_district)
async def seller_choose_district(message: Message, state: FSMContext):

    district = message.text.strip()

    if district not in DISTRICTS:
        await message.answer(
            "❌ Выберите район кнопкой",
            reply_markup=district_kb()
        )
        return

    await state.update_data(
        district=district,
        order_days=[]
    )

    await message.answer(
        "Выберите дни приёма заказов.\n"
        "После выбора нажмите ✅ Готово",
        reply_markup=week_days_kb()
    )

    await state.set_state(SellerRegister.schedule_order_days)


@router.message(SellerRegister.schedule_order_days)
async def seller_choose_order_days(message: Message, state: FSMContext):

    text = message.text.strip().lower()

    data = await state.get_data()

    order_days = data.get("order_days", [])

    # ---------------- ГОТОВО ----------------

    if text == "✅ готово".lower():

        if not order_days:
            await message.answer(
                "❌ Выберите хотя бы один день"
            )
            return

        await message.answer(
            "Выберите день доставки:",
            reply_markup=delivery_day_kb()
        )

        await state.set_state(
            SellerRegister.schedule_delivery_day
        )

        return

    # ---------------- ПРОВЕРКА ДНЯ ----------------

    if text not in WEEK_DAYS:

        await message.answer(
            "❌ Выберите день кнопкой",
            reply_markup=delivery_day_kb()
        )

        return

    # ---------------- ЗАЩИТА ОТ ДУБЛЕЙ ----------------

    if text in order_days:

        await message.answer(
            f"⚠️ День '{text}' уже добавлен"
        )

        return

    # ---------------- СОХРАНЯЕМ ----------------

    order_days.append(text)

    await state.update_data(
        order_days=order_days
    )

    await message.answer(
        f"✅ Добавлено: {text}\n\n"
        f"Выбрано дней: {len(order_days)}"
    )


@router.message(SellerRegister.schedule_delivery_day)
async def seller_choose_delivery_day(message: Message, state: FSMContext):

    delivery_day = message.text.strip().lower()

    if delivery_day not in WEEK_DAYS:

        await message.answer(
            "❌ Выберите день кнопкой",
            reply_markup=delivery_day_kb()
        )

        return

    data = await state.get_data()

    district = data.get("district")
    order_days = data.get("order_days", [])

    seller = get_seller(message.from_user.id)

    if not seller:

        await message.answer("❌ Продавец не найден")

        await state.clear()

        return

    seller_id = seller["id"]

    # ---------------- СОХРАНЯЕМ В БАЗУ ----------------

    save_seller_schedule(
        seller_id=seller_id,
        district=district,
        order_days=order_days,
        delivery_day=delivery_day
    )

    # ---------------- ЗАВЕРШЕНИЕ ----------------

    await message.answer(
        "✅ График сохранён\n\n"
        "Регистрация завершена",
        reply_markup=seller_menu()
    )

    await state.clear()

# ================= ГРАФИК ============================

@router.message(F.text == "📅 График")
async def seller_schedule_menu(message: Message):

    await message.answer(
        "Выберите район:",
        reply_markup=seller_schedule_districts_kb()
    )


@router.callback_query(F.data.startswith("schedule_"))
async def show_schedule(call: CallbackQuery):

    district = call.data.replace("schedule_", "")

    seller = get_seller(call.from_user.id)

    schedule = get_seller_schedule(
        seller["id"],
        district
    )

    if not schedule:

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Настроить",
                        callback_data=f"setup_schedule_{district}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="close_schedule"
                    )
                ]
            ]
        )

        await call.message.answer(
            f"⚠️ Район {district} ещё не настроен",
            reply_markup=kb
        )

        await call.answer()
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"edit_schedule_{district}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="close_schedule"
                )
            ]
        ]
    )

    await call.message.answer(
        f"📍 Район: {district}\n\n"
        f"📥 Дни приёма:\n{schedule['order_days']}\n\n"
        f"🚚 День доставки:\n{schedule['delivery_day']}",
        reply_markup=kb
    )

    await call.answer()


@router.callback_query(F.data == "close_schedule")
async def close_schedule(call: CallbackQuery):

    await call.message.delete()
    await call.answer()


@router.callback_query(F.data.startswith("setup_schedule_"))
async def setup_schedule(call: CallbackQuery, state: FSMContext):

    district = call.data.replace(
        "setup_schedule_",
        ""
    )

    await state.update_data(
        district=district,
        order_days=[]
    )

    await state.set_state(
        SellerSchedule.order_days
    )

    await call.message.answer(
        f"📍 Район: {district}\n\n"
        "Выберите дни приёма заявок.\n"
        "После выбора нажмите ✅ Готово",
        reply_markup=week_days_kb()
    )

    await call.answer()


@router.callback_query(F.data.startswith("edit_schedule_"))
async def edit_schedule(call: CallbackQuery, state: FSMContext):

    district = call.data.replace(
        "edit_schedule_",
        ""
    )

    seller = get_seller(call.from_user.id)

    delete_seller_schedule(
        seller["id"],
        district
    )

    await state.update_data(
        district=district,
        order_days=[]
    )

    await state.set_state(
        SellerSchedule.order_days
    )

    await call.message.answer(
        f"✏️ Редактирование района: {district}\n\n"
        "Выберите дни приёма заявок",
        reply_markup=week_days_kb()
    )

    await call.answer()


@router.message(SellerSchedule.order_days)
async def seller_choose_order_days(message: Message, state: FSMContext):

    text = message.text.strip().lower()

    data = await state.get_data()

    order_days = data.get("order_days", [])

    # ---------------- ГОТОВО ----------------

    if text == "✅ готово".lower():

        if not order_days:
            await message.answer(
                "❌ Выберите хотя бы один день"
            )
            return

        await message.answer(
            "Выберите день доставки:",
            reply_markup=delivery_day_kb()
        )

        await state.set_state(
            SellerSchedule.delivery_day
        )

        return

    # ---------------- ПРОВЕРКА ДНЯ ----------------

    if text not in WEEK_DAYS:

        await message.answer(
            "❌ Выберите день кнопкой",
            reply_markup=delivery_day_kb()
        )

        return

    # ---------------- ЗАЩИТА ОТ ДУБЛЕЙ ----------------

    if text in order_days:

        await message.answer(
            f"⚠️ День '{text}' уже добавлен"
        )

        return

    # ---------------- СОХРАНЯЕМ ----------------

    order_days.append(text)

    await state.update_data(
        order_days=order_days
    )

    await message.answer(
        f"✅ Добавлено: {text}\n\n"
        f"Выбрано дней: {len(order_days)}"
    )

@router.message(SellerSchedule.delivery_day)
async def seller_choose_delivery_day(message: Message, state: FSMContext):

    delivery_day = message.text.strip().lower()

    if delivery_day not in WEEK_DAYS:

        await message.answer(
            "❌ Выберите день кнопкой",
            reply_markup=delivery_day_kb()
        )

        return

    data = await state.get_data()

    district = data.get("district")
    order_days = data.get("order_days", [])

    seller = get_seller(message.from_user.id)

    if not seller:

        await message.answer("❌ Продавец не найден")

        await state.clear()

        return

    seller_id = seller["id"]

    # ---------------- СОХРАНЯЕМ В БАЗУ ----------------

    save_seller_schedule(
        seller_id=seller_id,
        district=district,
        order_days=order_days,
        delivery_day=delivery_day
    )

    # ---------------- ЗАВЕРШЕНИЕ ----------------

    await message.answer(
        "✅ График сохранён",
        reply_markup=seller_menu()
    )

    await state.clear()

# ================= ПРЕДОПЛАТА ========================

@router.message(F.text == "💰 Предоплата")
async def seller_prepayment_menu(message: Message):

    seller = get_seller(message.from_user.id)

    prepayment = get_seller_prepayment(
        seller["id"]
    )

    if not prepayment:

        await message.answer(
            "💰 Предоплата не настроена.\n\n"
            "Сейчас магазины могут "
            "оформлять заказы без предоплаты.",
            reply_markup=prepayment_setup_kb()
        )

        return

    if prepayment["qr_photo"]:

        await message.answer_photo(
        photo=prepayment["qr_photo"],
        caption=(
            f"💰 Предоплата\n\n"
            f"Сумма: {prepayment['amount']} сом\n\n"
            f"Реквизиты:\n{prepayment['payment_details']}"
        ),
        reply_markup=prepayment_edit_kb()
        )

    else:

        await message.answer(
        f"💰 Предоплата\n\n"
        f"Сумма: {prepayment['amount']} сом\n\n"
        f"Реквизиты:\n{prepayment['payment_details']}",
        reply_markup=prepayment_edit_kb()
        )


@router.callback_query(F.data == "close_prepayment")
async def close_prepayment(call: CallbackQuery):

    await call.message.delete()

    await call.answer()


@router.callback_query(F.data == "setup_prepayment")
@router.callback_query(F.data == "edit_prepayment")
async def setup_prepayment(
    call: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SellerPrepayment.amount
    )

    await call.message.answer(
        "Введите сумму предоплаты:"
    )

    await call.answer()


@router.message(SellerPrepayment.amount)
async def prepayment_amount(
    message: Message,
    state: FSMContext
):

    try:
        amount = int(message.text)
    except:
        await message.answer(
            "Введите число"
        )
        return

    if amount <= 0:
        await message.answer(
            "Сумма должна быть больше 0"
        )
        return

    await state.update_data(
        amount=amount
    )

    await state.set_state(
        SellerPrepayment.details
    )

    await message.answer(
    "Введите реквизиты в формате:\n"
    "(Банк): (Реквизит)\n\n"
    "Пример:\n"
    "Мбанк: 996500000000"
    )


@router.message(SellerPrepayment.details)
async def prepayment_details(
    message: Message,
    state: FSMContext
):

    details = message.text.strip()

    if len(details) < 5:

        await message.answer(
            "Слишком короткие реквизиты"
        )

        return

    data = await state.get_data()

    await state.update_data(
    details=details
    )

    await state.set_state(
    SellerPrepayment.qr
    )

    await message.answer(
    "Отправьте QR-код для оплаты.\n\n"
    "Или напишите 'пропустить'"
    )


@router.message(SellerPrepayment.qr)
async def prepayment_qr(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    seller = get_seller(
        message.from_user.id
    )

    qr_photo = None

    if message.photo:

        qr_photo = message.photo[-1].file_id

    elif message.text.lower() != "пропустить":

        await message.answer(
            "Отправьте QR-код или напишите 'пропустить'"
        )
        return

    save_seller_prepayment(
        seller["id"],
        data["amount"],
        data["details"],
        qr_photo
    )

    await message.answer(
        "✅ Предоплата сохранена",
        reply_markup=seller_menu()
    )

    await state.clear()


@router.callback_query(F.data == "delete_prepayment")
async def delete_prepayment_handler(
    call: CallbackQuery
):

    seller = get_seller(
        call.from_user.id
    )

    delete_seller_prepayment(
        seller["id"]
    )

    await call.message.answer(
        "✅ Предоплата отключена"
    )

    await call.answer()

# ================= ДОБАВЛЕНИЕ ========================

@router.message(F.text == "➕ Добавить товар")
async def start_add_product(message: Message, state: FSMContext):

    seller = check_seller(message.from_user.id)

    if not seller:
        await message.answer("⛔ Нет доступа")
        return

    await state.clear()

    await state.update_data(seller_id=seller["id"])

    categories = get_categories(seller["id"])

    if not categories:
        await message.answer("Введите название категории:")
        await state.set_state(AddProduct.new_category)
        return

    await show_categories(message, categories)

    await state.set_state(AddProduct.category)


async def show_categories(message, categories):

    kb = categories_kb(categories, "cat_")

    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="➕ Новая категория",
            callback_data="cat_new"
        )
    ])

    await message.answer("Выберите категорию:", reply_markup=kb)


@router.callback_query(F.data.startswith("cat_"))
async def choose_category(call: CallbackQuery, state: FSMContext):

    if call.data == "cat_new":

        await call.message.answer("Введите название категории:")
        await state.set_state(AddProduct.new_category)
        await call.answer()
        return

    cat_id = int(call.data.split("_")[1])

    await state.update_data(category_id=cat_id)

    await call.message.answer("Введите название товара:")

    await state.set_state(AddProduct.name)

    await call.answer()


@router.message(AddProduct.new_category)
async def save_category(message: Message, state: FSMContext):

    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Слишком коротко")
        return

    data = await state.get_data()

    add_category(data["seller_id"], name)

    categories = get_categories(data["seller_id"])

    await message.answer("✅ Категория добавлена")

    await show_categories(message, categories)

    await state.set_state(AddProduct.category)

# ================= СОЗДАНИЕ ТОВАРА ===================

@router.message(AddProduct.name)
async def product_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text.strip())

    await message.answer("Введите фасовку:")

    await state.set_state(AddProduct.amount)


@router.message(AddProduct.amount)
async def product_amount(message: Message, state: FSMContext):

    await state.update_data(amount=message.text.strip())

    await message.answer("Отправьте фото:")

    await state.set_state(AddProduct.image)


@router.message(AddProduct.image, F.photo)
async def product_image(message: Message, state: FSMContext):

    await state.update_data(image=message.photo[-1].file_id)

    await message.answer("Введите цену:")

    await state.set_state(AddProduct.price)


@router.message(AddProduct.image)
async def no_photo(message: Message):

    await message.answer("Отправьте фото")


@router.message(AddProduct.price)
async def product_price(message: Message, state: FSMContext):

    try:
        price = float(message.text)
    except:
        await message.answer("Введите число")
        return

    await state.update_data(price=price)

    await message.answer("Введите остаток:")

    await state.set_state(AddProduct.stock)


@router.message(AddProduct.stock)
async def product_stock(message: Message, state: FSMContext):

    try:
        stock = int(message.text)
    except:
        await message.answer("Введите число")
        return

    await state.update_data(stock=stock)

    data = await state.get_data()

    add_product_full(**data)

    await message.answer("✅ Товар добавлен", reply_markup=seller_menu())

    await state.clear()

# ================= МОИ ТОВАРЫ ========================

@router.message(F.text == "📦 Мои товары")
async def my_products(message: Message):

    seller = check_seller(message.from_user.id)

    if not seller:
        await message.answer("⛔ Нет доступа")
        return

    categories = get_categories(seller["id"])

    if not categories:
        await message.answer("Нет категорий")
        return

    kb = categories_kb(categories, "mycat_")

    await message.answer("Выберите категорию:", reply_markup=kb)


@router.callback_query(F.data.startswith("mycat_"))
async def show_products(call: CallbackQuery):

    cat_id = int(call.data.split("_")[1])

    seller = get_seller(call.from_user.id)

    products = get_products_full_by_seller(seller["id"])

    products = [p for p in products if p["category_id"] == cat_id]

    await show_products_with_action(
        call.message,
        products,
        action_prefix=None,
        title="Товары:"
    )

    await call.answer()

# ================= УДАЛЕНИЕ ==========================

@router.message(F.text == "🗑 Удалить товар")
async def delete_start(message: Message, state: FSMContext):

    seller = check_seller(message.from_user.id)

    if not seller:
        return

    categories = get_categories(seller["id"])

    kb = categories_kb(categories, "delcat_")

    await message.answer("Выберите категорию:", reply_markup=kb)

    await state.set_state(DeleteProduct.category)


@router.callback_query(F.data.startswith("delcat_"), DeleteProduct.category)
async def delete_choose_category(call: CallbackQuery, state: FSMContext):

    cat_id = int(call.data.split("_")[1])

    seller = get_seller(call.from_user.id)

    products = get_products_full_by_seller(seller["id"])

    products = [p for p in products if p["category_id"] == cat_id]

    await show_products_with_action(
        call.message,
        products,
        "delprod_",
        "Выберите товар для удаления:"
    )

    await state.set_state(DeleteProduct.product)

    await call.answer()


@router.callback_query(F.data.startswith("delprod_"), DeleteProduct.product)
async def delete_product(call: CallbackQuery, state: FSMContext):

    pid = int(call.data.split("_")[1])

    delete_product_by_id(pid)

    await call.message.answer("✅ Товар удалён")

    await state.clear()

    await call.answer()

# ================= РЕДАКТИРОВАНИЕ ====================

@router.message(F.text == "✏️ Изменить товар")
async def edit_start(message: Message, state: FSMContext):

    seller = check_seller(message.from_user.id)

    if not seller:
        return

    categories = get_categories(seller["id"])

    kb = categories_kb(categories, "editcat_")

    await message.answer("Выберите категорию:", reply_markup=kb)

    await state.set_state(EditProduct.category)


@router.callback_query(F.data.startswith("editcat_"), EditProduct.category)
async def edit_choose_category(call: CallbackQuery, state: FSMContext):

    cat_id = int(call.data.split("_")[1])

    seller = get_seller(call.from_user.id)

    products = get_products_full_by_seller(seller["id"])

    products = [p for p in products if p["category_id"] == cat_id]

    await show_products_with_action(
        call.message,
        products,
        "editprod_",
        "Выберите товар для редактирования:"
    )

    await state.set_state(EditProduct.product)

    await call.answer()


@router.callback_query(F.data.startswith("editprod_"), EditProduct.product)
async def edit_choose_product(call: CallbackQuery, state: FSMContext):

    pid = int(call.data.split("_")[1])

    await state.update_data(product_id=pid)

    await call.message.answer(
        "Что изменить?",
        reply_markup=edit_fields_kb()
    )

    await state.set_state(EditProduct.field)

    await call.answer()


@router.callback_query(F.data.startswith("edit_"), EditProduct.field)
async def edit_choose_field(call: CallbackQuery, state: FSMContext):

    field = call.data.replace("edit_", "")

    if field == "cancel":
        await state.clear()
        await call.message.answer("❌ Отменено")
        return

    await state.update_data(field=field)

    texts = {
        "name": "Введите название:",
        "amount": "Введите фасовку:",
        "price": "Введите цену:",
        "stock": "Введите остаток:",
        "image": "Отправьте фото 📸"
    }

    await call.message.answer(texts[field])

    await state.set_state(EditProduct.value)

    await call.answer()


@router.message(EditProduct.value, F.photo)
async def edit_save_image(message: Message, state: FSMContext):

    data = await state.get_data()

    if data["field"] != "image":
        await message.answer("Введите текст")
        return

    update_product_field(
        data["product_id"],
        "image",
        message.photo[-1].file_id
    )

    await message.answer("✅ Картинка обновлена")

    await state.clear()


@router.message(EditProduct.value, F.text)
async def edit_save_value(message: Message, state: FSMContext):

    data = await state.get_data()

    value = message.text.strip()

    if data["field"] in ["price", "stock"]:
        try:
            value = float(value) if data["field"] == "price" else int(value)
        except:
            await message.answer("Введите число")
            return

    update_product_field(
        data["product_id"],
        data["field"],
        value
    )

    await message.answer("✅ Товар обновлён")

    await state.clear()

# ================= УДАЛЕНИЕ КАТЕГОРИИ =================

@router.message(F.text == "🗂 Удалить категорию")
async def delete_category_start(message: Message):

    seller = check_seller(message.from_user.id)

    if not seller:
        return

    categories = get_categories(seller["id"])

    kb = categories_kb(categories, "delcat2_")

    await message.answer("Выберите категорию:", reply_markup=kb)


@router.callback_query(F.data.startswith("delcat2_"))
async def delete_category_confirm(call: CallbackQuery):

    cat_id = int(call.data.split("_")[1])

    delete_category(cat_id)

    await call.message.answer("✅ Категория удалена с товарами")

    await call.answer()

# ---------------- ЗАКАЗЫ ----------------
@router.message(F.text == "📥 Заказы")
async def seller_orders(message: Message, state: FSMContext):
    seller = get_seller(message.from_user.id)

    if not seller:
        await message.answer("❌ Продавец не найден")
        return

    orders = get_seller_orders(seller["id"])

    if not orders:
        await message.answer("❌ Заказов нет.")
        return

    orders_dict = {}
    for o in orders:
        oid = o["order_id"]
        if oid not in orders_dict:
            orders_dict[oid] = {
                "status": o["status"],
                "address": o["address"],
                "total_amount": o["total_amount"],
                "items": []
            }
        orders_dict[oid]["items"].append(o)

    text = "📥 Заказы:\n\n"

    for order_id, data in orders_dict.items():
        text += f"🆔 Заказ #{order_id}\n"
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
                f"    Цена за ед.: {item['price']} сом\n"
                f"    Сумма: {item['total_price']} сом\n"
            )

        text += "\n"

    await message.answer(text)