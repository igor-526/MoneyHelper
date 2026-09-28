from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from core.entities import Entity, TimestampMixin
from depends.providers import get_clock, get_id_generator
from tests.fakes import FixedClock, SequentialIdGenerator
from utils.clock import SystemClock
from utils.id_generator import UuidGenerator


def test_system_clock_returns_aware_utc_time() -> None:
    before = datetime.now(UTC)

    now = SystemClock().now()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    assert before <= now <= datetime.now(UTC)


def test_uuid_generator_returns_unique_v4() -> None:
    generator = UuidGenerator()

    ids = [generator.new() for _ in range(50)]

    assert len(set(ids)) == 50
    assert all(isinstance(value, UUID) and value.version == 4 for value in ids)


def test_fixed_clock_is_controlled_by_test() -> None:
    moment = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(moment)

    assert clock.now() == moment

    clock.advance(timedelta(hours=1))

    assert clock.now() == moment + timedelta(hours=1)


def test_sequential_id_generator_is_deterministic() -> None:
    first = [SequentialIdGenerator().new() for _ in range(2)]
    generator = SequentialIdGenerator()

    assert first[0] == first[1]
    assert generator.new() != generator.new()
    assert SequentialIdGenerator().new() == UUID(int=1)


def test_entity_requires_explicit_id() -> None:
    with pytest.raises(ValidationError):
        Entity()  # type: ignore[call-arg]


def test_timestamp_mixin_requires_explicit_created_at() -> None:
    with pytest.raises(ValidationError):
        TimestampMixin()  # type: ignore[call-arg]


def test_dependencies_provide_system_implementations() -> None:
    assert isinstance(get_clock(), SystemClock)
    assert isinstance(get_id_generator(), UuidGenerator)


def test_dependency_can_be_overridden_with_fake() -> None:
    from typing import Annotated

    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from core.protocols import Clock

    app = FastAPI()

    @app.get("/now")
    def now(clock: Annotated[Clock, Depends(get_clock)]) -> dict[str, str]:
        return {"now": clock.now().isoformat()}

    fixed = FixedClock(datetime(2026, 2, 3, tzinfo=UTC))
    app.dependency_overrides[get_clock] = lambda: fixed

    response = TestClient(app).get("/now")

    assert response.json() == {"now": fixed.now().isoformat()}
