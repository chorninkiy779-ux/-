from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from config import ADMIN_ID
from database import (
    get_withdrawal, set_withdrawal_status, add_balance
)

router = Router()


# ---------- ЗАЯВКИ НА ВЫВОД ----------
@router.callback_query(F.data.startswith("admin_done_"))
async def admin_done(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    wid = int(callback.data.split("_")[2])
    w = get_withdrawal(wid)

    if not w:
        await callback.answer("Заявка не найдена")
        return

    set_withdrawal_status(wid, "done")

    try:
        await bot.send_message(
            w[1],
            f"✅ <b>Подарок отправлен!</b>\n\n"
            f"Заявка #{wid} на сумму {w[3]:.1f} ⭐ выполнена.\n"
            f"Проверь уведомления в Telegram."
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>ВЫПОЛНЕНО</b>"
    )
    await callback.answer("Заявка закрыта")


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    wid = int(callback.data.split("_")[2])
    w = get_withdrawal(wid)

    if not w:
        await callback.answer("Заявка не найдена")
        return

    add_balance(w[1], w[3])
    set_withdrawal_status(wid, "rejected")

    try:
        await bot.send_message(
            w[1],
            f"❌ <b>Заявка #{wid} отклонена.</b>\n"
            f"Звёзды ({w[3]:.1f} ⭐) возвращены на баланс."
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО</b>"
    )
    await callback.answer("Заявка отклонена")