from aiogram.fsm.state import State, StatesGroup


class UserSearchState(StatesGroup):
    waiting_query = State()


class UserBanState(StatesGroup):
    waiting_query = State()


class UserUnbanState(StatesGroup):
    waiting_query = State()


class BroadcastState(StatesGroup):
    choosing_audience = State()
    waiting_message = State()
