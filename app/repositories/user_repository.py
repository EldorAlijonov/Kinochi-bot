from datetime import datetime, timedelta

from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError

from app.database.models.user import User
from app.database.models.user_action_log import UserActionLog


def _now() -> datetime:
    return datetime.now()


def _today_start() -> datetime:
    current = _now()
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


class UserRepository:
    def __init__(self, session):
        self.session = session

    async def upsert_user(
        self,
        telegram_id: int,
        full_name: str | None = None,
        username: str | None = None,
        referred_by: int | None = None,
        start_payload: str | None = None,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.full_name = full_name
            user.username = username
            user.last_active_at = _now()
            if referred_by and referred_by != telegram_id and user.referred_by is None:
                user.referred_by = referred_by
            if start_payload and user.start_payload is None:
                user.start_payload = start_payload
            await self.session.commit()
            return user

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            last_active_at=_now(),
            referred_by=referred_by if referred_by != telegram_id else None,
            start_payload=start_payload,
        )
        self.session.add(user)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return await self.upsert_user(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                referred_by=referred_by,
                start_payload=start_payload,
            )

        await self.session.refresh(user)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.get_by_telegram_id(telegram_id)

    async def get_user_by_username(self, username: str) -> User | None:
        normalized_username = (username or "").strip().lstrip("@")
        result = await self.session.execute(
            select(User).where(User.username == normalized_username)
        )
        return result.scalar_one_or_none()

    async def get_recent_users(self, limit: int = 10) -> list[User]:
        result = await self.session.execute(
            select(User)
            .order_by(User.joined_at.desc(), User.telegram_id.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def touch_user(self, telegram_id: int, full_name: str | None, username: str | None):
        return await self.upsert_user(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
        )

    async def update_last_active(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(last_active_at=_now())
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def list_active_users(self, limit: int, offset: int) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.last_active_at >= _now() - timedelta(days=7))
            .order_by(User.last_active_at.desc(), User.telegram_id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_inactive_users(self, limit: int, offset: int) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.last_active_at < _now() - timedelta(days=7))
            .order_by(User.last_active_at.asc(), User.telegram_id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_active_users_last_7d_for_list(self) -> int:
        return await self.count_active_users_last_7d()

    async def count_inactive_users(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at < _now() - timedelta(days=7))
        )
        return result.scalar_one()

    async def ban_user(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_banned=True)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def unban_user(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_banned=False)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def count_movies_received_by_user(self, telegram_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(UserActionLog)
            .where(
                UserActionLog.user_telegram_id == telegram_id,
                UserActionLog.action_type == "movie_received",
            )
        )
        return result.scalar_one()

    async def count_referrals_by_user(self, telegram_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.referred_by == telegram_id)
        )
        return result.scalar_one()

    async def list_broadcast_user_ids(
        self,
        audience: str,
        limit: int,
        offset: int,
    ) -> list[int]:
        query = select(User.telegram_id).where(User.is_banned.is_(False))
        if audience == "active":
            query = query.where(User.last_active_at >= _now() - timedelta(days=7))
        elif audience == "inactive":
            query = query.where(User.last_active_at < _now() - timedelta(days=7))

        result = await self.session.execute(
            query.order_by(User.telegram_id.asc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def list_broadcast_user_ids_after(
        self,
        audience: str,
        last_telegram_id: int,
        limit: int,
    ) -> list[int]:
        query = select(User.telegram_id).where(
            User.is_banned.is_(False),
            User.telegram_id > last_telegram_id,
        )
        if audience == "active":
            query = query.where(User.last_active_at >= _now() - timedelta(days=7))
        elif audience == "inactive":
            query = query.where(User.last_active_at < _now() - timedelta(days=7))

        result = await self.session.execute(
            query.order_by(User.telegram_id.asc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_user_targets(self, last_telegram_id: int = 0, limit: int = 100) -> list[int]:
        result = await self.session.execute(
            select(User.telegram_id)
            .where(
                User.is_banned.is_(False),
                User.telegram_id > last_telegram_id,
            )
            .order_by(User.telegram_id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def log_action(
        self,
        user_telegram_id: int,
        action_type: str,
        movie_id: int | None = None,
        movie_code: str | None = None,
        subscription_id: int | None = None,
        is_success: bool | None = None,
        payload: str | None = None,
    ) -> UserActionLog:
        action = UserActionLog(
            user_telegram_id=user_telegram_id,
            action_type=action_type,
            movie_id=movie_id,
            movie_code=movie_code,
            subscription_id=subscription_id,
            is_success=is_success,
            payload=payload,
        )
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)
        return action

    async def count_users(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def count_users_joined_today(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.joined_at >= _today_start())
        )
        return result.scalar_one()

    async def count_active_users_today(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= _today_start())
        )
        return result.scalar_one()

    async def count_active_users_last_24h(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= _now() - timedelta(hours=24))
        )
        return result.scalar_one()

    async def count_active_users_last_7d(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= _now() - timedelta(days=7))
        )
        return result.scalar_one()

    async def count_users_received_movie_today(self) -> int:
        result = await self.session.execute(
            select(func.count(distinct(UserActionLog.user_telegram_id))).where(
                UserActionLog.action_type == "movie_received",
                UserActionLog.created_at >= _today_start(),
            )
        )
        return result.scalar_one()

    async def count_users_sent_code_today(self) -> int:
        result = await self.session.execute(
            select(func.count(distinct(UserActionLog.user_telegram_id))).where(
                UserActionLog.action_type == "code_sent",
                UserActionLog.created_at >= _today_start(),
            )
        )
        return result.scalar_one()

    async def count_referral_users(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.referred_by.is_not(None))
        )
        return result.scalar_one()

    async def get_top_referrers(self, limit: int = 5) -> list[tuple[int, str | None, int]]:
        result = await self.session.execute(
            select(User.referred_by, func.count().label("total"))
            .where(User.referred_by.is_not(None))
            .group_by(User.referred_by)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rows = result.all()
        if not rows:
            return []

        referrer_ids = [row.referred_by for row in rows]
        users_result = await self.session.execute(
            select(User.telegram_id, User.full_name).where(User.telegram_id.in_(referrer_ids))
        )
        names = {row.telegram_id: row.full_name for row in users_result.all()}
        return [(row.referred_by, names.get(row.referred_by), row.total) for row in rows]

    async def record_start(self, user_telegram_id: int, payload: str | None = None):
        return await self.log_action(
            user_telegram_id=user_telegram_id,
            action_type="start",
            payload=payload,
        )

    async def record_code_sent(self, user_telegram_id: int, code: str):
        return await self.log_action(
            user_telegram_id=user_telegram_id,
            action_type="code_sent",
            movie_code=code,
        )

    async def record_share_start(self, user_telegram_id: int, movie_code: str):
        return await self.log_action(
            user_telegram_id=user_telegram_id,
            action_type="share_start",
            movie_code=movie_code,
        )

    async def record_subscription_check(
        self,
        user_telegram_id: int,
        is_success: bool,
        blocking_subscription_id: int | None = None,
    ):
        return await self.log_action(
            user_telegram_id=user_telegram_id,
            action_type="subscription_check",
            subscription_id=blocking_subscription_id,
            is_success=is_success,
        )

    async def record_subscription_block(
        self,
        user_telegram_id: int,
        blocking_subscription_id: int | None = None,
    ):
        return await self.log_action(
            user_telegram_id=user_telegram_id,
            action_type="subscription_blocked",
            subscription_id=blocking_subscription_id,
            is_success=False,
        )
