from app.core.config import PENDING_MOVIE_TTL_SECONDS
from app.repositories.pending_movie_request_repository import PendingMovieRequestRepository


async def set_pending_movie_code(session, user_id: int, code: str) -> None:
    repository = PendingMovieRequestRepository(session)
    await repository.set_pending_request(
        user_telegram_id=user_id,
        movie_code=code,
        ttl_seconds=PENDING_MOVIE_TTL_SECONDS,
    )


async def pop_pending_movie_code(session, user_id: int) -> str | None:
    repository = PendingMovieRequestRepository(session)
    return await repository.pop_valid_movie_code(user_id)


async def clear_pending_movie_code(session, user_id: int) -> bool:
    repository = PendingMovieRequestRepository(session)
    return await repository.delete_request(user_id)
