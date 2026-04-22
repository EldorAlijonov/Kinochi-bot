import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_admins(raw_value: str | None) -> list[int]:
    if not raw_value:
        return []

    admins: list[int] = []
    for chunk in raw_value.split(","):
        candidate = chunk.strip()
        if candidate:
            admins.append(int(candidate))

    return admins


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admins: tuple[int, ...]
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    log_level: str
    subscription_cache_ttl: int
    subscription_status_cache_ttl: int
    subscription_gate_fail_open: bool
    pending_movie_ttl_seconds: int
    auto_init_db: bool
    app_timezone: str
    rate_limit_window_seconds: int
    rate_limit_max_requests: int
    app_env: str
    base_webhook_url: str
    webhook_path: str
    webhook_secret: str
    webapp_host: str
    webapp_port: int
    webhook_max_connections: int
    webhook_setup_retries: int
    webhook_drop_pending_updates: bool
    delete_webhook_on_shutdown: bool
    bot_request_timeout: int
    redis_url: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def use_webhook(self) -> bool:
        return self.is_production or bool(self.base_webhook_url)

    @property
    def webhook_url(self) -> str:
        return f"{self.base_webhook_url.rstrip('/')}{self.webhook_path}"

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("TOKEN env o'zgaruvchisi topilmadi.")
        if self.is_production and self.auto_init_db:
            raise RuntimeError(
                "Production rejimida AUTO_INIT_DB=false bo'lishi kerak. "
                "Schema boshqaruvi uchun Alembic migrationlardan foydalaning."
            )
        if self.use_webhook:
            if not self.base_webhook_url:
                raise RuntimeError("Webhook rejimi uchun BASE_WEBHOOK_URL kerak.")
            if not self.webhook_path.startswith("/"):
                raise RuntimeError("WEBHOOK_PATH '/' bilan boshlanishi kerak.")
            if not self.webhook_secret:
                raise RuntimeError("Webhook rejimi uchun WEBHOOK_SECRET kerak.")


def load_settings() -> Settings:
    return Settings(
        bot_token=(os.getenv("TOKEN") or "").strip(),
        admins=tuple(_parse_admins(os.getenv("ADMINS"))),
        db_host=(os.getenv("DB_HOST") or "localhost").strip(),
        db_port=int((os.getenv("DB_PORT") or "5432").strip()),
        db_name=(os.getenv("DB_NAME") or "telegram_bot").strip(),
        db_user=(os.getenv("DB_USER") or "postgres").strip(),
        db_password=os.getenv("DB_PASSWORD") or "postgres",
        log_level=(os.getenv("LOG_LEVEL") or "INFO").strip().upper(),
        subscription_cache_ttl=int(
            (os.getenv("SUBSCRIPTION_CACHE_TTL_SECONDS") or "30").strip()
        ),
        subscription_status_cache_ttl=int(
            (os.getenv("SUBSCRIPTION_STATUS_CACHE_TTL_SECONDS") or "60").strip()
        ),
        subscription_gate_fail_open=(
            os.getenv("SUBSCRIPTION_GATE_FAIL_OPEN") or "true"
        ).strip().lower()
        == "true",
        pending_movie_ttl_seconds=int(
            (os.getenv("PENDING_MOVIE_TTL_SECONDS") or "1800").strip()
        ),
        auto_init_db=(os.getenv("AUTO_INIT_DB") or "true").strip().lower() == "true",
        app_timezone=(os.getenv("APP_TIMEZONE") or "Asia/Tashkent").strip(),
        rate_limit_window_seconds=int(
            (os.getenv("RATE_LIMIT_WINDOW_SECONDS") or "10").strip()
        ),
        rate_limit_max_requests=int(
            (os.getenv("RATE_LIMIT_MAX_REQUESTS") or "8").strip()
        ),
        app_env=(os.getenv("APP_ENV") or "development").strip().lower(),
        base_webhook_url=(os.getenv("BASE_WEBHOOK_URL") or "").strip(),
        webhook_path=(os.getenv("WEBHOOK_PATH") or "/webhook").strip(),
        webhook_secret=(os.getenv("WEBHOOK_SECRET") or "").strip(),
        webapp_host=(os.getenv("WEBAPP_HOST") or "0.0.0.0").strip(),
        webapp_port=int((os.getenv("WEBAPP_PORT") or "8080").strip()),
        webhook_max_connections=int(
            (os.getenv("WEBHOOK_MAX_CONNECTIONS") or "40").strip()
        ),
        webhook_setup_retries=int(
            (os.getenv("WEBHOOK_SETUP_RETRIES") or "3").strip()
        ),
        webhook_drop_pending_updates=(
            os.getenv("WEBHOOK_DROP_PENDING_UPDATES") or "false"
        ).strip().lower()
        == "true",
        delete_webhook_on_shutdown=(
            os.getenv("DELETE_WEBHOOK_ON_SHUTDOWN") or "false"
        ).strip().lower()
        == "true",
        bot_request_timeout=int((os.getenv("BOT_REQUEST_TIMEOUT") or "30").strip()),
        redis_url=(os.getenv("REDIS_URL") or "").strip(),
    )


settings = load_settings()

BOT_TOKEN = settings.bot_token
ADMINS = list(settings.admins)
DB_HOST = settings.db_host
DB_PORT = settings.db_port
DB_NAME = settings.db_name
DB_USER = settings.db_user
DB_PASSWORD = settings.db_password
DATABASE_URL = settings.database_url
LOG_LEVEL = settings.log_level
SUBSCRIPTION_CACHE_TTL_SECONDS = settings.subscription_cache_ttl
SUBSCRIPTION_STATUS_CACHE_TTL_SECONDS = settings.subscription_status_cache_ttl
SUBSCRIPTION_GATE_FAIL_OPEN = settings.subscription_gate_fail_open
PENDING_MOVIE_TTL_SECONDS = settings.pending_movie_ttl_seconds
AUTO_INIT_DB = settings.auto_init_db
APP_TIMEZONE = settings.app_timezone
RATE_LIMIT_WINDOW_SECONDS = settings.rate_limit_window_seconds
RATE_LIMIT_MAX_REQUESTS = settings.rate_limit_max_requests
APP_ENV = settings.app_env
BASE_WEBHOOK_URL = settings.base_webhook_url
WEBHOOK_PATH = settings.webhook_path
WEBHOOK_SECRET = settings.webhook_secret
WEBAPP_HOST = settings.webapp_host
WEBAPP_PORT = settings.webapp_port
REDIS_URL = settings.redis_url
