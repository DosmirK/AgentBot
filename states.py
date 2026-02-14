from aiogram.fsm.state import State, StatesGroup

class SellerRegister(StatesGroup):
    shop_name = State()

class AddProduct(StatesGroup):
    name = State()
    amount = State()
    price = State()
    stock = State()

class OrderState(StatesGroup):
    amount = State()
    address = State()
    confirm = State()

class DeclineState(StatesGroup):
    order_id = State()
    reason = State()

class BuyerState(StatesGroup):
    search = State()

class EditProduct(StatesGroup):
    choose = State()
    field = State()
    value = State()
