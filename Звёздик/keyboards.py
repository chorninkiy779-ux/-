from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Задания", callback_data="show_tasks")],
        [InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw")],
        [InlineKeyboardButton(text="📢 Купить рекламу", callback_data="buy_ads")],
        [InlineKeyboardButton(text="📊 Мои кампании", callback_data="my_ads")],
    ])


def back_to_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_start")]
    ])


def tasks_menu(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я подписался", callback_data=f"task_done_{ad_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")]
    ])


def ad_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="back_to_start")]
    ])


def admin_withdraw_buttons(wid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"admin_done_{wid}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{wid}")]
    ])