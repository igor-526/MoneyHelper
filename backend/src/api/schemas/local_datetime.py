from datetime import datetime


def validate_local_datetime(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is not None:
        raise ValueError("Дата и время должны быть указаны без часового пояса")
    return value
