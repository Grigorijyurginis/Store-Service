from app.exceptions import ConflictError, NotFoundError
from app.models.orm import Product as ProductORM
from app.repositories.product_repo import ProductRepository
from app.schemas.generated import Product, ProductCreate, ProductListResponse, ProductUpdate


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
        if data.sku is not None:
            if await self.repo.get_by_sku(data.sku) is not None:
                raise ConflictError(f"Product with SKU '{data.sku}' already exists")
        product = await self.repo.create(data)
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
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product", product_id)
        count = await self.repo.count_order_items(product_id)
        if count > 0:
            raise ConflictError(
                f"Product {product_id} is referenced by {count} order item(s) and cannot be deleted"
            )
        await self.repo.delete(product)

    @staticmethod
    def _to_schema(orm: ProductORM) -> Product:
        return Product.model_validate(orm, from_attributes=True)