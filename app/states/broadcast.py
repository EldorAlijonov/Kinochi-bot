from aiogram.fsm.state import State, StatesGroup


class BroadcastSendState(StatesGroup):
    waiting_post = State()
    choosing_target = State()
    confirming = State()


class BroadcastDeleteState(StatesGroup):
    waiting_campaign_id = State()
    confirming = State()


class BroadcastCancelState(StatesGroup):
    waiting_job_id = State()
    confirming = State()
