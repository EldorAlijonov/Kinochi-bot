import unittest
from types import SimpleNamespace

from aiogram.exceptions import TelegramAPIError

from app.services.broadcast_service import BroadcastService, BroadcastTarget


class FakeBroadcastRepository:
    def __init__(self):
        self.deliveries = []
        self.flush_count = 0
        self.campaign_status = None
        self.deleted_status = None

    async def create_campaign(self, **kwargs):
        return SimpleNamespace(id=1, **kwargs)

    async def create_delivery(self, **kwargs):
        self.deliveries.append(kwargs)
        return SimpleNamespace(id=len(self.deliveries), **kwargs)

    def add_delivery(self, **kwargs):
        self.deliveries.append(kwargs)
        return SimpleNamespace(id=len(self.deliveries), **kwargs)

    async def flush_deliveries(self):
        self.flush_count += 1

    async def mark_campaign_status(self, campaign_id: int, status: str):
        self.campaign_status = status
        return True

    async def list_deliveries_by_campaign_after(self, campaign_id: int, last_delivery_id: int, limit: int):
        return [
            SimpleNamespace(
                id=1,
                target_type="users",
                target_chat_id=1001,
                target_identifier="1001",
                sent_message_id=11,
                delivery_status="sent",
            ),
            SimpleNamespace(
                id=2,
                target_type="users",
                target_chat_id=1002,
                target_identifier="1002",
                sent_message_id=12,
                delivery_status="sent",
            ),
        ] if last_delivery_id == 0 else []

    async def mark_delivery_deleted(self, delivery_id: int):
        return True

    async def mark_campaign_deleted(self, campaign_id: int, status: str = "deleted"):
        self.deleted_status = status
        return True


class FakeUserRepository:
    async def list_user_targets(self, last_telegram_id: int = 0, limit: int = 100):
        return [1001, 1002] if last_telegram_id == 0 else []


class FakeBot:
    async def get_me(self):
        return SimpleNamespace(id=999)

    async def send_photo(self, **kwargs):
        return SimpleNamespace(message_id=kwargs["chat_id"] + 100)

    async def copy_message(self, **kwargs):
        raise AssertionError("file_id mavjud bo'lsa source message ishlatilmasligi kerak")


class ChannelBot:
    def __init__(self, *, member_status="administrator", can_post_messages=True):
        self.member_status = member_status
        self.can_post_messages = can_post_messages
        self.sent_kwargs = None

    async def get_chat(self, identifier):
        self.requested_identifier = identifier
        return SimpleNamespace(id=-1001234567890)

    async def get_chat_member(self, chat_id: int, user_id: int):
        self.member_check = {"chat_id": chat_id, "user_id": user_id}
        return SimpleNamespace(
            status=self.member_status,
            can_post_messages=self.can_post_messages,
        )

    async def send_message(self, **kwargs):
        self.sent_kwargs = kwargs
        return SimpleNamespace(message_id=777)


class DeletePartialBot:
    def __init__(self):
        self.calls = 0

    async def delete_message(self, **kwargs):
        self.calls += 1
        if self.calls == 2:
            raise TelegramAPIError(method=None, message="delete failed")


class BroadcastServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_campaign_uses_queued_status_and_file_id(self):
        repository = FakeBroadcastRepository()
        service = BroadcastService(
            user_repository=FakeUserRepository(),
            broadcast_repository=repository,
        )

        campaign = await service.prepare_campaign(
            admin_id=1,
            content_type="photo",
            text="Reklama",
            file_id="photo-file-id",
            source_chat_id=10,
            source_message_id=20,
            target_type="users",
        )

        self.assertEqual(campaign.status, "queued")
        self.assertEqual(campaign.file_id, "photo-file-id")

    async def test_send_campaign_batches_delivery_flushes_and_uses_file_id(self):
        repository = FakeBroadcastRepository()
        service = BroadcastService(
            user_repository=FakeUserRepository(),
            broadcast_repository=repository,
        )
        campaign = SimpleNamespace(
            id=1,
            content_type="photo",
            text="Reklama",
            file_id="photo-file-id",
            source_chat_id=10,
            source_message_id=20,
            target_type="users",
        )

        result = await service.send_campaign(FakeBot(), campaign)

        self.assertEqual(result["users"], 2)
        self.assertEqual(len(repository.deliveries), 2)
        self.assertEqual(repository.deliveries[0]["delivery_status"], "sent")
        self.assertEqual(repository.flush_count, 1)
        self.assertEqual(repository.campaign_status, "sent")

    async def test_delete_campaign_marks_partial_deleted_when_any_delete_fails(self):
        repository = FakeBroadcastRepository()
        service = BroadcastService(
            user_repository=FakeUserRepository(),
            broadcast_repository=repository,
        )
        campaign = SimpleNamespace(id=1)

        result = await service.delete_campaign_messages(DeletePartialBot(), campaign)

        self.assertEqual(result["users"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(repository.deleted_status, "partial_deleted")

    async def test_channel_target_is_normalized_checked_and_sent_to_resolved_chat_id(self):
        repository = FakeBroadcastRepository()
        service = BroadcastService(
            user_repository=FakeUserRepository(),
            broadcast_repository=repository,
        )
        campaign = SimpleNamespace(
            id=1,
            content_type="text",
            text="Kanal reklamasi",
            file_id=None,
            source_chat_id=10,
            source_message_id=20,
        )
        stats = service._empty_stats()
        bot = ChannelBot()

        await service._send_campaign_to_target(
            bot=bot,
            bot_id=999,
            campaign=campaign,
            target=BroadcastTarget(target_type="channels", identifier="@mychannel"),
            stats=stats,
        )

        self.assertEqual(bot.member_check, {"chat_id": -1001234567890, "user_id": 999})
        self.assertEqual(bot.sent_kwargs["chat_id"], -1001234567890)
        self.assertEqual(stats["channels"], 1)
        self.assertEqual(repository.deliveries[0]["delivery_status"], "sent")

    async def test_channel_without_post_permission_is_skipped_and_recorded_as_failed(self):
        repository = FakeBroadcastRepository()
        service = BroadcastService(
            user_repository=FakeUserRepository(),
            broadcast_repository=repository,
        )
        campaign = SimpleNamespace(
            id=1,
            content_type="text",
            text="Kanal reklamasi",
            file_id=None,
            source_chat_id=10,
            source_message_id=20,
        )
        stats = service._empty_stats()
        bot = ChannelBot(can_post_messages=False)

        await service._send_campaign_to_target(
            bot=bot,
            bot_id=999,
            campaign=campaign,
            target=BroadcastTarget(target_type="channels", identifier="@mychannel"),
            stats=stats,
        )

        self.assertIsNone(bot.sent_kwargs)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["failed_channels"], 1)
        self.assertEqual(repository.deliveries[0]["delivery_status"], "failed")
        self.assertIn("post yuborish huquqiga ega emas", repository.deliveries[0]["error_text"])

    async def test_chat_identifier_normalization_handles_public_links_and_private_invites(self):
        self.assertEqual(
            BroadcastService.normalize_chat_identifier("https://t.me/mychannel"),
            ("@mychannel", None),
        )
        self.assertEqual(
            BroadcastService.normalize_chat_identifier("t.me/mychannel"),
            ("@mychannel", None),
        )
        self.assertEqual(
            BroadcastService.normalize_chat_identifier("-1001234567890"),
            (-1001234567890, None),
        )

        identifier, error_text = BroadcastService.normalize_chat_identifier("https://t.me/+secret")

        self.assertIsNone(identifier)
        self.assertIn("Private invite link", error_text)

    async def test_campaign_list_preview_strips_html_and_formats_consistently(self):
        service = BroadcastService(user_repository=FakeUserRepository())
        campaign = SimpleNamespace(
            id=5,
            content_type="video",
            text="<b>Mushuk va it</b>\n<i>O'zbek tilida</i> | <code>720p</code> | Juda uzun caption",
        )

        preview = service._campaign_list_preview(campaign, sent=8)

        self.assertIn("ID: <code>5</code> | <b>video</b>", preview)
        self.assertIn("Nomi: <b>Mushuk va it</b>", preview)
        self.assertIn("Matn: O&#x27;zbek tilida | 720p | Juda uzun caption", preview)
        self.assertNotIn("&lt;b&gt;", preview)


if __name__ == "__main__":
    unittest.main()
