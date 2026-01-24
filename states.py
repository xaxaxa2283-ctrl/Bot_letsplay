from aiogram.fsm.state import StatesGroup, State

class Order(StatesGroup):
    period = State()
    region = State()
    sub_type = State()
    confirm = State()

    waiting_for_account_type = State()
    waiting_for_credentials = State()


class PromoState(StatesGroup):
    waiting_for_promo = State()


class GameOrder(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_price_confirmation = State()
    waiting_for_account_type = State()
    waiting_for_credentials = State()


from aiogram.fsm.state import StatesGroup, State

class TopupOrder(StatesGroup):
    region = State()
    amount = State()
    credentials = State()
    confirm = State()
