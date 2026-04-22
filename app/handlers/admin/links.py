import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import async_session_maker
from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import CANCEL_BUTTON, cancel_keyboard
from app.keyboards.admin.subscriptions import SUBSCRIPTIONS_EXTERNAL_LINK_BUTTON, subscriptions_menu
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService
from app.services.subscription_validator import validate_title
from app.states.subscription import AddExternalLinkState
from app.utils.text import safe_html

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())


@router.message(F.text == SUBSCRIPTIONS_EXTERNAL_LINK_BUTTON)
async def start_add_external_link(message: types.Message, state: FSMContext):
    await state.set_state(AddExternalLinkState.title)
    await message.answer(
        "Homiy havola nomini yuboring:",
        reply_markup=cancel_keyboard,
    )


@router.message(AddExternalLinkState.title, F.text, F.text != CANCEL_BUTTON)
async def get_external_link_title(message: types.Message, state: FSMContext):
    title = (message.text or "").strip()
    error = validate_title(title)

    if error:
        await message.answer(error, reply_markup=cancel_keyboard)
        return

    await state.update_data(title=title)
    await state.set_state(AddExternalLinkState.url)
    await message.answer(
        "Homiy havolani yuboring.\n\nMasalan:\n<code>https://example.com</code>",
        reply_markup=cancel_keyboard,
    )


@router.message(AddExternalLinkState.title)
async def invalid_external_link_title_input(message: types.Message):
    await message.answer(
        "Iltimos, havola nomini matn ko'rinishida yuboring.",
        reply_markup=cancel_keyboard,
    )


@router.message(AddExternalLinkState.url, F.text, F.text != CANCEL_BUTTON)
async def get_external_link_url(message: types.Message, state: FSMContext):
    url = (message.text or "").strip()
    data = await state.get_data()
    title = data.get("title")

    if not title:
        await state.clear()
        await message.answer(
            "Ma'lumotlar topilmadi. Jarayonni boshidan boshlang.",
            reply_markup=subscriptions_menu,
        )
        return

    async with async_session_maker() as session:
        repository = SubscriptionRepository(session)
        service = SubscriptionService(repository)

        try:
            result = await service.create_external_link(
                title=title,
                url=url,
            )
        except SQLAlchemyError:
            logger.exception("External link saqlashda xatolik yuz berdi")
            await message.answer(
                "Homiy havolani saqlashda vaqtinchalik database xatosi yuz berdi.",
                reply_markup=cancel_keyboard,
            )
            return

    if not result["ok"]:
        await message.answer(result["message"], reply_markup=cancel_keyboard)
        return

    subscription = result["subscription"]
    await state.clear()
    await message.answer(
        "Havola qo'shildi.\n\n"
        f"<b>Obuna nomi:</b> {safe_html(subscription.title)}\n"
        "<b>Turi:</b> Homiy havola\n"
        f"<b>Havola:</b> {safe_html(subscription.invite_link)}",
        reply_markup=subscriptions_menu,
    )


@router.message(AddExternalLinkState.url)
async def invalid_external_link_url_input(message: types.Message):
    await message.answer(
        "Iltimos, havolani matn ko'rinishida yuboring.",
        reply_markup=cancel_keyboard,
    )
