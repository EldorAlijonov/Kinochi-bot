import re

DEFAULT_MOVIE_TITLE = "Nomsiz kino"
MOVIE_TITLE_PREFIX = "Kino Nomi:"
MOVIE_TITLE_PREFIX_PATTERN = re.compile(r"^\s*Kino\s+Nomi\s*:\s*(?P<title>.+?)\s*$", re.IGNORECASE)
MOVIE_CODE_ICON = "🎬"
BOT_USERNAME_ICON = "🤖"
MOVIE_CODE_ICON_PATTERN = r"(?:🎬|СЂСџР‹В¬|РЎР‚РЎСџР вЂ№Р’В¬|Р РЋР вЂљР РЋРЎСџР В РІР‚в„–Р вЂ™Р’В¬|Р В Р Р‹Р В РІР‚С™Р В Р Р‹Р РЋРЎСџР В Р’В Р Р†Р вЂљРІвЂћвЂ“Р В РІР‚в„ўР вЂ™Р’В¬)?"
BOT_USERNAME_LINE_PATTERN = re.compile(r"^\s*🤖\s*@[\w\d_]{5,32}\s*$")
SLASH_TITLE_PATTERN = re.compile(r"^\s*/(?P<title>[^/\n][^\n]*?)/\s*$")

MOVIE_CODE_LINE_PATTERN = re.compile(r"^\s*(?:\S+\s*)?Kino kodi:\s*\d{4}\s*$", re.IGNORECASE)
MOVIE_SIZE_LINE_PATTERN = re.compile(r"^\s*(?:\S+\s*)?Hajmi\s*:", re.IGNORECASE)
MOVIE_CHANNEL_LINE_PATTERN = re.compile(r"^\s*Bizning kanal\s*:", re.IGNORECASE)


def _strip_edge_slashes(value: str) -> str:
    return value.strip().strip("/").strip()


def _normalize_title_for_compare(value: str | None) -> str:
    value = _strip_edge_slashes(value or "")
    prefix_match = MOVIE_TITLE_PREFIX_PATTERN.fullmatch(value)
    if prefix_match:
        value = _strip_edge_slashes(prefix_match.group("title"))
    return " ".join(value.casefold().split())


def _is_duplicate_title_line(line: str, title: str | None) -> bool:
    if not title:
        return False

    line_title = _normalize_title_for_compare(line)
    expected_title = _normalize_title_for_compare(title)
    return line_title == expected_title or line_title.endswith(f" {expected_title}")


def _compact_blank_lines(lines: list[str]) -> list[str]:
    compacted: list[str] = []
    previous_blank = False

    for line in lines:
        stripped_line = line.rstrip()
        is_blank = not stripped_line.strip()
        if is_blank and previous_blank:
            continue

        compacted.append(stripped_line)
        previous_blank = is_blank

    while compacted and not compacted[0].strip():
        compacted.pop(0)
    while compacted and not compacted[-1].strip():
        compacted.pop()

    return compacted


def extract_movie_title(caption: str | None) -> str:
    if not caption:
        return DEFAULT_MOVIE_TITLE

    for line in caption.splitlines():
        match = SLASH_TITLE_PATTERN.fullmatch(line)
        if match:
            title = _strip_edge_slashes(match.group("title"))
            if title:
                return title[:255]

    for line in caption.splitlines():
        match = MOVIE_TITLE_PREFIX_PATTERN.fullmatch(line)
        if match:
            title = _strip_edge_slashes(match.group("title"))
            if title:
                return title[:255]

    for line in caption.splitlines():
        stripped_line = line.strip()
        if _is_bot_managed_line(stripped_line):
            continue

        title = _strip_edge_slashes(stripped_line)
        if title:
            return title[:255]

    return DEFAULT_MOVIE_TITLE


def normalize_movie_title(text: str | None) -> str:
    return extract_movie_title(text)


def format_file_size(size_bytes: int | None) -> str:
    if not size_bytes or size_bytes <= 0:
        return "Noma'lum"

    mb_size = size_bytes / (1024 * 1024)
    if mb_size >= 1024:
        gb_size = mb_size / 1024
        return f"{gb_size:.1f}GB"

    return f"{round(mb_size)}MB"


