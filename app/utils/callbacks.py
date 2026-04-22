STALE_CALLBACK_MESSAGE = "Jarayon eskirgan, menyudan qayta oching."


def parse_callback_parts(data: str | None, min_parts: int = 1, separator: str = ":") -> list[str] | None:
    parts = (data or "").split(separator)
    if len(parts) < min_parts or any(part == "" for part in parts[:min_parts]):
        return None
    return parts


def parse_callback_int(
    data: str | None,
    index: int,
    default: int | None = None,
    separator: str = ":",
) -> int | None:
    parts = parse_callback_parts(data, min_parts=index + 1, separator=separator)
    if parts is None:
        return default

    try:
        return int(parts[index])
    except (TypeError, ValueError):
        return default


def normalize_page(value, min_value: int = 1) -> int:
    try:
        return max(min_value, int(value or min_value))
    except (TypeError, ValueError):
        return min_value


def normalize_offset(value, min_value: int = 0) -> int:
    try:
        return max(min_value, int(value or min_value))
    except (TypeError, ValueError):
        return min_value
