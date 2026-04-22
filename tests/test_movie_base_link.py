import unittest

from app.utils.movie_base_link import format_movie_base_address


class MovieBaseLinkTests(unittest.TestCase):
    def test_public_base_address_uses_username(self):
        movie_base = type(
            "MovieBase",
            (),
            {
                "chat_username": "kino_baza",
                "invite_link": "https://t.me/kino_baza",
            },
        )()

        self.assertEqual(format_movie_base_address(movie_base), "@kino_baza")

    def test_private_base_address_uses_invite_link(self):
        movie_base = type(
            "MovieBase",
            (),
            {
                "chat_username": None,
                "invite_link": "https://t.me/+abc123",
                "chat_id": -1003746814634,
            },
        )()

        address = format_movie_base_address(movie_base)

        self.assertEqual(address, '<a href="https://t.me/+abc123">Ochish</a>')
        self.assertNotIn("-1003746814634", address)

    def test_private_base_address_without_invite_link_uses_fallback(self):
        movie_base = type(
            "MovieBase",
            (),
            {
                "chat_username": None,
                "invite_link": None,
                "chat_id": -1003746814634,
            },
        )()

        self.assertEqual(format_movie_base_address(movie_base), "Havola mavjud emas")


if __name__ == "__main__":
    unittest.main()
