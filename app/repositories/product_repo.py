from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import OrderItem, Product
from app.schemas.generated import ProductCreate, ProductUpdate


class ProductRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, product_id: int) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        in_stock: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        filters = self._build_filters(category, min_price, max_price, in_stock)

        total = (await self.db.execute(select(func.count()).select_from(Product).where(*filters))).scalar_one()
        items = list((await self.db.execute(select(Product).where(*filters).limit(limit).offset(offset))).scalars())

        return items, total

    async def create(self, data: ProductCreate) -> Product:
        product = Product(**data.model_dump())
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def update(self, product: Product, data: ProductUpdate) -> Product:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self.db.delete(product)
        await self.db.flush()

    async def count_order_items(self, product_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(OrderItem).where(OrderItem.product_id == product_id)
        )
        return result.scalar_one()

    def _build_filters(
        self,
        category: str | None,
        min_price: float | None,
        max_price: float | None,
        in_stock: bool | None,
    ) -> list:
        filters = []
        if category is not None:
            filters.append(Product.category == category)
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)
        if in_stock is True:
            filters.append(Product.stock_quantity > 0)
        elif in_stock is False:
            filters.append(Product.stock_quantity == 0)
        return filters
