import unittest

from app.services.subscription_validator import (
    is_valid_external_url,
    parse_username_or_link,
    validate_private_invite_link,
    validate_public_channel_data,
    validate_title,
)


class SubscriptionValidatorTests(unittest.TestCase):
    def test_validate_title_rejects_empty_value(self):
        self.assertEqual(validate_title("   "), "Nomi bo'sh bo'lmasin.")

    def test_parse_username_or_link_parses_username(self):
        username, invite_link = parse_username_or_link("@mychannel")
        self.assertEqual(username, "@mychannel")
        self.assertEqual(invite_link, "https://t.me/mychannel")

    def test_parse_username_or_link_parses_public_link(self):
        username, invite_link = parse_username_or_link("https://t.me/mychannel")
        self.assertEqual(username, "@mychannel")
        self.assertEqual(invite_link, "https://t.me/mychannel")

    def test_validate_public_channel_data_rejects_invalid_username(self):
        error = validate_public_channel_data("Test kanal", "@ab", "https://t.me/ab")
        self.assertEqual(error, "Username noto'g'ri formatda.")

    def test_validate_private_invite_link_accepts_valid_telegram_link(self):
        self.assertIsNone(validate_private_invite_link("https://t.me/+abc123"))
        self.assertIsNone(validate_private_invite_link("https://t.me/joinchat/abc123"))

    def test_validate_private_invite_link_rejects_non_telegram_link(self):
        self.assertEqual(
            validate_private_invite_link("https://example.com/invite"),
            "Maxfiy kanal uchun to'g'ri invite link yuboring.",
        )

    def test_is_valid_external_url(self):
        self.assertTrue(is_valid_external_url("https://example.com"))
        self.assertFalse(is_valid_external_url("javascript:alert(1)"))


if __name__ == "__main__":
    unittest.main()
