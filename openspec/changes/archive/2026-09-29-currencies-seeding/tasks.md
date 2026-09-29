## 1. Настройки

- [x] 1.1 Добавить в `Settings` поле `seeding_enabled: bool` (`SEEDING_ENABLED`, по умолчанию `true`)
- [x] 1.2 Обновить `backend/.env` и `backend/.env.example`; unit-тест настройки (дефолт и чтение из окружения)

## 2. Ядро (core)

- [x] 2.1 Сущность `Currency` (`core/entities/currency.py`): `code`, `name`, `decimal_places`
- [x] 2.2 Протокол `CurrencyRepository` (`core/protocols/repositories/currency_repository.py`): `list`, `count`,
      `upsert_many`; экспорт в `core/protocols/__init__.py`
- [x] 2.3 `CurrencyService` (`core/services/currency.py`): `list_currencies(limit, offset) -> (items, total)`
- [x] 2.4 `FakeCurrencyRepository` в `tests/fakes/` (upsert-семантика: добавление, обновление по `id`, без удаления);
      unit-тесты `CurrencyService` на fake

## 3. Механизм сидирования (переиспользуемый)

- [x] 3.1 `utils/seeding.py`: `SeedSource[T]`, `seed_from_json` (DB-агностичная часть: чтение JSON, валидация,
      вызов `repository.upsert_many`)
- [x] 3.2 Unit-тесты `seed_from_json` на `FakeCurrencyRepository`: идемпотентность повторного запуска, обновление
      изменённого поля по существующему `id`, отсутствие удаления записи, чей `id` убрали из набора
- [x] 3.3 `utils/seeding.py`: `SeedDefinition`, `run_seeding(engine, definitions)` — advisory lock
      (`pg_advisory_lock`/`pg_advisory_unlock` по ключу `hashtext('moneyhelper:seeding')`) вокруг вызова
      `seed_from_json` для всех определений, одна транзакция на запуск

## 4. Инфраструктура (БД)

- [x] 4.1 Таблица `models/currency.py` (`id`, `code`, `name`, `decimal_places`, ограничения `CHECK`); импорт в
      `models/__init__.py`
- [x] 4.2 Миграция Alembic (только схема, без данных): `create_table("currencies")` с теми же ограничениями,
      `downgrade` удаляет таблицу
- [x] 4.3 `repositories/currency.py`: реализация `CurrencyRepository` на SQLAlchemy Core (`list`/`count` —
      `select`/`func.count`; `upsert_many` — multi-row `INSERT ... ON CONFLICT (id) DO UPDATE`)
- [x] 4.4 `src/seeds/currencies.json`: три валюты (CNY, RUB, USDT), `decimal_places=2`, зафиксированные явные UUID;
      `seeds/currencies.py` с `SeedSource`/`SeedDefinition` для валют
- [x] 4.5 Infrastructure-тесты `CurrencyRepository` (`tests/infrastructure/`): добавление, чтение, пагинация,
      `upsert_many` — вставка новых, обновление изменённых по `id`, отсутствие удаления при неполном наборе

## 5. API

- [x] 5.1 `api/schemas/currency.py`: `CurrencyOut` (`id`, `code`, `name`, `decimal_places`)
- [x] 5.2 `depends/currency.py`: `get_currency_repository`, `get_currency_service`
- [x] 5.3 `api/currencies.py`: `GET /api/currencies` (`PageParams` → `Page[CurrencyOut]`, сортировка по `code`);
      подключение роутера в `main.py`
- [x] 5.4 API/smoke-тесты: `/api/currencies` зарегистрирован (дополнение к списку в smoke-тесте), список с
      дефолтной и явной пагинацией, ошибка валидации параметров (400)

## 6. Подключение сидирования к запуску приложения

- [x] 6.1 `main.py`: вызов `run_seeding(engine, SEED_DEFINITIONS)` в `lifespan` при `settings.seeding_enabled`
- [x] 6.2 `tests/conftest.py`: `os.environ["SEEDING_ENABLED"] = "false"` рядом с существующими переопределениями
      окружения — `make test`/голый `pytest` не обращаются к БД
- [x] 6.3 Infrastructure-тест `run_seeding` целиком: после запуска в БД три ожидаемые валюты, повторный запуск не
      создаёт дублей
- [x] 6.4 Infrastructure-тест advisory lock: соединение удерживает `pg_advisory_lock` с ключом сидирования →
      `pg_try_advisory_lock` тем же ключом с другого соединения возвращает `false`; после освобождения — `true`

## 7. Документация и проверка

- [x] 7.1 Обновить `README.md`/`backend/README.md` при необходимости (новая переменная окружения, команда сидирования
      не требуется отдельно — работает автоматически в `lifespan`)
- [x] 7.2 QualityGate: `make format`, `make lint`, `make test`, `make test-infra`
