from app.keyboards.user.subscription import subscription_check_keyboard
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService


def serialize_subscription(sub) -> dict:
    return {
        "id": sub.id,
        "title": sub.title,
        "subscription_type": sub.subscription_type,
        "chat_username": sub.chat_username,
        "invite_link": sub.invite_link,
    }


async def get_subscription_gate(bot, user_id: int, session, use_cache: bool = True):
    repository = SubscriptionRepository(session)
    service = SubscriptionService(repository)
    subscriptions = await service.get_active_subscriptions()

    telegram_subscriptions = [
        sub for sub in subscriptions if sub.subscription_type != "external_link"
    ]
    external_links = [
        sub for sub in subscriptions if sub.subscription_type == "external_link"
    ]

    check_result = await service.check_subscription_status(
        bot=bot,
        user_id=user_id,
        subscriptions=telegram_subscriptions,
        use_cache=use_cache,
    )
    unsubscribed_channels = check_result["unsubscribed_channels"] + [
        item["subscription"] for item in check_result["uncheckable_channels"]
    ]

    return unsubscribed_channels, external_links, check_result["message"]


def build_subscription_keyboard(
    unsubscribed_channels,
    external_links,
    check_callback_data: str = "check_subscriptions",
):
    return subscription_check_keyboard(
        [serialize_subscription(sub) for sub in unsubscribed_channels],
        extra_links=[serialize_subscription(sub) for sub in external_links],
        check_callback_data=check_callback_data,
    )
