.PHONY: format lint test test-unit test-smoke test-infra

format:
	uv run ruff check . --fix
	uv run ruff format .

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src tests
	uv run flake8 src tests

# Все тесты, не требующие внешней инфраструктуры: unit + smoke
test:
	uv run pytest -m "not infrastructure"

test-unit:
	uv run pytest -m "not infrastructure and not smoke"

test-smoke:
	uv run pytest -m "smoke and not infrastructure"

test-infra:
	uv run pytest -m infrastructure
