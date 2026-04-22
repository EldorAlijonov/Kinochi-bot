import unittest

from app.services.movie_base_service import MovieBaseService


class FakeMovieBaseRepository:
    def __init__(self):
        self.by_id = {}

    async def get_by_id(self, movie_base_id):
        return self.by_id.get(movie_base_id)

    async def activate_base(self, movie_base_id):
        movie_base = self.by_id.get(movie_base_id)
        if not movie_base:
            return False

        movie_base.is_active = True
        return True

    async def deactivate_base(self, movie_base_id):
        movie_base = self.by_id.get(movie_base_id)
        if not movie_base:
            return False

        movie_base.is_active = False
        return True

    async def get_all_paginated(self, limit, offset):
        return None

    async def get_paginated_by_active(self, is_active, limit, offset):
        return None

    async def count_all(self):
        return None

    async def count_by_active(self, is_active):
        return None


class MovieBaseServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_activate_base_changes_inactive_base(self):
        repository = FakeMovieBaseRepository()
        movie_base = type("MovieBase", (), {"id": 1, "is_active": False})()
        repository.by_id[1] = movie_base
        service = MovieBaseService(repository)

        result = await service.activate_base(1)

        self.assertTrue(result["ok"])
        self.assertTrue(movie_base.is_active)
        self.assertEqual(result["message"], "Baza aktiv qilindi")

    async def test_deactivate_base_changes_active_base(self):
        repository = FakeMovieBaseRepository()
        movie_base = type("MovieBase", (), {"id": 1, "is_active": True})()
        repository.by_id[1] = movie_base
        service = MovieBaseService(repository)

        result = await service.deactivate_base(1)

        self.assertTrue(result["ok"])
        self.assertFalse(movie_base.is_active)
        self.assertEqual(result["message"], "Baza noaktiv qilindi")

    async def test_list_and_count_methods_return_safe_defaults(self):
        service = MovieBaseService(FakeMovieBaseRepository())

        self.assertEqual(await service.get_paginated_bases(limit=5, offset=0), [])
        self.assertEqual(
            await service.get_paginated_bases_by_status(
                is_active=True,
                limit=5,
                offset=0,
            ),
            [],
        )
        self.assertEqual(await service.count_bases(), 0)
        self.assertEqual(await service.count_bases_by_status(True), 0)


if __name__ == "__main__":
    unittest.main()
