import re
from urllib.parse import urlparse

TITLE_MAX_LENGTH = 100
USERNAME_PATTERN = re.compile(r"^@[A-Za-z0-9_]{4,}$")
TELEGRAM_PUBLIC_LINK_PATTERN = re.compile(r"^https?://t\.me/[A-Za-z0-9_]{4,}/?$")


def validate_title(title: str) -> str | None:
    title = (title or "").strip()

    if not title:
        return "Nomi bo'sh bo'lmasin."

    if len(title) > TITLE_MAX_LENGTH:
        return f"Nomi juda uzun. Maksimal {TITLE_MAX_LENGTH} ta belgi."

    if not re.search(r"\w", title, re.UNICODE):
        return "Nomi noto'g'ri."

    return None


def parse_username_or_link(value: str) -> tuple[str | None, str | None]:
    value = (value or "").strip()

    if USERNAME_PATTERN.fullmatch(value):
        return value, f"https://t.me/{value[1:]}"

    if TELEGRAM_PUBLIC_LINK_PATTERN.fullmatch(value):
        cleaned = value.replace("https://t.me/", "").replace("http://t.me/", "")
        cleaned = cleaned.strip("/")
        return f"@{cleaned}", f"https://t.me/{cleaned}"

    return None, None


def validate_public_channel_data(
    title: str,
    username: str | None,
    invite_link: str | None,
) -> str | None:
    title_error = validate_title(title)
    if title_error:
        return title_error

    if not username:
        return "Ommaviy kanal uchun username aniqlanishi kerak."

    if not USERNAME_PATTERN.fullmatch(username):
        return "Username noto'g'ri formatda."

    if not invite_link:
        return "Havola aniqlanmadi."

    return None


def validate_private_invite_link(invite_link: str) -> str | None:
    invite_link = (invite_link or "").strip()

    if not invite_link:
        return "Havola bo'sh bo'lmasin."

    parsed = urlparse(invite_link)
    if parsed.scheme != "https" or parsed.netloc != "t.me":
        return "Maxfiy kanal uchun to'g'ri invite link yuboring."

    if not (parsed.path.startswith("/+") or parsed.path.startswith("/joinchat/")):
        return "Maxfiy kanal uchun to'g'ri invite link yuboring."

    return None


def is_valid_external_url(url: str) -> bool:
    if not url:
        return False

    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
