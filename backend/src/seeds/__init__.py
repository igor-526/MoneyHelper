from typing import Any

from seeds.currencies import CURRENCY_SEED_DEFINITION
from utils.seeding import SeedDefinition

SEED_DEFINITIONS: list[SeedDefinition[Any]] = [CURRENCY_SEED_DEFINITION]

__all__ = ["SEED_DEFINITIONS"]
