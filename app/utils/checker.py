import logging
from dataclasses import dataclass
from typing import Any

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotChatValidationResult:
    ok: bool
    message: str | None = None
    chat: Any | None = None
    member: Any | None = None


@dataclass(frozen=True)
class UserSubscriptionCheckResult:
    ok: bool
    is_subscribed: bool = False
    message: str | None = None
    member: Any | None = None


BOT_NOT_IN_CHAT_MESSAGE = "Bot kanal/guruhga qo'shilmagan yoki chiqarib yuborilgan."
BOT_ADMIN_REQUIRED_MESSAGE = "Botni admin qiling."
BOT_PERMISSION_REQUIRED_MESSAGE = "Botda yetarli huquq yo'q."
CHAT_NOT_FOUND_MESSAGE = "Kanal/guruh topilmadi."
CHAT_CHECK_FAILED_MESSAGE = "Kanal/guruhni tekshirib bo'lmadi."
SUBSCRIPTION_CHECK_FAILED_MESSAGE = (
    "Obuna holatini tekshirib bo'lmadi. Bot kanal/guruhga qo'shilgan va admin "
    "ekanini tekshiring."
)


async def is_user_subscribed(bot, chat_identifier, user_id: int) -> bool:
    result = await check_user_subscription(bot, chat_identifier, user_id)
    return result.ok and result.is_subscribed


async def check_user_subscription(
    bot,
    chat_identifier,
    user_id: int,
) -> UserSubscriptionCheckResult:
    try:
        member = await bot.get_chat_member(
            chat_id=chat_identifier,
            user_id=user_id,
        )
    except TelegramForbiddenError as error:
        logger.warning(
            "Bot obunani tekshira olmayapti | chat=%s user=%s error=%s",
            chat_identifier,
            user_id,
            error,
        )
        return UserSubscriptionCheckResult(
            ok=False,
            message=BOT_NOT_IN_CHAT_MESSAGE,
        )
    except TelegramBadRequest as error:
        logger.warning(
            "Obuna kanali/guruhi topilmadi | chat=%s user=%s error=%s",
            chat_identifier,
            user_id,
            error,
        )
        return UserSubscriptionCheckResult(
            ok=False,
            message=SUBSCRIPTION_CHECK_FAILED_MESSAGE,
        )
    except TelegramAPIError as error:
        logger.warning(
            "Obuna holatini tekshirib bo'lmadi | chat=%s user=%s error=%s",
            chat_identifier,
            user_id,
            error,
        )
        return UserSubscriptionCheckResult(
            ok=False,
            message=SUBSCRIPTION_CHECK_FAILED_MESSAGE,
        )

    return UserSubscriptionCheckResult(
        ok=True,
        is_subscribed=member.status in ("member", "administrator", "creator"),
        member=member,
    )


async def get_bot_id(bot) -> int:
    cached_bot_id = getattr(bot, "_cached_bot_id", None)
    if cached_bot_id is not None:
        return cached_bot_id

    me = await bot.get_me()
    setattr(bot, "_cached_bot_id", me.id)
    return me.id


async def is_bot_admin_in_chat(bot, chat_identifier) -> bool:
    result = await check_bot_admin(bot, chat_identifier)
    return result.ok


async def check_bot_in_chat(bot, chat_identifier) -> BotChatValidationResult:
    try:
        chat = await bot.get_chat(chat_identifier)
    except TelegramForbiddenError as error:
        logger.warning(
            "Bot chatga kira olmayapti | chat=%s error=%s",
            chat_identifier,
            error,
        )
        return BotChatValidationResult(ok=False, message=BOT_NOT_IN_CHAT_MESSAGE)
    except TelegramBadRequest as error:
        logger.warning(
            "Chat topilmadi | chat=%s error=%s",
            chat_identifier,
            error,
        )
        return BotChatValidationResult(ok=False, message=CHAT_NOT_FOUND_MESSAGE)
    except TelegramAPIError as error:
        logger.warning(
            "Chatni tekshirib bo'lmadi | chat=%s error=%s",
            chat_identifier,
            error,
        )
        return BotChatValidationResult(ok=False, message=CHAT_CHECK_FAILED_MESSAGE)

    return BotChatValidationResult(ok=True, chat=chat)


async def check_bot_admin(bot, chat_identifier) -> BotChatValidationResult:
    chat_result = await check_bot_in_chat(bot, chat_identifier)
    if not chat_result.ok:
        return chat_result

    try:
        bot_id = await get_bot_id(bot)
        member = await bot.get_chat_member(
            chat_id=chat_identifier,
            user_id=bot_id,
        )
    except TelegramForbiddenError as error:
        logger.warning(
            "Bot adminligini tekshirishda forbidden | chat=%s error=%s",
            chat_identifier,
            error,
        )
        return BotChatValidationResult(
            ok=False,
            message=BOT_NOT_IN_CHAT_MESSAGE,
            chat=chat_result.chat,
        )
    except TelegramBadRequest as error:
        logger.warning(
            "Bot adminligini tekshirishda chat topilmadi | chat=%s error=%s",
            chat_identifier,
            error,
        )
        return BotChatValidationResult(
            ok=False,
            message=BOT_ADMIN_REQUIRED_MESSAGE,
            chat=chat_result.chat,
        )
    except TelegramAPIError as error:
        logger.warning(
            "Bot admin huquqini tekshirib bo'lmadi | chat=%s error=%s",
            chat_identifier,
            error,
        )
        return BotChatValidationResult(
            ok=False,
            message=CHAT_CHECK_FAILED_MESSAGE,
            chat=chat_result.chat,
        )

    if member.status not in ("administrator", "creator"):
        return BotChatValidationResult(
            ok=False,
            message=BOT_ADMIN_REQUIRED_MESSAGE,
            chat=chat_result.chat,
            member=member,
        )

    return BotChatValidationResult(
        ok=True,
        chat=chat_result.chat,
        member=member,
    )


def _has_permission(member, permission_name: str) -> bool:
    if getattr(member, "status", None) == "creator":
        return True
    return bool(getattr(member, permission_name, False))


def _format_missing_permissions(missing_permissions: list[str]) -> str:
    if not missing_permissions:
        return BOT_PERMISSION_REQUIRED_MESSAGE

    return f"{BOT_PERMISSION_REQUIRED_MESSAGE} Yetishmayotgan huquqlar: {', '.join(missing_permissions)}."


async def check_bot_permissions(
    bot,
    chat_identifier,
    *,
    can_post_messages: bool = False,
    can_delete_messages: bool = False,
    can_invite_users: bool = False,
) -> BotChatValidationResult:
    admin_result = await check_bot_admin(bot, chat_identifier)
    if not admin_result.ok:
        return admin_result

    permissions = {
        "post yuborish": ("can_post_messages", can_post_messages),
        "message o'chirish": ("can_delete_messages", can_delete_messages),
        "invite link olish": ("can_invite_users", can_invite_users),
    }
    missing_permissions = [
        label
        for label, (attribute, required) in permissions.items()
        if required and not _has_permission(admin_result.member, attribute)
    ]

    if missing_permissions:
        return BotChatValidationResult(
            ok=False,
            message=_format_missing_permissions(missing_permissions),
            chat=admin_result.chat,
            member=admin_result.member,
        )

    return admin_result


async def validate_bot_for_movie_base(bot, chat_identifier) -> BotChatValidationResult:
    return await check_bot_permissions(
        bot,
        chat_identifier,
        can_post_messages=True,
        can_delete_messages=True,
    )


async def validate_bot_for_subscription(bot, chat_identifier) -> BotChatValidationResult:
    return await check_bot_admin(bot, chat_identifier)
