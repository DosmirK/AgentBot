import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN

from database import create_tables

from handlers.start import router as start_router
from handlers.admin import router as admin_router
from handlers.seller import router as seller_router
from handlers.buyer import router as buyer_router
from handlers.orders import router as orders_router
from handlers.other import router as other_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


async def main():

    bot = Bot(TOKEN)

    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(seller_router)
    dp.include_router(buyer_router)
    dp.include_router(orders_router)
    dp.include_router(other_router)

    create_tables()

    logging.info("🤖 Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())