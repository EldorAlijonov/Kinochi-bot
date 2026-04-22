from app.utils.share_text import build_share_link


def build_movie_deep_link(bot_username: str, movie_code: str) -> str:
    return build_share_link(bot_username, movie_code)
