from typing import List, Iterable, Optional
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)

from data import DISTRICTS, WEEK_DAYS

# ------------------- КОНСТАНТЫ -------------------
BTN_BUYER = "🛒 Магазин"
BTN_SELLER = "🏪 Фирма"

BTN_ADD_PRODUCT = "➕ Добавить товар"
BTN_MY_PRODUCTS = "📦 Мои товары"
BTN_DELETE_PRODUCT = "🗑 Удалить товар"
BTN_EDIT_PRODUCT = "✏️ Изменить товар"
BTN_DELETE_CATEGORY = "🗂 Удалить категорию"
BTN_ORDERS = "📥 Заказы"
BTN_SCHEDULE = "📅 График"
BTN_PREPAYMENT = "💰 Предоплата"

BTN_SHOPS = "📋 Список фирм"

BTN_CONFIRM = "✅ Подтвердить"
BTN_CANCEL = "❌ Отменить"

BTN_ACCEPT = "✅ Принять"
BTN_DECLINE = "❌ Отклонить"

# ------------------- ВСПОМОГАТЕЛЬНЫЕ -------------------
def _safe_str(value, default: str = "—") -> str:
    
    if value is None:
        return default
    return str(value)


def _safe_iter(data: Optional[Iterable]) -> List:
    
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
            [
                KeyboardButton(text=BTN_ADD_PRODUCT),
                KeyboardButton(text=BTN_MY_PRODUCTS)
            ],
            [
                KeyboardButton(text=BTN_EDIT_PRODUCT),
                KeyboardButton(text=BTN_DELETE_PRODUCT)
            ],
            [
                KeyboardButton(text=BTN_DELETE_CATEGORY),
                KeyboardButton(text=BTN_ORDERS)
            ],
            [
                KeyboardButton(text=BTN_SCHEDULE),
                KeyboardButton(text=BTN_PREPAYMENT)
            ]
        ],
        resize_keyboard=True
    )

def prepayment_setup_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Настроить",
                    callback_data="setup_prepayment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="close_prepayment"
                )
            ]
        ]
    )

def prepayment_edit_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data="edit_prepayment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Отключить",
                    callback_data="delete_prepayment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="close_prepayment"
                )
            ]
        ]
    )

def prepayment_confirm_kb():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Я оплатил",
                    callback_data="prepayment_done"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="prepayment_cancel"
                )
            ]
        ]
    )

def buyer_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SHOPS)],
            [KeyboardButton(text="📥 Мои заказы"), KeyboardButton(text="👤 Профиль")]
        ],
        resize_keyboard=True,
        selective=True
    )

def repeat_order_kb(order_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Повторить заказ",
                    callback_data=f"repeat_order_{order_id}"
                )
            ]
        ]
    )

def orders_pagination_kb(page, total_pages):

    buttons = []

    row = []

    if page > 0:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="orders_prev"
            )
        )

    if page < total_pages:
        row.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data="orders_next"
            )
        )

    buttons.append(row)

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

def profile_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Изменить название")],
            [KeyboardButton(text="🗺 Изменить район")],
            [KeyboardButton(text="📍 Изменить адрес")],
            [KeyboardButton(text="📞 Изменить телефон")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def hide_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()

def week_days_kb():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="понедельник"),
                KeyboardButton(text="вторник")
            ],
            [
                KeyboardButton(text="среда"),
                KeyboardButton(text="четверг")
            ],
            [
                KeyboardButton(text="пятница"),
                KeyboardButton(text="суббота")
            ],
            [
                KeyboardButton(text="воскресенье")
            ],
            [
                KeyboardButton(text="✅ Готово")
            ]
        ],
        resize_keyboard=True
    )

def delivery_day_kb():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="понедельник"),
                KeyboardButton(text="вторник")
            ],
            [
                KeyboardButton(text="среда"),
                KeyboardButton(text="четверг")
            ],
            [
                KeyboardButton(text="пятница"),
                KeyboardButton(text="суббота")
            ],
            [
                KeyboardButton(text="воскресенье")
            ]
        ],
        resize_keyboard=True
    )

def district_kb():
    rows = []

    for district in DISTRICTS:
        rows.append([KeyboardButton(text=district)])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True
    )


def seller_schedule_districts_kb():

    buttons = []

    for district in DISTRICTS:
        buttons.append([
            InlineKeyboardButton(
                text=district,
                callback_data=f"schedule_{district}"
            )
        ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

# ------------------- INLINE КЛАВИАТУРЫ -------------------
def shops_kb(shops) -> InlineKeyboardMarkup:

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for shop in shops:

        shop_id = shop["id"]
        name = shop.get("shop_name", "Без названия")

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"shop_{shop_id}"
            )
        ])

    return kb

def products_kb(products) -> InlineKeyboardMarkup:

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

def search_products_kb(products) -> InlineKeyboardMarkup:

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for product in _safe_iter(products):

        if len(product) < 4:
            continue

        product_id = product[0]
        name = _safe_str(product[2])
        amount = _safe_str(product[3])
        price = _safe_str(product[4])

        text = f"{name} | 📦 {amount} | 💰 {price} сом"

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"product_{product_id}"
            )
        ])

    return kb

def edit_products_kb(products):

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for p in products:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{p[1]} | {p[2]} | {p[3]} сом",
                callback_data=f"editprod_{p[0]}"
            )
        ])

    return kb

def edit_fields_kb():

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Название", callback_data="edit_name"),
            InlineKeyboardButton(text="📦 Фасовка", callback_data="edit_amount")
        ],
        [
            InlineKeyboardButton(text="💰 Цена", callback_data="edit_price"),
            InlineKeyboardButton(text="📊 Остаток", callback_data="edit_stock")
        ],
        [
            InlineKeyboardButton(text="🖼 Картинка", callback_data="edit_image")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")
        ]
    ])

    return kb

def order_confirm_kb(order_ids_str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=  BTN_ACCEPT,
                    callback_data=f"order_ok_{order_ids_str}"
                ),
                InlineKeyboardButton(
                    text= BTN_DECLINE,
                    callback_data=f"order_no_{order_ids_str}"
                ),
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

def categories_kb_buy(categories, prefix=""):

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for c in categories:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=c["name"],
                callback_data=f"{prefix}{c['id']}"
            )
        ])

    return kb

def categories_kb(categories):

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for cid, name in categories:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"📂 {name}",
                callback_data=f"cat_{cid}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="➕ Добавить категорию",
            callback_data="cat_add"
        )
    ])

    return kb


def product_select_kb(pid: int):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Выбрать",
                    callback_data=f"product_{pid}"
                )
            ]
        ]
    )

def cart_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить ещё")],
            [KeyboardButton(text="📦 Оформить заказ")],
            [KeyboardButton(text="❌ Очистить корзину")]
        ],
        resize_keyboard=True
    )