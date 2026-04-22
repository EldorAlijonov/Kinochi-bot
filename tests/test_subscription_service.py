import unittest

from app.services.subscription_service import SubscriptionService


class FakeRepository:
    def __init__(self):
        self.active_calls = 0
        self.links = set()
        self.items = []
        self.by_id = {}

    async def exists_by_username(self, username):
        return False

    async def exists_by_chat_id(self, chat_id):
        return False

    async def exists_by_invite_link(self, invite_link):
        return invite_link in self.links

    async def create_external_link(self, title, invite_link):
        self.links.add(invite_link)
        item = type(
            "Subscription",
            (),
            {"title": title, "invite_link": invite_link, "subscription_type": "external_link"},
        )()
        self.items.append(item)
        return item

    async def get_active(self):
        self.active_calls += 1
        return list(self.items)

    async def get_by_id(self, subscription_id):
        return self.by_id.get(subscription_id)

    async def activate_subscription(self, subscription_id):
        item = self.by_id.get(subscription_id)
        if not item:
            return False

        item.is_active = True
        return True

    async def deactivate_subscription(self, subscription_id):
        item = self.by_id.get(subscription_id)
        if not item:
            return False

        item.is_active = False
        return True

    async def delete_by_id(self, subscription_id):
        return False


class SubscriptionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        SubscriptionService.invalidate_cache()

    async def test_get_active_subscriptions_uses_cache(self):
        repository = FakeRepository()
        repository.items = [object()]
        service = SubscriptionService(repository)

        first = await service.get_active_subscriptions()
        second = await service.get_active_subscriptions()

        self.assertEqual(repository.active_calls, 1)
        self.assertEqual(first, second)

    async def test_create_external_link_rejects_duplicate_link(self):
        repository = FakeRepository()
        service = SubscriptionService(repository)

        first = await service.create_external_link("Docs", "https://example.com")
        second = await service.create_external_link("Docs", "https://example.com")

        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(second["message"], "Bu havola oldin qo'shilgan.")

    async def test_deactivate_subscription_invalidates_active_cache(self):
        repository = FakeRepository()
        subscription = type("Subscription", (), {"id": 1, "is_active": True})()
        repository.by_id[1] = subscription
        repository.items = [subscription]
        service = SubscriptionService(repository)

        await service.get_active_subscriptions()
        result = await service.deactivate_subscription(1)
        await service.get_active_subscriptions()

        self.assertTrue(result["ok"])
        self.assertFalse(subscription.is_active)
        self.assertEqual(repository.active_calls, 2)


if __name__ == "__main__":
    unittest.main()
