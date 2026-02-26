import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID

from keyboards import seller_menu, edit_fields_kb
from states import SellerRegister, AddProduct, DeleteProduct, EditProduct

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
    get_product_by_name_and_seller,
    get_seller_orders
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

@router.message(F.text == "🏪 Продавец")
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
        await message.answer("Введите название магазина:")
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

    await message.answer("✅ Магазин сохранён", reply_markup=seller_menu())

    await state.clear()

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

    text = "📥 Заказы:\n\n"

    for o in orders:
        order_id = o["id"]
        product_name = o["name"]
        status = o["status"]

        try:
            amount = int(float(o["amount"]))
        except (TypeError, ValueError):
            amount = 0

        product = get_product_by_name_and_seller(product_name, seller["id"])
        packaging = product["amount"] if product else "Не указано"

        text += (
            f"🆔 Заказ #{order_id}\n"
            f"📦 Товар: {product_name}\n"
            f"📊 Фасовка: {packaging}\n"
            f"🔢 Кол-во: {amount}\n"
            f"📌 Статус: {status}\n\n"
        )

    await message.answer(text)