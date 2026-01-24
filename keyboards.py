from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def cancel_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def cancel_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="flow_cancel")]
    ])

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛒 Купить подписку"),
                KeyboardButton(text="🛒 Купить игру")
            ],
            [
                KeyboardButton(text="💸 Пополнить аккаунт"),
                KeyboardButton(text="📦 Мои заказы"),
                KeyboardButton(text="💰 Прайс"),


            ]
        ],
        resize_keyboard=True
    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="menu:buy")],
        [InlineKeyboardButton(text="💰 Прайс", callback_data="menu:price")],
        [InlineKeyboardButton(text="🎮 Узнать цену игры", callback_data="menu:game")]
    ])


def period_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц", callback_data="period:1 месяц")],
        [InlineKeyboardButton(text="3 месяца", callback_data="period:3 месяца")],
        [InlineKeyboardButton(text="1 год", callback_data="period:1 год")]
    ])

def account_type_kb_simple():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 На мой аккаунт", callback_data="game_account:own")],
            [InlineKeyboardButton(text="🆕 Новый аккаунт", callback_data="game_account:new")]
        ]
    )


def region_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇹🇷 Турция", callback_data="region:Турция")],
        [InlineKeyboardButton(text="🌎 СНГ", callback_data="region:СНГ")]
    ])




def sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Plus Deluxe", callback_data="sub:Plus Deluxe")],
        [InlineKeyboardButton(text="Plus Extra", callback_data="sub:Plus Extra")],
        [InlineKeyboardButton(text="Plus Essential", callback_data="sub:Plus Essential")],
        [InlineKeyboardButton(text="EA Play", callback_data="sub:EA Play")]
    ])



def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no")]
    ])


def pay_kb(pay_url, order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{order_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_order:{order_id}")]
        ]
    )






def admin_order_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Закрыть", callback_data=f"admin_done:{order_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"admin_cancel:{order_id}")]
    ])



# ===== ХЕЛПЕРЫ =====

from storage import is_vip

def is_wholesale(user_id: int) -> bool:
    """
    ОПТ = VIP пользователь (по промокоду)
    """
    return is_vip(user_id)


def sub_account_type_kb():
    """
    Клавиатура выбора аккаунта для ПОДПИСКИ
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 На мой аккаунт", callback_data="sub_account:own")],
            [InlineKeyboardButton(text="🆕 Новый аккаунт", callback_data="sub_account:new")]
        ]
    )



from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def pay_methods_kb(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Crypto (USDT)", callback_data=f"pay_method:crypto:{order_id}")],
        [InlineKeyboardButton(text="🏦 Перевод на карту", callback_data=f"pay_method:card:{order_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_order:{order_id}")]
    ])

def pay_crypto_kb(pay_url: str, order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить (Crypto)", url=pay_url)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"i_paid:{order_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_order:{order_id}")]
    ])

def pay_card_kb(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"i_paid:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pay_back:{order_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_order:{order_id}")]
    ])

def admin_confirm_payment_kb(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплата получена", callback_data=f"admin_pay_ok:{order_id}")],
        [InlineKeyboardButton(text="❌ Не оплачено", callback_data=f"admin_pay_no:{order_id}")]
    ])



from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def topup_region_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 СНГ", callback_data="topup_region:СНГ")],
        [InlineKeyboardButton(text="🌍 Турция", callback_data="topup_region:Турция")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="topup_cancel")],
    ])

def topup_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="topup_confirm:yes")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="topup_confirm:no")],
    ])



from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def cancel_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
