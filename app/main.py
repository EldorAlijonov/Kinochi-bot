import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from app.core.config import AUTO_INIT_DB, BOT_TOKEN, settings
from app.core.logging import configure_logging
from app.database.db import init_db
from app.handlers.admin.broadcast import router as admin_broadcast_router
from app.handlers.admin.common import router as admin_common_router
from app.handlers.admin.links import router as links_router
from app.handlers.admin.movie_base_add import router as movie_base_add_router
from app.handlers.admin.movie_base_delete import router as movie_base_delete_router
from app.handlers.admin.movie_base_list import router as movie_base_list_router
from app.handlers.admin.movie_base_status import router as movie_base_status_router
from app.handlers.admin.movie_bases_menu import router as movie_bases_menu_router
from app.handlers.admin.movie_list import router as movie_list_router
from app.handlers.admin.movie_upload import router as movie_upload_router
from app.handlers.admin.private_channel import router as private_channel_router
from app.handlers.admin.private_group import router as private_group_router
from app.handlers.admin.public_channel import router as public_channel_router
from app.handlers.admin.public_group import router as public_group_router
from app.handlers.admin.subscription_delete import router as subscription_delete_router
from app.handlers.admin.subscription_list import router as subscription_list_router
from app.handlers.admin.subscription_status import router as subscription_status_router
from app.handlers.admin.subscriptions_menu import router as admin_subscriptions_router
from app.handlers.admin.statistics import router as admin_statistics_router
from app.handlers.admin.users import router as admin_users_router
from app.handlers.start import router as start_router
from app.handlers.user.movie_request import router as user_movie_request_router
from app.handlers.user.movie_share import router as user_movie_share_router
from app.handlers.user.subscription_check import router as user_subscription_check_router
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.subscription_middleware import SubscriptionMiddleware
from app.middlewares.user_tracking import UserTrackingMiddleware
from app.services.broadcast_worker import BroadcastWorker
from app.services.startup_checks import validate_runtime_dependencies
from app.webhook import create_webhook_app

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    session = AiohttpSession(timeout=settings.bot_request_timeout)
    return Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode="HTML"),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    dp.message.outer_middleware(RateLimitMiddleware())
    dp.callback_query.outer_middleware(RateLimitMiddleware())
    dp.message.outer_middleware(UserTrackingMiddleware())
    dp.callback_query.outer_middleware(UserTrackingMiddleware())
    dp.message.outer_middleware(SubscriptionMiddleware())
    dp.callback_query.outer_middleware(SubscriptionMiddleware())

    dp.include_router(start_router)
    dp.include_router(admin_common_router)
    dp.include_router(admin_broadcast_router)
    dp.include_router(admin_statistics_router)
    dp.include_router(admin_users_router)
    dp.include_router(movie_bases_menu_router)
    dp.include_router(movie_base_add_router)
    dp.include_router(movie_base_list_router)
    dp.include_router(movie_base_status_router)
    dp.include_router(movie_base_delete_router)
    dp.include_router(movie_list_router)
    dp.include_router(movie_upload_router)
    dp.include_router(admin_subscriptions_router)
    dp.include_router(public_channel_router)
    dp.include_router(private_channel_router)
    dp.include_router(subscription_list_router)
    dp.include_router(subscription_status_router)
    dp.include_router(user_subscription_check_router)
    dp.include_router(user_movie_request_router)
    dp.include_router(user_movie_share_router)
    dp.include_router(public_group_router)
    dp.include_router(private_group_router)
    dp.include_router(links_router)
    dp.include_router(subscription_delete_router)
    return dp


async def start_polling() -> None:
    configure_logging()
    settings.validate()
    await validate_runtime_dependencies()
    if AUTO_INIT_DB:
        await init_db()

    bot = create_bot()
    dp = create_dispatcher()
    broadcast_worker = BroadcastWorker(bot)
    broadcast_worker.start()

    await bot.delete_webhook(drop_pending_updates=settings.webhook_drop_pending_updates)
    logger.info("Bot polling rejimida ishga tushdi")
    try:
        await dp.start_polling(bot)
    finally:
        await broadcast_worker.stop()
        await bot.session.close()


def start_webhook() -> None:
    configure_logging()
    settings.validate()

    bot = create_bot()
    dp = create_dispatcher()
    app = create_webhook_app(bot, dp)

    logger.info(
        "Bot webhook rejimida ishga tushmoqda | host=%s port=%s path=%s env=%s",
        settings.webapp_host,
        settings.webapp_port,
        settings.webhook_path,
        settings.app_env,
    )
    web.run_app(
        app,
        host=settings.webapp_host,
        port=settings.webapp_port,
        shutdown_timeout=30,
        access_log=None if settings.is_production else logger,
    )


async def start_bot() -> None:
    await start_polling()


def run_bot() -> None:
    if settings.use_webhook:
        start_webhook()
        return

    import asyncio

    asyncio.run(start_polling())
