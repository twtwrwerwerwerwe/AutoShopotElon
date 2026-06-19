import asyncio
import logging
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database import get_or_create_user, update_user
from app.keyboards import kb_phone_menu, kb_confirm_disconnect, kb_share_phone, kb_cancel, kb_main_menu, remove_kb
from app.states import PhoneFlow
from app.services import telethon_service
from config import config

router = Router()
logger = logging.getLogger(__name__)

_pending_logins = {}  # user_tg_id -> {client, phone, phone_code_hash}


def _check_active(user) -> bool:
    return user and user.is_active and not user.is_banned


@router.message(F.text == "📱 Raqam qo'shish")
async def btn_add_number(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if not _check_active(user):
        await message.answer("❌ Bu funksiyadan foydalanish uchun faol obuna kerak.")
        return

    has_phone = bool(user.session_string)

    if has_phone:
        await state.set_state(PhoneFlow.agreeing)

        phone_text = user.phone_number if user.phone_number else "Noma'lum"

        await message.answer(
            f"📱 <b>Telegram Hisob Boshqaruvi</b>\n\n"
            f"✅ Ulangan raqam: <code>{phone_text}</code>\n\n"
            "Nima qilishni xohlaysiz?",
            parse_mode="HTML",
            reply_markup=kb_phone_menu(has_phone=True)
        )
    else:
        await state.set_state(PhoneFlow.agreeing)
        await message.answer(
            "📱 <b>Telegram Hisobingizni Ulash</b>\n\n"
            "⚠️ <b>Muhim:</b>\n"
            "Bot sizning Telegram hisobingizga ulanib, guruplarga xabar yuboradi.\n\n"
            "🔐 <b>Xavfsizlik:</b>\n"
            "• Sessiyangiz serverda xavfsiz saqlanadi\n"
            "• Shaxsiy xabarlaringizga hech qachon kirilmaydi\n"
            "• Istalgan vaqt uzishingiz mumkin\n"
            "• Xabarlar faqat siz tanlagan guruplarga yuboriladi\n\n"
            "📋 <b>Rozilik shartlari:</b>\n"
            "• Hisobingiz e'lonlarni yuborish uchun ishlatiladi\n"
            "• Yuborilgan kontent uchun o'zingiz javobgarsiz\n"
            "• Ommaviy xabar yuborish Telegram shartlariga mos bo'lishi kerak\n\n"
            "Davom etishga rozimisiz?",
            parse_mode="HTML",
            reply_markup=kb_phone_menu(has_phone=False)
        )


# ─── Disconnect / O'chirish ───────────────────────────────────────────────────

@router.callback_query(F.data == "phone:disconnect")
async def cb_phone_disconnect(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "🗑 <b>Raqamni uzish</b>\n\n"
        "⚠️ Hisobingiz uziladi va session o'chiriladi.\n"
        "Yuborishlar to'xtaydi.\n\n"
        "Davom etishni xohlaysizmi?",
        parse_mode="HTML",
        reply_markup=kb_confirm_disconnect()
    )
    await call.answer()


@router.callback_query(F.data == "phone:confirm_disconnect")
async def cb_confirm_disconnect(call: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(call.from_user.id)

    # Disconnect telethon client
    try:
        await telethon_service.disconnect_client(user.id)
    except Exception as e:
        logger.warning(f"Disconnect error for {user.id}: {e}")

    # Clear session from DB
    await update_user(call.from_user.id, session_string=None, phone_number=None)
    await state.clear()

    await call.message.edit_text(
        "✅ <b>Raqam muvaffaqiyatli uzildi!</b>\n\n"
        "📱 Session o'chirildi.\n"
        "Yangi raqam ulash uchun <b>📱 Raqam qo'shish</b> tugmasini bosing.",
        parse_mode="HTML"
    )
    await call.message.answer(
        "📋 Asosiy menyu:",
        reply_markup=kb_main_menu(is_admin=user.is_admin)
    )
    await call.answer("✅ Uzildi!")


# ─── Agree & Enter Phone ──────────────────────────────────────────────────────

@router.callback_query(F.data == "phone:agree")
async def cb_phone_agree(call: CallbackQuery, state: FSMContext):
    await state.set_state(PhoneFlow.entering_phone)
    await call.message.edit_text(
        "📱 <b>Telefon raqamingizni kiriting</b>\n\n"
        "Xalqaro formatda yuboring:\n"
        "<code>+998901234567</code>\n\n"
        "Yoki kontaktingizni ulashing:",
        parse_mode="HTML"
    )
    await call.message.answer("👇 Kontakt ulashing yoki raqam kiriting:", reply_markup=kb_share_phone())
    await call.answer()


@router.callback_query(F.data == "phone:cancel")
async def cb_phone_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(call.from_user.id)
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.message.answer("📋 Asosiy menyu:", reply_markup=kb_main_menu(is_admin=user.is_admin))
    await call.answer()


@router.message(PhoneFlow.entering_phone, F.contact)
async def receive_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await _process_phone(message, state, phone)


@router.message(PhoneFlow.entering_phone, F.text)
async def receive_phone_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        user = await get_or_create_user(message.from_user.id)
        await message.answer("❌ Bekor qilindi.", reply_markup=kb_main_menu(is_admin=user.is_admin))
        return

    phone = re.sub(r"[^\d+]", "", text)
    if not phone.startswith("+"):
        phone = "+" + phone

    if len(phone) < 10:
        await message.answer(
            "❌ Noto'g'ri raqam. Xalqaro formatda kiriting:\n<code>+998901234567</code>",
            parse_mode="HTML"
        )
        return

    await _process_phone(message, state, phone)


async def _process_phone(message: Message, state: FSMContext, phone: str):
    loading_msg = await message.answer(
        "⏳ <b>Tasdiqlash kodi yuborilmoqda...</b>\n\n<i>Iltimos kuting...</i>",
        parse_mode="HTML",
        reply_markup=remove_kb
    )

    try:
        client, result = await telethon_service.send_code(phone)
        _pending_logins[message.from_user.id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": result.phone_code_hash,
        }
        await state.update_data(phone=phone)
        await state.set_state(PhoneFlow.entering_code)

        # ← ReplyKeyboardMarkup ishlatamiz, edit_text EMAS
        await message.answer(
            "✅ <b>Tasdiqlash kodi yuborildi!</b>\n\n"
            f"📱 Raqam: <code>{phone}</code>\n\n"
            "📝 Kodni quyidagi formatda kiriting:\n"
            "<b>1 2 . 3 4 5</b>  →  <code>12.345</code>\n\n"
            "⚠️ Nuqta birinchi 2 va oxirgi 3 raqamni ajratadi.\n\n"
            "🔒 <i>Bu kodni hech kimga bermang!</i>",
            parse_mode="HTML",
            reply_markup=kb_cancel()
        )

    except Exception as e:
        logger.error(f"Kod yuborishda xato {phone}: {e}")
        await message.answer(
            f"❌ <b>Kod yuborib bo'lmadi</b>\n\n"
            f"Xato: <code>{str(e)[:200]}</code>\n\n"
            "Raqamni tekshirib qayta urinib ko'ring.",
            parse_mode="HTML"
        )
        await state.set_state(PhoneFlow.entering_phone)


@router.message(PhoneFlow.entering_code, F.text)
async def receive_code(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        user = await get_or_create_user(message.from_user.id)
        if message.from_user.id in _pending_logins:
            try:
                await _pending_logins[message.from_user.id]["client"].disconnect()
            except Exception:
                pass
            del _pending_logins[message.from_user.id]
        await message.answer("❌ Bekor qilindi.", reply_markup=kb_main_menu(is_admin=user.is_admin))
        return

    code = text.replace(".", "").replace(" ", "").strip()
    if not code.isdigit() or len(code) < 4:
        await message.answer(
            "❌ Noto'g'ri format. Kodni shunday kiriting:\n<code>12.345</code>",
            parse_mode="HTML"
        )
        return

    pending = _pending_logins.get(message.from_user.id)
    if not pending:
        await message.answer("❌ Sessiya muddati o'tdi. /start dan qayta boshlang.")
        await state.clear()
        return

    loading_msg = await message.answer("⏳ <b>Kod tekshirilmoqda...</b>", parse_mode="HTML")

    try:
        session_string = await telethon_service.sign_in(
            client=pending["client"],
            phone=pending["phone"],
            code=code,
            phone_code_hash=pending["phone_code_hash"],
        )

        user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
        await update_user(message.from_user.id, session_string=session_string, phone_number=pending["phone"])
        del _pending_logins[message.from_user.id]
        await state.clear()

        await loading_msg.edit_text(
            "✅ <b>Hisob muvaffaqiyatli ulandi!</b>\n\n"
            f"📱 Raqam: <code>{pending['phone']}</code>\n\n"
            "Telegram hisobingiz botga ulandi.\n"
            "Endi guruhlar qo'shib, e'lon yuborishni boshlashingiz mumkin!",
            parse_mode="HTML"
        )
        await message.answer("📋 Asosiy menyuga qaytish:", reply_markup=kb_main_menu(is_admin=user.is_admin))

    except Exception as e:
        err_str = str(e)
        if "SessionPasswordNeeded" in err_str or "password" in err_str.lower():
            await state.set_state(PhoneFlow.entering_password)
            await state.update_data(code=code)
            await loading_msg.edit_text(
                "🔐 <b>Ikki bosqichli tasdiqlash</b>\n\n"
                "Hisobingizda 2FA yoqilgan.\n"
                "<b>Bulut parolingizni</b> kiriting:",
                parse_mode="HTML",
                reply_markup=kb_cancel()
            )
        elif "PhoneCodeInvalid" in err_str:
            await loading_msg.edit_text("❌ <b>Noto'g'ri kod!</b>\n\nTo'g'ri kodni kiriting:", parse_mode="HTML")
        elif "PhoneCodeExpired" in err_str:
            await loading_msg.edit_text(
                "❌ <b>Kod muddati o'tdi!</b>\n\n/start dan qayta boshlang.",
                parse_mode="HTML"
            )
            await state.clear()
        else:
            logger.error(f"Kirish xatosi {message.from_user.id}: {e}")
            await loading_msg.edit_text(
                f"❌ <b>Xato:</b> <code>{err_str[:200]}</code>\n\nQayta urinib ko'ring.",
                parse_mode="HTML"
            )


@router.message(PhoneFlow.entering_password, F.text)
async def receive_2fa_password(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        user = await get_or_create_user(message.from_user.id)
        await message.answer("❌ Bekor qilindi.", reply_markup=kb_main_menu(is_admin=user.is_admin))
        return

    pending = _pending_logins.get(message.from_user.id)
    if not pending:
        await message.answer("❌ Sessiya muddati o'tdi. Qayta boshlang.")
        await state.clear()
        return

    data = await state.get_data()
    loading_msg = await message.answer("⏳ <b>Parol tekshirilmoqda...</b>", parse_mode="HTML")

    try:
        session_string = await telethon_service.sign_in(
            client=pending["client"],
            phone=pending["phone"],
            code=data.get("code", ""),
            phone_code_hash=pending["phone_code_hash"],
            password=text,
        )

        user = await get_or_create_user(message.from_user.id)
        await update_user(message.from_user.id, session_string=session_string, phone_number=pending["phone"])
        del _pending_logins[message.from_user.id]
        await state.clear()

        await loading_msg.edit_text(
            "✅ <b>Hisob ulandi!</b>\n\n"
            "Ikki bosqichli tasdiqlash muvaffaqiyatli o'tdi.\n"
            "Hisobingiz ulandi!",
            parse_mode="HTML"
        )
        await message.answer("📋 Asosiy menyu:", reply_markup=kb_main_menu(is_admin=user.is_admin))

    except Exception as e:
        logger.error(f"2FA xatosi {message.from_user.id}: {e}")
        await loading_msg.edit_text("❌ <b>Noto'g'ri parol!</b>\n\nQayta kiriting:", parse_mode="HTML")
