## Context

Backend сейчас — пустой шаблон: `/health`, `AppError` → `ClientError` → `AlreadyExistsError`, пустые пакеты слоёв,
глобальные `settings`, `engine` и `get_session` в `utils/database.py`, одна пустая миграция. Есть два места, где
шаблон нарушает правила SOLID из AGENTS.md и мешает дальнейшим этапам:

- `Entity.id` и `TimestampMixin.created_at` имеют `default_factory` (`uuid4()`, `datetime.now(UTC)`) — сущности сами
  обращаются к источнику времени и идентификаторов, поэтому тесты недетерминированы, а `core` жёстко связан с реализацией.
- Обработчик ошибок валидации отдаёт `exc.errors()` напрямую: если в `ctx` лежит исключение (`ValueError` из
  валидатора), `JSONResponse` падает при сериализации.

Ограничения: Python 3.14, FastAPI, SQLAlchemy Core + asyncpg, Alembic; frontend будет на другом origin (same-site) и
использовать cookies; `make test` не должен требовать БД; QualityGate — `make format`, `make lint`, `make test`.

## Goals / Non-Goals

**Goals:**
- Дать последующим этапам готовые абстракции (`Clock`, `IdGenerator`), тип денег, контракты пагинации и ошибок.
- Разрешить CORS для frontend строго по списку origin с credentials.
- Дать воспроизводимую тестовую БД для `make test-infra`, не затрагивающую БД разработки.
- Дать fake-реализации, чтобы unit-тесты сервисов не требовали БД.

**Non-Goals:**
- Пользователи, JWT, cookies, проверка `Origin` (задача 005), сидирование (006), iconpack (007).
- Таблицы бизнес-сущностей и миграции.
- Валидация точности сумм под конкретную валюту.

## Decisions

### 1. `Clock` и `IdGenerator` за протоколами; сущности без default-фабрик
- `core/protocols/clock.py`: `Clock.now() -> datetime` (aware, UTC). `core/protocols/id_generator.py`: `IdGenerator.new() -> UUID`.
- Реализации `SystemClock` и `UuidGenerator` (uuid4) лежат в `utils/` (инфраструктура), в `depends/providers.py` —
  функции `get_clock` и `get_id_generator`.
- Из `Entity` и `TimestampMixin` убираем `default_factory`: `id` и `created_at` передаются явно (их задаёт сервис через
  провайдеры). Это принудительно проводит зависимости через DI, а не «по договорённости».
- Fake: `FixedClock` (фиксированное время, `advance()`) и `SequentialIdGenerator` (детерминированная последовательность
  UUID) в `tests/fakes/`.
- *Альтернатива:* оставить `default_factory` и подменять `uuid4` monkeypatch'ем — отвергнуто: скрытая зависимость, нарушение D.

### 2. Деньги: `Decimal` в `core`, `NUMERIC(24, 8)` в БД, строка в JSON
- Общая аннотация `Money` в `core/schemas/money.py`: `Decimal` с `max_digits=24`, `decimal_places=8`,
  `allow_inf_nan=False`; в JSON сериализуется строкой (без потери точности, независимо от парсера frontend).
- Тип столбца `MONEY = Numeric(24, 8)` в `models/types.py` для всех будущих таблиц.
- Точность 8 знаков покрывает USDT (6), CNY/RUB (2) и запас; строгость по конкретной валюте добавим на этапе операций.
- *Альтернатива:* целые «минорные единицы» (копейки) — отвергнуто: у валют разное число знаков, усложняет курсы.
  *`float`* запрещён правилами проекта.

### 3. Пагинация: `limit`/`offset`
- `core/schemas/pagination.py`: `PageParams` (`limit` 1..100, по умолчанию 20; `offset` ≥ 0, по умолчанию 0) и
  универсальный `Page[T]` (`items`, `total`, `limit`, `offset`).
- Роутеры получают параметры как `Annotated[PageParams, Query()]` (FastAPI принимает pydantic-модель как набор query-параметров),
  поэтому `core` не импортирует FastAPI.
- Нарушение границ — ошибка валидации (400, как принято в проекте).
- *Альтернатива:* cursor-пагинация — отвергнута: списки пользователя небольшие, offset проще для frontend и аналитики.

