import unittest
from types import SimpleNamespace

from app.middlewares.rate_limit import RateLimitMiddleware


class FakeMessage:
    def __init__(self, user_id: int):
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class RateLimitMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocks_user_after_limit(self):
        middleware = RateLimitMiddleware(max_requests=2, window_seconds=60)
        event = FakeMessage(user_id=999001)

        async def handler(evt, data):
            return "ok"

        first = await middleware(handler, event, {})
        second = await middleware(handler, event, {})
        third = await middleware(handler, event, {})

        self.assertEqual(first, "ok")
        self.assertEqual(second, "ok")
        self.assertIsNone(third)
        self.assertEqual(len(event.answers), 1)
        self.assertIn("So'rovlar juda tez", event.answers[0])


if __name__ == "__main__":
    unittest.main()
