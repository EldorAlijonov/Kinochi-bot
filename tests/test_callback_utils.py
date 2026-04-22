import unittest

from app.utils.callbacks import (
    normalize_offset,
    normalize_page,
    parse_callback_int,
    parse_callback_parts,
)


class CallbackUtilsTests(unittest.TestCase):
    def test_parse_callback_parts_rejects_missing_required_parts(self):
        self.assertIsNone(parse_callback_parts("movie_delete:select", min_parts=3))
        self.assertIsNone(parse_callback_parts(None, min_parts=1))
        self.assertIsNone(parse_callback_parts("movie_delete::0001", min_parts=3))

    def test_parse_callback_parts_allows_optional_empty_tail(self):
        self.assertEqual(
            parse_callback_parts("subscription_deactivate:page:", min_parts=2),
            ["subscription_deactivate", "page", ""],
        )

    def test_parse_callback_int_returns_default_for_invalid_value(self):
        self.assertEqual(parse_callback_int("users_active:page:x", 2, default=1), 1)
        self.assertIsNone(parse_callback_int("users_active:page", 2))
        self.assertEqual(parse_callback_int("users_active:page:-2", 2), -2)

    def test_normalize_page_and_offset_are_defensive(self):
        self.assertEqual(normalize_page(None), 1)
        self.assertEqual(normalize_page("-5"), 1)
        self.assertEqual(normalize_offset(None), 0)
        self.assertEqual(normalize_offset("-5"), 0)


if __name__ == "__main__":
    unittest.main()
