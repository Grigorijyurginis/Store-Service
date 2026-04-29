from app.exceptions import ConflictError, InsufficientStockError, InvalidStatusTransitionError, NotFoundError
from app.models.orm import Order as OrderORM
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.generated import Order, OrderCreate, OrderItem, OrderListResponse, OrderStatus, OrderStatusUpdate

# Allowed status transitions — terminal states map to empty sets
_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending":    frozenset({"confirmed", "cancelled"}),
    "confirmed":  frozenset({"processing", "cancelled"}),
    "processing": frozenset({"shipped", "cancelled"}),
    "shipped":    frozenset({"delivered"}),
    "delivered":  frozenset(),
    "cancelled":  frozenset(),
}


class OrderService:
    def __init__(self, order_repo: OrderRepository, product_repo: ProductRepository) -> None:
        self.order_repo = order_repo
        self.product_repo = product_repo

    async def list_orders(
        self,
        *,
        status: str | None = None,
        customer_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> OrderListResponse:
        items, total = await self.order_repo.list(
            status=status, customer_id=customer_id, limit=limit, offset=offset
        )
        return OrderListResponse(
            items=[self._to_schema(o) for o in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_order(self, order_id: int) -> Order:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        return self._to_schema(order)

    async def create_order(self, data: OrderCreate) -> Order:
        resolved_items: list[dict] = []
        for item in data.items:
            product = await self.product_repo.get_by_id(item.product_id)
            if product is None:
                raise NotFoundError("Product", item.product_id)
            if product.stock_quantity < item.quantity:
                raise InsufficientStockError(item.product_id, item.quantity, product.stock_quantity)
            product.stock_quantity -= item.quantity
            resolved_items.append(
                {"product_id": product.id, "quantity": item.quantity, "unit_price": product.price}
            )

        order = await self.order_repo.create(
            customer_id=data.customer_id,
            notes=data.notes,
            resolved_items=resolved_items,
        )
        return self._to_schema(order)

    async def update_order_status(self, order_id: int, data: OrderStatusUpdate) -> Order:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order", order_id)

        target = data.status.value
        if target not in _TRANSITIONS.get(order.status, frozenset()):
            raise InvalidStatusTransitionError(order.status, target)

        if target == "cancelled":
            await self._restore_stock(order)

        updated = await self.order_repo.set_status(order, target)
        return self._to_schema(updated)

    async def cancel_order(self, order_id: int) -> Order:
        return await self.update_order_status(order_id, OrderStatusUpdate(status=OrderStatus.cancelled))

    async def _restore_stock(self, order: OrderORM) -> None:
        for item in order.items:
            product = await self.product_repo.get_by_id(item.product_id)
            if product is not None:
                product.stock_quantity += item.quantity

    @staticmethod
    def _to_schema(orm: OrderORM) -> Order:
        return Order(
            id=orm.id,
            customer_id=orm.customer_id,
            status=OrderStatus(orm.status),
            total_amount=orm.total_amount,
            notes=orm.notes,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            items=[
                OrderItem(
                    id=oi.id,
                    product_id=oi.product_id,
                    product_name=oi.product.name if oi.product else None,
                    quantity=oi.quantity,
                    unit_price=oi.unit_price,
                )
                for oi in orm.items
            ],
        )