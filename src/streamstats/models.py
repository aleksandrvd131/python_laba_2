from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .errors import Invalid_event, Invalid_time

ALLOWED_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


@dataclass(slots=True, frozen=True)
class Event:
    timestamp: datetime
    level: str
    source: str
    message: str

    @classmethod
    def scanf(
        cls,
        data: dict[str, Any],
        *,
        file_path: str | None = None,
        line_number: int | None = None,
    ):
        for field in ("timestamp", "level", "source", "message"):
            if field not in data or data[field] is None:
                raise Invalid_event(
                    f"Поле '{field}' отсутствует или не заполнено",
                    file_path=file_path,
                    line_number=line_number,
                )

        t_raw = data["timestamp"]
        if not isinstance(t_raw, str):
            raise Invalid_event(
                "Поле 'timestamp' должно быть строкой ISO 8601",
                file_path=file_path,
                line_number=line_number,
            )
        try:
            parsed_time = datetime.fromisoformat(t_raw)
        except (ValueError, TypeError):
            raise Invalid_time(
                f"Некорректная дата '{t_raw}'",
                file_path=file_path,
                line_number=line_number,
            )

        level = data["level"]
        if not isinstance(level, str) or level not in ALLOWED_LEVELS:
            raise Invalid_event(
                f"Уровень '{level}' недопустим, разрешены: {set(ALLOWED_LEVELS)}",
                file_path=file_path,
                line_number=line_number,
            )

        source = data["source"]
        if not isinstance(source, str) or not source.strip():
            raise Invalid_event(
                "Поле 'source' должно быть непустой строкой",
                file_path=file_path,
                line_number=line_number,
            )

        message = data["message"]
        if not isinstance(message, str):
            raise Invalid_event(
                "Поле 'message' должно быть строкой",
                file_path=file_path,
                line_number=line_number,
            )

        return cls(
            timestamp=parsed_time,
            level=level,
            source=source.strip(),
            message=message,
        )
