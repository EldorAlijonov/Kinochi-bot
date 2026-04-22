import re
import random

MOVIE_CODE_PATTERN = re.compile(r"^\d{4}$")
MIN_MOVIE_CODE = 1
MAX_MOVIE_CODE = 9999


def is_movie_code(value: str | None) -> bool:
    return bool(value and MOVIE_CODE_PATTERN.fullmatch(value.strip()))


def generate_next_movie_code(last_code: str | None) -> str:
    if not last_code:
        return "0001"

    return f"{int(last_code) + 1:04d}"


def generate_random_movie_code() -> str:
    return f"{random.randint(MIN_MOVIE_CODE, MAX_MOVIE_CODE):04d}"
