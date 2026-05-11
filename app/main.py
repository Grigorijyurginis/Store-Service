import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.config import settings
from app.database import Base, engine
from app.logging_config import setup_logging
from app.models import orm as _orm_models  # noqa: F401 — registers ORM classes with Base.metadata
from app.routers import health, orders, products
from app.metrics import instrumentator
from app.tracing import setup_tracing

setup_logging()
setup_tracing()
logger = logging.getLogger("store.http")
_startup_log = logging.getLogger("store")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _startup_log.info("startup", extra={"event": "startup"})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    _startup_log.info("shutdown", extra={"event": "shutdown"})


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Product catalog and order management. Designed for ELK observability.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
instrumentator.instrument(app).expose(app, include_in_schema=True)
FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "http_request",
        extra={
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


app.include_router(health.router)
app.include_router(products.router)
app.include_router(orders.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        extra={"event": "unhandled_exception", "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )

@app.get("/debug/error")
async def debug_error():
    raise RuntimeError("test 500 for logging demo")