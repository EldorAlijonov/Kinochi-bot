from sqlalchemy.exc import SQLAlchemyError


MOVIE_SCHEMA_MISMATCH_ADMIN_MESSAGE = (
    "Database schema mos emas: movies.title ustuni topilmadi. "
    "Iltimos, `alembic upgrade head` ni ishga tushiring yoki "
    "`migrations/002_add_movie_title.sql` patchini bajaring."
)


def is_movie_title_schema_mismatch(error: SQLAlchemyError) -> bool:
    error_text = repr(error)
    return (
        "UndefinedColumnError" in error_text
        and "movies.title" in error_text
        and "does not exist" in error_text
    )
