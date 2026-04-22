import math

from app.utils.datetime import format_local_datetime
from app.utils.text import safe_html


class UserManagementService:
    ACTIVE_DAYS = 7

    def __init__(self, user_repository):
        self.user_repository = user_repository

    async def build_user_overview(self, limit: int = 10) -> str:
        total_users = await self.user_repository.count_users()
        active_24h = await self.user_repository.count_active_users_last_24h()
        active_7d = await self.user_repository.count_active_users_last_7d()
        inactive = await self.user_repository.count_inactive_users()
        recent_users = await self.user_repository.get_recent_users(limit=limit)

        return (
            "👥 <b>Foydalanuvchilar umumiy ko'rinishi</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
            f"🕒 So'nggi 24 soat aktiv: <b>{active_24h}</b>\n"
            f"📅 So'nggi 7 kun aktiv: <b>{active_7d}</b>\n"
            f"🔴 Noaktiv userlar: <b>{inactive}</b>\n\n"
            "🆕 <b>Oxirgi qo'shilgan userlar</b>\n"
            f"{self._format_user_rows(recent_users)}"
        )

    async def search_user(self, query: str):
        normalized_query = (query or "").strip()
        if not normalized_query:
            return None

        if normalized_query.isdigit():
            return await self.user_repository.get_user_by_telegram_id(
                int(normalized_query)
            )

        return await self.user_repository.get_user_by_username(normalized_query)

    async def build_user_detail(self, user) -> str:
        movies_count = await self.user_repository.count_movies_received_by_user(
            user.telegram_id
        )
        referrals_count = await self.user_repository.count_referrals_by_user(
            user.telegram_id
        )
        referred_text = (
            f"Ha, <code>{user.referred_by}</code> orqali"
            if user.referred_by
            else "Yo'q"
        )
        username = f"@{safe_html(user.username)}" if user.username else "Yo'q"
        full_name = safe_html(user.full_name) if user.full_name else "Noma'lum"
        ban_status = "🚫 Ban qilingan" if user.is_banned else "✅ Aktiv"

        return (
            "👤 <b>Foydalanuvchi ma'lumoti</b>\n\n"
            f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
            f"👤 Username: {username}\n"
            f"📛 Full name: {full_name}\n"
            f"📅 Qo'shilgan sana: {format_local_datetime(user.joined_at)}\n"
            f"⏱ Oxirgi faollik: {format_local_datetime(user.last_active_at)}\n"
            f"🎬 Olgan kinolari: <b>{movies_count}</b>\n"
            f"🔗 Referral orqali kelganmi: {referred_text}\n"
            f"👥 Olib kelgan referrallari: <b>{referrals_count}</b>\n"
            f"🚫 Ban holati: {ban_status}"
        )

    async def build_users_list(
        self,
        list_type: str,
        page: int,
        page_size: int,
    ) -> tuple[str | None, int, int]:
        if list_type == "active":
            total_count = await self.user_repository.count_active_users_last_7d()
            title = "🟢 Aktiv foydalanuvchilar"
            subtitle = "So'nggi 7 kun ichida aktiv bo'lganlar"
            users = await self.user_repository.list_active_users(
                limit=page_size,
                offset=self._offset(page, page_size, total_count),
            )
        else:
            total_count = await self.user_repository.count_inactive_users()
            title = "🔴 Noaktiv foydalanuvchilar"
            subtitle = "So'nggi 7 kun ichida aktiv bo'lmaganlar"
            users = await self.user_repository.list_inactive_users(
                limit=page_size,
                offset=self._offset(page, page_size, total_count),
            )

        if total_count == 0:
            return None, 1, 1

        total_pages = max(1, math.ceil(total_count / page_size))
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size

        text = (
            f"{title}\n"
            f"{subtitle}\n"
            f"Sahifa: <b>{page}/{total_pages}</b>\n\n"
            f"{self._format_user_rows(users, start=offset + 1)}"
        )
        return text, page, total_pages

    async def ban_user(self, query: str) -> dict:
        user = await self.search_user(query)
        if not user:
            return {"ok": False, "message": "Foydalanuvchi topilmadi."}

        if user.is_banned:
            return {"ok": False, "message": "Bu foydalanuvchi allaqachon ban qilingan."}

        updated = await self.user_repository.ban_user(user.telegram_id)
        return {
            "ok": updated,
            "user": user,
            "message": "Foydalanuvchi ban qilindi." if updated else "Ban qilishda xatolik yuz berdi.",
        }

    async def unban_user(self, query: str) -> dict:
        user = await self.search_user(query)
        if not user:
            return {"ok": False, "message": "Foydalanuvchi topilmadi."}

        if not user.is_banned:
            return {"ok": False, "message": "Bu foydalanuvchi ban qilinmagan."}

        updated = await self.user_repository.unban_user(user.telegram_id)
        return {
            "ok": updated,
            "user": user,
            "message": "Foydalanuvchi bandan chiqarildi." if updated else "Bandan chiqarishda xatolik yuz berdi.",
        }

    @staticmethod
    def _offset(page: int, page_size: int, total_count: int) -> int:
        if total_count <= 0:
            return 0
        total_pages = max(1, math.ceil(total_count / page_size))
        page = max(1, min(page, total_pages))
        return (page - 1) * page_size

    def _format_user_rows(self, users, start: int = 1) -> str:
        if not users:
            return "Hali foydalanuvchi yo'q."

        lines = []
        for index, user in enumerate(users, start=start):
            username = f"@{safe_html(user.username)}" if user.username else "username yo'q"
            full_name = safe_html(user.full_name) if user.full_name else "Noma'lum"
            status = "🚫" if user.is_banned else "✅"
            lines.append(
                f"{index}. {status} <b>{full_name}</b>\n"
                f"ID: <code>{user.telegram_id}</code> | {username}\n"
                f"Oxirgi faollik: {format_local_datetime(user.last_active_at)}"
            )
        return "\n\n".join(lines)
