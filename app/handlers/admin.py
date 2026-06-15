import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Filter

from app.database import (
    get_or_create_user, get_all_users, get_user, get_user_payments,
    get_active_subscription, update_user, update_settings,
    get_total_stats
)
from app.keyboards import kb_admin_panel, kb_main_menu, kb_cancel
from app.states import AdminFlow
from app.services import sender_service
from config import config

router = Router()
logger = logging.getLogger(__name__)


class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in config.ADMIN_IDS


@router.message(F.text == "⚙️ Admin Panel", IsAdmin())
async def btn_admin_panel(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.panel)
    await message.answer(
        "⚙️ <b>Admin Panel</b>\n\nXush kelibsiz, Admin! Kerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=kb_admin_panel()
    )


@router.message(AdminFlow.panel, F.text == "👥 Foydalanuvchilar", IsAdmin())
async def btn_users(message: Message):
    users = await get_all_users()
    lines = [f"👥 <b>Barcha Foydalanuvchilar ({len(users)} ta)</b>\n"]
    for u in users[:30]:
        status = "✅" if u.is_active else ("🚫" if u.is_banned else "⏳")
        name = u.full_name or u.username or f"ID:{u.telegram_id}"
        lines.append(f"{status} <a href='tg://user?id={u.telegram_id}'>{name}</a> — <code>{u.telegram_id}</code>")
    if len(users) > 30:
        lines.append(f"\n<i>...va yana {len(users)-30} ta</i>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(AdminFlow.panel, F.text == "📊 Statistika", IsAdmin())
async def btn_statistics(message: Message):
    stats = await get_total_stats()
    await message.answer(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"✅ Faol foydalanuvchilar: <b>{stats['active_users']}</b>\n"
        f"💰 Jami daromad: <b>{stats['total_revenue']:,} so'm</b>\n"
        f"📨 Yuborilgan xabarlar: <b>{stats['messages_sent']}</b>\n\n"
        f"🕐 Vaqt: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        parse_mode="HTML"
    )


@router.message(AdminFlow.panel, F.text == "💰 To'lovlar", IsAdmin())
async def btn_payments(message: Message):
    users = await get_all_users()
    lines = [f"💰 <b>So'nggi To'lovlar</b>\n"]
    count = 0
    for u in users:
        payments = await get_user_payments(u.id)
        for p in payments[:3]:
            status_emoji = {"approved": "✅", "rejected": "❌", "pending": "⏳"}.get(p.status, "❓")
            method_uz = {"admin": "Admin", "click": "Click", "card": "Karta"}.get(p.method, p.method)
            name = u.full_name or u.username or str(u.telegram_id)
            lines.append(
                f"{status_emoji} {name} — <b>{p.amount:,} so'm</b> ({method_uz}) "
                f"[{p.created_at.strftime('%m-%d')}]"
            )
            count += 1
            if count >= 20:
                break
        if count >= 20:
            break
    await message.answer("\n".join(lines) if len(lines) > 1 else "To'lovlar topilmadi.", parse_mode="HTML")


@router.message(AdminFlow.panel, F.text == "📢 Xabar yuborish", IsAdmin())
async def btn_broadcast(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.broadcast)
    await message.answer(
        "📢 <b>Ommaviy Xabar</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(AdminFlow.broadcast, F.text == "❌ Bekor qilish", IsAdmin())
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.panel)
    await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin_panel())


