from fastapi import FastAPI

from app.api.routes import analytics, health, tasks, users
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, latency_logging_middleware


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Telegram Learning Bot API", version="0.1.0")
    app.state.session_factory = AsyncSessionLocal
    app.middleware("http")(latency_logging_middleware)
    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(tasks.router)
    app.include_router(analytics.router)
    return app


app = create_app()
