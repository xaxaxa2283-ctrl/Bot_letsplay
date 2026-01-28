from keyboards import (
    main_reply_keyboard,
    main_menu,
    period_kb,
    region_kb,
    sub_kb,
    confirm_kb,
    account_type_kb_simple,
    sub_account_type_kb,
    cancel_reply_kb,

    # оплата
    pay_methods_kb,
    pay_crypto_kb,
    pay_card_kb,
    admin_confirm_payment_kb,

    # пополнение
    topup_region_kb,
    topup_confirm_kb,
)


import sys
import asyncio
import uuid
import re
from typing import Optional, Tuple, Dict, Any

from keyboards import cancel_reply_kb, cancel_inline_kb

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import BOT_TOKEN, ADMIN_ID



from prices import (
    PRICES, get_price,
    TOPUP, VIP_TOPUP, TOPUP_CURRENCY, get_topup_fee, calc_topup_total
)

from storage import USERS, PROMO_CODES, save_json, is_vip
from states import Order, GameOrder, PromoState, TopupOrder
from payments import create_invoice
from orders_storage import load_orders, save_orders

print(sys.version)

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

ORDERS = load_orders()


# ----------------------------
# Orders helpers
# ----------------------------
def reload_orders() -> Dict[str, Any]:
    global ORDERS
    ORDERS = load_orders()
    return ORDERS


def get_order(order_id: str):
    reload_orders()
    return ORDERS.get(order_id)


# ----------------------------
# Helpers
# ----------------------------
def is_wholesale(user_id: int) -> bool:
    return is_vip(user_id)


def extract_order_id_from_text(text: str) -> Optional[str]:
    """
    Поддерживает варианты:
    - '🆔 1234abcd'
    - '🆔 order_id:1234abcd'
    - 'order_id:1234abcd'
    """
    if not text:
        return None

    if "🆔" in text:
        try:
            tail = text.split("🆔", 1)[1].strip()
            first_line = tail.split("\n", 1)[0].strip()
            if first_line.startswith("order_id:"):
                return first_line.split("order_id:", 1)[1].strip()
            return first_line
        except Exception:
            pass

    if "order_id:" in text:
        try:
            return text.split("order_id:", 1)[1].split("\n", 1)[0].strip()
        except Exception:
            pass

    return None


EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def validate_credentials_text(raw: str) -> Tuple[bool, Optional[str], Optional[str]]:
    if not raw:
        return False, None, "❌ Пустое сообщение. Пришлите данные аккаунта текстом."

    text = raw.strip()

    if len(text) < 15:
        return False, None, "❌ Слишком коротко. Пришлите данные полностью (почта/пароли/2FA и т.д.)."

    if len(text) > 3500:
        return False, None, "❌ Слишком много текста. Разбейте данные на 2 сообщения и отправьте первое."

    emails = EMAIL_RE.findall(text)
    if not emails:
        return False, None, "❌ Не вижу email в данных. Добавьте почту (например name@mail.com)."

    lowered = text.lower()
    has_password_keyword = any(k in lowered for k in ["пароль", "password", "pass"])
    has_dash_value = bool(re.search(r".+\s*[-:]\s*\S{4,}", text))

    if not (has_password_keyword or has_dash_value):
        return False, None, "❌ Не вижу паролей. Добавьте строки с паролями (например: 'Пароль - qwerty123')."

    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    return True, cleaned, None


# ----------------------------
# START / PROMO
# ----------------------------
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()  # ✅ ВАЖНО: убирает "залипший процесс"
    user_id = str(message.from_user.id)

    if user_id in USERS:
        user_type = USERS[user_id]
        await message.answer(
            f"Привет! Вы {user_type} клиент. Выберите действие:",
            reply_markup=main_reply_keyboard(),
        )
        return

    await message.answer(
        "Привет! Если у вас есть промокод оптовика, введите его сейчас. "
        "Если нет — напишите 'нет'."
    )
    await state.set_state(PromoState.waiting_for_promo)


