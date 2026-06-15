from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import config


def kb_plans() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, plan in config.PLANS.items():
        builder.button(text=plan["label"], callback_data=f"plan:{key}")
    builder.adjust(1)
    return builder.as_markup()


def kb_payment_methods() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👨‍💼 Admin orqali to'lash", callback_data="pay:admin")
    builder.button(text="💳 Click orqali avtomatik to'lash", callback_data="pay:click")
    builder.button(text="🏦 Karta o'tkazma + Screenshot", callback_data="pay:card")
    builder.button(text="🔙 Orqaga", callback_data="pay:back")
    builder.adjust(1)
    return builder.as_markup()


def kb_agree_phone() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Roziman, davom etish", callback_data="phone:agree")
    builder.button(text="🔙 Menyuga qaytish", callback_data="phone:cancel")
    builder.adjust(1)
    return builder.as_markup()


def kb_share_phone() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Kontaktni ulashish", request_contact=True)
    builder.button(text="✏️ Qo'lda kiritish")
    builder.button(text="❌ Bekor qilish")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_cancel() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Bekor qilish")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def kb_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Raqam qo'shish")
    builder.button(text="📂 Guruh qo'shish")
    builder.button(text="📝 E'lonlar")
    builder.button(text="⏱ Interval")
    builder.button(text="▶️ Yuborishni boshlash")
    builder.button(text="💰 To'lovlarim")
    builder.button(text="👨‍💼 Admin bilan bog'lanish")
    if is_admin:
        builder.button(text="⚙️ Admin Panel")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def kb_ads_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ E'lon qo'shish")
    builder.button(text="🆕 E'lonni almashtirish")
    builder.button(text="🗑 E'lonlarni o'chirish")
    builder.button(text="🔙 Orqaga")
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)


def kb_confirm_clear() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data="clear_ads:yes")
    builder.button(text="❌ Yo'q, saqlab qolish", callback_data="clear_ads:no")
    builder.adjust(2)
    return builder.as_markup()


def kb_interval() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mins in [7, 10, 15, 20]:
        builder.button(text=f"⏱ {mins} daqiqa", callback_data=f"interval:{mins}")
    builder.button(text="🔙 Orqaga", callback_data="interval:back")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def kb_sending() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="⏸ Pauza")
    builder.button(text="⏹ To'xtatish")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def kb_sending_paused() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="▶️ Davom ettirish")
    builder.button(text="⏹ To'xtatish")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def kb_admin_panel() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="👥 Foydalanuvchilar")
    builder.button(text="💰 To'lovlar")
    builder.button(text="📊 Statistika")
    builder.button(text="📢 Xabar yuborish")
    builder.button(text="🚫 Bloklash")
    builder.button(text="✅ Foydalanuvchini tasdiqlash")
    builder.button(text="⏹ Yuborishni to'xtatish")
    builder.button(text="🔙 Asosiy menyu")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def kb_approve_payment(payment_id: int, user_tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"admin_pay:approve:{payment_id}:{user_tg_id}")
    builder.button(text="❌ Rad etish", callback_data=f"admin_pay:reject:{payment_id}:{user_tg_id}")
    builder.adjust(2)
    return builder.as_markup()


def kb_user_actions(user_tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Bloklash", callback_data=f"admin_user:ban:{user_tg_id}")
    builder.button(text="✅ Blokdan chiqarish", callback_data=f"admin_user:unban:{user_tg_id}")
    builder.button(text="⏹ Yuborishni to'xtatish", callback_data=f"admin_user:stop:{user_tg_id}")
    builder.button(text="🔙 Orqaga", callback_data="admin_user:back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def kb_folders(folders: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, folder in enumerate(folders):
        builder.button(text=f"📁 {folder['title']}", callback_data=f"folder:{i}")
    builder.button(text="🗑 Guruhlarni tozalash", callback_data="folder:clear")
    builder.button(text="🔙 Orqaga", callback_data="folder:back")
    builder.adjust(1)
    return builder.as_markup()


def kb_groups_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📁 Jild tanlash", callback_data="groups:choose_folder")
    builder.button(text="🗑 Guruhlarni tozalash", callback_data="groups:clear")
    builder.button(text="🔙 Orqaga", callback_data="groups:back")
    builder.adjust(1)
    return builder.as_markup()


def kb_confirm_clear_groups() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data="groups:confirm_clear")
    builder.button(text="❌ Bekor qilish", callback_data="groups:cancel_clear")
    builder.adjust(2)
    return builder.as_markup()


def kb_phone_menu(has_phone: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_phone:
        builder.button(text="🔄 Raqamni almashtirish", callback_data="phone:agree")
        builder.button(text="🗑 Raqamni uzish (session o'chirish)", callback_data="phone:disconnect")
    else:
        builder.button(text="✅ Roziman, davom etish", callback_data="phone:agree")
    builder.button(text="🔙 Menyuga qaytish", callback_data="phone:cancel")
    builder.adjust(1)
    return builder.as_markup()


def kb_confirm_disconnect() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, uzish", callback_data="phone:confirm_disconnect")
    builder.button(text="❌ Bekor qilish", callback_data="phone:cancel")
    builder.adjust(2)
    return builder.as_markup()


def kb_back_inline(callback: str = "back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data=callback)
    return builder.as_markup()


remove_kb = ReplyKeyboardRemove()
