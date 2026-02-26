# services/stock_service.py

from database import decrease_stock, get_product


def reduce_stock(product_id: int, amount: int):

    product = get_product(product_id)

    if not product:
        return False

    if product[5] < amount:
        return False

    decrease_stock(product_id, amount)

    return True