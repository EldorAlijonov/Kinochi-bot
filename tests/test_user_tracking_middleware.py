import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.middlewares.user_tracking import UserTrackingMiddleware


class FakeMessage:
    def __init__(self, user_id: int = 1001):
        self.from_user = SimpleNamespace(
            id=user_id,
            full_name="Test User",
            username="testuser",
        )
        self.chat = SimpleNamespace(type="private")
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class FakeStore:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ttl_seconds):
        self.values[key] = value

    async def delete(self, key):
        self.values.pop(key, None)

    async def ping(self):
        return True


class FakeRepository:
    touch_calls = 0
    ban_checks = 0

    def __init__(self, session):
        pass

    async def touch_user(self, **kwargs):
        self.__class__.touch_calls += 1
        return SimpleNamespace(is_banned=False)

    async def get_is_banned(self, telegram_id):
        self.__class__.ban_checks += 1
        return False


class UserTrackingMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_tracking_touch_is_throttled_but_ban_check_keeps_running(self):
        FakeRepository.touch_calls = 0
        FakeRepository.ban_checks = 0
        store = FakeStore()
        middleware = UserTrackingMiddleware(store=store, throttle_seconds=300)
        event = FakeMessage()

        async def handler(evt, data):
            return "ok"

        with patch(
            "app.middlewares.user_tracking.async_session_maker",
            return_value=AsyncMock(),
        ), patch(
            "app.middlewares.user_tracking.UserRepository",
            FakeRepository,
        ):
            first = await middleware(handler, event, {})
            second = await middleware(handler, event, {})

        self.assertEqual(first, "ok")
        self.assertEqual(second, "ok")
        self.assertEqual(FakeRepository.touch_calls, 1)
        self.assertEqual(FakeRepository.ban_checks, 1)


if __name__ == "__main__":
    unittest.main()
