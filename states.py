from aiogram.fsm.state import State, StatesGroup

# Состояния для регистрации продавца
class SellerRegister(StatesGroup):
    shop_name = State()

# Состояния для добавления товара
class AddProduct(StatesGroup):
    name = State()
    amount = State()
    price = State()

# Состояния для оформления заказа покупателем
class OrderState(StatesGroup):
    amount = State()
    address = State()
    confirm = State()

# Состояния для отклонения заказа продавцом
class DeclineState(StatesGroup):
    order_id = State()
    reason = State()
