from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.database.models.subscription import Subscription
from app.database.models.user_action_log import UserActionLog


class SubscriptionRepository:
    def __init__(self, session):
        self.session = session

    async def create_public_channel(
        self,
        title: str,
        chat_username: str,
        invite_link: str,
    ) -> Subscription:
        subscription = Subscription(
            title=title,
            subscription_type="public_channel",
            chat_username=chat_username,
            invite_link=invite_link,
            is_active=True,
        )

        self.session.add(subscription)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(subscription)
        return subscription

    async def create_private_channel(
        self,
        title: str,
        chat_id: int,
        invite_link: str,
    ) -> Subscription:
        subscription = Subscription(
            title=title,
            subscription_type="private_channel",
            chat_id=chat_id,
            invite_link=invite_link,
            is_active=True,
        )

        self.session.add(subscription)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(subscription)
        return subscription

    async def create_public_group(
        self,
        title: str,
        chat_username: str,
        invite_link: str,
    ) -> Subscription:
        subscription = Subscription(
            title=title,
            subscription_type="public_group",
            chat_username=chat_username,
            invite_link=invite_link,
            is_active=True,
        )

        self.session.add(subscription)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(subscription)
        return subscription

    async def create_private_group(
        self,
        title: str,
        chat_id: int,
        invite_link: str,
    ) -> Subscription:
        subscription = Subscription(
            title=title,
            subscription_type="private_group",
            chat_id=chat_id,
            invite_link=invite_link,
            is_active=True,
        )

        self.session.add(subscription)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(subscription)
        return subscription

    async def create_external_link(
        self,
        title: str,
        invite_link: str,
    ) -> Subscription:
        subscription = Subscription(
            title=title,
            subscription_type="external_link",
            invite_link=invite_link,
            is_active=True,
        )

        self.session.add(subscription)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

        await self.session.refresh(subscription)
        return subscription

    async def get_by_username(self, chat_username: str) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.chat_username == chat_username)
        )
        return result.scalar_one_or_none()

    async def exists_by_username(self, chat_username: str) -> bool:
        subscription = await self.get_by_username(chat_username)
        return subscription is not None

    async def get_by_chat_id(self, chat_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    async def exists_by_chat_id(self, chat_id: int) -> bool:
        subscription = await self.get_by_chat_id(chat_id)
        return subscription is not None

    async def get_by_invite_link(self, invite_link: str) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.invite_link == invite_link)
        )
        return result.scalar_one_or_none()

    async def exists_by_invite_link(self, invite_link: str) -> bool:
        subscription = await self.get_by_invite_link(invite_link)
        return subscription is not None

    async def get_active(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.is_active.is_(True))
            .order_by(Subscription.id.desc())
        )
        return result.scalars().all()

    async def list_active_subscriptions(self) -> list[Subscription]:
        return await self.get_active()

    async def list_group_targets(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.is_active.is_(True),
                Subscription.subscription_type.in_(("public_group", "private_group")),
            )
            .order_by(Subscription.id.desc())
        )
        return list(result.scalars().all())

    async def list_channel_targets(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.is_active.is_(True),
                Subscription.subscription_type.in_(("public_channel", "private_channel")),
            )
            .order_by(Subscription.id.desc())
        )
        return list(result.scalars().all())

    async def list_inactive_subscriptions(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.is_active.is_(False))
            .order_by(Subscription.id.desc())
        )
        return result.scalars().all()

    async def get_all(self) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription).order_by(Subscription.id.desc())
        )
        return result.scalars().all()

    async def get_all_paginated(self, limit: int, offset: int):
        result = await self.session.execute(
            select(Subscription)
            .order_by(Subscription.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_paginated_by_active(
        self,
        is_active: bool,
        limit: int,
        offset: int,
    ):
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.is_active.is_(is_active))
            .order_by(Subscription.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_all(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Subscription)
        )
        return result.scalar_one()

    async def count_subscriptions(self) -> int:
        return await self.count_all()

    async def count_active_subscriptions(self) -> int:
        return await self.count_by_active(True)

    async def count_by_active(self, is_active: bool) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.is_active.is_(is_active))
        )
        return result.scalar_one()

    async def get_by_id(self, subscription_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def activate_subscription(self, subscription_id: int) -> bool:
        return await self._set_active(subscription_id, True)

    async def deactivate_subscription(self, subscription_id: int) -> bool:
        return await self._set_active(subscription_id, False)

    async def _set_active(self, subscription_id: int, is_active: bool) -> bool:
        subscription = await self.get_by_id(subscription_id)
        if not subscription:
            return False

        subscription.is_active = is_active
        await self.session.commit()
        return True

    async def delete_by_id(self, subscription_id: int) -> bool:
        subscription = await self.get_by_id(subscription_id)
        if not subscription:
            return False

        await self.session.delete(subscription)
        await self.session.commit()
        return True

    async def count_successful_subscription_checks(self) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(UserActionLog.user_telegram_id))).where(
                UserActionLog.action_type == "subscription_check",
                UserActionLog.is_success.is_(True),
            )
        )
        return result.scalar_one()

    async def count_failed_subscription_checks(self) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(UserActionLog.user_telegram_id))).where(
                UserActionLog.action_type == "subscription_check",
                UserActionLog.is_success.is_(False),
            )
        )
        return result.scalar_one()

    async def count_subscription_check_attempts(self) -> int:
        result = await self.session.execute(
            select(func.count()).where(UserActionLog.action_type == "subscription_check")
        )
        return result.scalar_one()

    async def get_subscription_blocking_stats(self, limit: int = 5) -> list[tuple[Subscription, int]]:
        result = await self.session.execute(
            select(Subscription, func.count(UserActionLog.id).label("total"))
            .join(UserActionLog, UserActionLog.subscription_id == Subscription.id)
            .where(
                UserActionLog.action_type.in_(
                    ("subscription_check", "subscription_blocked")
                ),
                UserActionLog.is_success.is_(False),
            )
            .group_by(Subscription.id)
            .order_by(func.count(UserActionLog.id).desc(), Subscription.id.desc())
            .limit(limit)
        )
        return list(result.all())
