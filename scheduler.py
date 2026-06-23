
from database import get_all_buyers, get_buyer_sellers, get_ready_order, can_order_today, group_ready_orders
from keyboards import ready_order_kb

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo

scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Bishkek"))

async def send_order_reminders(bot):

    buyers = get_all_buyers()

    for buyer in buyers:

        sellers = get_buyer_sellers(buyer["tg_id"])

        for seller in sellers:

            if not can_order_today(seller["id"], buyer["district"]):
                continue

            ready_items = get_ready_order(buyer["id"])

            if not ready_items:
                continue

            grouped = group_ready_orders(ready_items)

            if seller["id"] not in grouped:
                continue

            data = grouped[seller["id"]]

            text = (
                f"🔔 Сегодня день приема заявок\n\n"
                f"🏪 {seller['shop_name']}\n\n"
            )

            for item in data["items"]:
                text += (
                    f"📦 {item['product_name']}\n"
                    f"{item['quantity']} шт × "
                    f"{item['price']} = "
                    f"{item['sum']} сом\n\n"
                )

            text += f"💵 Итого: {data['total_sum']} сом"

            await bot.send_message(
                buyer["tg_id"],
                text,
                reply_markup=ready_order_kb(seller["id"])
            )

def setup_scheduler(bot):

    if scheduler.running:
        return

    scheduler.add_job(
        send_order_reminders,
        "cron",
        hour=13,
        minute=00,
        args=[bot]
    )

    scheduler.start()