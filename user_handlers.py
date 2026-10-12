import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    PreCheckoutQuery
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import (
    ADMIN_ID, ADMIN_USERNAME, PRICE_PER_SUB, REWARD_PER_TASK,
    MIN_WITHDRAW, MIN_SUBS_ORDER
)
from database import (
    add_user, get_user, add_balance, deduct_balance,
    get_active_ads, get_ad, is_task_completed, mark_task_completed,
    increment_ad_done, create_withdrawal, create_ad,
    confirm_ad_payment, get_user_ads
)
from keyboards import (
    main_menu, back_to_menu, tasks_menu,
    ad_cancel, admin_withdraw_buttons
)

router = Router()


# ---------- FSM для покупки рекламы ----------
class AdStates(StatesGroup):
    waiting_channel = State()
    waiting_amount = State()


# ---------- Проверка прав бота в канале ----------
async def is_bot_admin_in_channel(bot: Bot, channel_username: str) -> bool:
    try:
        bot_member = await bot.get_chat_member(
            chat_id=channel_username,
            user_id=bot.id
        )
        return bot_member.status in ("administrator", "creator")
    except Exception as e:
        logging.warning(f"Проверка прав бота не удалась для {channel_username}: {e}")
        return False


# ---------- /start ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет_юзернейма"
    add_user(user_id, username)

    user = get_user(user_id)
    balance = user[2] if user else 0.0

    await message.answer(
        f"👋 Привет! Твой баланс: <b>{balance:.1f} ⭐</b>\n\n"
        f"📋 <b>Задания</b> — зарабатывай звёзды за подписки\n"
        f"💸 <b>Вывести</b> — минимум {MIN_WITHDRAW} ⭐\n"
        f"📢 <b>Купить рекламу</b> — {PRICE_PER_SUB} ⭐ за подписчика\n"
        f"📊 <b>Мои кампании</b> — статистика твоих заказов",
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    balance = user[2] if user else 0.0
    await callback.message.edit_text(
        f"👋 Твой баланс: <b>{balance:.1f} ⭐</b>",
        reply_markup=main_menu()
    )
    await callback.answer()


# ---------- ЗАДАНИЯ ----------
@router.callback_query(F.data == "show_tasks")
async def show_tasks(callback: CallbackQuery):
    ads = get_active_ads()

    if not ads:
        await callback.message.edit_text(
            "😕 Пока нет активных заданий. Заходи позже!",
            reply_markup=back_to_menu()
        )
        await callback.answer()
        return

    ad_id, channel, title = ads[0]

    await callback.message.edit_text(
        f"📌 <b>Задание:</b>\n"
        f"Подпишись на канал: <b>{title}</b> ({channel})\n"
        f"Награда: <b>{REWARD_PER_TASK} ⭐</b>",
        reply_markup=tasks_menu(ad_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_done_"))
async def task_done(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    ad_id = int(callback.data.split("_")[2])

    ad = get_ad(ad_id)
    if not ad:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    channel_username = ad[2]

    if is_task_completed(user_id, ad_id):
        await callback.answer("❌ Ты уже выполнял это задание!", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(
            chat_id=channel_username,
            user_id=user_id
        )
        is_subscribed = member.status in ("member", "administrator", "creator")
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        await callback.answer(
            "❌ Ошибка проверки. Убедись, что ты подписан.",
            show_alert=True
        )
        return

    if not is_subscribed:
        await callback.answer(
            "❌ Ты ещё не подписан на канал! Подпишись и нажми снова.",
            show_alert=True
        )
        return

    add_balance(user_id, REWARD_PER_TASK)
    mark_task_completed(user_id, ad_id)
    increment_ad_done(ad_id)

    user = get_user(user_id)
    balance = user[2] if user else 0.0

    await callback.message.edit_text(
        f"✅ Задание выполнено! Начислено <b>{REWARD_PER_TASK} ⭐</b>\n"
        f"Твой баланс: <b>{balance:.1f} ⭐</b>",
        reply_markup=back_to_menu()
    )
    await callback.answer(f"+{REWARD_PER_TASK} ⭐")


# ---------- ВЫВОД ----------
@router.callback_query(F.data == "withdraw")
async def withdraw_request(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not user:
        await callback.answer("Сначала нажми /start")
        return

    balance = user[2]

    if balance < MIN_WITHDRAW:
        await callback.message.edit_text(
            f"❌ Недостаточно звёзд для вывода.\n"
            f"Минимум: <b>{MIN_WITHDRAW} ⭐</b>\n"
            f"У тебя: <b>{balance:.1f} ⭐</b>",
            reply_markup=back_to_menu()
        )
        await callback.answer()
        return

    deduct_balance(user_id, balance)
    wid = create_withdrawal(user_id, callback.from_user.username, balance)

    await bot.send_message(
        ADMIN_ID,
        f"📥 <b>Новая заявка на вывод</b>\n\n"
        f"Номер: <code>#{wid}</code>\n"
        f"Юзер: @{callback.from_user.username} (ID: {user_id})\n"
        f"Сумма: <b>{balance:.1f} ⭐</b>",
        reply_markup=admin_withdraw_buttons(wid)
    )

    await callback.message.edit_text(
        f"✅ <b>Заявка создана!</b>\n\n"
        f"Номер: <code>#{wid}</code>\n"
        f"Сумма: <b>{balance:.1f} ⭐</b>\n\n"
        f"<b>Что делать:</b>\n"
        f"1. Напиши админу: {ADMIN_USERNAME}\n"
        f"2. Отправь номер: <code>#{wid}</code>\n"
        f"3. Жди подарок в течение 24 часов.\n\n"
        f"⚠️ Не удаляй это сообщение!",
        reply_markup=back_to_menu()
    )
    await callback.answer()


# ---------- ПОКУПКА РЕКЛАМЫ ----------
@router.callback_query(F.data == "buy_ads")
async def buy_ads_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"📢 <b>Покупка рекламы</b>\n\n"
        f"Цена: <b>{PRICE_PER_SUB} ⭐ за 1 подписчика</b>\n"
        f"Минимум: <b>{MIN_SUBS_ORDER} подписчиков</b>\n\n"
        f"Оплата проходит <b>прямо в боте через Telegram Stars</b>.\n\n"
        f"Отправь юзернейм своего канала (например, <code>@my_channel</code>):",
        reply_markup=ad_cancel()
    )
    await state.set_state(AdStates.waiting_channel)
    await callback.answer()


@router.message(AdStates.waiting_channel)
async def ad_channel(message: Message, state: FSMContext, bot: Bot):
    channel = message.text.strip()

    if not channel.startswith("@"):
        await message.answer("❌ Юзернейм должен начинаться с @. Попробуй ещё раз:")
        return

    try:
        chat = await bot.get_chat(channel)
    except Exception:
        await message.answer("❌ Не могу найти этот канал. Проверь юзернейм.")
        return

    await state.update_data(channel=channel, channel_title=chat.title)

    await message.answer(
        f"✅ Канал: <b>{chat.title}</b>\n\n"
        f"Сколько подписчиков хочешь купить?\n"
        f"Минимум: {MIN_SUBS_ORDER}\n"
        f"Стоимость: количество × {PRICE_PER_SUB} ⭐",
        reply_markup=ad_cancel()
    )
    await state.set_state(AdStates.waiting_amount)


@router.message(AdStates.waiting_amount)
async def ad_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи целое число.")
        return

    if amount < MIN_SUBS_ORDER:
        await message.answer(f"❌ Минимум {MIN_SUBS_ORDER} подписчиков.")
        return

    data = await state.get_data()
    channel = data["channel"]
    channel_title = data["channel_title"]
    total_price = int(amount * PRICE_PER_SUB)

    ad_id = create_ad(
        message.from_user.id, channel, channel_title, amount, PRICE_PER_SUB
    )

    await message.answer_invoice(
        title=f"Реклама: {amount} подписчиков",
        description=(
            f"Канал: {channel_title}\n"
            f"Количество подписчиков: {amount}\n"
            f"Цена за подписчика: {PRICE_PER_SUB} ⭐"
        ),
        payload=f"ad_{ad_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Реклама", amount=total_price)],
        start_parameter=f"ad_{ad_id}"
    )
    await state.clear()


# ---------- ОПЛАТА STARS ----------
@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    payment = message.successful_payment
    payload = payment.invoice_payload

    try:
        ad_id = int(payload.split("_")[1])
    except (IndexError, ValueError):
        await message.answer("❌ Ошибка обработки платежа. Свяжись с админом.")
        return

    confirm_ad_payment(ad_id)
    ad = get_ad(ad_id)

    if not ad:
        return

    channel_username = ad[2]
    channel_title = ad[3]
    amount = ad[4]

    bot_me = await bot.get_me()

    instruction = (
        f"✅ <b>Оплата получена!</b>\n\n"
        f"Канал: <b>{channel_title}</b>\n"
        f"Подписчиков: <b>{amount}</b>\n"
        f"Оплачено: <b>{payment.total_amount} ⭐</b>\n\n"
        f"<b>Что нужно сделать сейчас:</b>\n\n"
        f"1. Открой свой канал: {channel_username}\n"
        f"2. Настройки канала → <b>Администраторы</b>\n"
        f"3. Нажми <b>Добавить администратора</b>\n"
        f"4. Введи: <code>@{bot_me.username}</code>\n"
        f"5. Выдай права администратора (достаточно базовых)\n\n"
        f"⚠️ <b>Без этого бот не сможет проверять подписки</b>, "
        f"и задание не запустится.\n\n"
        f"После добавления нажми /start и проверь статус."
    )

    await message.answer(instruction)

    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>Оплата Stars получена</b>\n\n"
        f"ID: #{ad_id}\n"
        f"Пользователь: {message.from_user.id}\n"
        f"Канал: {channel_title} ({channel_username})\n"
        f"Сумма: {payment.total_amount} ⭐"
    )


# ---------- МОИ КАМПАНИИ ----------
@router.callback_query(F.data == "my_ads")
async def my_ads(callback: CallbackQuery):
    ads = get_user_ads(callback.from_user.id)

    if not ads:
        await callback.message.edit_text(
            "📊 У тебя пока нет кампаний.\n\n"
            "Нажми «📢 Купить рекламу», чтобы создать первую.",
            reply_markup=back_to_menu()
        )
        await callback.answer()
        return

    status_map = {
        "pending_payment": "⏳ Ожидает оплаты",
        "active": "✅ Активна",
        "completed": "🏁 Завершена",
        "rejected": "❌ Отклонена"
    }

    text = "📊 <b>Твои кампании:</b>\n\n"
    for ad in ads:
        ad_id, title, bought, done, status = ad
        text += (
            f"<b>#{ad_id}</b> — {title}\n"
            f"   Выполнено: {done}/{bought}\n"
            f"   Статус: {status_map.get(status, status)}\n\n"
        )

    await callback.message.edit_text(text, reply_markup=back_to_menu())
    await callback.answer()