### 4. Формат ошибок и их доставка до frontend
- Единое тело `{"detail": <str | list>}`; статус-код — основной признак для клиента. Frontend по каждой ошибке
  (400, 401, 403, 404, 409, 500, а также сетевой сбой) показывает toast и обрабатывает её в каждом действии
  (требование задачи 003); поэтому ответ с ошибкой обязан дойти до браузера читаемым.
- Иерархия в `core/exceptions/base.py`: `ClientError` (400) → `AlreadyExistsError` (409), `NotFoundError` (404),
  `AuthenticationError` (401), `PermissionDeniedError` (403). `NotFoundError` добавляем сразу: он нужен каждому
  следующему этапу.
- Ошибки валидации остаются с кодом 400; тело собирается через `jsonable_encoder`, чтобы `ctx` с исключениями
  сериализовался.
- 500: обработчик `@app.exception_handler(Exception)` **не подходит**. Starlette выполняет его в
  `ServerErrorMiddleware`, которая стоит снаружи `CORSMiddleware`, поэтому ответ 500 остаётся без CORS-заголовков, и
  браузер отдаёт frontend лишь сетевую ошибку без статуса: toast «ошибка сервера» показать нельзя.
  Вместо этого — внутренний ASGI-middleware `UnhandledErrorMiddleware` (`utils/`), который стоит *внутри* CORS:
  ловит необработанное исключение, пишет его в лог (`logger.exception`), отправляет в Sentry
  (`sentry_sdk.capture_exception`, no-op при выключенном Sentry) и возвращает `500` с
  `{"detail": "Internal server error"}` без деталей. Порядок в `main.py`: сначала добавляется
  `UnhandledErrorMiddleware`, затем CORS (последний добавленный — самый внешний).
- 404 (несуществующий маршрут, `NotFoundError`), 400, 401, 403, 409 обрабатываются `ExceptionMiddleware`, которая уже
  внутри CORS, поэтому получают CORS-заголовки без дополнительных мер; это закрепляется тестами.
- Сообщения 401 не раскрывают причину (правило для этапа 005).
- *Альтернатива:* обработчик `Exception` + ручное добавление CORS-заголовков — отвергнуто: дублирует политику CORS
  в двух местах.

### 5. CORS
- `Settings.cors_origins: list[str]` читается из `CORS_ORIGINS` (значения через запятую, `NoDecode` + валидатор).
  Пустой список — CORS не включается.
- Валидатор отклоняет `*`, значения без схемы и с путём; допускает только `scheme://host[:port]`.
- `utils/configure_cors.py::configure_cors(app)` (по образцу `configure_sentry`) добавляет `CORSMiddleware` с
  `allow_credentials=True`, методами `GET/POST/PUT/PATCH/DELETE/OPTIONS`, заголовком `Content-Type`.
- CORS — политика браузера; защита от CSRF (проверка `Origin` на небезопасных методах) остаётся в задаче 005 и
  будет использовать тот же `settings.cors_origins`.
- Тест шаблона «CORS отсутствует» заменяется тестами: разрешённый origin (в том числе preflight) получает
  `access-control-allow-origin` и `access-control-allow-credentials`, чужой — нет.

### 6. Тестовая БД и разделение тестов
- Три набора: **unit** (`tests/` без БД), **smoke** (`tests/smoke/`, in-process, без БД, маркер `smoke`) и
  **infrastructure** (`tests/infrastructure/`, нужна БД).
- Каталог `tests/infrastructure/` получает маркер `infrastructure` автоматически (`pytest_collection_modifyitems`),
  забыть его нельзя; фикстуры БД определены только в `tests/infrastructure/conftest.py`, поэтому unit- и smoke-тесты не
  могут случайно потребовать БД.
- В `pyproject.toml` `addopts` содержит `-m "not infrastructure"`: голый `pytest`, IDE и CI по умолчанию не требуют БД.
  `make test-infra` явно передаёт `-m infrastructure` (последний `-m` побеждает). Если БД недоступна, `make test-infra`
  падает с понятным сообщением, а не пропускает тесты молча.
- CI (`.github/workflows/ci.yml`): job `quality` — `make lint` и `make test` без сервисов (поэтому любое скрытое
  требование БД в unit/smoke-тестах ломает CI сразу); job `infrastructure` — сервисный контейнер `postgres:16`,
  переменные `POSTGRES_*` и `make test-infra`. Деплой в workflow не входит.
