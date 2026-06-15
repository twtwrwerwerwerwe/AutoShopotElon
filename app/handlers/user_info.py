import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from app.database import get_or_create_user, get_user_payments, get_active_subscription
from config import config

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "💰 To'lovlarim")
async def btn_my_payments(message: Message):
    user = await get_or_create_user(message.from_user.id)
    if not user.is_active:
        await message.answer("❌ Faol obuna yo'q.")
        return

    sub = await get_active_subscription(user.id)
    payments = await get_user_payments(user.id)

    lines = []

    if sub:
        days_left = max(0, (sub.expires_at - datetime.utcnow()).days) if sub.expires_at else 0
        lines.append(
            f"📋 <b>Joriy Obuna</b>\n"
            f"  Reja: <b>{sub.plan_name}</b>\n"
            f"  Faollashtirilgan: <b>{sub.activated_at.strftime('%Y-%m-%d') if sub.activated_at else 'N/A'}</b>\n"
            f"  Tugaydi: <b>{sub.expires_at.strftime('%Y-%m-%d') if sub.expires_at else 'N/A'}</b>\n"
            f"  Qolgan kunlar: <b>{days_left} kun</b>"
        )
    else:
        lines.append("📋 <b>Faol obuna yo'q</b>")

    if payments:
        lines.append("\n\n💳 <b>To'lovlar tarixi:</b>")
        for p in payments[:10]:
            status_emoji = {"approved": "✅", "rejected": "❌", "pending": "⏳"}.get(p.status, "❓")
            method_name = {"admin": "Admin", "click": "Click", "card": "Karta"}.get(p.method, p.method)
            status_uz = {"approved": "Tasdiqlandi", "rejected": "Rad etildi", "pending": "Kutilmoqda"}.get(p.status, p.status)
            lines.append(
                f"\n{status_emoji} <b>{p.amount:,} so'm</b> — {method_name}\n"
                f"   📅 {p.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"   Holat: {status_uz}"
            )
    else:
        lines.append("\n\n💳 <i>To'lovlar tarixi yo'q.</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "👨‍💼 Admin bilan bog'lanish")
async def btn_contact_admin(message: Message):
    admin_username = getattr(config, "ADMIN_USERNAME", None)
    if admin_username:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="👨‍💼 Admin chatini ochish", url=f"https://t.me/{admin_username}")
        await message.answer(
            "👨‍💼 <b>Admin bilan bog'lanish</b>\n\n"
            "Quyidagi tugmani bosib admin bilan chat oching:",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    else:
        for admin_id in config.ADMIN_IDS:
            try:
                chat = await message.bot.get_chat(admin_id)
                if chat.username:
                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                    builder = InlineKeyboardBuilder()
                    builder.button(text="👨‍💼 Admin chatini ochish", url=f"https://t.me/{chat.username}")
                    await message.answer(
                        "👨‍💼 <b>Admin bilan bog'lanish</b>",
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                    return
            except Exception:
                pass
        await message.answer(
            "👨‍💼 <b>Admin</b>\n\n"
            "To'lov arizasi yuborish uchun /start buyrug'ini ishlating.",
            parse_mode="HTML"
        )
