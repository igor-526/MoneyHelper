from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.errors import register_error_handlers
from core.schemas import Page, PageParams


def test_page_params_defaults() -> None:
    params = PageParams()

    assert (params.limit, params.offset) == (20, 0)


@pytest.mark.parametrize("data", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_page_params_reject_out_of_range(data: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        PageParams(**data)


def test_page_contains_pagination_fields() -> None:
    page = Page[int](items=[1, 2], total=5, limit=2, offset=0)

    assert page.model_dump() == {"items": [1, 2], "total": 5, "limit": 2, "offset": 0}


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/items")
    def items(params: Annotated[PageParams, Query()]) -> Page[int]:
        return Page[int](items=list(range(params.limit))[:2], total=2, limit=params.limit, offset=params.offset)

    return TestClient(app)


def test_query_defaults() -> None:
    response = _client().get("/items")

    assert response.status_code == 200
    assert (response.json()["limit"], response.json()["offset"]) == (20, 0)


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_query_out_of_range_returns_400(query: str) -> None:
    response = _client().get(f"/items?{query}")

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], list)
