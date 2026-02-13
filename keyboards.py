from typing import List, Iterable, Optional

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)

# ------------------- КОНСТАНТЫ -------------------

BTN_BUYER = "🛒 Покупатель"
BTN_SELLER = "🏪 Продавец"

BTN_ADD_PRODUCT = "➕ Добавить товар"
BTN_MY_PRODUCTS = "📦 Мои товары"
BTN_DELETE_PRODUCT = "🗑 Удалить товар"
BTN_ORDERS = "📥 Заказы"

BTN_SHOPS = "📋 Список магазинов"

BTN_CONFIRM = "✅ Подтвердить"
BTN_CANCEL = "❌ Отменить"

BTN_ACCEPT = "✅ Принять"
BTN_DECLINE = "❌ Отклонить"


# ------------------- ВСПОМОГАТЕЛЬНЫЕ -------------------

def _safe_str(value, default: str = "—") -> str:
    """
    Безопасно приводит к строке
    """
    if value is None:
        return default
    return str(value)


def _safe_iter(data: Optional[Iterable]) -> List:
    """
    Гарантирует список
    """
    if not data:
        return []
    return list(data)


# ------------------- ОСНОВНЫЕ КЛАВИАТУРЫ -------------------

def role_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BUYER)],
            [KeyboardButton(text=BTN_SELLER)]
        ],
        resize_keyboard=True,
        selective=True
    )


def seller_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_PRODUCT)],
            [KeyboardButton(text=BTN_MY_PRODUCTS)],
            [KeyboardButton(text=BTN_DELETE_PRODUCT)],
            [KeyboardButton(text=BTN_ORDERS)]
        ],
        resize_keyboard=True,
        selective=True
    )


def buyer_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SHOPS)]
        ],
        resize_keyboard=True,
        selective=True
    )


def hide_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ------------------- INLINE КЛАВИАТУРЫ -------------------

def shops_kb(shops) -> InlineKeyboardMarkup:
    """
    shops = [(id, name), ...]
    """

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for shop in _safe_iter(shops):

        if len(shop) < 2:
            continue

        shop_id = shop[0]
        name = _safe_str(shop[1], "Без названия")

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"shop_{shop_id}"
            )
        ])

    return kb


def products_kb(products) -> InlineKeyboardMarkup:
    """
    products = [(id, name, amount, price), ...]
    """

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for product in _safe_iter(products):

        if len(product) < 4:
            continue

        product_id = product[0]
        name = _safe_str(product[1])
        amount = _safe_str(product[2])
        price = _safe_str(product[3])

        text = f"{name} | 📦 {amount} | 💰 {price} сом"

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"product_{product_id}"
            )
        ])

    return kb


def order_confirm_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_ACCEPT,
                    callback_data=f"order_ok_{order_id}"
                ),
                InlineKeyboardButton(
                    text=BTN_DECLINE,
                    callback_data=f"order_no_{order_id}"
                )
            ]
        ]
    )


def order_confirm_buyer_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_CONFIRM,
                    callback_data="buyer_confirm_yes"
                ),
                InlineKeyboardButton(
                    text=BTN_CANCEL,
                    callback_data="buyer_confirm_no"
                )
            ]
        ]
    )


def delete_products_kb(products) -> InlineKeyboardMarkup:
    """
    products = [(id, name, amount, price), ...]
    """

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for product in _safe_iter(products):

        if len(product) < 4:
            continue

        product_id = product[0]
        name = _safe_str(product[1])
        amount = _safe_str(product[2])
        price = _safe_str(product[3])

        text = f"🗑 {name} | {amount} шт | {price} сом"

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"delprod_{product_id}"
            )
        ])

    return kb