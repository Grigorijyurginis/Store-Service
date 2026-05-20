from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import ConflictError, NotFoundError
from app.repositories.product_repo import ProductRepository
from app.schemas.generated import Product, ProductCategory, ProductCreate, ProductListResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def _svc(db: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))


@router.get("", response_model=ProductListResponse)
async def list_products(
    category: ProductCategory | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    in_stock: bool | None = Query(None),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    svc: ProductService = Depends(_svc),
) -> ProductListResponse:
    return await svc.list_products(
        category=category.value if category else None,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, svc: ProductService = Depends(_svc)) -> Product:
    try:
        return await svc.create_product(data)
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"error": "conflict", "message": str(exc)}) from exc


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int, svc: ProductService = Depends(_svc)) -> Product:
    try:
        return await svc.get_product(product_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": str(exc)}) from exc


@router.put("/{product_id}", response_model=Product)
async def update_product(product_id: int, data: ProductUpdate, svc: ProductService = Depends(_svc)) -> Product:
    try:
        return await svc.update_product(product_id, data)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": str(exc)}) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"error": "conflict", "message": str(exc)}) from exc


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, svc: ProductService = Depends(_svc)) -> None:
    try:
        await svc.delete_product(product_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": str(exc)}) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"error": "conflict", "message": str(exc)}) from exc
