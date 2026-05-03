from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator


instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_group_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)

orders_created_total = Counter(
    "store_orders_created_total",
    "Total number of orders created",
    ["initial_status"]
)

insufficient_stock_total = Counter(
    "store_insufficient_stock_total",
    "Total number of order rejections due to insufficient stock",
    ["product_id"],
)
