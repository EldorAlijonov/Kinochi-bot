from datetime import UTC, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import APP_TIMEZONE


def get_app_timezone() -> tzinfo:
    try:
        return ZoneInfo(APP_TIMEZONE)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=5), name="Asia/Tashkent")


def to_local_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    aware_value = value
    if aware_value.tzinfo is None:
        aware_value = aware_value.replace(tzinfo=UTC)

    return aware_value.astimezone(get_app_timezone())


def format_local_datetime(value: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    local_value = to_local_datetime(value)
    if local_value is None:
        return "Noma'lum"

    return local_value.strftime(fmt)
