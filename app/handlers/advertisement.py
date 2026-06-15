import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database import (
    get_or_create_user, get_active_advertisement,
    save_advertisement, clear_advertisements
)
from app.keyboards import kb_ads_menu, kb_confirm_clear, kb_main_menu, kb_cancel
from app.states import AdvertisementFlow

router = Router()
logger = logging.getLogger(__name__)


def _check_active(user) -> bool:
    return user and user.is_active and not user.is_banned


@router.message(F.text == "📝 E'lonlar")
async def btn_advertisements(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if not _check_active(user):
        await message.answer("❌ Bu funksiyadan foydalanish uchun faol obuna kerak.")
        return

    ad = await get_active_advertisement(user.id)
    preview = (
        f"\n\n📄 <b>Joriy e'lon:</b>\n<i>{ad.text[:200]}{'...' if len(ad.text) > 200 else ''}</i>"
        if ad else "\n\n📭 <i>Hali e'lon qo'shilmagan.</i>"
    )

    await state.set_state(AdvertisementFlow.menu)
    await message.answer(
        "📝 <b>E'lonlar Boshqaruvi</b>" + preview,
        parse_mode="HTML",
        reply_markup=kb_ads_menu()
    )


@router.message(AdvertisementFlow.menu, F.text == "➕ E'lon qo'shish")
async def btn_add_ad(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    ad = await get_active_advertisement(user.id)
    if ad:
        await message.answer(
            "⚠️ E'lon allaqachon mavjud.\n"
            "<b>🆕 E'lonni almashtirish</b> tugmasini ishlating.",
            parse_mode="HTML"
        )
        return
    await state.set_state(AdvertisementFlow.adding)
    await message.answer(
        "✏️ <b>E'lon Qo'shish</b>\n\n"
        "E'lon matnini yuboring.\n"
        "Barcha formatlash qo'llab-quvvatlanadi (qalin, kursiv, havolalar).\n\n"
        "💡 <i>Maslahat: Qisqa va qiziqarli matn yozing!</i>",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(AdvertisementFlow.menu, F.text == "🆕 E'lonni almashtirish")
async def btn_replace_ad(message: Message, state: FSMContext):
    await state.set_state(AdvertisementFlow.replacing)
    await message.answer(
        "✏️ <b>E'lonni Almashtirish</b>\n\n"
        "Yangi e'lon matnini yuboring.\n"
        "Bu mavjud e'lonni almashtiradi:",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(AdvertisementFlow.menu, F.text == "🗑 E'lonlarni o'chirish")
async def btn_clear_ads(message: Message, state: FSMContext):
    await state.set_state(AdvertisementFlow.confirm_clear)
    await message.answer(
        "🗑 <b>Barcha E'lonlarni O'chirish?</b>\n\n"
        "Bu e'loningizni butunlay o'chiradi.\n"
        "Ishonchingiz komilmi?",
        parse_mode="HTML",
        reply_markup=kb_confirm_clear()
    )


@router.message(AdvertisementFlow.menu, F.text == "🔙 Orqaga")
async def btn_ads_back(message: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(message.from_user.id)
    await message.answer("📋 Asosiy menyu:", reply_markup=kb_main_menu(is_admin=user.is_admin))


@router.message(AdvertisementFlow.adding, F.text)
async def receive_new_ad(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.set_state(AdvertisementFlow.menu)
        await message.answer("❌ Bekor qilindi.", reply_markup=kb_ads_menu())
        return

    user = await get_or_create_user(message.from_user.id)
    await save_advertisement(user.id, message.text)
    await state.set_state(AdvertisementFlow.menu)

    await message.answer(
        "✅ <b>E'lon saqlandi!</b>\n\n"
        f"📄 Ko'rinish:\n<i>{message.text[:300]}</i>",
        parse_mode="HTML",
        reply_markup=kb_ads_menu()
    )


@router.message(AdvertisementFlow.replacing, F.text)
async def receive_replace_ad(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.set_state(AdvertisementFlow.menu)
        await message.answer("❌ Bekor qilindi.", reply_markup=kb_ads_menu())
        return

    user = await get_or_create_user(message.from_user.id)
    await save_advertisement(user.id, message.text)
    await state.set_state(AdvertisementFlow.menu)

    await message.answer(
        "✅ <b>E'lon yangilandi!</b>\n\n"
        f"📄 Ko'rinish:\n<i>{message.text[:300]}</i>",
        parse_mode="HTML",
        reply_markup=kb_ads_menu()
    )


@router.callback_query(AdvertisementFlow.confirm_clear, F.data == "clear_ads:yes")
async def cb_confirm_clear(call: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(call.from_user.id)
    await clear_advertisements(user.id)
    await state.set_state(AdvertisementFlow.menu)
    await call.message.edit_text("🗑 <b>Barcha e'lonlar o'chirildi.</b>", parse_mode="HTML")
    await call.message.answer("📝 E'lonlar Boshqaruvi:", reply_markup=kb_ads_menu())
    await call.answer("O'chirildi!")


@router.callback_query(AdvertisementFlow.confirm_clear, F.data == "clear_ads:no")
async def cb_cancel_clear(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdvertisementFlow.menu)
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.message.answer("📝 E'lonlar Boshqaruvi:", reply_markup=kb_ads_menu())
    await call.answer()
