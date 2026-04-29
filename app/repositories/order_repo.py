from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm import Order, OrderItem


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, order_id: int) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        status: str | None = None,
        customer_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Order], int]:
        filters = []
        if status is not None:
            filters.append(Order.status == status)
        if customer_id is not None:
            filters.append(Order.customer_id == customer_id)

        total = (await self.db.execute(select(func.count()).select_from(Order).where(*filters))).scalar_one()
        items = list(
            (
                await self.db.execute(
                    select(Order)
                    .options(selectinload(Order.items).selectinload(OrderItem.product))
                    .where(*filters)
                    .limit(limit)
                    .offset(offset)
                )
            ).scalars()
        )

        return items, total

    async def create(
        self,
        *,
        customer_id: str,
        notes: str | None,
        resolved_items: list[dict],
    ) -> Order:
        order = Order(customer_id=customer_id, status="pending", notes=notes, total_amount=0.0)
        self.db.add(order)
        await self.db.flush()

        total = 0.0
        for item_data in resolved_items:
            oi = OrderItem(
                order_id=order.id,
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
            )
            total += item_data["quantity"] * item_data["unit_price"]
            self.db.add(oi)

        order.total_amount = round(total, 2)
        await self.db.flush()

        return await self.get_by_id(order.id)  # type: ignore[return-value]

    async def set_status(self, order: Order, status: str) -> Order:
        order.status = status
        await self.db.flush()
        return await self.get_by_id(order.id)  # type: ignore[return-value]

    async def delete(self, order: Order) -> None:
        await self.db.delete(order)
        await self.db.flush()