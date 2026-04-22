import unittest

from app.handlers.admin.subscription_status import (
    _parse_status_page_callback,
    _parse_status_select_callback,
)
from app.utils.callbacks import normalize_offset, normalize_page


class SubscriptionStatusHandlerTests(unittest.TestCase):
    def test_normalize_offset_uses_zero_for_none(self):
        self.assertEqual(normalize_offset(None), 0)

    def test_normalize_page_uses_one_for_missing_or_invalid_value(self):
        self.assertEqual(normalize_page(None), 1)
        self.assertEqual(normalize_page("bad"), 1)

    def test_select_callback_uses_first_page_when_page_is_missing(self):
        subscription_id, page = _parse_status_select_callback("subscription_deactivate:select:12")

        self.assertEqual(subscription_id, 12)
        self.assertEqual(page, 1)

    def test_page_callback_uses_first_page_when_page_is_missing(self):
        self.assertEqual(_parse_status_page_callback("subscription_deactivate:page:"), 1)


if __name__ == "__main__":
    unittest.main()
