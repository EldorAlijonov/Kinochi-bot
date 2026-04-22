import unittest

from app.utils.share_text import (
    build_general_share_text,
    build_movie_share_text,
    build_share_link,
)


class ShareTextTests(unittest.TestCase):
    def test_build_share_link_uses_full_https_url_with_payload(self):
        self.assertEqual(
            build_share_link("@my_movie_bot", "0001"),
            "https://t.me/my_movie_bot?start=0001",
        )

    def test_build_general_share_text_includes_referral_link_and_bot_value(self):
        text = build_general_share_text("my_movie_bot", "ref_123")

        self.assertTrue(text.startswith("https://t.me/my_movie_bot https://t.me/my_movie_bot?start=ref_123"))
        self.assertIn("Kino olish uchun qulay bot", text)
        self.assertIn("Kino kodini yuborib kerakli kinoni oling", text)
        self.assertIn("Kirish:", text)
        self.assertIn("https://t.me/my_movie_bot?start=ref_123", text)

    def test_build_movie_share_text_uses_movie_title_and_code_link(self):
        text = build_movie_share_text("@my_movie_bot", "Hayot Uchun Kurash", "0007")

        self.assertTrue(text.startswith("https://t.me/my_movie_bot https://t.me/my_movie_bot?start=0007"))
        self.assertIn('"Hayot Uchun Kurash" filmini olish uchun botga kiring', text)
        self.assertIn("Hayot Uchun Kurash", text)
        self.assertIn("Kirish:", text)
        self.assertIn("https://t.me/my_movie_bot?start=0007", text)

    def test_movie_share_keyboard_uses_https_share_link(self):
        from app.keyboards.user.movie import movie_share_keyboard

        keyboard = movie_share_keyboard("my_movie_bot", "0007")
        button = keyboard.inline_keyboard[0][0]

        self.assertEqual(
            button.switch_inline_query_chosen_chat.query,
            "https://t.me/my_movie_bot?start=0007",
        )


if __name__ == "__main__":
    unittest.main()
