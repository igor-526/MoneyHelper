from pathlib import Path

from core.entities import Currency
from repositories.currency import CurrencyRepository
from utils.seeding import SeedDefinition, SeedSource

CURRENCY_SEED_SOURCE = SeedSource(path=Path(__file__).parent / "currencies.json", parse_row=Currency.model_validate)

CURRENCY_SEED_DEFINITION = SeedDefinition(source=CURRENCY_SEED_SOURCE, repository_factory=CurrencyRepository)
