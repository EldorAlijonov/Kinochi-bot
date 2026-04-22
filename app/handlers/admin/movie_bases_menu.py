from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.filters.admin import AdminFilter
from app.keyboards.admin.movies import (
    MOVIES_ADD_BASE_BUTTON,
    MOVIES_ADMIN_BUTTON,
    MOVIES_BACK_BUTTON,
    MOVIES_PANEL_BUTTON,
    movie_base_add_menu,
    movies_menu,
)
from app.keyboards.admin.reply import admin_menu

router = Router()
router.message.filter(AdminFilter())


@router.message(lambda message: message.text == MOVIES_PANEL_BUTTON)
async def open_movies_panel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Kinolar bazasi bo'limi.",
        reply_markup=movies_menu,
    )


@router.message(lambda message: message.text == MOVIES_ADD_BASE_BUTTON)
async def open_add_movie_base_menu(message: types.Message):
    await message.answer(
        "Qanday baza qo'shmoqchisiz?",
        reply_markup=movie_base_add_menu,
    )


@router.message(lambda message: message.text == MOVIES_BACK_BUTTON)
async def movies_back_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Kinolar bazasi bo'limiga qaytdingiz.",
        reply_markup=movies_menu,
    )


@router.message(lambda message: message.text == MOVIES_ADMIN_BUTTON)
async def movies_admin_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Admin panelga qaytdingiz.",
        reply_markup=admin_menu,
    )
