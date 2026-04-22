from app.utils.movie_base_link import format_movie_base_open_line
from app.utils.datetime import format_local_datetime
from app.utils.movie_title import DEFAULT_MOVIE_TITLE, normalize_movie_title
from app.utils.text import safe_html


def _created_at_text(movie) -> str:
    return format_local_datetime(movie.created_at)


def build_movie_admin_preview(movie, movie_base, index: int | None = None) -> str:
    movie_title = getattr(movie, "title", None)
    movie_caption = getattr(movie, "caption", None)
    title_source = movie_caption if movie_title == DEFAULT_MOVIE_TITLE else movie_title or movie_caption
    title = normalize_movie_title(title_source)
    prefix = f"{index}. " if index is not None else ""

    return (
        f"{prefix}Kino nomi: {safe_html(title)}\n"
        f"🎬 Kino kodi: <code>{safe_html(movie.code)}</code>\n"
        f"Baza: {safe_html(movie_base.title)}\n"
        f"{format_movie_base_open_line(movie_base)}\n"
        f"Sana: {safe_html(_created_at_text(movie))}"
    )