@router.message(AdminFlow.broadcast, IsAdmin())
async def do_broadcast(message: Message, state: FSMContext):
    users = await get_all_users()
    sent = failed = 0
    status_msg = await message.answer(f"📢 {len(users)} ta foydalanuvchiga yuborilmoqda...")

    for u in users:
        if u.is_banned:
            continue
        try:
            await message.bot.send_message(
                u.telegram_id,
                f"📢 <b>Admin xabari</b>\n\n{message.text}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

    await state.set_state(AdminFlow.panel)
    await status_msg.edit_text(
        f"📢 <b>Yuborish Yakunlandi</b>\n\n"
        f"✅ Yuborildi: <b>{sent}</b>\n"
        f"❌ Xato: <b>{failed}</b>",
        parse_mode="HTML"
    )
    await message.answer("Admin Panel:", reply_markup=kb_admin_panel())


@router.message(AdminFlow.panel, F.text == "🚫 Bloklash", IsAdmin())
async def btn_ban_user(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.ban_input)
    await message.answer(
        "🚫 <b>Foydalanuvchini Bloklash</b>\n\nBloklash uchun Telegram ID kiriting:",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(AdminFlow.ban_input, F.text == "❌ Bekor qilish", IsAdmin())
async def cancel_ban(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.panel)
    await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin_panel())


@router.message(AdminFlow.ban_input, IsAdmin())
async def do_ban(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
        target = await get_user(target_id)
        if not target:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            return
        await update_user(target_id, is_banned=True, is_active=False)
        await sender_service.stop_all_for_user(target.id)
        try:
            await message.bot.send_message(
                target_id,
                "🚫 <b>Hisobingiz bloklandi.</b>\n\nMurojaat uchun qo'llab-quvvatlash xizmatiga yozing.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await state.set_state(AdminFlow.panel)
        await message.answer(
            f"✅ Foydalanuvchi <code>{target_id}</code> bloklandi.",
            parse_mode="HTML",
            reply_markup=kb_admin_panel()
        )
    except ValueError:
        await message.answer("❌ Noto'g'ri ID. Raqamli Telegram ID kiriting.")


@router.message(AdminFlow.panel, F.text == "✅ Foydalanuvchini tasdiqlash", IsAdmin())
async def btn_approve_user(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.edit_sub)
    await state.update_data(action="approve")
    await message.answer(
        "✅ <b>Foydalanuvchini Tasdiqlash</b>\n\nFaollashtirish uchun Telegram ID kiriting:",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(AdminFlow.panel, F.text == "⏹ Yuborishni to'xtatish", IsAdmin())
async def btn_stop_user(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.edit_sub)
    await state.update_data(action="stop_sending")
    await message.answer(
        "⏹ <b>Foydalanuvchi Yuborishini To'xtatish</b>\n\nTelegram ID kiriting:",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(AdminFlow.edit_sub, F.text == "❌ Bekor qilish", IsAdmin())
async def cancel_edit_sub(message: Message, state: FSMContext):
    await state.set_state(AdminFlow.panel)
    await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin_panel())


@router.message(AdminFlow.edit_sub, IsAdmin())
async def do_edit_sub(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")
    try:
        target_id = int(message.text.strip())
        target = await get_user(target_id)
        if not target:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            return

        if action == "approve":
            await update_user(target_id, is_active=True, is_banned=False)
            try:
                await message.bot.send_message(
                    target_id,
                    "✅ <b>Kirish Berildi!</b>\n\nAdmin tomonidan tasdiqlandi. Davom etish uchun /menu yuboring.",
                    parse_mode="HTML",
                    reply_markup=kb_main_menu(is_admin=False)
                )
            except Exception:
                pass
            result = f"✅ Foydalanuvchi <code>{target_id}</code> tasdiqlandi."

        elif action == "stop_sending":
            await sender_service.stop_all_for_user(target.id)
            await update_settings(target.id, is_sending=False, sending_paused=False)
            try:
                await message.bot.send_message(
                    target_id,
                    "⏹ <b>Yuborish To'xtatildi</b>\n\nYuborishingiz admin tomonidan to'xtatildi.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            result = f"⏹ Foydalanuvchi <code>{target_id}</code> yuborishi to'xtatildi."
        else:
            result = "❓ Noma'lum amal."

        await state.set_state(AdminFlow.panel)
        await message.answer(result, parse_mode="HTML", reply_markup=kb_admin_panel())

    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")


@router.message(AdminFlow.panel, F.text == "🔙 Asosiy menyu", IsAdmin())
async def btn_admin_back(message: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(message.from_user.id)
    await message.answer("📋 Asosiy menyu:", reply_markup=kb_main_menu(is_admin=True))
