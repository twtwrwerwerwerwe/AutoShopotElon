import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.database import get_or_create_user
from config import config

logger = logging.getLogger(__name__)

EXEMPT_TEXTS = {"💰 To'lovlarim", "👨‍💼 Admin bilan bog'lanish"}


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        if event.from_user and event.from_user.id in config.ADMIN_IDS:
            return await handler(event, data)

        text = event.text or ""
        if text.startswith("/start") or text.startswith("/menu"):
            return await handler(event, data)

        user = await get_or_create_user(
            telegram_id=event.from_user.id,
            username=event.from_user.username,
            full_name=event.from_user.full_name,
        )

        if user.is_banned:
            await event.answer("🚫 Hisobingiz bloklangan. Murojaat uchun admin bilan bog'laning.")
            return

        if not user.is_active:
            if text in EXEMPT_TEXTS:
                return await handler(event, data)

            state = data.get("state")
            if state:
                current = await state.get_state()
                if current and ("PaymentFlow" in (current or "") or "PhoneFlow" in (current or "")):
                    return await handler(event, data)

            if not text.startswith("/"):
                await event.answer(
                    "❌ <b>Faol obuna yo'q</b>\n\n"
                    "Botdan foydalanish uchun obuna kerak.\n"
                    "Reja tanlash uchun /start yuboring.",
                    parse_mode="HTML",
                )
                return

        return await handler(event, data)
