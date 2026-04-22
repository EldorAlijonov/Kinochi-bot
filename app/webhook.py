import logging
from asyncio import sleep

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.core.config import settings
from app.database.db import engine
from app.database.db import init_db
from app.services.broadcast_worker import BroadcastWorker
from app.services.runtime_store import cache_store
from app.services.startup_checks import validate_runtime_dependencies
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def healthcheck(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "mode": "webhook"})


async def readiness(request: web.Request) -> web.Response:
    checks = {"db": False, "redis": False}

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception:
        logger.exception("Healthcheck DB ulanishida xatolik")

    try:
        checks["redis"] = await cache_store.ping()
    except Exception:
        logger.exception("Healthcheck runtime store ulanishida xatolik")

    status_code = 200 if all(checks.values()) else 503
    return web.json_response(
        {
            "status": "ok" if status_code == 200 else "degraded",
            "mode": "webhook",
            "checks": checks,
        },
        status=status_code,
    )


async def setup_webhook(bot: Bot, dispatcher: Dispatcher) -> None:
    await validate_runtime_dependencies()

    if settings.auto_init_db:
        await init_db()

    webhook_url = settings.webhook_url
    allowed_updates = dispatcher.resolve_used_update_types()
    for attempt in range(1, settings.webhook_setup_retries + 1):
        try:
            await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.webhook_secret,
                max_connections=settings.webhook_max_connections,
                drop_pending_updates=settings.webhook_drop_pending_updates,
                allowed_updates=allowed_updates,
            )
            break
        except TelegramAPIError as error:
            if attempt >= settings.webhook_setup_retries:
                logger.exception("Webhook o'rnatilmadi | url=%s", webhook_url)
                raise
            logger.warning(
                "Webhook o'rnatishda vaqtinchalik xato | attempt=%s/%s error=%s",
                attempt,
                settings.webhook_setup_retries,
                error,
            )
            await sleep(min(attempt * 2, 10))

    webhook_info = await bot.get_webhook_info()
    logger.info(
        "Webhook o'rnatildi | url=%s pending=%s max_connections=%s",
        webhook_info.url,
        webhook_info.pending_update_count,
        settings.webhook_max_connections,
    )


async def close_webhook(bot: Bot) -> None:
    if settings.delete_webhook_on_shutdown:
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Webhook shutdown vaqtida o'chirildi")

    await bot.session.close()
    logger.info("Bot sessiyasi yopildi")


def create_webhook_app(bot: Bot, dispatcher: Dispatcher) -> web.Application:
    app = web.Application()
    app["broadcast_worker"] = BroadcastWorker(bot)
    app.router.add_get("/health", healthcheck)
    app.router.add_get("/healthz", readiness)

    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret,
    ).register(app, path=settings.webhook_path)

    async def on_startup(bot: Bot) -> None:
        await setup_webhook(bot, dispatcher)
        app["broadcast_worker"].start()

    async def on_shutdown(bot: Bot) -> None:
        await app["broadcast_worker"].stop()
        await close_webhook(bot)

    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
    setup_application(app, dispatcher, bot=bot)
    return app
