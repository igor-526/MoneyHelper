from typing import Annotated
from uuid import UUID

from pydantic import BeforeValidator


def split_ids(value: object) -> object:
    if isinstance(value, str):
        return value.split(",") if value else []
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        return value[0].split(",") if value[0] else []
    return value


OperationIds = Annotated[list[UUID], BeforeValidator(split_ids)]