@dp.message(StateFilter(PromoState.waiting_for_promo))
async def check_promo(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    promo = message.text.strip()

    if promo in PROMO_CODES:
        USERS[user_id] = "VIP"
        save_json("users.json", USERS)
        await message.answer(
            "🎉 Промокод принят! Вы VIP клиент (ОПТ). Оплата не требуется.",
            reply_markup=main_reply_keyboard(),
        )
    else:
        USERS[user_id] = "REGULAR"
        save_json("users.json", USERS)
        await message.answer(
            "Вы зашли в розницу. После подтверждения заказа потребуется оплата.",
            reply_markup=main_reply_keyboard(),
        )

    await state.clear()
from aiogram.filters import Command


@dp.callback_query(F.data == "flow_cancel")
async def flow_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ Отменено", reply_markup=main_menu())


@dp.message(Command("cancel"))
@dp.message(F.text, F.text.func(lambda t: "отмена" in (t or "").strip().lower()))
async def cancel_any_flow(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Отменено", reply_markup=main_reply_keyboard())

@dp.message(~StateFilter(None), F.text.in_({"🛒 Купить игру", "🛒 Купить подписку", "💸 Пополнить аккаунт"}))
async def busy_flow_guard(message: Message):
    await message.answer(
        "⚠️ У вас уже запущен процесс.\nСначала завершите его или нажмите «❌ Отмена».",
        reply_markup=cancel_reply_kb(),
    )

# ----------------------------
# PRICE
# ----------------------------
@dp.message(StateFilter(None), F.text == "💰 Прайс")
async def price_from_keyboard(message: Message):
    user_id = message.from_user.id
    user_is_vip = is_vip(user_id)

    text = "💰 Прайс\n"
    text += "👑 ОПТ (VIP)\n\n" if user_is_vip else "💳 Розница\n\n"

    # --- ПОДПИСКИ (через get_price) ---
    for region, periods in PRICES.items():  # берем структуру (регионы/периоды/названия), цены считаем отдельно
        text += f"🌍 {region}\n"
        for period, subs in periods.items():
            text += f"  📆 {period}\n"
            for sub_name in subs.keys():
                try:
                    price = get_price(
                        user_id=user_id,
                        region=region,
                        period=period,
                        sub_type=sub_name,
                    )
                    text += f"    {sub_name}: {price} ₽\n"
                except ValueError:
                    continue
        text += "\n"

    # --- ПОПОЛНЕНИЕ (разделение VIP/Розница) ---
    tables = VIP_TOPUP if user_is_vip else TOPUP
    label = "👑 ОПТ (VIP)" if user_is_vip else "💳 Розница"

    text += "💸 Пополнение аккаунта:\n"
    text += f"{label}:\n"

    for region, tiers in tables.items():
        cur = TOPUP_CURRENCY.get(region, "")
        text += f"🌍 {region} ({cur})\n"
        for t in tiers:
            text += f"  {t['from']}-{t['to']}: комиссия {t['fee']}{cur}\n"
        text += "\n"

    await message.answer(text)




# ----------------------------
# MY ORDERS
# ----------------------------
@dp.message(F.text == "📦 Мои заказы")
async def my_orders(message: Message):
    user_id = message.from_user.id
    reload_orders()

    text = "📦 Ваши заказы:\n\n"
    found = False

    for oid, order in ORDERS.items():
        if order.get("user_id") != user_id or order.get("status") != "DONE":
            continue

        found = True
        d = order.get("data", {})

        if order.get("type") == "subscription":
            text += (
                f"🆔 {oid}\n"
                f"📦 Подписка\n"
                f"{d.get('subscription')} | {d.get('period')} | {d.get('region')}\n"
                f"💰 {d.get('price', '-') } ₽\n"
                f"📄 Данные:\n{order.get('credentials', '-')}\n\n"
            )

        elif order.get("type") == "game":
            text += (
                f"🆔 {oid}\n"
                f"🎮 Игра: {d.get('game_name')}\n"
                f"💰 {d.get('price', '-') } ₽\n"
                f"📄 Данные:\n{order.get('credentials', '-')}\n\n"
            )

        elif order.get("type") == "topup":
            cur = d.get("currency", TOPUP_CURRENCY.get(d.get("region", ""), ""))
            text += (
                f"🆔 {oid}\n"
                f"💸 Пополнение\n"
                f"🌍 {d.get('region')} ({cur})\n"
                f"💰 Сумма: {d.get('amount')}{cur}\n"
                f"➕ Комиссия: {d.get('fee')}{cur}\n"
                f"✅ Итого: {d.get('total')}{cur}\n"
                f"📄 Результат:\n{order.get('credentials', '-')}\n\n"
            )

    await message.answer(text if found else "У вас пока нет выполненных заказов")


# ----------------------------
# TOPUP (Пополнение аккаунта)
# ----------------------------
@dp.message(StateFilter(None), F.text == "💸 Пополнить аккаунт")
async def topup_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TopupOrder.region)
    await message.answer(
        "🌍 Выберите страну/регион пополнения:",
        reply_markup=topup_region_kb()
    )


@dp.callback_query(StateFilter(TopupOrder.region), F.data.startswith("topup_region:"))
async def topup_set_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":", 1)[1]
    await state.update_data(region=region)
    await state.set_state(TopupOrder.amount)

    cur = TOPUP_CURRENCY.get(region, "")
    await callback.message.edit_text(
        "💸 Введите сумму пополнения числом.\n"
        "Пример: 1500\n\n"
        f"Валюта региона: {cur}",
        reply_markup=cancel_inline_kb()
    )



@dp.callback_query(F.data == "topup_cancel")
async def topup_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено", reply_markup=main_menu())


@dp.message(StateFilter(TopupOrder.amount))
async def topup_amount(message: Message, state: FSMContext):
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(raw)
    except ValueError:
        await message.answer("❌ Введите сумму числом. Например: 1500")
        return

    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0")
        return

    data = await state.get_data()
    region = data.get("region")
    if not region:
        await message.answer("⚠️ Сессия устарела. Начните заново.", reply_markup=main_menu())
        await state.clear()
        return

    fee = get_topup_fee(message.from_user.id, region, amount)
    total = calc_topup_total(message.from_user.id, region, amount)
    cur = TOPUP_CURRENCY.get(region, "")

    await state.update_data(amount=amount, fee=fee, total=total)
    await state.set_state(TopupOrder.credentials)

    await message.answer(
        "🔐 Теперь отправьте данные аккаунта для пополнения (любым текстом).\n"
        "Почта, пароли, 2FA, резервные коды и т.д.\n\n"
        f"📌 Регион: {region} ({cur})\n"
        f"💰 Сумма: {amount}{cur}\n"
        f"➕ Комиссия: {fee}{cur}\n"
        f"✅ Итого к оплате: {total}{cur}",
        reply_markup=cancel_reply_kb()
    )


@dp.message(StateFilter(TopupOrder.credentials))
async def topup_credentials(message: Message, state: FSMContext):
    ok, cleaned, err = validate_credentials_text(message.text)
    if not ok:
        await message.answer(err)
        return

    await state.update_data(credentials=cleaned)
    await state.set_state(TopupOrder.confirm)

    data = await state.get_data()
    region = data.get("region")
    amount = data.get("amount")
    fee = data.get("fee")
    total = data.get("total")
    cur = TOPUP_CURRENCY.get(region, "")

    text = (
        "✅ Подтвердите пополнение:\n\n"
        f"🌍 Регион: {region} ({cur})\n"
        f"💰 Сумма: {amount}{cur}\n"
        f"➕ Комиссия: {fee}{cur}\n"
        f"✅ Итого к оплате: {total}{cur}\n\n"
        "После подтверждения появится выбор способа оплаты."
    )
    await message.answer(text, reply_markup=topup_confirm_kb())


