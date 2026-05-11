import logging

from opentelemetry.trace import StatusCode

from app.exceptions import ConflictError, NotFoundError
from app.models.orm import Product as ProductORM
from app.repositories.product_repo import ProductRepository
from app.schemas.generated import Product, ProductCreate, ProductListResponse, ProductUpdate
from app.tracing import tracer

_log = logging.getLogger("store.products")


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self.repo = repo

    async def list_products(
        self,
        *,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        in_stock: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ProductListResponse:
        items, total = await self.repo.list(
            category=category,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            limit=limit,
            offset=offset,
        )
        return ProductListResponse(
            items=[self._to_schema(p) for p in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_product(self, product_id: int) -> Product:
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product", product_id)
        return self._to_schema(product)

    async def create_product(self, data: ProductCreate) -> Product:
        with tracer.start_as_current_span("product.create") as span:
            span.set_attribute("sku", data.sku or "")
            span.set_attribute("category", data.category or "")

            if data.sku is not None:
                if await self.repo.get_by_sku(data.sku) is not None:
                    span.set_status(StatusCode.ERROR, "sku_conflict")
                    raise ConflictError(f"Product with SKU '{data.sku}' already exists")
            product = await self.repo.create(data)
            span.set_attribute("product_id", product.id)
            _log.info(
                "product_created",
                extra={
                    "event": "product_created",
                    "product_id": product.id,
                    "sku": product.sku,
                    "category": product.category,
                    "price": float(product.price),
                },
            )
            return self._to_schema(product)

    async def update_product(self, product_id: int, data: ProductUpdate) -> Product:
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product", product_id)
        if data.sku is not None and data.sku != product.sku:
            if await self.repo.get_by_sku(data.sku) is not None:
                raise ConflictError(f"Product with SKU '{data.sku}' already exists")
        updated = await self.repo.update(product, data)
        return self._to_schema(updated)

    async def delete_product(self, product_id: int) -> None:
        with tracer.start_as_current_span("product.delete") as span:
            span.set_attribute("product_id", product_id)

            product = await self.repo.get_by_id(product_id)
            if product is None:
                span.set_status(StatusCode.ERROR, "product_not_found")
                raise NotFoundError("Product", product_id)
            count = await self.repo.count_order_items(product_id)
            if count > 0:
                span.set_status(StatusCode.ERROR, "has_order_items")
                raise ConflictError(
                    f"Product {product_id} is referenced by {count} order item(s) and cannot be deleted"
                )
            _log.info("product_deleted", extra={"event": "product_deleted", "product_id": product_id})
            await self.repo.delete(product)

    @staticmethod
    def _to_schema(orm: ProductORM) -> Product:
        return Product.model_validate(orm, from_attributes=True)