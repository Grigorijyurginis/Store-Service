class StoreException(Exception):
    pass


class NotFoundError(StoreException):
    def __init__(self, resource: str, resource_id: int | str) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} with id={resource_id} not found")


class ConflictError(StoreException):
    pass


class InsufficientStockError(StoreException):
    def __init__(self, product_id: int, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: "
            f"requested={requested}, available={available}"
        )


class InvalidStatusTransitionError(StoreException):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition order from '{current}' to '{target}'")