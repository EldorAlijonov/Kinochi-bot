from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from app.filters.admin import AdminFilter
from app.keyboards.admin.cancel import CANCEL_BUTTON
from app.keyboards.admin.movies import movies_menu
from app.keyboards.admin.reply import admin_menu
from app.keyboards.admin.subscriptions import subscriptions_menu
from app.states.broadcast import BroadcastCancelState, BroadcastDeleteState, BroadcastSendState
from app.states.movie import (
    AddPrivateMovieBaseState,
    AddPublicMovieBaseState,
    DeleteMovieBaseState,
    DeleteMovieState,
    UploadMovieState,
)
from app.states.subscription import (
    AddExternalLinkState,
    AddPrivateChannelState,
    AddPrivateGroupState,
    AddPublicChannelState,
    AddPublicGroupState,
    DeleteSubscriptionState,
)

router = Router()
router.message.filter(AdminFilter())

MOVIE_STATE_NAMES = {
    state.state
    for group in (
        AddPublicMovieBaseState,
        AddPrivateMovieBaseState,
        UploadMovieState,
        DeleteMovieBaseState,
        DeleteMovieState,
    )
    for state in group.__all_states__
}
SUBSCRIPTION_STATE_NAMES = {
    state.state
    for group in (
        AddPublicChannelState,
        AddPrivateChannelState,
        AddPublicGroupState,
        AddPrivateGroupState,
        AddExternalLinkState,
        DeleteSubscriptionState,
    )
    for state in group.__all_states__
}
BROADCAST_STATE_NAMES = {
    state.state
    for group in (
        BroadcastSendState,
        BroadcastDeleteState,
        BroadcastCancelState,
    )
    for state in group.__all_states__
}


@router.message(F.text == CANCEL_BUTTON)
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "Bekor qilinadigan jarayon yo'q.",
            reply_markup=admin_menu,
        )
        return

    reply_markup = admin_menu
    if current_state in MOVIE_STATE_NAMES:
        reply_markup = movies_menu
    elif current_state in SUBSCRIPTION_STATE_NAMES:
        reply_markup = subscriptions_menu
    elif current_state in BROADCAST_STATE_NAMES:
        from app.keyboards.admin.broadcast import broadcast_menu

        reply_markup = broadcast_menu

    await state.clear()
    await message.answer(
        "Amal bekor qilindi.",
        reply_markup=reply_markup,
    )
