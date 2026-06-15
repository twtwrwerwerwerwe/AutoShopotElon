import asyncio
import logging
from datetime import datetime
from typing import Dict

from app.database import (
    get_active_advertisement, get_user_groups,
    get_or_create_settings, update_settings, add_send_stat
)
from app.services.telethon_service import send_message_to_group

logger = logging.getLogger(__name__)

# Aktiv yuborish tasklari: {user_db_id: asyncio.Task}
_sending_tasks: Dict[int, asyncio.Task] = {}

# Guruhlar orasidagi kutish (spam himoyasi uchun sekundda)
DELAY_BETWEEN_GROUPS = 8  # har bir guruh orasida 8 soniya


async def start_sending(bot, user_db_id: int, telegram_id: int, session_string: str):
    """Foydalanuvchi uchun yuborish siklini boshlash."""
    if user_db_id in _sending_tasks:
        task = _sending_tasks[user_db_id]
        if not task.done():
            return

    task = asyncio.create_task(
        _sending_loop(bot, user_db_id, telegram_id, session_string),
        name=f"send_{user_db_id}"
    )
    _sending_tasks[user_db_id] = task


async def stop_sending(user_db_id: int):
    """Foydalanuvchi uchun yuborish siklini to'xtatish."""
    if user_db_id in _sending_tasks:
        task = _sending_tasks[user_db_id]
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=3)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        del _sending_tasks[user_db_id]
    await update_settings(user_db_id, is_sending=False, sending_paused=False)


async def pause_sending(user_db_id: int):
    await update_settings(user_db_id, sending_paused=True)


async def resume_sending(user_db_id: int):
    await update_settings(user_db_id, sending_paused=False)


def is_sending(user_db_id: int) -> bool:
    if user_db_id not in _sending_tasks:
        return False
    return not _sending_tasks[user_db_id].done()


async def stop_all_for_user(user_db_id: int):
    """Admin tomonidan majburiy to'xtatish."""
    await stop_sending(user_db_id)


async def _sending_loop(bot, user_db_id: int, telegram_id: int, session_string: str):
    """
    Asosiy yuborish sikli.

    Mantiq:
    1. Barcha tanlangan guruplarga birin-ketin xabar yuboriladi (guruhlar orasida DELAY_BETWEEN_GROUPS soniya kutiladi)
    2. HAMMA guruhlarga yuborib bo'lgandan keyin interval_minutes kutiladi
    3. Keyin yana boshidan takrorlanadi
    """
    logger.info(f"Yuborish sikli boshlandi: foydalanuvchi {user_db_id}")
    await update_settings(user_db_id, is_sending=True, sending_paused=False)

    try:
        while True:
            settings = await get_or_create_settings(user_db_id)

            # Pauza holatini tekshirish
            if settings.sending_paused:
                await asyncio.sleep(3)
                continue

            # Joriy e'lonni olish
            ad = await get_active_advertisement(user_db_id)
            if not ad:
                logger.warning(f"Foydalanuvchi {user_db_id} uchun e'lon topilmadi, 30 soniya kutilmoqda")
                await asyncio.sleep(30)
                continue

            # Joriy guruhlarni olish
            groups = await get_user_groups(user_db_id)
            if not groups:
                logger.warning(f"Foydalanuvchi {user_db_id} uchun guruhlar topilmadi, 30 soniya kutilmoqda")
                await asyncio.sleep(30)
                continue

            interval_minutes = settings.interval_minutes or 10
            total_groups = len(groups)

            logger.info(
                f"Foydalanuvchi {user_db_id}: {total_groups} ta guruhga yuborilmoqda, "
                f"interval={interval_minutes} daqiqa, guruhlar orasida {DELAY_BETWEEN_GROUPS}s kutish"
            )

            sent_count = 0
            failed_count = 0

            # ── Hamma guruplarga ketma-ket yuborish ──────────────────────────
            for idx, group in enumerate(groups, 1):

                # Har bir guruhdan oldin pauza/to'xtatishni tekshirish
                settings = await get_or_create_settings(user_db_id)
                if settings.sending_paused:
                    logger.info(f"Foydalanuvchi {user_db_id}: pauza qilindi ({idx}/{total_groups})")
                    while True:
                        await asyncio.sleep(3)
                        settings = await get_or_create_settings(user_db_id)
                        if not settings.sending_paused:
                            logger.info(f"Foydalanuvchi {user_db_id}: davom ettirildi")
                            break

                # E'lon o'zgargan bo'lishi mumkin — yangilab olamiz
                ad = await get_active_advertisement(user_db_id)
                if not ad:
                    break

                # Xabar yuborish
                success, error_msg = await send_message_to_group(
                    user_db_id=user_db_id,
                    session_string=session_string,
                    group_id=group.group_id,
                    text=ad.text,
                    group_username=group.group_username,
                )

                await add_send_stat(
                    user_db_id=user_db_id,
                    group_id=group.group_id,
                    group_title=group.group_title or "",
                    success=success,
                    error_msg=error_msg if not success else None,
                )

                if success:
                    sent_count += 1
                    logger.info(f"✅ [{idx}/{total_groups}] {group.group_title} — foydalanuvchi {user_db_id}")
                else:
                    failed_count += 1
                    logger.warning(f"❌ [{idx}/{total_groups}] {group.group_title}: {error_msg}")

                # Oxirgi guruhdan keyin kutmaslik
                if idx < total_groups:
                    await asyncio.sleep(DELAY_BETWEEN_GROUPS)

            # ── Bir sikl tugadi ───────────────────────────────────────────────
            logger.info(
                f"Foydalanuvchi {user_db_id}: sikl tugadi. "
                f"✅{sent_count} ❌{failed_count}. "
                f"Keyingi sikl {interval_minutes} daqiqadan keyin."
            )

            # Foydalanuvchiga statistika yuborish (ixtiyoriy — har 5 siklda 1 ta)
            # (Spam bo'lmasin deb o'chirib qo'yilgan, kerak bo'lsa yoqiladi)

            # Intervalning to'liq vaqtini kutish
            await asyncio.sleep(interval_minutes * 60)

    except asyncio.CancelledError:
        logger.info(f"Yuborish sikli bekor qilindi: foydalanuvchi {user_db_id}")
        raise
    except Exception as e:
        logger.error(f"Yuborish sikli xatosi foydalanuvchi {user_db_id}: {e}", exc_info=True)
    finally:
        await update_settings(user_db_id, is_sending=False, sending_paused=False)
        if user_db_id in _sending_tasks:
            del _sending_tasks[user_db_id]
        logger.info(f"Yuborish sikli tugatildi: foydalanuvchi {user_db_id}")
