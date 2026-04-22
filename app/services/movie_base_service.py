import math

from sqlalchemy.exc import IntegrityError

from app.services.subscription_validator import parse_username_or_link
from app.services.subscription_validator import validate_private_invite_link


class MovieBaseService:
    TYPE_LABELS = {
        "public_channel": "Ommaviy kanal",
        "private_channel": "Maxfiy kanal",
    }

    def __init__(self, repository):
        self.repository = repository

    async def create_public_base(
        self,
        title: str,
        chat_username: str,
        chat_id: int,
        invite_link: str,
    ):
        if await self.repository.exists_by_chat_id(chat_id):
            return {"ok": False, "message": "Bu kanal allaqachon baza sifatida qo'shilgan."}

        if chat_username and await self.repository.exists_by_username(chat_username):
            return {"ok": False, "message": "Bu kanal allaqachon baza sifatida qo'shilgan."}

        try:
            movie_base = await self.repository.create_base(
                title=title,
                base_type="public_channel",
                chat_id=chat_id,
                chat_username=chat_username,
                invite_link=invite_link,
            )
        except IntegrityError:
            return {"ok": False, "message": "Bu kanal allaqachon baza sifatida qo'shilgan."}

        return {"ok": True, "movie_base": movie_base}

    async def create_private_base(
        self,
        title: str,
        chat_id: int,
        invite_link: str | None = None,
    ):
        if await self.repository.exists_by_chat_id(chat_id):
            return {"ok": False, "message": "Bu maxfiy kanal allaqachon baza sifatida qo'shilgan."}

        try:
            movie_base = await self.repository.create_base(
                title=title,
                base_type="private_channel",
                chat_id=chat_id,
                invite_link=invite_link,
            )
        except IntegrityError:
            return {"ok": False, "message": "Bu maxfiy kanal allaqachon baza sifatida qo'shilgan."}

        return {"ok": True, "movie_base": movie_base}

    async def get_paginated_bases(self, limit: int, offset: int):
        return await self.repository.get_all_paginated(limit=limit, offset=offset)

    async def get_paginated_bases_by_status(
        self,
        is_active: bool,
        limit: int,
        offset: int,
    ):
        return await self.repository.get_paginated_by_active(
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    async def count_bases(self) -> int:
        return await self.repository.count_all()

    async def count_bases_by_status(self, is_active: bool) -> int:
        return await self.repository.count_by_active(is_active)

    async def get_by_id(self, movie_base_id: int):
        return await self.repository.get_by_id(movie_base_id)

    async def get_by_chat_id(self, chat_id: int):
        return await self.repository.get_by_chat_id(chat_id)

    async def delete_base(self, movie_base_id: int) -> bool:
        return await self.repository.delete_by_id(movie_base_id)

    async def activate_base(self, movie_base_id: int):
        movie_base = await self.repository.get_by_id(movie_base_id)
        if not movie_base:
            return {"ok": False, "message": "Baza topilmadi."}

        if movie_base.is_active:
            return {"ok": False, "message": "Baza allaqachon aktiv."}

        updated = await self.repository.activate_base(movie_base_id)
        return {
            "ok": updated,
            "message": "Baza aktiv qilindi" if updated else "Baza topilmadi.",
        }

    async def deactivate_base(self, movie_base_id: int):
        movie_base = await self.repository.get_by_id(movie_base_id)
        if not movie_base:
            return {"ok": False, "message": "Baza topilmadi."}

        if not movie_base.is_active:
            return {"ok": False, "message": "Baza allaqachon noaktiv."}

        updated = await self.repository.deactivate_base(movie_base_id)
        return {
            "ok": updated,
            "message": "Baza noaktiv qilindi" if updated else "Baza topilmadi.",
        }

    @classmethod
    def type_label(cls, base_type: str) -> str:
        return cls.TYPE_LABELS.get(base_type, "Noma'lum")

    @staticmethod
    def total_pages(total_count: int, page_size: int) -> int:
        return max(1, math.ceil(total_count / page_size))

    @staticmethod
    def normalize_public_reference(value: str) -> tuple[str | None, str | None]:
        return parse_username_or_link(value)

    @staticmethod
    def normalize_private_invite_link(value: str) -> tuple[str | None, str | None]:
        invite_link = (value or "").strip()
        error = validate_private_invite_link(invite_link)
        if error:
            return None, error

        return invite_link, None
