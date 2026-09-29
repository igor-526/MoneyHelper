from typing import Annotated

from pydantic import AfterValidator

from core.icons import ALLOWED_ICONS


def _check_known_icon(value: str) -> str:
    if value not in ALLOWED_ICONS:
        raise ValueError(f"Unknown icon name: {value!r}")
    return value


IconName = Annotated[str, AfterValidator(_check_known_icon)]
