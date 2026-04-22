from app.utils.movie_caption import (
    DEFAULT_MOVIE_TITLE,
    build_user_movie_caption_from_storage,
    extract_movie_title,
    normalize_movie_title,
    remove_movie_code_caption,
)


def normalize_movie_caption(caption: str | None) -> str | None:
    return remove_movie_code_caption(caption)


def build_user_movie_caption(movie, bot_username: str | None = None) -> str:
    movie_title = getattr(movie, "title", None) or DEFAULT_MOVIE_TITLE
    movie_caption = getattr(movie, "caption", None)
    title = movie_title if movie_title != DEFAULT_MOVIE_TITLE else extract_movie_title(movie_caption)
    return build_user_movie_caption_from_storage(movie_caption, title, bot_username=bot_username)
