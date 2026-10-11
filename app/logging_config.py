import json
import logging
from datetime import datetime, timezone
from logging.config import dictConfig

from .config import LOG_LEVEL


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        fields = getattr(record, "fields", {})
        if isinstance(fields, dict):
            event.update(fields)

        return json.dumps(event, default=str)


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                },
            },
            "root": {
                "level": LOG_LEVEL,
                "handlers": ["console"],
            },
        }
    )