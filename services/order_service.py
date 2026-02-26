# services/order_service.py

from database import create_order, get_product


def create_new_order(buyer_id: int, data: dict):

    product = get_product(data["product_id"])

    order_id = create_order(
        buyer_id,
        product[1],
        product[0],
        int(data["amount"]),
        data["address"]
    )

    return order_id