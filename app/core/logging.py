import logging
import os
import sys

from app.core.config import APP_ENV, LOG_LEVEL


def configure_logging() -> None:
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    noisy_loggers = {
        "aiogram.event": logging.WARNING,
        "aiohttp.access": logging.WARNING if APP_ENV == "production" else logging.INFO,
        "aiohttp.server": logging.WARNING,
        "asyncio": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
    }
    for logger_name, level in noisy_loggers.items():
        logging.getLogger(logger_name).setLevel(level)

    logging.captureWarnings(True)

    if os.getenv("DEBUG_SQL", "false").strip().lower() == "true":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
