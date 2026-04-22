import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app.services.movie_service import MovieCodePoolExhaustedError, MovieService
from app.utils.datetime import format_local_datetime
from app.utils.movie_admin_preview import build_movie_admin_preview
from app.utils.movie_caption import (
    build_storage_movie_caption,
    extract_movie_title,
    format_file_size,
)
from app.utils.movie_deep_link import build_movie_deep_link
from app.utils.movie_title import build_user_movie_caption, normalize_movie_title


class FakeMovieRepository:
    def __init__(self):
        self.codes = set()
        self.movies = {}

    async def exists_by_code(self, code: str) -> bool:
        return code in self.codes

    async def create_movie(self, **kwargs):
        self.codes.add(kwargs["code"])
        movie = type("Movie", (), kwargs)()
        self.movies[kwargs["code"]] = movie
        return movie

    async def get_by_code(self, code: str):
        return self.movies.get(code)

    async def get_last_movie(self):
        if not self.movies:
            return None

        return list(self.movies.values())[-1]

    async def count_all(self) -> int:
        return len(self.movies)


class MovieServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_unique_code_returns_four_digit_code(self):
        repository = FakeMovieRepository()
        service = MovieService(repository)

        code = await service.generate_unique_code()

        self.assertRegex(code, r"^\d{4}$")
        self.assertNotEqual(code, "0000")

    async def test_generate_unique_code_skips_existing_code(self):
        repository = FakeMovieRepository()
        repository.codes.add("0001")
        service = MovieService(repository)

        with patch("app.utils.movie_code.random.randint", side_effect=[1, 2]):
            code = await service.generate_unique_code()

        self.assertEqual(code, "0002")

    async def test_generate_unique_code_raises_when_all_codes_are_busy(self):
        repository = FakeMovieRepository()
        repository.movies = {f"{code:04d}": object() for code in range(1, 10000)}
        service = MovieService(repository)

        with self.assertRaises(MovieCodePoolExhaustedError) as context:
            await service.generate_unique_code()

        self.assertEqual(str(context.exception), "Barcha kodlar band (9999 ta kino to'lgan)")

    async def test_upload_movie_retries_with_new_code_after_integrity_error(self):
        class RetryRepository(FakeMovieRepository):
            def __init__(self):
                super().__init__()
                self.create_attempts = 0

            async def create_movie(self, **kwargs):
                self.create_attempts += 1
                if self.create_attempts == 1:
                    raise IntegrityError("insert movie", {}, Exception("duplicate code"))

                return await super().create_movie(**kwargs)

        class FakeBot:
            def __init__(self):
                self.captions = []

            async def copy_message(self, **kwargs):
                return SimpleNamespace(message_id=555)

            async def edit_message_caption(self, **kwargs):
                self.captions.append(kwargs["caption"])

            async def delete_message(self, **kwargs):
                raise AssertionError("successful retry should not delete copied movie")

        repository = RetryRepository()
        service = MovieService(repository)
        bot = FakeBot()
        movie_base = SimpleNamespace(
            id=10,
            chat_id=-100123,
            chat_username="@kino_baza",
        )
        source_message = SimpleNamespace(
            content_type="video",
            video=SimpleNamespace(file_unique_id="file-1", file_size=100),
            document=None,
            animation=None,
            audio=None,
            photo=None,
            caption="Test kino",
            chat=SimpleNamespace(id=777),
            message_id=42,
        )

        with patch("app.utils.movie_code.random.randint", side_effect=[1, 2]):
            result = await service.upload_movie_to_base(bot, movie_base, source_message)

        self.assertTrue(result["ok"])
        self.assertEqual(result["movie"].code, "0002")
        self.assertEqual(repository.create_attempts, 2)
        self.assertIn("Kino kodi: 0001", bot.captions[0])
        self.assertIn("Kino kodi: 0002", bot.captions[1])

    async def test_get_movie_by_code_normalizes_input(self):
        repository = FakeMovieRepository()
        repository.movies["0001"] = object()
        service = MovieService(repository)

        movie = await service.get_movie_by_code(" 0001 ")

        self.assertIsNotNone(movie)

    def test_normalize_movie_title_strips_only_edge_slashes(self):
        self.assertEqual(normalize_movie_title(" /Fantastik 4 lik/ "), "Fantastik 4 lik")
        self.assertEqual(normalize_movie_title("/Fan/tastik 4/"), "Fan/tastik 4")
        self.assertEqual(
            normalize_movie_title("Kino Nomi: Fantastik 4 lik"),
            "Fantastik 4 lik",
        )

    def test_extract_movie_title_finds_slash_wrapped_title(self):
        self.assertEqual(
            extract_movie_title(
                "/Hayot Uchun Kurash/\n\n"
                "🎭 Janri: #Sarguzasht #Biografiya\n"
                "🚩 Tili: O'zbek tili"
            ),
            "Hayot Uchun Kurash",
        )

    def test_format_file_size_uses_mb_or_gb(self):
        self.assertEqual(format_file_size(850 * 1024 * 1024), "850MB")
        self.assertEqual(format_file_size(2_470_000_000), "2.3GB")

    def test_build_storage_movie_caption_matches_channel_format(self):
        caption = build_storage_movie_caption(
            "/Hayot Uchun Kurash/\n\n"
            "🎭 Janri: #Sarguzasht #Biografiya\n"
            "🚩 Tili: O'zbek tili\n"
            "🎥 Sifati: 1080p\n"
            "🇺🇸 Davlati: Turkiya\n"
            "📆 Chiqqan yili: 2024",
            "Hayot Uchun Kurash",
            "0003",
            file_size=2_470_000_000,
            channel_username="@kino_baza",
        )

        self.assertTrue(caption.startswith("🎬 Hayot Uchun Kurash"))
        self.assertIn("🎭 Janri: #Sarguzasht #Biografiya", caption)
        self.assertIn("🚩 Tili: O'zbek tili", caption)
        self.assertIn("Hajmi: 2.3GB", caption)
        self.assertIn("Bizning kanal: @kino_baza", caption)
        self.assertTrue(caption.endswith("Kino kodi: 0003"))
        self.assertNotIn("/Hayot Uchun Kurash/", caption)

    def test_storage_caption_does_not_duplicate_bot_managed_lines(self):
        caption = build_storage_movie_caption(
            "Kino Nomi: Eski nom\n\n"
            "🎭 Janri: #Drama\n"
            "📥 Hajmi: 700MB\n\n"
            "Bizning kanal: @old\n\n"
            "🎬 Kino kodi: 0001",
            "Yangi nom",
            "0002",
            file_size=900 * 1024 * 1024,
            channel_username="@kino_baza",
        )

        self.assertNotIn("Kino Nomi:", caption)
        self.assertEqual(caption.count("Kino kodi:"), 1)
        self.assertEqual(caption.count("Bizning kanal:"), 1)
        self.assertEqual(caption.count("Hajmi:"), 1)
        self.assertIn("🎭 Janri: #Drama", caption)

    def test_normalize_movie_title_prefers_slash_wrapped_caption_line(self):
        self.assertEqual(
            normalize_movie_title("Janr: fantastika\n/Fantastik 4 lik/\nTil: uzbek"),
            "Fantastik 4 lik",
        )

    def test_user_movie_caption_uses_clean_user_format(self):
        movie = type(
            "Movie",
            (),
            {
                "title": "Hayot Uchun Kurash",
                "code": "0003",
                "caption": (
                    "Kino Nomi: Hayot Uchun Kurash\n\n"
                    "🎭 Janri: #Sarguzasht #Biografiya\n"
                    "🚩 Tili: O'zbek tili\n"
                    "📥 Hajmi: 2.3GB\n\n"
                    "Bizning kanal: @kino_baza\n\n"
                    "🎬 Kino kodi: 0003"
                ),
            },
        )()

        caption = build_user_movie_caption(movie)

        self.assertNotIn("Hayot Uchun Kurash", caption)
        self.assertIn("🎭 Janri: #Sarguzasht #Biografiya", caption)
        self.assertIn("Hajmi: 2.3GB", caption)
        self.assertNotIn("Kino kodi", caption)
        self.assertNotIn("Bizning kanal", caption)
        self.assertNotIn("Kino Nomi", caption)

    def test_user_movie_caption_removes_storage_title_duplicate(self):
        movie = type(
            "Movie",
            (),
            {
                "title": "Hayot Uchun Kurash",
                "code": "0003",
                "caption": (
                    "🎬 Hayot Uchun Kurash\n\n"
                    "🎭 Janri: #Drama\n\n"
                    "🎬 Kino kodi: 0003"
                ),
            },
        )()

        caption = build_user_movie_caption(movie)

        self.assertEqual(caption.count("Hayot Uchun Kurash"), 0)
        self.assertNotIn("Kino kodi", caption)

    def test_format_local_datetime_converts_utc_to_tashkent_time(self):
        uploaded_at = datetime(2026, 4, 21, 8, 47, tzinfo=UTC)

        self.assertEqual(format_local_datetime(uploaded_at), "21.04.2026 13:47")

    def test_build_movie_deep_link_uses_full_https_url(self):
        self.assertEqual(
            build_movie_deep_link("@my_movie_bot", "0001"),
            "https://t.me/my_movie_bot?start=0001",
        )

    def test_admin_preview_uses_clean_title_and_open_link(self):
        movie = type(
            "Movie",
            (),
            {
                "title": " /Fantastik 4 lik/ ",
                "caption": None,
                "code": "0004",
                "created_at": None,
            },
        )()
        movie_base = type(
            "MovieBase",
            (),
            {
                "title": "Plan B",
                "chat_username": None,
                "invite_link": "https://t.me/+abc123",
                "chat_id": -1001,
            },
        )()

        preview = build_movie_admin_preview(movie, movie_base, index=1)

        self.assertIn("1. Kino nomi: Fantastik 4 lik", preview)
        self.assertIn('Bazani <a href="https://t.me/+abc123">Ochish</a>', preview)


if __name__ == "__main__":
    unittest.main()
