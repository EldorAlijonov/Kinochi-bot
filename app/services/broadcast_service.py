import asyncio
import logging
import re
from dataclasses import dataclass
from html import unescape

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from app.utils.datetime import format_local_datetime
from app.utils.telegram_errors import call_telegram_with_retry, classify_telegram_error
from app.utils.text import safe_html

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BroadcastTarget:
    target_type: str
    identifier: int | str
    target_chat_id: int | None = None
    error_text: str | None = None


class BroadcastService:
    BATCH_SIZE = 100
    DELIVERY_FLUSH_SIZE = 100
    PROGRESS_INTERVAL = 500
    PROGRESS_MIN_SECONDS = 30
    SLEEP_SECONDS = 0.05

    TARGET_LABELS = {
        "users": "foydalanuvchilar",
        "groups": "guruhlar",
        "channels": "kanallar",
        "all": "barchasi",
    }
    CONTENT_LABELS = {
        "text": "matn",
        "photo": "photo",
        "video": "video",
        "document": "hujjat",
        "animation": "animation",
        "audio": "audio",
        "voice": "voice",
    }

    def __init__(
        self,
        user_repository,
        broadcast_repository=None,
        subscription_repository=None,
    ):
        self.user_repository = user_repository
        self.broadcast_repository = broadcast_repository
        self.subscription_repository = subscription_repository

    async def send_broadcast(self, bot, text: str, audience: str) -> dict:
        sent_count = 0
        failed_count = 0
        last_telegram_id = 0

        while True:
            user_ids = await self.user_repository.list_broadcast_user_ids_after(
                audience=audience,
                limit=self.BATCH_SIZE,
                last_telegram_id=last_telegram_id,
            )
            if not user_ids:
                break

            for user_id in user_ids:
                try:
                    await bot.send_message(chat_id=user_id, text=text)
                    sent_count += 1
                except TelegramAPIError:
                    failed_count += 1
                    logger.exception("Broadcast yuborishda Telegram xatosi | user_id=%s", user_id)
                except Exception:
                    failed_count += 1
                    logger.exception("Broadcast yuborishda kutilmagan xatolik | user_id=%s", user_id)

                await asyncio.sleep(self.SLEEP_SECONDS)

            last_telegram_id = user_ids[-1]

        return {
            "sent": sent_count,
            "failed": failed_count,
            "audience": audience,
        }

    async def prepare_campaign(
        self,
        admin_id: int,
        content_type: str,
        text: str | None,
        file_id: str | None,
        source_chat_id: int,
        source_message_id: int,
        target_type: str,
    ):
        self._require_broadcast_repository()
        return await self.broadcast_repository.create_campaign(
            admin_id=admin_id,
            content_type=content_type,
            text=text,
            file_id=file_id,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            target_type=target_type,
            status="queued",
        )

    async def send_campaign(
        self,
        bot,
        campaign,
        progress_callback=None,
        cancel_checker=None,
    ) -> dict:
        self._require_broadcast_repository()
        stats = self._empty_stats()
        processed = 0
        pending_deliveries = 0

        bot_user = await bot.get_me()
        async for target in self._iter_targets(campaign.target_type):
            await self._send_campaign_to_target(bot, bot_user.id, campaign, target, stats)
            processed += 1
            pending_deliveries += 1

            if pending_deliveries >= self.DELIVERY_FLUSH_SIZE:
                await self._flush_deliveries()
                pending_deliveries = 0

            if progress_callback and processed % self.PROGRESS_INTERVAL == 0:
                await self._flush_deliveries()
                pending_deliveries = 0
                await progress_callback(processed, stats)

            if cancel_checker and await cancel_checker():
                stats["cancelled"] = True
                break

            await asyncio.sleep(self.SLEEP_SECONDS)

        if pending_deliveries:
            await self._flush_deliveries()

        if stats.get("cancelled"):
            status = "cancelled"
        else:
            status = "sent" if stats["failed"] == 0 else "partial"
        await self.broadcast_repository.mark_campaign_status(campaign.id, status)
        return stats

    async def delete_campaign_messages(self, bot, campaign) -> dict:
        self._require_broadcast_repository()
        stats = self._empty_delete_stats()
        last_delivery_id = 0

        while True:
            deliveries = await self.broadcast_repository.list_deliveries_by_campaign_after(
                campaign_id=campaign.id,
                last_delivery_id=last_delivery_id,
                limit=self.BATCH_SIZE,
            )
            if not deliveries:
                break

            for delivery in deliveries:
                last_delivery_id = delivery.id
                if delivery.delivery_status not in {"sent"} or not delivery.sent_message_id:
                    continue

                chat_id = delivery.target_chat_id or delivery.target_identifier
                if not chat_id:
                    stats["failed"] += 1
                    continue

                try:
                    await bot.delete_message(
                        chat_id=chat_id,
                        message_id=delivery.sent_message_id,
                    )
                    await self.broadcast_repository.mark_delivery_deleted(delivery.id)
                    stats[delivery.target_type] += 1
                except TelegramAPIError as error:
                    stats["failed"] += 1
                    logger.warning(
                        "Reklama xabarini o'chirishda Telegram xatosi | delivery_id=%s error=%s",
                        delivery.id,
                        error,
                    )
                except Exception:
                    stats["failed"] += 1
                    logger.exception(
                        "Reklama xabarini o'chirishda kutilmagan xatolik | delivery_id=%s",
                        delivery.id,
                    )

                await asyncio.sleep(self.SLEEP_SECONDS)

        status = "partial_deleted" if stats["failed"] > 0 else "deleted"
        await self.broadcast_repository.mark_campaign_deleted(campaign.id, status=status)
        return stats

    async def estimate_recipients(self, target_type: str) -> dict:
        users = await self.user_repository.count_users() if self.user_repository and target_type in {"users", "all"} else 0
        groups = len(await self.subscription_repository.list_group_targets()) if self.subscription_repository and target_type in {"groups", "all"} else 0
        channels = len(await self.subscription_repository.list_channel_targets()) if self.subscription_repository and target_type in {"channels", "all"} else 0
        return {"users": users or 0, "groups": groups, "channels": channels}

    def build_campaign_preview(
        self,
        content_type: str,
        text: str | None,
        target_type: str,
        estimate: dict | None = None,
    ) -> str:
        preview = safe_html(self.clean_preview_text(text))
        estimate_text = ""
        if estimate:
            estimate_text = (
                "\n"
                f"Taxminiy userlar: <b>{estimate.get('users', 0)}</b>\n"
                f"Taxminiy guruhlar: <b>{estimate.get('groups', 0)}</b>\n"
                f"Taxminiy kanallar: <b>{estimate.get('channels', 0)}</b>\n"
            )
        return (
            "📢 <b>Reklama tasdiqlash</b>\n\n"
            f"Turi: <b>{self.CONTENT_LABELS.get(content_type, content_type)}</b>\n"
            f"Auditoriya: <b>{self.TARGET_LABELS.get(target_type, target_type)}</b>\n"
            f"{estimate_text}"
            f"Preview: {preview}\n\n"
            "Yuborishni tasdiqlaysizmi?"
        )

    async def build_campaign_history(self, page: int = 1, page_size: int = 10) -> str:
        self._require_broadcast_repository()
        page = max(1, page)
        offset = (page - 1) * page_size
        campaigns = await self.broadcast_repository.list_campaigns(
            limit=page_size,
            offset=offset,
        )
        total = await self.broadcast_repository.count_campaigns()
        if not campaigns:
            return "📋 Reklamalar tarixi hozircha bo'sh."

        rows = []
        for campaign in campaigns:
            counts = await self.broadcast_repository.count_deliveries_by_status(campaign.id)
            sent = counts.get("sent", 0) + counts.get("deleted", 0)
            status = "o'chirilgan" if campaign.is_deleted else "o'chirilmagan"
            rows.append(
                self._campaign_list_preview(campaign, sent)
                + "\n"
                f"Sana: {format_local_datetime(campaign.created_at)}\n"
                f"Auditoriya: <b>{self.TARGET_LABELS.get(campaign.target_type, campaign.target_type)}</b> | "
                f"Holat: <b>{status}</b>"
            )

        total_pages = max(1, (total + page_size - 1) // page_size)
        return (
            "📋 <b>Reklamalar tarixi</b>\n"
            f"Sahifa: <b>{page}/{total_pages}</b>\n\n"
            + "\n\n".join(rows)
        )

    async def build_delete_list(self, limit: int = 10) -> str:
        self._require_broadcast_repository()
        campaigns = await self.broadcast_repository.list_campaigns(limit=limit, offset=0)
        campaigns = [campaign for campaign in campaigns if not campaign.is_deleted]
        if not campaigns:
            return "O'chiriladigan reklama topilmadi."

        rows = []
        for campaign in campaigns:
            counts = await self.broadcast_repository.count_deliveries_by_status(campaign.id)
            sent = counts.get("sent", 0)
            rows.append(self._campaign_list_preview(campaign, sent))
        return (
            "🗑 <b>O'chiriladigan reklamani tanlang</b>\n\n"
            + "\n".join(rows)
            + "\n\nReklama ID raqamini yuboring."
        )

    async def build_campaign_delete_confirm(self, campaign_id: int) -> str | None:
        self._require_broadcast_repository()
        campaign = await self.broadcast_repository.get_campaign_by_id(campaign_id)
        if not campaign or campaign.is_deleted:
            return None

        counts = await self.broadcast_repository.count_deliveries_by_status(campaign.id)
        sent = counts.get("sent", 0)
        return (
            "Ushbu reklamani barcha yuborilgan joylardan o'chirmoqchimisiz?\n\n"
            f"{self._campaign_list_preview(campaign, sent)}\n"
            f"O'chirishga urinishlar: <b>{sent}</b>"
        )

    async def _send_campaign_to_target(self, bot, bot_id: int, campaign, target, stats: dict) -> None:
        try:
            if target.error_text:
                raise ValueError(target.error_text)

            resolved_target = await self._resolve_target(bot, bot_id, target)
            sent_message = await self._send_campaign_message(bot, campaign, resolved_target.identifier)
            await self._add_delivery(
                campaign_id=campaign.id,
                target_type=resolved_target.target_type,
                target_chat_id=resolved_target.target_chat_id,
                target_identifier=str(resolved_target.identifier),
                sent_message_id=sent_message.message_id,
                delivery_status="sent",
            )
            stats[resolved_target.target_type] += 1
        except ValueError as error:
            await self._record_failed_delivery(campaign.id, target, str(error))
            self._increment_failed_stats(stats, target.target_type)
            logger.warning(
                "Reklama target manzili noto'g'ri | target_type=%s target=%s error=%s",
                target.target_type,
                target.identifier,
                error,
            )
        except (TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter) as error:
            await self._record_failed_delivery(campaign.id, target, str(error))
            self._increment_failed_stats(stats, target.target_type)
            logger.warning(
                "Reklama yuborilmadi | error_type=%s target_type=%s target=%s error=%s",
                classify_telegram_error(error),
                target.target_type,
                target.identifier,
                error,
            )
        except TelegramAPIError as error:
            await self._record_failed_delivery(campaign.id, target, str(error))
            self._increment_failed_stats(stats, target.target_type)
            logger.warning(
                "Reklama yuborishda Telegram xatosi | target=%s error=%s",
                target.identifier,
                error,
            )
        except Exception as error:
            await self._record_failed_delivery(campaign.id, target, str(error))
            self._increment_failed_stats(stats, target.target_type)
            logger.exception(
                "Reklama yuborishda kutilmagan xatolik | target=%s",
                target.identifier,
            )

    async def _send_campaign_message(self, bot, campaign, chat_id: int | str):
        text = campaign.text or None
        file_id = getattr(campaign, "file_id", None)

        if campaign.content_type == "text":
            return await call_telegram_with_retry(
                lambda: bot.send_message(chat_id=chat_id, text=text or ""),
                logger=logger,
                context=f"broadcast send_message | chat_id={chat_id}",
            )

        if file_id:
            if campaign.content_type == "photo":
                return await call_telegram_with_retry(
                    lambda: bot.send_photo(chat_id=chat_id, photo=file_id, caption=text),
                    logger=logger,
                    context=f"broadcast send_photo | chat_id={chat_id}",
                )
            if campaign.content_type == "video":
                return await call_telegram_with_retry(
                    lambda: bot.send_video(chat_id=chat_id, video=file_id, caption=text),
                    logger=logger,
                    context=f"broadcast send_video | chat_id={chat_id}",
                )
            if campaign.content_type == "document":
                return await call_telegram_with_retry(
                    lambda: bot.send_document(chat_id=chat_id, document=file_id, caption=text),
                    logger=logger,
                    context=f"broadcast send_document | chat_id={chat_id}",
                )
            if campaign.content_type == "animation":
                return await call_telegram_with_retry(
                    lambda: bot.send_animation(chat_id=chat_id, animation=file_id, caption=text),
                    logger=logger,
                    context=f"broadcast send_animation | chat_id={chat_id}",
                )
            if campaign.content_type == "audio":
                return await call_telegram_with_retry(
                    lambda: bot.send_audio(chat_id=chat_id, audio=file_id, caption=text),
                    logger=logger,
                    context=f"broadcast send_audio | chat_id={chat_id}",
                )
            if campaign.content_type == "voice":
                return await call_telegram_with_retry(
                    lambda: bot.send_voice(chat_id=chat_id, voice=file_id, caption=text),
                    logger=logger,
                    context=f"broadcast send_voice | chat_id={chat_id}",
                )

        return await call_telegram_with_retry(
            lambda: bot.copy_message(
                chat_id=chat_id,
                from_chat_id=campaign.source_chat_id,
                message_id=campaign.source_message_id,
            ),
            logger=logger,
            context=f"broadcast copy_message | chat_id={chat_id}",
        )

    async def _record_failed_delivery(self, campaign_id: int, target: BroadcastTarget, error: str):
        await self._add_delivery(
            campaign_id=campaign_id,
            target_type=target.target_type,
            target_chat_id=target.target_chat_id,
            target_identifier=str(target.identifier),
            sent_message_id=None,
            delivery_status="failed",
            error_text=error[:1000],
        )

    async def _add_delivery(self, **kwargs) -> None:
        if hasattr(self.broadcast_repository, "add_delivery"):
            self.broadcast_repository.add_delivery(**kwargs)
            return

        await self.broadcast_repository.create_delivery(**kwargs)

    async def _flush_deliveries(self) -> None:
        if hasattr(self.broadcast_repository, "flush_deliveries"):
            await self.broadcast_repository.flush_deliveries()

    async def _resolve_target(self, bot, bot_id: int, target: BroadcastTarget) -> BroadcastTarget:
        if target.target_type == "users":
            return target

        chat = await bot.get_chat(target.identifier)
        member = await bot.get_chat_member(chat_id=chat.id, user_id=bot_id)
        status = self._member_status(member)
        if status in {"left", "kicked"}:
            raise ValueError("Bot bu chat a'zosi emas.")
        if target.target_type == "channels":
            if status not in {"creator", "administrator"}:
                raise ValueError("Bot kanalda admin emas.")
            if status == "administrator" and getattr(member, "can_post_messages", None) is False:
                raise ValueError("Bot kanalda post yuborish huquqiga ega emas.")

        return BroadcastTarget(
            target_type=target.target_type,
            identifier=chat.id,
            target_chat_id=chat.id,
        )

    async def _iter_targets(self, target_type: str):
        if target_type in {"users", "all"}:
            async for target in self._iter_user_targets():
                yield target
        if target_type in {"groups", "all"}:
            for target in await self._load_subscription_targets("groups"):
                yield target
        if target_type in {"channels", "all"}:
            for target in await self._load_subscription_targets("channels"):
                yield target

    async def _iter_user_targets(self):
        last_telegram_id = 0
        while True:
            user_ids = await self.user_repository.list_user_targets(
                last_telegram_id=last_telegram_id,
                limit=self.BATCH_SIZE,
            )
            if not user_ids:
                break

            for user_id in user_ids:
                yield BroadcastTarget(
                    target_type="users",
                    identifier=user_id,
                    target_chat_id=user_id,
                )
            last_telegram_id = user_ids[-1]

    async def _load_subscription_targets(self, target_type: str) -> list[BroadcastTarget]:
        if not self.subscription_repository:
            return []

        if target_type == "groups":
            rows = await self.subscription_repository.list_group_targets()
        else:
            rows = await self.subscription_repository.list_channel_targets()

        targets = []
        for row in rows:
            identifier, error_text = self.normalize_chat_identifier(
                row.chat_id or row.chat_username or row.invite_link
            )
            target_chat_id = identifier if isinstance(identifier, int) else None
            if error_text:
                identifier = row.chat_id or row.chat_username or row.invite_link or f"subscription:{row.id}"
                target_chat_id = row.chat_id if row.chat_id else None
            targets.append(
                BroadcastTarget(
                    target_type=target_type,
                    identifier=identifier,
                    target_chat_id=target_chat_id,
                    error_text=error_text,
                )
            )
        return targets

    @classmethod
    def normalize_chat_identifier(cls, value: int | str | None) -> tuple[int | str | None, str | None]:
        if value is None:
            return None, "Kanal/guruh uchun chat_id yoki username topilmadi."
        if isinstance(value, int):
            return value, None

        raw_value = str(value).strip()
        if not raw_value:
            return None, "Kanal/guruh uchun chat_id yoki username bo'sh."
        if raw_value.lstrip("-").isdigit():
            return int(raw_value), None

        normalized = raw_value.replace("https://", "").replace("http://", "")
        normalized = normalized.split("?", 1)[0].strip("/")
        if normalized.startswith("t.me/"):
            path = normalized.removeprefix("t.me/").strip("/")
            if path.startswith("+") or path.startswith("joinchat/"):
                return None, "Private invite link broadcast chat_id sifatida ishlatilmaydi. Kanalni bot admin bo'lgan chat_id bilan qo'shing."
            if not path:
                return None, "Telegram link ichida username topilmadi."
            return f"@{path.lstrip('@')}", None

        if raw_value.startswith("@"):
            return raw_value, None
        if "/" in raw_value or raw_value.startswith("+"):
            return None, "Noto'g'ri Telegram chat manzili. @username yoki -100... chat_id kerak."
        return f"@{raw_value}", None

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "users": 0,
            "groups": 0,
            "channels": 0,
            "failed": 0,
            "failed_users": 0,
            "failed_groups": 0,
            "failed_channels": 0,
            "cancelled": False,
        }

    @staticmethod
    def _member_status(member) -> str:
        status = getattr(member, "status", "")
        return getattr(status, "value", status)

    @staticmethod
    def _increment_failed_stats(stats: dict, target_type: str) -> None:
        stats["failed"] += 1
        key = f"failed_{target_type}"
        if key in stats:
            stats[key] += 1

    @staticmethod
    def _empty_delete_stats() -> dict:
        return {
            "users": 0,
            "groups": 0,
            "channels": 0,
            "failed": 0,
        }

    @staticmethod
    def clean_preview_text(text: str | None, limit: int = 120) -> str:
        if not text:
            return "caption/matn yo'q"

        without_tags = re.sub(r"<[^>]+>", " ", text)
        normalized = " ".join(unescape(without_tags).split())
        if len(normalized) > limit:
            normalized = normalized[:limit].rstrip() + "..."
        return normalized

    def _campaign_list_preview(self, campaign, sent: int) -> str:
        title, body = self._campaign_preview_parts(campaign.text)
        content_type = self.CONTENT_LABELS.get(campaign.content_type, campaign.content_type)
        return (
            f"ID: <code>{campaign.id}</code> | <b>{safe_html(content_type)}</b>\n"
            f"Nomi: <b>{safe_html(title)}</b>\n"
            f"Matn: {safe_html(body)}\n"
            f"Yuborilgan: <b>{sent}</b>"
        )

    def _campaign_preview_parts(self, text: str | None) -> tuple[str, str]:
        if not text:
            return "Nomsiz reklama", "caption/matn yo'q"

        cleaned_lines = []
        for line in text.splitlines():
            cleaned = self.clean_preview_text(line, limit=160)
            if cleaned and cleaned != "caption/matn yo'q":
                cleaned_lines.append(cleaned)

        if not cleaned_lines:
            return "Nomsiz reklama", "caption/matn yo'q"

        title = self._truncate_plain(cleaned_lines[0], 56)
        body_source = " ".join(cleaned_lines[1:]) if len(cleaned_lines) > 1 else cleaned_lines[0]
        body = self._truncate_plain(body_source, 110)
        return title, body

    @staticmethod
    def _truncate_plain(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "..."

    def _require_broadcast_repository(self) -> None:
        if not self.broadcast_repository:
            raise RuntimeError("BroadcastRepository berilmagan.")
