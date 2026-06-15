from aiogram.fsm.state import State, StatesGroup


class PaymentFlow(StatesGroup):
    choosing_plan = State()
    choosing_method = State()
    waiting_screenshot = State()
    waiting_click_confirm = State()


class PhoneFlow(StatesGroup):
    agreeing = State()
    entering_phone = State()
    entering_code = State()
    entering_password = State()


class AdvertisementFlow(StatesGroup):
    menu = State()
    adding = State()
    replacing = State()
    confirm_clear = State()


class GroupFlow(StatesGroup):
    choosing_folder = State()


class IntervalFlow(StatesGroup):
    choosing = State()


class SendingFlow(StatesGroup):
    active = State()


class AdminFlow(StatesGroup):
    panel = State()
    viewing_users = State()
    user_detail = State()
    broadcast = State()
    ban_input = State()
    edit_sub = State()
