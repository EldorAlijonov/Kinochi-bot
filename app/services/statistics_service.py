from app.utils.text import safe_html


class StatisticsService:
    def __init__(
        self,
        user_repository,
        movie_repository,
        movie_base_repository,
        subscription_repository,
    ):
        self.user_repository = user_repository
        self.movie_repository = movie_repository
        self.movie_base_repository = movie_base_repository
        self.subscription_repository = subscription_repository

    async def build_general_stats(self) -> str:
        total_users = await self.user_repository.count_users()
        joined_today = await self.user_repository.count_users_joined_today()
        total_movies = await self.movie_repository.count_movies()
        total_bases = await self.movie_base_repository.count_bases()
        active_bases = await self.movie_base_repository.count_active_bases()
        total_subscriptions = await self.subscription_repository.count_subscriptions()
        active_subscriptions = await self.subscription_repository.count_active_subscriptions()

        return (
            "📊 <b>Umumiy statistika</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
            f"🆕 Bugun qo'shilganlar: <b>{joined_today}</b>\n"
            f"🎬 Jami kinolar: <b>{total_movies}</b>\n"
            f"📂 Jami bazalar: <b>{total_bases}</b>\n"
            f"✅ Aktiv bazalar: <b>{active_bases}</b>\n"
            f"📢 Jami obunalar: <b>{total_subscriptions}</b>\n"
            f"✅ Aktiv obunalar: <b>{active_subscriptions}</b>"
        )

    async def build_user_activity_stats(self) -> str:
        active_today = await self.user_repository.count_active_users_today()
        active_24h = await self.user_repository.count_active_users_last_24h()
        active_7d = await self.user_repository.count_active_users_last_7d()
        received_movie_today = await self.user_repository.count_users_received_movie_today()
        sent_code_today = await self.user_repository.count_users_sent_code_today()
        referral_users = await self.user_repository.count_referral_users()
        top_referrers = await self.user_repository.get_top_referrers(limit=5)

        return (
            "👥 <b>Foydalanuvchi faolligi</b>\n\n"
            f"🟢 Bugun aktiv userlar: <b>{active_today}</b>\n"
            f"🕒 So'nggi 24 soat aktiv userlar: <b>{active_24h}</b>\n"
            f"📅 So'nggi 7 kun aktiv userlar: <b>{active_7d}</b>\n"
            f"🎥 Bugun kino olgan userlar: <b>{received_movie_today}</b>\n"
            f"🔎 Bugun kod yuborgan userlar: <b>{sent_code_today}</b>\n\n"
            "🔗 <b>Referral / share</b>\n"
            f"Share/referral orqali kelganlar: <b>{referral_users}</b>\n\n"
            f"{self._format_referrers(top_referrers)}"
        )

    async def build_movie_stats(self) -> str:
        uploaded_today = await self.movie_repository.count_movies_uploaded_today()
        total_movies = await self.movie_repository.count_movies()
        top_movies = await self.movie_repository.get_top_movies(limit=5)
        most_active_base = await self.movie_repository.get_most_active_base()
        most_used_codes = await self.movie_repository.get_most_used_codes(limit=5)

        active_base_text = "Hali foydalanish yo'q"
        if most_active_base:
            movie_base, total = most_active_base
            active_base_text = f"{safe_html(movie_base.title)} — <b>{total}</b> marta"

        return (
            "🎬 <b>Kino statistikasi</b>\n\n"
            f"📤 Bugun yuklangan kinolar: <b>{uploaded_today}</b>\n"
            f"📤 Umumiy yuklangan kinolar: <b>{total_movies}</b>\n"
            f"🗂 Eng faol baza: {active_base_text}\n\n"
            "🔥 <b>Eng ko'p olingan TOP 5 kinolar</b>\n"
            f"{self._format_top_movies(top_movies)}\n\n"
            "🔢 <b>Eng ko'p ishlatilgan kino kodlari</b>\n"
            f"{self._format_codes(most_used_codes)}"
        )

    async def build_subscription_stats(self) -> str:
        total_subscriptions = await self.subscription_repository.count_subscriptions()
        active_subscriptions = await self.subscription_repository.count_active_subscriptions()
        successful = await self.subscription_repository.count_successful_subscription_checks()
        failed = await self.subscription_repository.count_failed_subscription_checks()
        attempts = await self.subscription_repository.count_subscription_check_attempts()
        blocking_stats = await self.subscription_repository.get_subscription_blocking_stats(limit=5)

        return (
            "📢 <b>Obuna statistikasi</b>\n\n"
            f"📢 Jami obunalar: <b>{total_subscriptions}</b>\n"
            f"✅ Aktiv obunalar: <b>{active_subscriptions}</b>\n"
            f"✅ Obunani to'liq bajarganlar: <b>{successful}</b>\n"
            f"❌ Obunani bajarmaganlar: <b>{failed}</b>\n"
            f"🔁 Tekshirish bosilgan: <b>{attempts}</b>\n\n"
            "🚧 <b>Eng ko'p userni to'xtatayotgan obunalar</b>\n"
            f"{self._format_blocking_subscriptions(blocking_stats)}"
        )

    async def build_base_stats(self) -> str:
        total_bases = await self.movie_base_repository.count_bases()
        active_bases = await self.movie_base_repository.count_active_bases()
        usage_stats = await self.movie_base_repository.get_base_usage_stats(limit=10)

        return (
            "🗂 <b>Baza statistikasi</b>\n\n"
            f"📂 Jami bazalar: <b>{total_bases}</b>\n"
            f"✅ Aktiv bazalar: <b>{active_bases}</b>\n\n"
            "📌 <b>Bazalar kesimida</b>\n"
            f"{self._format_base_usage(usage_stats)}"
        )

    async def build_top_movies_stats(self) -> str:
        top_movies = await self.movie_repository.get_top_movies(limit=10)
        most_used_codes = await self.movie_repository.get_most_used_codes(limit=10)

        return (
            "🔥 <b>Top kinolar</b>\n\n"
            "🎬 <b>Eng ko'p olingan kinolar</b>\n"
            f"{self._format_top_movies(top_movies)}\n\n"
            "🔢 <b>Eng faol kodlar</b>\n"
            f"{self._format_codes(most_used_codes)}"
        )

    @staticmethod
    def _empty(text: str = "Hali ma'lumot yo'q.") -> str:
        return text

    def _format_top_movies(self, rows) -> str:
        if not rows:
            return self._empty()

        lines = []
        for index, (movie, total) in enumerate(rows, start=1):
            lines.append(
                f"{index}. <code>{safe_html(movie.code)}</code> — "
                f"{safe_html(movie.title)}: <b>{total}</b> marta"
            )
        return "\n".join(lines)

    def _format_codes(self, rows) -> str:
        if not rows:
            return self._empty()

        return "\n".join(
            f"{index}. <code>{safe_html(code)}</code> — <b>{total}</b> marta"
            for index, (code, total) in enumerate(rows, start=1)
        )

    def _format_base_usage(self, rows) -> str:
        if not rows:
            return self._empty()

        lines = []
        for index, (movie_base, movie_count, usage_count) in enumerate(rows, start=1):
            status = "✅" if movie_base.is_active else "❌"
            lines.append(
                f"{index}. {status} {safe_html(movie_base.title)} — "
                f"kinolar: <b>{movie_count}</b>, olinish: <b>{usage_count}</b>"
            )
        return "\n".join(lines)

    def _format_blocking_subscriptions(self, rows) -> str:
        if not rows:
            return self._empty()

        return "\n".join(
            f"{index}. {safe_html(subscription.title)} — <b>{total}</b> marta"
            for index, (subscription, total) in enumerate(rows, start=1)
        )

    def _format_referrers(self, rows) -> str:
        if not rows:
            return "Eng ko'p referral olib kelgan userlar: hali ma'lumot yo'q."

        lines = ["Eng ko'p referral olib kelgan userlar:"]
        for index, (telegram_id, full_name, total) in enumerate(rows, start=1):
            name = safe_html(full_name) if full_name else f"ID {telegram_id}"
            lines.append(f"{index}. {name} — <b>{total}</b> user")
        return "\n".join(lines)