- `tests/conftest.py` в самом начале, до импорта `settings`, принудительно задаёт `POSTGRES_DB` из
  `TEST_POSTGRES_DB` (по умолчанию `app_test`); при наличии `TEST_POSTGRES_HOST` и `TEST_POSTGRES_PORT` переопределяет
  также хост и порт (в `backend/.env` хост — имя контейнера `moneyhelper-db`, доступное только внутри docker-сети, а с
  хоста БД видна как `localhost:5471`). Так тесты по построению не могут обратиться к БД разработки; пользователь и пароль
  берутся из `.env`.
- Фикстура (session, только для infrastructure-тестов): проверяет, что имя БД оканчивается на `_test`, подключается к
  служебной БД `postgres`, создаёт тестовую БД при отсутствии и применяет `alembic upgrade head`
  (синхронная фикстура: `env.py` использует `asyncio.run`).
- Изоляция тестов: соединение с внешней транзакцией и `AsyncSession(join_transaction_mode="create_savepoint")`, откат
  после теста. Engine в фикстуре создаётся с `NullPool`, а не глобальный: пул asyncpg нельзя делить между
  event loop разных тестов.
- Пример infrastructure-теста: миграции применены (`alembic_version`), откат действительно отменяет запись.
- *Альтернатива:* testcontainers — отвергнуто: добавляет зависимость и требует Docker в каждом запуске, тогда как
  инфраструктурный PostgreSQL уже поднимается через `make infra`.

### 7. Fake-репозитории
- `tests/fakes/repository.py`: небольшой базовый `InMemoryRepository[T: Entity]` (`add`, `get`, `delete`, `list` со
  срезом) — основа для fake-репозиториев конкретных сущностей. По правилу L он ведёт себя как боевой репозиторий:
  `get` возвращает `None` для отсутствующего, а `NotFoundError` бросает сервис.
- Конкретные fake-репозитории и контрактные тесты появятся вместе с первыми настоящими протоколами (005).

### 8. Единое имя переменной БД: `POSTGRES_DB`
- Официальный образ PostgreSQL называет имя базы `POSTGRES_DB`, backend (`Settings`, `.env.example`) уже использует то же имя.
  Поэтому в `.docker-compose/.env` и `docker-compose.infra.yml` `POSTGRES_NAME` заменяется на `POSTGRES_DB` — одно имя
  на всех уровнях без переименований. Значение `moneyhelper` остаётся.
- В `backend/README.md` версия PostgreSQL приводится к фактической (16, как в compose).

## Risks / Trade-offs

- [Убрали `default_factory` у `Entity` — код, создающий сущности без `id`, перестанет работать] → в шаблоне сущностей нет;
  задача проверки `grep` по `Entity(`/`TimestampMixin` включена в tasks.
- [`NoDecode` и разбор `CORS_ORIGINS` зависят от версии pydantic-settings] → проверить на установленной версии
  (`>=2.10`) тестом настроек.
- [Создание тестовой БД требует прав `CREATEDB` у пользователя PostgreSQL] → в шаблоне пользователь `app` — владелец
  контейнера; при отказе фикстура падает с понятным сообщением.
- [Общий базовый `InMemoryRepository` может обрасти лишним] → держим минимальным, расширяем только по факту нужды.
- [Перехват исключений в middleware скрывает их от интеграции Sentry] → явный `capture_exception` и `logger.exception`,
  проверяется unit-тестом с подменой `sentry_sdk`.
- [Переименование `POSTGRES_NAME` → `POSTGRES_DB` ломает локальные `.env`, которые не обновили] → изменение описано в
  tasks и README; у тома БД имя не меняется, данные не теряются.

## Migration Plan

- Миграций Alembic нет, схема БД не меняется.
- Развёртывание: добавить в `.env` `CORS_ORIGINS` (по умолчанию пусто — поведение прежнее) и, при желании,
  `TEST_POSTGRES_DB`; в `.docker-compose/.env` переименовать `POSTGRES_NAME` в `POSTGRES_DB`.
- Откат: revert изменения; данные и схема не затронуты.

## Open Questions

- Нужно ли ограничивать `limit` для отдельных списков сверх общего максимума 100 (решим на этапах с большими выборками)?
- Нужно ли позже подключить кэш зависимостей и матрицу версий в CI (сейчас один job на Python 3.14).
