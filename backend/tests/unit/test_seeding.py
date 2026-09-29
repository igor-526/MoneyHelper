import json
from pathlib import Path
from uuid import uuid4

from core.entities import Currency
from tests.fakes import InMemoryCurrencyRepository
from utils.seeding import SeedSource, seed_from_json

CURRENCY_ID = uuid4()
OTHER_CURRENCY_ID = uuid4()


def write_seed(path: Path, rows: list[dict[str, object]]) -> Path:
    file_path = path / "seed.json"
    file_path.write_text(json.dumps(rows), encoding="utf-8")
    return file_path


def make_source(path: Path) -> SeedSource[Currency]:
    return SeedSource(path=path, parse_row=Currency.model_validate)


async def test_seed_from_json_creates_records(tmp_path: Path) -> None:
    path = write_seed(
        tmp_path, [{"id": str(CURRENCY_ID), "code": "RUB", "name": "Российский рубль", "decimal_places": 2}]
    )
    repository = InMemoryCurrencyRepository()

    await seed_from_json(make_source(path), repository)

    items = await repository.list(limit=20, offset=0)
    assert [item.code for item in items] == ["RUB"]


async def test_repeated_run_is_idempotent(tmp_path: Path) -> None:
    path = write_seed(
        tmp_path, [{"id": str(CURRENCY_ID), "code": "RUB", "name": "Российский рубль", "decimal_places": 2}]
    )
    repository = InMemoryCurrencyRepository()

    await seed_from_json(make_source(path), repository)
    await seed_from_json(make_source(path), repository)

    assert await repository.count() == 1


async def test_changed_field_updates_existing_record(tmp_path: Path) -> None:
    repository = InMemoryCurrencyRepository()
    first_path = write_seed(tmp_path, [{"id": str(CURRENCY_ID), "code": "RUB", "name": "Рубль", "decimal_places": 2}])
    await seed_from_json(make_source(first_path), repository)

    second_path = write_seed(
        tmp_path, [{"id": str(CURRENCY_ID), "code": "RUB", "name": "Российский рубль", "decimal_places": 2}]
    )
    await seed_from_json(make_source(second_path), repository)

    items = await repository.list(limit=20, offset=0)
    assert len(items) == 1
    assert items[0].name == "Российский рубль"


async def test_record_removed_from_source_is_not_deleted(tmp_path: Path) -> None:
    repository = InMemoryCurrencyRepository()
    first_path = write_seed(
        tmp_path,
        [
            {"id": str(CURRENCY_ID), "code": "RUB", "name": "Российский рубль", "decimal_places": 2},
            {"id": str(OTHER_CURRENCY_ID), "code": "CNY", "name": "Китайский юань", "decimal_places": 2},
        ],
    )
    await seed_from_json(make_source(first_path), repository)

    second_path = write_seed(
        tmp_path, [{"id": str(CURRENCY_ID), "code": "RUB", "name": "Российский рубль", "decimal_places": 2}]
    )
    await seed_from_json(make_source(second_path), repository)

    assert await repository.count() == 2
