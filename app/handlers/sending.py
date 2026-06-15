import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database import (
    get_or_create_user, get_or_create_settings, update_settings,
    get_active_advertisement, get_user_groups
)
from app.keyboards import kb_interval, kb_main_menu, kb_sending, kb_sending_paused
from app.states import IntervalFlow, SendingFlow
from app.services import sender_service
from app.services.sender_service import DELAY_BETWEEN_GROUPS

router = Router()
logger = logging.getLogger(__name__)


def _check_active(user) -> bool:
    return user and user.is_active and not user.is_banned


# ─── Interval ─────────────────────────────────────────────────────────────────

@router.message(F.text == "⏱ Interval")
async def btn_interval(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if not _check_active(user):
        await message.answer("❌ Bu funksiyadan foydalanish uchun faol obuna kerak.")
        return

    settings = await get_or_create_settings(user.id)
    await state.set_state(IntervalFlow.choosing)
    await message.answer(
        f"⏱ <b>Yuborish Intervali</b>\n\n"
        f"Joriy interval: <b>{settings.interval_minutes} daqiqa</b>\n\n"
        "Barcha guruplarga yuborib bo'lgach, keyingi siklni qancha vaqtdan keyin boshlash kerak?",
        parse_mode="HTML",
        reply_markup=kb_interval()
    )


@router.callback_query(IntervalFlow.choosing, F.data.startswith("interval:"))
async def cb_interval_selected(call: CallbackQuery, state: FSMContext):
    value = call.data.split(":")[1]

    if value == "back":
        await state.clear()
        user = await get_or_create_user(call.from_user.id)
        await call.message.edit_text("🔙 Menyuga qaytildi.")
        await call.message.answer("📋 Asosiy menyu:", reply_markup=kb_main_menu(is_admin=user.is_admin))
        await call.answer()
        return

    minutes = int(value)
    user = await get_or_create_user(call.from_user.id)
    await update_settings(user.id, interval_minutes=minutes)
    await state.clear()

    await call.message.edit_text(
        f"✅ <b>Interval yangilandi!</b>\n\n"
        f"⏱ Yangi interval: <b>{minutes} daqiqa</b>\n\n"
        f"Barcha guruplarga yuborib bo'lингач, keyingi sikl\n"
        f"<b>{minutes} daqiqadan</b> keyin boshlanadi.",
        parse_mode="HTML"
    )
    await call.message.answer("📋 Asosiy menyu:", reply_markup=kb_main_menu(is_admin=user.is_admin))
    await call.answer(f"✅ {minutes} daqiqaga o'rnatildi!")


# ─── Yuborishni boshlash ───────────────────────────────────────────────────────

@router.message(F.text == "▶️ Yuborishni boshlash")
async def btn_start_sending(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if not _check_active(user):
        await message.answer("❌ Bu funksiyadan foydalanish uchun faol obuna kerak.")
        return

    if not user.session_string:
        await message.answer(
            "❌ <b>Hisob ulanmagan!</b>\n\n"
            "Avval <b>📱 Raqam qo'shish</b> orqali Telegram hisobingizni ulang.",
            parse_mode="HTML"
        )
        return

    ad = await get_active_advertisement(user.id)
    if not ad:
        await message.answer(
            "❌ <b>E'lon yo'q!</b>\n\n"
            "<b>📝 E'lonlar</b> bo'limidan e'lon qo'shing.",
            parse_mode="HTML"
        )
        return

    groups = await get_user_groups(user.id)
    if not groups:
        await message.answer(
            "❌ <b>Guruhlar tanlanmagan!</b>\n\n"
            "<b>📂 Guruh qo'shish</b> orqali guruhlarni qo'shing.",
            parse_mode="HTML"
        )
        return

    settings = await get_or_create_settings(user.id)

    if sender_service.is_sending(user.id):
        await message.answer(
            "▶️ <b>Yuborish allaqachon boshlangan!</b>\n\nYuborish jarayoni davom etmoqda.",
            parse_mode="HTML",
            reply_markup=kb_sending()
        )
        return

    await state.set_state(SendingFlow.active)
    await sender_service.start_sending(message.bot, user.id, message.from_user.id, user.session_string)

    estimated_cycle = (len(groups) * DELAY_BETWEEN_GROUPS) // 60

    await message.answer(
        f"🚀 <b>Yuborish boshlandi!</b>\n\n"
        f"📝 E'lon: ✅\n"
        f"👥 Guruhlar: <b>{len(groups)} ta</b>\n"
        f"⏱ Guruhlar orasidagi pauza: <b>{DELAY_BETWEEN_GROUPS} soniya</b>\n"
        f"🔄 Bir sikl taxminan: <b>~{max(1, estimated_cycle)} daqiqa</b>\n"
        f"⏳ Sikl orasidagi interval: <b>{settings.interval_minutes} daqiqa</b>\n\n"
        "✅ Xabarlar avtomatik yuborilmoqda.\n"
        "⏸ Vaqtincha to'xtatish uchun <b>Pauza</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=kb_sending()
    )


@router.message(SendingFlow.active, F.text == "⏸ Pauza")
async def btn_pause_sending(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    await sender_service.pause_sending(user.id)
    await message.answer(
        "⏸ <b>Yuborish to'xtatib turildi</b>\n\n"
        "Yuborish vaqtincha to'xtatildi.\n"
        "Davom etish uchun ▶️ <b>Davom ettirish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=kb_sending_paused()
    )


@router.message(SendingFlow.active, F.text == "▶️ Davom ettirish")
async def btn_resume_sending(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    await sender_service.resume_sending(user.id)
    await message.answer(
        "▶️ <b>Yuborish davom ettirildi!</b>\n\nXabarlar yana yuborilmoqda.",
        parse_mode="HTML",
        reply_markup=kb_sending()
    )


@router.message(SendingFlow.active, F.text == "⏹ To'xtatish")
async def btn_stop_sending(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    await sender_service.stop_sending(user.id)
    await state.clear()

    settings = await get_or_create_settings(user.id)
    await message.answer(
        f"⏹ <b>Yuborish to'xtatildi</b>\n\n"
        f"📊 Jami yuborilgan xabarlar: <b>{settings.messages_sent} ta</b>\n\n"
        "AutoAd Bot dan foydalanganingiz uchun rahmat!",
        parse_mode="HTML",
        reply_markup=kb_main_menu(is_admin=user.is_admin)
    )
