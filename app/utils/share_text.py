from urllib.parse import quote


def build_share_link(bot_username: str, code: str | None = None) -> str:
    username = (bot_username or "").strip().lstrip("@")
    link = f"https://t.me/{username}"
    payload = (code or "").strip()
    if payload:
        link = f"{link}?start={quote(payload)}"
    return link


def build_general_share_text(bot_username: str, referral_code: str | None = None) -> str:
    link = build_share_link(bot_username, referral_code)
    return (
        "🎬 Kino olish uchun qulay bot\n\n"
        "Kino kodini yuborib kerakli kinoni oling.\n\n"
        "📥 Kirish:\n"
        f"{link}"
    )


def build_movie_share_text(bot_username: str, movie_title: str, movie_code: str) -> str:
    title = " ".join((movie_title or "").strip().split()) or "Ushbu"
    link = build_share_link(bot_username, movie_code)
    return (
        f"🎬 \"{title}\" filmini olish uchun botga kiring\n\n"
        "📥 Kirish:\n"
        f"{link}"
    )
