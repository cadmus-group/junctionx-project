"""GridTrace API application entrypoint."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from gridtrace_api import __version__
from gridtrace_api.config import get_settings
from gridtrace_api.logging import configure_logging
from gridtrace_api.modules.assets.router import router as assets_router
from gridtrace_api.modules.auth.router import router as auth_router
from gridtrace_api.modules.customers.router import router as customers_router
from gridtrace_api.modules.dashboard.router import router as dashboard_router
from gridtrace_api.modules.gis.router import router as gis_router
from gridtrace_api.modules.health.router import router as health_router
from gridtrace_api.modules.inspections.router import router as inspections_router
from gridtrace_api.modules.models.router import router as models_router
from gridtrace_api.shared.errors import register_exception_handlers


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="GridTrace API",
        version=__version__,
        description="Authoritative operational API for non-technical loss detection.",
        default_response_class=ORJSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    api = APIRouter(prefix="/api/v1")
    api.include_router(health_router)
    api.include_router(auth_router)
    api.include_router(dashboard_router)
    api.include_router(gis_router)
    api.include_router(assets_router)
    api.include_router(customers_router)
    api.include_router(inspections_router)
    api.include_router(models_router)
    app.include_router(api)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"name": "GridTrace API", "version": __version__, "docs": "/docs"}

    return app


app = create_app()
