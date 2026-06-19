from aiogram.fsm.state import State, StatesGroup

class SellerRegister(StatesGroup):
    shop_name = State()
    schedule_district = State()
    schedule_order_days = State()
    schedule_delivery_day = State()

class SellerSchedule(StatesGroup):
    order_days = State()
    delivery_day = State()

class SellerPrepayment(StatesGroup):
    amount = State()
    details = State()
    qr = State()

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
    register_name = State()    
    register_district = State()
    register_address = State()  
    register_phone = State()
    search = State() 

class ProfileEdit(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_district = State()
    waiting_for_phone = State()

class DeleteProduct(StatesGroup):
    category = State()
    product = State()


class EditProduct(StatesGroup):
    category = State()
    product = State()
    field = State()
    value = State()

class OrdersView(StatesGroup):
    page = State()

class BuyerStockState(StatesGroup):
    page = State()