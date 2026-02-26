from aiogram.fsm.state import State, StatesGroup

class SellerRegister(StatesGroup):
    shop_name = State()

class AddProduct(StatesGroup):

    category = State()
    new_category = State()

    name = State()
    amount = State()
    image = State()
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

class DeleteProduct(StatesGroup):
    category = State()
    product = State()


class EditProduct(StatesGroup):
    category = State()
    product = State()
    field = State()
    value = State()
