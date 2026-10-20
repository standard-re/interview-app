import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import structlog
from fastapi import Depends, FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from service_api.config import Settings, get_settings
from service_api.dependencies import cleanup_services, startup_services
from service_api.logging import configure_logging
from service_api.models.common import HealthResponse, VersionResponse
from service_api.routes.loans import router as loans_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    await startup_services()
    try:
        yield
    finally:
        await cleanup_services()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.environment)
    app = FastAPI(title="Service API", lifespan=lifespan)

    @app.middleware("http")
    async def log_request(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            )
            raise

        logger.info(
            "request_complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )
        return response

    @app.get(
        "/health",
        operation_id="health",
        include_in_schema=False,
    )
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/version", operation_id="version")
    async def version(
        current_settings: Annotated[Settings, Depends(get_settings)],
    ) -> VersionResponse:
        return VersionResponse(
            commit=current_settings.commit,
            release=current_settings.release,
        )

    app.include_router(loans_router)
    return app
