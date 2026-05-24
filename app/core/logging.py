import logging
import sys
from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import Request, Response

from app.core.config import get_settings
from app.repositories.logs import TechnicalLogRepository


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def latency_logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = perf_counter()
    response = await call_next(request)
    latency_ms = (perf_counter() - started) * 1000
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        try:
            async with session_factory() as session:
                await TechnicalLogRepository(session).create(
                    "api_request",
                    f"{request.method} {request.url.path} -> {response.status_code}",
                    latency_ms,
                    {"path": request.url.path},
                )
                await session.commit()
        except Exception:
            logging.getLogger(__name__).exception("Failed to write technical log")
    response.headers["X-Process-Time-ms"] = f"{latency_ms:.2f}"
    return response
