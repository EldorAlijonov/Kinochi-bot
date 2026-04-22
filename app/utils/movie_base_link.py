from app.utils.text import safe_html


def get_movie_base_url(movie_base) -> str | None:
    if movie_base.chat_username:
        return f"https://t.me/{movie_base.chat_username.lstrip('@')}"

    if movie_base.invite_link:
        return movie_base.invite_link

    return None


def format_movie_base_address(movie_base) -> str:
    if movie_base.chat_username:
        return safe_html(_normalize_public_username(movie_base.chat_username))

    if movie_base.invite_link:
        return f'<a href="{safe_html(movie_base.invite_link)}">Ochish</a>'

    return "Havola mavjud emas"


def format_movie_base_link(movie_base) -> str:
    url = get_movie_base_url(movie_base)
    if url:
        return f'<a href="{safe_html(url)}">Ochish</a>'

    return "Bazani ochish havolasi mavjud emas"


def format_movie_base_open_line(movie_base) -> str:
    url = get_movie_base_url(movie_base)
    if url:
        return f'Bazani <a href="{safe_html(url)}">Ochish</a>'

    return "Bazani ochish havolasi mavjud emas"


def _normalize_public_username(username: str) -> str:
    username = username.strip()
    if username.startswith("@"):
        return username

    return f"@{username}"
