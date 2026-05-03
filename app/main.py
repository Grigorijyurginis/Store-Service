from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.models import orm as _orm_models  # noqa: F401 — registers ORM classes with Base.metadata
from app.routers import health, orders, products
from app.metrics import instrumentator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Product catalog and order management. Designed for ELK observability.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
instrumentator.instrument(app).expose(app, include_in_schema=True)

app.include_router(health.router)
app.include_router(products.router)
app.include_router(orders.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )