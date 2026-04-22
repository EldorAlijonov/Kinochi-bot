from aiogram.fsm.state import State, StatesGroup


class AddPublicMovieBaseState(StatesGroup):
    channel_reference = State()


class AddPrivateMovieBaseState(StatesGroup):
    invite_link = State()
    chat_reference = State()


class UploadMovieState(StatesGroup):
    selecting_base = State()
    waiting_media = State()


class DeleteMovieBaseState(StatesGroup):
    selecting = State()
    confirming = State()


class DeleteMovieState(StatesGroup):
    waiting_code = State()
    confirming = State()
