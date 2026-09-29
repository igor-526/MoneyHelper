import pytest
from pydantic import BaseModel, ValidationError

from core.schemas import IconName


class IconHolder(BaseModel):
    icon: IconName


def test_icon_name_accepts_known_icon() -> None:
    assert IconHolder(icon="wallet").icon == "wallet"


def test_icon_name_rejects_unknown_icon() -> None:
    with pytest.raises(ValidationError):
        IconHolder(icon="no-such-icon")
