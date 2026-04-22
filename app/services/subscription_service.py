import asyncio

from sqlalchemy.exc import IntegrityError

from app.core.config import SUBSCRIPTION_CACHE_TTL_SECONDS, SUBSCRIPTION_STATUS_CACHE_TTL_SECONDS
from app.services.runtime_store import CacheStore, cache_store
from app.services.subscription_validator import (
    is_valid_external_url,
    parse_username_or_link,
    validate_private_invite_link,
    validate_public_channel_data,
    validate_title,
)
from app.utils.checker import check_user_subscription


class SubscriptionService:
    ACTIVE_CACHE_KEY = "subscriptions:active"

    def __init__(self, repository, store: CacheStore = cache_store):
        self.repository = repository
        self.store = store

    async def invalidate_active_cache(self) -> None:
        await self.store.delete(self.ACTIVE_CACHE_KEY)

    @classmethod
    def invalidate_cache(cls) -> None:
        # Testlar va eski chaqiriqlar bilan moslik uchun qoldirildi.
        global cache_store
        if hasattr(cache_store, "_items"):
            cache_store._items.pop(cls.ACTIVE_CACHE_KEY, None)

    async def _cache_active_subscriptions(self, subscriptions: list) -> list:
        if not getattr(self.store, "supports_complex_values", False):
            return subscriptions

        await self.store.set(
            self.ACTIVE_CACHE_KEY,
            list(subscriptions),
            ttl_seconds=SUBSCRIPTION_CACHE_TTL_SECONDS,
        )
        return subscriptions

    async def create_public_channel(self, title: str, raw_value: str):
        username, invite_link = parse_username_or_link(raw_value)

        error = validate_public_channel_data(title, username, invite_link)
        if error:
            return {"ok": False, "message": error}

        exists = await self.repository.exists_by_username(username)
        if exists:
            return {"ok": False, "message": "Bu ommaviy kanal oldin qo'shilgan."}

        try:
            subscription = await self.repository.create_public_channel(
                title=title,
                chat_username=username,
                invite_link=invite_link,
            )
        except IntegrityError:
            return {"ok": False, "message": "Bu ommaviy kanal oldin qo'shilgan."}

        await self.invalidate_active_cache()
        return {"ok": True, "subscription": subscription}

    async def create_private_channel(
        self,
        title: str,
        chat_id: int,
        invite_link: str,
    ):
        title_error = validate_title(title)
        if title_error:
            return {"ok": False, "message": title_error}

        invite_link_error = validate_private_invite_link(invite_link)
        if invite_link_error:
            return {"ok": False, "message": invite_link_error}

        exists = await self.repository.exists_by_chat_id(chat_id)
        if exists:
            return {"ok": False, "message": "Bu maxfiy kanal oldin qo'shilgan."}

        try:
            subscription = await self.repository.create_private_channel(
                title=title,
                chat_id=chat_id,
                invite_link=invite_link,
            )
        except IntegrityError:
            return {"ok": False, "message": "Bu maxfiy kanal oldin qo'shilgan."}

        await self.invalidate_active_cache()
        return {"ok": True, "subscription": subscription}

    async def create_public_group(self, title: str, raw_value: str):
        username, invite_link = parse_username_or_link(raw_value)

        error = validate_public_channel_data(title, username, invite_link)
        if error:
            return {"ok": False, "message": error}

        exists = await self.repository.exists_by_username(username)
        if exists:
            return {"ok": False, "message": "Bu guruh oldin qo'shilgan."}

        try:
            subscription = await self.repository.create_public_group(
                title=title,
                chat_username=username,
                invite_link=invite_link,
            )
        except IntegrityError:
            return {"ok": False, "message": "Bu guruh oldin qo'shilgan."}

        await self.invalidate_active_cache()
        return {"ok": True, "subscription": subscription}

    async def create_private_group(
        self,
        title: str,
        chat_id: int,
        invite_link: str,
    ):
        title_error = validate_title(title)
        if title_error:
            return {"ok": False, "message": title_error}

        invite_link_error = validate_private_invite_link(invite_link)
        if invite_link_error:
            return {"ok": False, "message": invite_link_error}

        exists = await self.repository.exists_by_chat_id(chat_id)
        if exists:
            return {"ok": False, "message": "Bu guruh oldin qo'shilgan."}

        try:
            subscription = await self.repository.create_private_group(
                title=title,
                chat_id=chat_id,
                invite_link=invite_link,
            )
        except IntegrityError:
            return {"ok": False, "message": "Bu guruh oldin qo'shilgan."}

        await self.invalidate_active_cache()
        return {"ok": True, "subscription": subscription}

    async def create_external_link(self, title: str, url: str):
        title_error = validate_title(title)
        if title_error:
            return {"ok": False, "message": title_error}

        if not is_valid_external_url(url):
            return {"ok": False, "message": "Havola noto'g'ri formatda."}

        exists = await self.repository.exists_by_invite_link(url)
        if exists:
            return {"ok": False, "message": "Bu havola oldin qo'shilgan."}

        try:
            subscription = await self.repository.create_external_link(
                title=title,
                invite_link=url,
            )
        except IntegrityError:
            return {"ok": False, "message": "Bu havola oldin qo'shilgan."}

        await self.invalidate_active_cache()
        return {"ok": True, "subscription": subscription}

    async def get_active_subscriptions(self, use_cache: bool = True):
        if use_cache and getattr(self.store, "supports_complex_values", False):
            cached = await self.store.get(self.ACTIVE_CACHE_KEY)
            if cached is not None:
                return list(cached)

        subscriptions = await self.repository.get_active()
        if use_cache:
            return await self._cache_active_subscriptions(subscriptions)

        return subscriptions

    async def get_all_subscriptions(self):
        return await self.repository.get_all()

    async def get_paginated_subscriptions(self, limit: int, offset: int):
        return await self.repository.get_all_paginated(
            limit=limit,
            offset=offset,
        )

    async def get_paginated_subscriptions_by_status(
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

    async def count_all_subscriptions(self) -> int:
        return await self.repository.count_all()

    async def count_subscriptions_by_status(self, is_active: bool) -> int:
        return await self.repository.count_by_active(is_active)

    async def get_unsubscribed_channels(self, bot, user_id: int, subscriptions):
        result = await self.check_subscription_status(bot, user_id, subscriptions)
        return result["unsubscribed_channels"] + [
            item["subscription"] for item in result["uncheckable_channels"]
        ]

    async def check_subscription_status(self, bot, user_id: int, subscriptions, use_cache: bool = True):
        unsubscribed = []
        uncheckable = []
        semaphore = asyncio.Semaphore(5)
        checks = []

        for sub in subscriptions:
            if sub.subscription_type == "external_link":
                continue

            chat_identifier = sub.chat_username if sub.chat_username else sub.chat_id

            if not chat_identifier:
                continue

            cache_key = f"sub_status:{user_id}:{sub.id}"
            if use_cache:
                cached_status = await self.store.get(cache_key)
                if cached_status == "1":
                    continue
                if cached_status == "0":
                    unsubscribed.append(sub)
                    continue

            async def run_check(subscription=sub, identifier=chat_identifier, key=cache_key):
                async with semaphore:
                    result = await check_user_subscription(
                        bot,
                        identifier,
                        user_id,
                    )
                    return subscription, key, result

            checks.append(run_check())

        for sub, cache_key, check_result in await asyncio.gather(*checks):
            if not check_result.ok:
                uncheckable.append(
                    {
                        "subscription": sub,
                        "message": check_result.message,
                    }
                )
                continue

            if not check_result.is_subscribed:
                unsubscribed.append(sub)
                if use_cache:
                    await self.store.set(cache_key, "0", SUBSCRIPTION_STATUS_CACHE_TTL_SECONDS)
                continue

            if use_cache:
                await self.store.set(cache_key, "1", SUBSCRIPTION_STATUS_CACHE_TTL_SECONDS)

        return {
            "ok": not uncheckable,
            "unsubscribed_channels": unsubscribed,
            "uncheckable_channels": uncheckable,
            "message": (
                "Obuna holatini tekshirib bo'lmadi. Bot kanal/guruhga qo'shilgan "
                "va admin ekanini tekshiring."
                if uncheckable
                else None
            ),
        }

    async def delete_subscription(self, subscription_id: int) -> bool:
        subscription = await self.repository.get_by_id(subscription_id)
        if not subscription:
            return False

        deleted = await self.repository.delete_by_id(subscription_id)
        if deleted:
            await self.invalidate_active_cache()
        return deleted

    async def activate_subscription(self, subscription_id: int):
        subscription = await self.repository.get_by_id(subscription_id)
        if not subscription:
            return {"ok": False, "message": "Obuna topilmadi."}

        if subscription.is_active:
            return {"ok": False, "message": "Obuna allaqachon aktiv."}

        updated = await self.repository.activate_subscription(subscription_id)
        if updated:
            await self.invalidate_active_cache()

        return {
            "ok": updated,
            "message": "Obuna aktiv qilindi" if updated else "Obuna topilmadi.",
        }

    async def deactivate_subscription(self, subscription_id: int):
        subscription = await self.repository.get_by_id(subscription_id)
        if not subscription:
            return {"ok": False, "message": "Obuna topilmadi."}

        if not subscription.is_active:
            return {"ok": False, "message": "Obuna allaqachon noaktiv."}

        updated = await self.repository.deactivate_subscription(subscription_id)
        if updated:
            await self.invalidate_active_cache()

        return {
            "ok": updated,
            "message": "Obuna noaktiv qilindi" if updated else "Obuna topilmadi.",
        }
