import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.reply import admin_menu
from app.keyboards.admin.statistics import (
    STATISTICS_ADMIN_BUTTON,
    STATISTICS_BACK_BUTTON,
    STATISTICS_BASE_BUTTON,
    STATISTICS_GENERAL_BUTTON,
    STATISTICS_MOVIE_BUTTON,
    STATISTICS_PANEL_BUTTON,
    STATISTICS_REFRESH_BUTTON,
    STATISTICS_SUBSCRIPTION_BUTTON,
    STATISTICS_TOP_MOVIES_BUTTON,
    STATISTICS_USER_ACTIVITY_BUTTON,
    statistics_menu,
)
from app.repositories.movie_base_repository import MovieBaseRepository
from app.repositories.movie_repository import MovieRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.statistics_service import StatisticsService

router = Router()
router.message.filter(AdminFilter())

logger = logging.getLogger(__name__)

STATISTICS_ERROR_MESSAGE = (
    "Statistikani olishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
)


async def _build_statistics_text(builder_name: str) -> str:
    async with async_session_maker() as session:
        service = StatisticsService(
            user_repository=UserRepository(session),
            movie_repository=MovieRepository(session),
            movie_base_repository=MovieBaseRepository(session),
            subscription_repository=SubscriptionRepository(session),
        )
        builder = getattr(service, builder_name)
        return await builder()


async def _answer_statistics(message: types.Message, builder_name: str) -> None:
    try:
        text = await _build_statistics_text(builder_name)
    except (SQLAlchemyError, RuntimeError, ValueError):
        logger.exception("Statistikani olishda xatolik yuz berdi")
        await message.answer(STATISTICS_ERROR_MESSAGE, reply_markup=statistics_menu)
        return

    await message.answer(text, reply_markup=statistics_menu)


@router.message(F.text == STATISTICS_PANEL_BUTTON)
async def open_statistics_panel(message: types.Message, state: FSMContext):
    await state.clear()
    await _answer_statistics(message, "build_general_stats")


@router.message(F.text == STATISTICS_GENERAL_BUTTON)
async def show_general_statistics(message: types.Message):
    await _answer_statistics(message, "build_general_stats")


@router.message(F.text == STATISTICS_USER_ACTIVITY_BUTTON)
async def show_user_activity_statistics(message: types.Message):
    await _answer_statistics(message, "build_user_activity_stats")


@router.message(F.text == STATISTICS_MOVIE_BUTTON)
async def show_movie_statistics(message: types.Message):
    await _answer_statistics(message, "build_movie_stats")


@router.message(F.text == STATISTICS_SUBSCRIPTION_BUTTON)
async def show_subscription_statistics(message: types.Message):
    await _answer_statistics(message, "build_subscription_stats")


@router.message(F.text == STATISTICS_TOP_MOVIES_BUTTON)
async def show_top_movies_statistics(message: types.Message):
    await _answer_statistics(message, "build_top_movies_stats")


@router.message(F.text == STATISTICS_BASE_BUTTON)
async def show_base_statistics(message: types.Message):
    await _answer_statistics(message, "build_base_stats")


@router.message(F.text == STATISTICS_REFRESH_BUTTON)
async def refresh_statistics(message: types.Message):
    await _answer_statistics(message, "build_general_stats")


@router.message(F.text == STATISTICS_BACK_BUTTON)
async def statistics_back_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Admin panelga qaytdingiz.",
        reply_markup=admin_menu,
    )


@router.message(F.text == STATISTICS_ADMIN_BUTTON)
async def statistics_admin_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Admin panelga qaytdingiz.",
        reply_markup=admin_menu,
    )
