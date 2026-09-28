## 1. Провайдеры времени и идентификаторов

- [x] 1.1 Добавить протоколы `Clock` (`core/protocols/clock.py`) и `IdGenerator` (`core/protocols/id_generator.py`), экспортировать в `core/protocols/__init__.py`
- [x] 1.2 Добавить реализации `SystemClock` и `UuidGenerator` в `utils/`
- [x] 1.3 Добавить `depends/providers.py` с `get_clock` и `get_id_generator`
- [x] 1.4 Убрать `default_factory` у `Entity.id` и `TimestampMixin.created_at`; проверить `grep` по `Entity(` и `TimestampMixin`, что использований без явных значений нет
- [x] 1.5 Добавить `tests/fakes/` с `FixedClock` (`advance()`) и `SequentialIdGenerator`
- [x] 1.6 Написать unit-тесты `SystemClock`, `UuidGenerator`, fake-реализаций и ошибки при создании сущности без `id`

## 2. Соглашения API

- [x] 2.1 Добавить тип `Money` в `core/schemas/money.py` (`Decimal`, 24 цифры, 8 знаков, без NaN/Infinity, JSON-строка)
- [x] 2.2 Добавить `MONEY = Numeric(24, 8)` в `models/types.py`
- [x] 2.3 Добавить `PageParams` и `Page[T]` в `core/schemas/pagination.py`
- [x] 2.4 Добавить `NotFoundError`, `AuthenticationError`, `PermissionDeniedError` в `core/exceptions/base.py` и экспортировать
- [x] 2.5 Исправить обработчик ошибок валидации в `main.py` (`jsonable_encoder`)
- [x] 2.6 Добавить `UnhandledErrorMiddleware` в `utils/` (лог, `sentry_sdk.capture_exception`, ответ 500 `{"detail": "Internal server error"}`) и подключить в `main.py` до CORS, чтобы он оказался внутри него
- [x] 2.7 Написать unit-тесты `Money` (сериализация, лишние знаки, NaN/Infinity), `PageParams`/`Page`, кодов ошибок 400/401/403/404/405/409 (JSON с `detail`), валидации с исключением в `ctx`, ответа 500 и вызова лога и Sentry

## 3. CORS

- [x] 3.1 Добавить `Settings.cors_origins` (`CORS_ORIGINS`, значения через запятую, `NoDecode`) с валидатором формата (запрет `*`, схемы и пути)
- [x] 3.2 Добавить `utils/configure_cors.py` и вызвать его в `main.py` (только при непустом списке)
- [x] 3.3 Добавить `CORS_ORIGINS` в `backend/.env.example`
- [x] 3.4 Заменить тест `test_template_runtime_has_no_cors_configuration_or_headers` тестами разрешённого origin, preflight и чужого origin
- [x] 3.5 Написать тесты CORS-заголовков на ответах 400, 404 и 500 с разрешённого origin (500 — через тестовый маршрут, бросающий исключение)
- [x] 3.6 Написать unit-тесты разбора и валидации `CORS_ORIGINS`

## 4. Тестовая БД, разделение тестов и fake-репозитории

- [x] 4.1 В начале `tests/conftest.py` до импорта `settings` принудительно задавать `POSTGRES_DB` из `TEST_POSTGRES_DB` (по умолчанию `app_test`), а также `POSTGRES_HOST`/`POSTGRES_PORT` из `TEST_POSTGRES_HOST`/`TEST_POSTGRES_PORT`, если они заданы
- [x] 4.2 Создать `tests/infrastructure/` с `conftest.py`: автоматический маркер `infrastructure` (`pytest_collection_modifyitems`) и все фикстуры БД только здесь
- [x] 4.3 Session-фикстура: проверка суффикса `_test`, создание БД через служебную БД `postgres`, `alembic upgrade head`; понятное сообщение об ошибке, если БД недоступна
- [x] 4.4 Фикстура сессии с внешней транзакцией, `create_savepoint` и откатом; engine с `NullPool`
- [x] 4.5 Написать infrastructure-тесты: миграции применены (`alembic_version`), откат отменяет запись, отказ при недопустимом имени БД
- [x] 4.6 В `pyproject.toml` добавить `-m "not infrastructure"` в `addopts`; в `backend/Makefile` для `test-infra` явно передавать `-m infrastructure`; проверить, что `make test` и голый `pytest` проходят без БД, а `make test-infra` без БД падает с понятной ошибкой
- [x] 4.7 Добавить `tests/fakes/repository.py` с `InMemoryRepository` и unit-тесты (`get` возвращает `None`, `list` со срезом)
- [x] 4.8 Добавить `TEST_POSTGRES_DB`, `TEST_POSTGRES_HOST`, `TEST_POSTGRES_PORT` и `CORS_ORIGINS` в `backend/.env.example` и локальный `backend/.env` (выполнено вручную до apply)

## 5. CI и конфигурация БД

- [x] 5.1 Добавить `.github/workflows/ci.yml`: job `quality` (`uv sync`, `make lint`, `make test`, без сервисов) и job `infrastructure` (сервис `postgres:16`, переменные `POSTGRES_*`, `make test-infra`); без деплоя
- [x] 5.2 Заменить `POSTGRES_NAME` на `POSTGRES_DB` в `.docker-compose/.env` и `.docker-compose/docker-compose.infra.yml`; проверить `grep`, что `POSTGRES_NAME` нигде не осталось (выполнено вручную до apply)
- [x] 5.3 Привести версию PostgreSQL в `backend/README.md` к фактической (16) (выполнено вручную до apply)

## 6. Документация

- [x] 6.1 Обновить `AGENTS.md`: `Clock`/`IdGenerator`, тип денег, пагинация, формат ошибок и его доставка до frontend (в том числе 500 с CORS), разделение тестов и CI, fakes
- [x] 6.2 Обновить `README.md` и `backend/README.md`: `CORS_ORIGINS`, `TEST_POSTGRES_DB`, `POSTGRES_DB`, запуск `make test-infra`, CI

## 7. QualityGate

- [x] 7.1 Выполнить `make format`
- [x] 7.2 Выполнить `make lint` и устранить замечания
- [x] 7.3 Выполнить `make test` (unit и smoke) при остановленном PostgreSQL
- [x] 7.4 Выполнить `make test-infra` на поднятом PostgreSQL (`make infra`)
