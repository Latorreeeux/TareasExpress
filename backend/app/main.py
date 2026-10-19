from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.errors import register_errors
from app.db.database import Database
from app.api.routes import router
from app.core.body_limit import BodyLimitMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(_):
        try:
            yield
        finally:
            database.dispose()

    api = FastAPI(title="Tareas Express", version="0.1.0", description="Solo desarrollo local: identidad declarada por cabeceras.", lifespan=lifespan)
    api.state.settings = settings
    api.state.db = database
    register_errors(api)
    api.include_router(router)
    api.add_middleware(BodyLimitMiddleware, limit=settings.max_request_bytes)
    if settings.cors_origins:
        api.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                           allow_methods=["GET", "POST", "PUT"],
                           allow_headers=["Content-Type", "X-Actor-Rol", "X-Actor-Id"])
    return api


app = create_app()
