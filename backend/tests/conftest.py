import os
from pathlib import Path

import pytest

from tests.testing_settings import DatabaseTestSettings, apply_test_database_env

os.environ["SENTRY_ENABLED"] = "false"
os.environ["CORS_ORIGINS"] = "https://app.example.com"
apply_test_database_env(os.environ, DatabaseTestSettings())

INFRASTRUCTURE_DIR = Path(__file__).parent / "infrastructure"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.is_relative_to(INFRASTRUCTURE_DIR):
            item.add_marker(pytest.mark.infrastructure)
