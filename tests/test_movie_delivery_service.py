import unittest

from app.services.movie_delivery_service import MovieDeliveryService


class FakeMovieRepository:
    def __init__(self, movie=None):
        self.movie = movie

    async def get_by_code(self, code: str):
        if self.movie and self.movie.code == code:
            return self.movie

        return None


class FakeBot:
    def __init__(self):
        self.copy_message_kwargs = None

    async def get_me(self):
        return type("BotInfo", (), {"username": "kino_bot"})()

    async def copy_message(self, **kwargs):
        self.copy_message_kwargs = kwargs
        return type("Message", (), {"message_id": 42})()


class MovieDeliveryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_movie_by_code_uses_protected_copy_message(self):
        movie = type(
            "Movie",
            (),
            {
                "code": "0001",
                "title": "Hayot Uchun Kurash",
                "caption": "Kino Nomi: Hayot Uchun Kurash\n\n🎬 Kino kodi: 0001",
                "storage_chat_id": -100123,
                "storage_message_id": 15,
            },
        )()
        bot = FakeBot()
        service = MovieDeliveryService(FakeMovieRepository(movie))

        result = await service.send_movie_by_code(
            bot=bot,
            chat_id=777,
            raw_code="0001",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(bot.copy_message_kwargs["chat_id"], 777)
        self.assertEqual(bot.copy_message_kwargs["from_chat_id"], -100123)
        self.assertEqual(bot.copy_message_kwargs["message_id"], 15)
        self.assertTrue(bot.copy_message_kwargs["protect_content"])
        self.assertIn("reply_markup", bot.copy_message_kwargs)
        self.assertIn("🎬 Hayot Uchun Kurash", bot.copy_message_kwargs["caption"])
        self.assertNotIn("Kino kodi", bot.copy_message_kwargs["caption"])
        self.assertTrue(bot.copy_message_kwargs["caption"].endswith("🤖 @kino_bot"))


if __name__ == "__main__":
    unittest.main()
