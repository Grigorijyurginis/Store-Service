from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import ConflictError, InsufficientStockError, InvalidStatusTransitionError, NotFoundError
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.generated import Order, OrderCreate, OrderListResponse, OrderStatus, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def _svc(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db), ProductRepository(db))


@router.get("", response_model=OrderListResponse)
async def list_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    customer_id: str | None = Query(None),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    svc: OrderService = Depends(_svc),
) -> OrderListResponse:
    return await svc.list_orders(
        status=status_filter.value if status_filter else None,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, svc: OrderService = Depends(_svc)) -> Order:
    try:
        return await svc.create_order(data)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": str(exc)}) from exc
    except InsufficientStockError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "error": "insufficient_stock",
                "message": str(exc),
                "details": {"product_id": exc.product_id, "requested": exc.requested, "available": exc.available},
            },
        ) from exc


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: int, svc: OrderService = Depends(_svc)) -> Order:
    try:
        return await svc.get_order(order_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": str(exc)}) from exc


@router.patch("/{order_id}/status", response_model=Order)
async def update_order_status(order_id: int, data: OrderStatusUpdate, svc: OrderService = Depends(_svc)) -> Order:
    try:
        return await svc.update_order_status(order_id, data)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": str(exc)}) from exc
    except (InvalidStatusTransitionError, ConflictError) as exc:
        detail = {"error": "invalid_transition", "message": str(exc)}
        if isinstance(exc, InvalidStatusTransitionError):
            detail["details"] = {"current": exc.current, "target": exc.target}
        raise HTTPException(status.HTTP_409_CONFLICT, detail=detail) from exc


@router.delete("/{order_id}", response_model=Order)
async def cancel_order(order_id: int, svc: OrderService = Depends(_svc)) -> Order:
    try:
        return await svc.cancel_order(order_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": str(exc)}) from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "error": "invalid_transition",
                "message": str(exc),
                "details": {"current": exc.current, "target": exc.target},
            },
        ) from exc