def build_storage_movie_caption(
    original_caption: str | None,
    title: str,
    code: str,
    file_size: int | None = None,
    channel_username: str | None = None,
    bot_username: str | None = None,
) -> str:
    metadata = extract_admin_metadata(original_caption, title=title)
    lines = [
        f"{MOVIE_CODE_ICON} {title}",
        "",
        *metadata,
    ]

    if metadata:
        lines.append("")

    lines.append(f"📥 Hajmi: {format_file_size(file_size)}")

    channel_line = _build_channel_line(channel_username)
    if channel_line:
        lines.extend(["", channel_line])

    lines.extend(["", f"{MOVIE_CODE_ICON} Kino kodi: {code}"])

    bot_line = _build_bot_username_line(bot_username)
    if bot_line:
        lines.extend(["", bot_line])

    return "\n".join(_compact_blank_lines(lines))


def build_user_movie_caption_from_storage(
    storage_caption: str | None,
    title: str,
    code: str | None = None,
    bot_username: str | None = None,
) -> str:
    metadata = extract_admin_metadata(storage_caption, keep_size=True, title=title)
    lines = [f"{MOVIE_CODE_ICON} {title}"]

    if metadata:
        lines.extend(["", *metadata])

    bot_line = _build_bot_username_line(bot_username)
    if bot_line:
        lines.extend(["", bot_line])

    return "\n".join(_compact_blank_lines(lines))


def extract_admin_metadata(
    caption: str | None,
    keep_size: bool = False,
    title: str | None = None,
) -> list[str]:
    if not caption:
        return []

    metadata_lines: list[str] = []
    for line in caption.splitlines():
        stripped_line = line.strip()

        if _is_bot_managed_line(stripped_line, keep_size=keep_size):
            continue
        if _is_duplicate_title_line(stripped_line, title):
            continue

        metadata_lines.append(line.rstrip())

    return _compact_blank_lines(metadata_lines)


def remove_movie_code_caption(caption: str | None) -> str | None:
    metadata = extract_admin_metadata(caption)
    return "\n".join(metadata).strip() or None


def append_movie_code_caption(caption: str | None, code: str) -> str:
    cleaned_caption = remove_movie_code_caption(caption)
    code_line = f"{MOVIE_CODE_ICON} Kino kodi: {code}"

    if cleaned_caption:
        return f"{cleaned_caption}\n\n{code_line}"

    return code_line


def build_movie_caption(movie_or_title, code: str | None = None, bot_username: str | None = None) -> str:
    if not isinstance(movie_or_title, str) and hasattr(movie_or_title, "title"):
        movie = movie_or_title
        title = getattr(movie, "title", None) or DEFAULT_MOVIE_TITLE
        movie_code = code or getattr(movie, "code", None)
        caption = getattr(movie, "caption", None)
        return build_user_movie_caption_from_storage(caption, title, movie_code, bot_username)

    title = (movie_or_title or DEFAULT_MOVIE_TITLE).strip()
    lines = [f"{MOVIE_CODE_ICON} {title}"]

    if code:
        lines.extend(["", f"{MOVIE_CODE_ICON} Kino kodi: {code}"])

    bot_line = _build_bot_username_line(bot_username)
    if bot_line:
        lines.extend(["", bot_line])

    return "\n".join(lines)


def remove_movie_info_caption(caption: str | None) -> str | None:
    return remove_movie_code_caption(caption)


def _is_bot_managed_line(line: str, keep_size: bool = False) -> bool:
    if not line:
        return False

    return bool(
        SLASH_TITLE_PATTERN.fullmatch(line)
        or MOVIE_TITLE_PREFIX_PATTERN.fullmatch(line)
        or MOVIE_CODE_LINE_PATTERN.fullmatch(line)
        or (not keep_size and MOVIE_SIZE_LINE_PATTERN.match(line))
        or MOVIE_CHANNEL_LINE_PATTERN.match(line)
        or BOT_USERNAME_LINE_PATTERN.match(line)
    )


def _build_channel_line(channel_username: str | None) -> str | None:
    username = (channel_username or "").strip()
    if not username:
        return None

    if not username.startswith("@"):
        username = f"@{username}"

    return f"Bizning kanal: {username}"


def _build_bot_username_line(bot_username: str | None) -> str | None:
    username = (bot_username or "").strip()
    if not username:
        return None

    if not username.startswith("@"):
        username = f"@{username}"

    return f"{BOT_USERNAME_ICON} {username}"