@dp.callback_query(StateFilter(TopupOrder.confirm), F.data == "topup_confirm:yes")
async def topup_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    region = data.get("region")
    amount = data.get("amount")
    fee = data.get("fee")
    total = data.get("total")
    creds = data.get("credentials")

    if not region or amount is None or total is None or not creds:
        await callback.message.edit_text(
            "⚠️ Сессия устарела. Начните заново.",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    order_id = str(uuid.uuid4())[:8]
    cur = TOPUP_CURRENCY.get(region, "")

    # 🔥 ВОТ КЛЮЧЕВОЕ МЕСТО
    is_vip_user = is_vip(callback.from_user.id)
    status = "WAITING" if is_vip_user else "WAIT_PAY"

    reload_orders()
    ORDERS[order_id] = {
        "type": "topup",
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "status": status,
        "data": {
            "region": region,
            "amount": amount,
            "fee": fee,
            "total": total,
            "currency": cur,
            "client_credentials": creds,
            "pay_method": None,
            "invoice_id": None,
        },
    }
    save_orders(ORDERS)

    # сообщение админу
    admin_text = (
        "💸 НОВОЕ ПОПОЛНЕНИЕ\n"
        f"🆔 {order_id}\n"
        f"🌍 Регион: {region} ({cur})\n"
        f"💰 Сумма: {amount}{cur}\n"
        f"➕ Комиссия: {fee}{cur}\n"
        f"✅ Итого: {total}{cur}\n"
        f"🧾 Тип клиента: {'VIP (ОПТ)' if is_vip_user else 'Розница'}\n"
        f"👤 @{callback.from_user.username}\n\n"
        "🔐 Данные аккаунта клиента:\n"
        f"{creds}"
    )

    admin_msg = await bot.send_message(ADMIN_ID, admin_text)
    ORDERS[order_id]["admin_message_id"] = admin_msg.message_id
    save_orders(ORDERS)

    # 👑 VIP — БЕЗ ОПЛАТЫ
    if is_vip_user:
        await callback.message.edit_text(
            f"✅ Пополнение принято (VIP)\n"
            f"🆔 {order_id}\n\n"
            "Оплата не требуется.\n"
            "Ожидайте выполнение.",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    # 💳 РОЗНИЦА — С ОПЛАТОЙ
    await callback.message.edit_text(
        f"💳 Оплата пополнения\n"
        f"🆔 {order_id}\n"
        f"✅ Итого к оплате: {total}{cur}\n\n"
        "Выберите способ оплаты:",
        reply_markup=pay_methods_kb(order_id),
    )

    await state.clear()


# ----------------------------
# BUY SUBSCRIPTION
# ----------------------------
@dp.message(StateFilter(None), F.text == "🛒 Купить подписку")
async def buy_sub_from_keyboard(message: Message, state: FSMContext):
    await state.set_state(Order.period)
    await message.answer("Выберите срок подписки:", reply_markup=period_kb())


@dp.callback_query(StateFilter(Order.period), F.data.startswith("period:"))
async def set_period(callback: CallbackQuery, state: FSMContext):
    period = callback.data.split(":", 1)[1]
    await state.update_data(period=period)
    await state.set_state(Order.region)
    await callback.message.edit_text("Выберите регион:", reply_markup=region_kb())


@dp.callback_query(StateFilter(Order.region), F.data.startswith("region:"))
async def set_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":", 1)[1]
    await state.update_data(region=region)
    await state.set_state(Order.sub_type)
    await callback.message.edit_text("Выберите тип подписки:", reply_markup=sub_kb())


@dp.callback_query(StateFilter(Order.sub_type), F.data.startswith("sub:"))
async def set_subscription(callback: CallbackQuery, state: FSMContext):
    sub = callback.data.split(":", 1)[1]
    data = await state.get_data()

    if "region" not in data or "period" not in data:
        await callback.message.edit_text("⚠️ Сессия устарела. Начните заново.", reply_markup=main_menu())
        await state.clear()
        return

    await state.update_data(subscription=sub)

    try:
        price = get_price(
            user_id=callback.from_user.id,
            region=data["region"],
            period=data["period"],
            sub_type=sub,
        )
    except ValueError:
        await callback.message.edit_text(
            "⚠️ Цена для выбранной конфигурации не найдена.\nПопробуйте оформить заказ заново.",
            reply_markup=main_menu(),
        )
        await state.clear()
        return

    await state.update_data(price=price)
    await state.set_state(Order.confirm)

    text = (
        "📦 Подтверждение заказа:\n\n"
        f"Регион: {data['region']}\n"
        f"Период: {data['period']}\n"
        f"Подписка: {sub}\n"
        f"Цена: {price} ₽\n\n"
    )
    text += "👑 ОПТ (VIP): оплата не требуется." if is_wholesale(callback.from_user.id) else "💳 Розница: после подтверждения потребуется оплата."
    await callback.message.edit_text(text, reply_markup=confirm_kb())


async def create_subscription_order(obj, state: FSMContext, client_credentials: Optional[str]):
    st = await state.get_data()
    draft = st.get("_sub_draft")
    acc_type = st.get("sub_account_type")

    if not draft or not acc_type:
        if isinstance(obj, CallbackQuery):
            await obj.message.edit_text("⚠️ Сессия устарела. Начните заново.")
        else:
            await obj.answer("⚠️ Сессия устарела. Начните заново.")
        await state.clear()
        return

    order_id = str(uuid.uuid4())[:8]

    reload_orders()
    ORDERS[order_id] = {
        "type": "subscription",
        "user_id": obj.from_user.id,
        "username": obj.from_user.username,
        "status": "WAITING" if is_wholesale(obj.from_user.id) else "WAIT_PAY",
        "data": {
            "region": draft["region"],
            "period": draft["period"],
            "subscription": draft["subscription"],
            "price": draft["price"],
            "account_type": acc_type,
            "client_credentials": client_credentials,
            "pay_method": None,
            "invoice_id": None,
        },
    }
    save_orders(ORDERS)

    text = (
        "📦 НОВАЯ ПОДПИСКА\n"
        f"🆔 {order_id}\n"
        f"{draft['subscription']} | {draft['period']} | {draft['region']}\n"
        f"💰 {draft['price']} ₽\n"
        f"🔐 Аккаунт: {'СВОЙ' if acc_type == 'own' else 'НОВЫЙ'}\n"
        f"👤 @{obj.from_user.username}\n"
    )
    if acc_type == "own" and client_credentials:
        text += f"\n🔐 Данные аккаунта клиента:\n{client_credentials}"

    admin_msg = await bot.send_message(ADMIN_ID, text)
    ORDERS[order_id]["admin_message_id"] = admin_msg.message_id
    save_orders(ORDERS)

    if is_wholesale(obj.from_user.id):
        if isinstance(obj, CallbackQuery):
            await obj.message.edit_text("✅ Заказ принят (ОПТ). Оплата не требуется. Ожидайте выполнение.")
        else:
            await obj.answer("✅ Заказ принят (ОПТ). Оплата не требуется. Ожидайте выполнение.")
        await state.clear()
        return

    if isinstance(obj, CallbackQuery):
        await obj.message.edit_text(
            f"💳 Оплата заказа\n🆔 {order_id}\n💰 {draft['price']} ₽\n\n"
            "Выберите способ оплаты:",
            reply_markup=pay_methods_kb(order_id),
        )
    else:
        await obj.answer(
            f"💳 Оплата заказа\n🆔 {order_id}\n💰 {draft['price']} ₽\n\n"
            "Выберите способ оплаты:",
            reply_markup=pay_methods_kb(order_id),
        )

    await state.clear()


@dp.callback_query(StateFilter(Order.confirm), F.data == "confirm:yes")
async def sub_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "price" not in data:
        await callback.message.edit_text("⚠️ Данные заказа устарели. Начните заново.", reply_markup=main_menu())
        await state.clear()
        return

    await state.update_data(_sub_draft={
        "region": data["region"],
        "period": data["period"],
        "subscription": data["subscription"],
        "price": data["price"],
    })

    await callback.message.edit_text(
        "📦 Подписка оформляется.\nВыберите тип аккаунта:",
        reply_markup=sub_account_type_kb(),
    )
    await state.set_state(Order.waiting_for_account_type)


@dp.callback_query(F.data.startswith("menu:"))
async def menu_router(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 1)[1]

    await state.clear()

    if action == "buy":
        await state.set_state(Order.period)
        await callback.message.edit_text("Выберите срок подписки:", reply_markup=period_kb())
        return

    if action == "price":
        # проще: попросить нажать кнопку "💰 Прайс" или сделать отдельную функцию печати прайса
        await callback.message.edit_text("Нажмите «💰 Прайс» в меню бота.")
        return

    if action == "game":
        await state.set_state(GameOrder.waiting_for_name)
        await callback.message.edit_text("Напишите название игры, которую хотите купить.")
        return



@dp.callback_query(StateFilter(Order.waiting_for_account_type), F.data.startswith("sub_account:"))
async def sub_choose_account(callback: CallbackQuery, state: FSMContext):
    acc_type = callback.data.split(":")[1]
    st = await state.get_data()

    if not st.get("_sub_draft"):
        await callback.message.edit_text("⚠️ Сессия устарела. Начните заново.")
        await state.clear()
        return

    await state.update_data(sub_account_type=acc_type)

    if acc_type == "own":
        await callback.message.edit_text("🔐 Отправьте данные аккаунта одним сообщением.")
        await state.set_state(Order.waiting_for_credentials)
    else:
        await create_subscription_order(callback, state, client_credentials=None)


@dp.message(StateFilter(Order.waiting_for_credentials))
async def sub_get_credentials(message: Message, state: FSMContext):
    ok, cleaned, err = validate_credentials_text(message.text)
    if not ok:
        await message.answer(err)
        return
    await create_subscription_order(message, state, client_credentials=cleaned)


@dp.callback_query(StateFilter(Order.confirm), F.data == "confirm:no")
async def cancel_any_confirm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено", reply_markup=main_menu())


# ----------------------------
# BUY GAME
# ----------------------------
@dp.message(StateFilter(None), F.text == "🛒 Купить игру")
async def buy_game_keyboard(message: Message, state: FSMContext):
    await state.set_state(GameOrder.waiting_for_name)
    await message.answer("Напишите название игры, которую хотите купить. Можно прикрепить фото для удобства.")


@dp.message(StateFilter(GameOrder.waiting_for_name), F.content_type.in_({"text", "photo"}))
async def game_get_info(message: Message, state: FSMContext):
    game_name = message.text if message.text else "Название не указано"
    photo = message.photo[-1].file_id if message.photo else None

    await state.update_data(game_name=game_name, photo=photo)
    await state.set_state(GameOrder.waiting_for_account_type)

    await message.answer(
        "🎮 Игра указана.\n\nВыберите тип аккаунта:",
        reply_markup=account_type_kb_simple(),
    )


async def create_game_order(obj, state: FSMContext, credentials: Optional[str]):
    data = await state.get_data()
    order_id = str(uuid.uuid4())[:8]

    account_type = data.get("account_type")
    game_name = data.get("game_name")
    photo = data.get("photo")

    reload_orders()
    ORDERS[order_id] = {
        "type": "game",
        "user_id": obj.from_user.id,
        "username": obj.from_user.username,
        "status": "WAIT_PRICE",
        "data": {
            "game_name": game_name,
            "photo": photo,
            "account_type": account_type,
            "client_credentials": credentials,
            "pay_method": None,
            "invoice_id": None,
        },
    }
    save_orders(ORDERS)

    txt = (
        "🎮 НОВАЯ ИГРА\n"
        f"🆔 {order_id}\n"
        f"Игра: {game_name}\n"
        f"🔐 Аккаунт: {'СВОЙ' if account_type == 'own' else 'НОВЫЙ'}\n"
        f"👤 @{obj.from_user.username}\n"
    )
    if account_type == "own" and credentials:
        txt += f"\n🔐 Данные аккаунта клиента:\n{credentials}"

    if photo:
        admin_msg = await bot.send_photo(ADMIN_ID, photo, caption=txt)
    else:
        admin_msg = await bot.send_message(ADMIN_ID, txt)

    ORDERS[order_id]["admin_message_id"] = admin_msg.message_id
    save_orders(ORDERS)

    if isinstance(obj, CallbackQuery):
        await obj.message.edit_text("✅ Заказ отправлен продавцу. Ожидайте расчёт цены.")
    else:
        await obj.answer("✅ Заказ отправлен продавцу. Ожидайте расчёт цены.")

    await state.clear()


@dp.callback_query(StateFilter(GameOrder.waiting_for_account_type), F.data.startswith("game_account:"))
async def game_choose_account(callback: CallbackQuery, state: FSMContext):
    account_type = callback.data.split(":")[1]
    await state.update_data(account_type=account_type)

    if account_type == "own":
        await callback.message.edit_text("🔐 Отправьте данные аккаунта одним сообщением.")
        await state.set_state(GameOrder.waiting_for_credentials)
    else:
        await create_game_order(callback, state, credentials=None)


@dp.message(StateFilter(GameOrder.waiting_for_credentials))
async def game_get_credentials(message: Message, state: FSMContext):
    ok, cleaned, err = validate_credentials_text(message.text)
    if not ok:
        await message.answer(err)
        return
    await create_game_order(message, state, credentials=cleaned)


@dp.callback_query(F.data.startswith("confirm_game:"))
async def confirm_game(callback: CallbackQuery):
    order_id = callback.data.split(":", 1)[1]
    order = get_order(order_id)

    if not order:
        await callback.message.edit_text("⚠️ Заказ не найден", reply_markup=main_menu())
        return

    if is_wholesale(callback.from_user.id):
        order["status"] = "WAITING"
        save_orders(ORDERS)

        await callback.message.edit_text("✅ Заказ подтверждён. Оплата не требуется (ОПТ). Ожидайте выполнение.")
        await bot.send_message(
            ADMIN_ID,
            "✅ ОПТ заказ подтверждён клиентом\n"
            f"🆔 {order_id}\n"
            f"🎮 {order['data']['game_name']}\n"
            "✍️ Ответьте на заказ данными аккаунта/выполнением",
        )
        return

    order["status"] = "WAIT_PAY"
    save_orders(ORDERS)

    await callback.message.edit_text(
        "💳 Выберите способ оплаты:",
        reply_markup=pay_methods_kb(order_id),
    )


# ----------------------------
# PAYMENT FLOW (Retail)
# ----------------------------
@dp.callback_query(F.data.startswith("pay_method:"))
async def choose_pay_method(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    method = parts[1]
    order_id = parts[2]

    order = get_order(order_id)
    if not order:
        await callback.answer(f"Заказ не найден: {order_id}", show_alert=True)
        return

    # оплата нужна только когда статус WAIT_PAY
    if order.get("status") != "WAIT_PAY":
        await callback.answer("Сейчас нельзя выбрать оплату для этого заказа", show_alert=True)
        return

    order["data"]["pay_method"] = method
    save_orders(ORDERS)

    if method == "crypto":
        # для topup: total, для остальных: price
        amount_to_pay = float(order["data"].get("total") or order["data"].get("price") or 0)
        price_usdt = round(amount_to_pay / 80, 2)

        invoice = create_invoice(price_usdt, order_id)
        order["data"]["invoice_id"] = invoice["invoice_id"]
        save_orders(ORDERS)

        await callback.message.edit_text(
            "💳 Оплата криптой:\n"
            "1) Нажмите «💳 Оплатить»\n"
            "2) После оплаты нажмите «✅ Я оплатил» (проверит продавец)\n",
            reply_markup=pay_crypto_kb(invoice["pay_url"], order_id),
        )
        return

    if method == "card":
        await callback.message.edit_text(
            "💳 Оплата картой:\n"
            "Переведите по реквизитам продавца (89221481514 т-банк Иван В.).\n\n"
            "После оплаты нажмите «✅ Я оплатил» — продавец подтвердит.",
            reply_markup=pay_card_kb(order_id),
        )
        return

    await callback.answer("Неизвестный метод оплаты", show_alert=True)


@dp.callback_query(F.data.startswith("pay_back:"))
async def pay_back(callback: CallbackQuery):
    order_id = callback.data.split(":", 1)[1]
    order = get_order(order_id)
    if not order:
        await callback.message.edit_text("⚠️ Заказ не найден", reply_markup=main_menu())
        return

    if order.get("status") != "WAIT_PAY":
        await callback.answer("Сейчас нельзя менять оплату", show_alert=True)
        return

    await callback.message.edit_text("💳 Выберите способ оплаты:", reply_markup=pay_methods_kb(order_id))


@dp.callback_query(F.data.startswith("i_paid:"))
async def i_paid(callback: CallbackQuery):
    order_id = callback.data.split(":", 1)[1]
    order = get_order(order_id)

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    if order.get("status") != "WAIT_PAY":
        await callback.answer("Оплата уже обработана или не требуется", show_alert=True)
        return

    order["status"] = "WAIT_ADMIN_PAY_CONFIRM"
    save_orders(ORDERS)

    d = order.get("data", {})
    header = "🟠 КЛИЕНТ НАЖАЛ «Я ОПЛАТИЛ»"
    pay_method = d.get("pay_method") or "не выбран"

    info = (
        f"{header}\n"
        f"🆔 {order_id}\n"
        f"👤 @{order.get('username')}\n"
        f"💳 Метод: {pay_method}\n"
    )

    if order.get("type") == "game":
        info += "🎮 {0}\n💰 {1} ₽\n".format(d.get("game_name"), d.get("price"))

    elif order.get("type") == "subscription":
        info += "📦 {0} | {1} | {2}\n💰 {3} ₽\n".format(
            d.get("subscription"), d.get("period"), d.get("region"), d.get("price")
        )

    elif order.get("type") == "topup":
        cur = d.get("currency", TOPUP_CURRENCY.get(d.get("region", ""), ""))
        info += "💸 Пополнение\n🌍 {0} ({1})\n💰 Сумма: {2}{1}\n➕ Комиссия: {3}{1}\n✅ Итого: {4}{1}\n".format(
            d.get("region"), cur, d.get("amount"), d.get("fee"), d.get("total")
        )

    await bot.send_message(
        ADMIN_ID,
        info + "\nПодтвердите оплату кнопкой:",
        reply_markup=admin_confirm_payment_kb(order_id),
    )

    await callback.message.edit_text(
        "✅ Заявка на проверку оплаты отправлена продавцу.\n"
        "Ожидайте подтверждение оплаты."
    )


@dp.callback_query(F.data.startswith("admin_pay_ok:"))
async def admin_pay_ok(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    order_id = callback.data.split(":", 1)[1]
    order = get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    if order.get("status") != "WAIT_ADMIN_PAY_CONFIRM":
        await callback.answer("Этот заказ не ожидает подтверждения оплаты", show_alert=True)
        return

    order["status"] = "PAID"
    save_orders(ORDERS)

    await callback.message.edit_text("✅ Оплата подтверждена продавцом\n🆔 {0}".format(order_id))
    await bot.send_message(order["user_id"], "✅ Оплата подтверждена продавцом.\nОжидайте выполнение заказа.")


@dp.callback_query(F.data.startswith("admin_pay_no:"))
async def admin_pay_no(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    order_id = callback.data.split(":", 1)[1]
    order = get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    if order.get("status") != "WAIT_ADMIN_PAY_CONFIRM":
        await callback.answer("Этот заказ не ожидает подтверждения оплаты", show_alert=True)
        return

    order["status"] = "WAIT_PAY"
    save_orders(ORDERS)

    await callback.message.edit_text("❌ Оплата НЕ подтверждена\n🆔 {0}\nСтатус возвращён на оплату.".format(order_id))

    await bot.send_message(
        order["user_id"],
        "❌ Продавец не подтвердил оплату.\n"
        "Проверьте оплату и попробуйте снова.\n\n"
        "Выберите способ оплаты:",
        reply_markup=pay_methods_kb(order_id),
    )


# ----------------------------
# CANCEL ORDER
# ----------------------------
@dp.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order(callback: CallbackQuery):
    order_id = callback.data.split(":", 1)[1]
    order = get_order(order_id)

    if not order:
        await callback.message.edit_text("⚠️ Заказ не найден", reply_markup=main_menu())
        return

    order["status"] = "CANCELLED"
    save_orders(ORDERS)

    try:
        if order.get("admin_message_id"):
            await bot.edit_message_text(
                chat_id=ADMIN_ID,
                message_id=order["admin_message_id"],
                text="❌ ЗАКАЗ ОТМЕНЁН КЛИЕНТОМ",
            )
    except Exception:
        pass

    await callback.message.edit_text("❌ Заказ отменён", reply_markup=main_menu())




# ----------------------------
# ADMIN fulfills order by replying with credentials/info
# ----------------------------
@dp.message()
async def admin_reply_router(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.reply_to_message:
        return

    src_text = message.reply_to_message.text or message.reply_to_message.caption
    if not src_text:
        return

    order_id = extract_order_id_from_text(src_text)
    if not order_id:
        return

    order = get_order(order_id)
    if not order:
        await message.answer("⚠️ Заказ {0} не найден".format(order_id))
        return

    # 1) Админ отвечает на игру (WAIT_PRICE) -> цена
    if "🎮 НОВАЯ ИГРА" in src_text and order.get("type") == "game" and order.get("status") == "WAIT_PRICE":
        try:
            price = float(message.text.strip())
        except ValueError:
            await message.answer("⚠️ Для цены отправьте только число (например: 2900)")
            return

        order["data"]["price"] = price
        order["status"] = "WAIT_CONFIRM"
        save_orders(ORDERS)

        await bot.send_message(
            order["user_id"],
            "🎮 Игра: {0}\n💰 Цена: {1} ₽\nПодтвердите заказ:".format(order["data"]["game_name"], price),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_game:{0}".format(order_id))],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order:{0}".format(order_id))],
            ]),
        )
        await message.answer("✅ Цена отправлена клиенту")
        return

    # 2) Выполнение: только PAID или WAITING (если вдруг используешь для VIP)
    if order.get("status") in ("PAID", "WAITING"):
        text_to_client = message.text.strip()

        try:
            await bot.send_message(
                order["user_id"],
                "✅ Заказ выполнен!\n\n📄 Данные/информация:\n{0}".format(text_to_client),
            )
        except Exception as e:
            await message.answer("⚠️ Не смог отправить клиенту. Ошибка: {0}".format(e))
            return

        order["status"] = "DONE"
        order["credentials"] = text_to_client
        save_orders(ORDERS)

        await message.answer("✅ Заказ {0} завершён".format(order_id))
        return


# ----------------------------
# RUN
# ----------------------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
