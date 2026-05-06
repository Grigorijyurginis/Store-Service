import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def setup_logging() -> None:
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]

    # Заглушить встроенные uvicorn access-логи — HTTP-логи делаем сами через middleware
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)