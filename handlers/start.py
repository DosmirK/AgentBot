
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards import role_kb


router = Router()


# ---------------- START ----------------

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "Кто вы?",
        reply_markup=role_kb()
    )