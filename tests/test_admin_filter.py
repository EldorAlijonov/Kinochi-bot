import os
import unittest
from importlib import reload
from types import SimpleNamespace

import app.core.config as config_module

os.environ["ADMINS"] = "1,2"
reload(config_module)

from app.filters.admin import AdminFilter


class AdminFilterTests(unittest.IsolatedAsyncioTestCase):
    async def test_allows_admin_user(self):
        filter_ = AdminFilter()
        event = SimpleNamespace(from_user=SimpleNamespace(id=1))
        self.assertTrue(await filter_(event))

    async def test_rejects_non_admin_user(self):
        filter_ = AdminFilter()
        event = SimpleNamespace(from_user=SimpleNamespace(id=99))
        self.assertFalse(await filter_(event))


if __name__ == "__main__":
    unittest.main()
