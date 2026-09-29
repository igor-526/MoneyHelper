## Context

Скелет backend готов (`backend-foundation`): `Clock`/`IdGenerator` как протоколы, иерархия `AppError`, CORS с
credentials, пустая начальная миграция, тесты без БД плюс `tests/infrastructure/`. Авторизация готова
(`backend-auth`) и даёт образец полного вертикального среза (сущность → протокол → репозиторий на SQLAlchemy Core →
сервис → API → тесты на всех уровнях), которому эта задача следует.

Задача: `docs/tasks/006_currencies_seeding.md`. Правило сидирования уже зафиксировано в AGENTS.md (раздел
«Сидирование»): справочные данные заполняются не миграциями, а при старте приложения в `lifespan`; механизм — в
`utils/seeding.py`, данные — JSON в `src/seeds/`; сидирование идемпотентно (upsert по явному UUID) и безопасно при
нескольких репликах (advisory lock); в тестах отключается настройкой.

Кроме собственно справочника валют, задача явно вводит **переиспользуемый механизм**: следующие задачи дорожной
карты (например, iconpack, если ему тоже понадобится сидирование) не должны придумывать advisory lock и upsert-логику
заново. Поэтому механизм сидирования проектируется как две независимые части: DB-агностичная (upsert по данным) и
инфраструктурная (advisory lock, транзакция, подключение к БД) — это отдельная декомпозиция, обоснование ниже.

## Goals / Non-Goals

**Goals:**
- Таблица `currencies` и миграция (только схема).
- Сущность, протокол репозитория, репозиторий на SQLAlchemy Core, сервис чтения, `GET /api/currencies`.
- `utils/seeding.py`: обобщённый механизм — идемпотентный upsert по `id`, без удаления отсутствующих в JSON записей,
  безопасный при параллельном старте нескольких реплик (advisory lock PostgreSQL).
- Сид `src/seeds/currencies.json` с тремя валютами (CNY, RUB, USDT), явные зафиксированные UUID.
- Настройка включения/отключения сидирования; в тестах — выключено, чтобы `make test` не требовал БД.
- Тесты на всех уровнях: unit (механизм на fake-репозитории), smoke (без БД), infrastructure (реальная БД, advisory
  lock).

**Non-Goals:**
- Пользовательские валюты, расчёт курсов (см. `proposal.md`).
- Создание/изменение/удаление валют через API.
- Общий admin-UI или CLI для управления сидами сверх того, что запускается в `lifespan`.

## Decisions

### Формат JSON сида

Файл `backend/src/seeds/currencies.json` — список объектов:

```json
[
  {"id": "5f7c7b9e-a33c-4d66-9a0b-eee6f3e98a81", "code": "CNY", "name": "Китайский юань", "decimal_places": 2},
  {"id": "1c9586e7-c3d6-465b-8efb-81f74a2dc28b", "code": "RUB", "name": "Российский рубль", "decimal_places": 2},
  {"id": "ab66dc61-9873-4b46-a2d7-51e04e85a6af", "code": "USDT", "name": "USDT", "decimal_places": 2}
]
```

Поля 1:1 соответствуют колонкам таблицы и полям сущности `Currency` — сидер не занимается трансформацией данных,
только валидацией через ту же pydantic-модель, что использует сущность (ошибка формата в JSON — это баг в коде,
приложение не должно тихо стартовать с неполным справочником: невалидная запись роняет `lifespan` с понятной
ошибкой). UUID сгенерированы один раз командой `uv run python -c "import uuid; print(uuid.uuid4())"` и больше не
меняются — это первичный ключ сопоставления при апдейте.

**Альтернатива (отвергнута):** формат `{"CNY": {...}}` (словарь по коду). Отвергнут, потому что `code` — не
первичный ключ сопоставления (открытый вопрос задачи прямо требует сопоставления по `id`, чтобы переименование кода
не создавало вторую запись), а список объектов проще расширять полями в будущем без изменения структуры документа.

### Начальный набор валют

Ровно три: CNY, RUB, USDT, у каждой `decimal_places = 2`. Это единственные валюты, явно упомянутые в предметной
области (кошельки UPay USDT, Alipay/WeChatPay/NihaoChina CNY, наличные RUB — `openspec/config.yaml`). Курс USDT
привязан к доллару и на бытовом уровне всегда учитывается с двумя знаками, как остальные, поэтому исключений в
`decimal_places` не делаем.

### Таблица `currencies`

```
id              UUID PRIMARY KEY
code            VARCHAR(10) NOT NULL UNIQUE
name            VARCHAR(100) NOT NULL
decimal_places  SMALLINT NOT NULL

CHECK (code = upper(code))
CHECK (decimal_places BETWEEN 0 AND 8)
```

- `id`, как и у `users`, задаётся приложением (сидом), а не `gen_random_uuid()` — БД не генерирует значения бизнес-
  идентификаторов нигде в проекте (см. `users.id` через `IdGenerator`), здесь роль генератора играет явный UUID сида.
- `code` до 10 символов — покрывает и трёхбуквенные ISO-подобные коды (`CNY`, `RUB`), и `USDT`, который не входит в
  ISO 4217; запас на возможные будущие коды длиннее 3 символов. `CHECK (code = upper(code))` — по аналогии с
  `ck_users_email_lowercase`: нормализация фиксируется на уровне БД, а не только в приложении.
- `decimal_places` ограничен `[0, 8]`, тем же верхним пределом, что `MONEY_DECIMAL_PLACES` в `core/schemas/money.py`
  — валюта не может требовать больше знаков, чем способен хранить тип `Money`.
- Никакой `TimestampMixin`/`created_at`/`updated_at`, в отличие от `users`. **Решение:** справочник не показывает
  пользователю историю изменений, и `upsert` всегда отражает текущее целевое состояние из JSON (который сам живёт в
  git-истории) — добавление аудита без применения было бы неиспользуемым полем. Если аудит понадобится (например,
  для отладки миграции курсов), это отдельная задача с миграцией `ADD COLUMN`.
- Никакого `deleted_at`/soft delete — сидирование по решению ниже никогда не удаляет записи, а прямого API удаления
  нет (вне рамок), так что физическое удаление просто не вызывается.

Миграция (только схема, без данных) — следующая после `20260929_0002_users`, например
`<дата>_0003_currencies.py`: `op.create_table("currencies", ...)` с теми же ограничениями; `downgrade` удаляет
таблицу.

### Слои и протоколы (SOLID)

- `core/entities/currency.py`: `Currency(Entity)` — `code: str`, `name: str`, `decimal_places: int`. Без
  `TimestampMixin` (см. решение по таблице).
- `core/protocols/repositories/currency_repository.py`: узкий протокол под два разных потребителя (ISP) — сервис
  чтения использует только `list`/`count`, сидирование — только `upsert_many`. Разделять на два протокола
  (`CurrencyReader`/`CurrencyWriter`) избыточно: оба принадлежат одному и тому же репозиторию валют и одному
  агрегату, в отличие от `TokenIssuer`/`TokenVerifier` в `backend-auth`, которые шли к разным реализациям.
  ```python
  class CurrencyRepository(Protocol):
      async def list(self, *, limit: int, offset: int) -> list[Currency]: ...
      async def count(self) -> int: ...
      async def upsert_many(self, currencies: Sequence[Currency]) -> None:
          """Добавляет отсутствующие и обновляет code/name/decimal_places у существующих по id.
          Не удаляет записи, которых нет в currencies."""
          ...
  ```
- `core/services/currency.py`: `CurrencyService(repository: CurrencyRepository)` — `async def list_currencies(limit,
  offset) -> tuple[list[Currency], int]`, тонкая обёртка над `list`/`count` (как у пагинации в остальных списочных
  сценариях проекта, если такой сервис уже появится к моменту реализации — иначе первый прецедент). Сервис не знает
  про HTTP и `Page`.
- `repositories/currency.py`: `CurrencyRepository` на SQLAlchemy Core. `upsert_many` — один multi-row `INSERT ...
  VALUES (...), (...), ...` с `ON CONFLICT (id) DO UPDATE SET code = excluded.code, name = excluded.name,
  decimal_places = excluded.decimal_places` (`sqlalchemy.dialects.postgresql.insert`), не построчный цикл: один
  round-trip к БД для всего сида.
- `models/currency.py`: таблица на `utils.basemodel.metadata`, импортируется в `models/__init__.py`.
- `api/schemas/currency.py`: `CurrencyOut` (`id`, `code`, `name`, `decimal_places`), `from_attributes=True`, как
  `UserOut`.
- `api/currencies.py`: `GET /api/currencies`, `Annotated[PageParams, Query()]` → `Page[CurrencyOut]` — используется
  общая схема пагинации `core/schemas/pagination.py`, уже закреплённая в `api-conventions` (`backend-foundation`) для
  всех списочных эндпоинтов; отдельного одноразового формата ответа не вводим, даже при текущих трёх записях.
- `depends/currency.py`: `get_currency_repository(session)`, `get_currency_service(repository)`.

### Механизм сидирования: две части, а не одна функция

**Решение:** `utils/seeding.py` разделяет DB-агностичную логику (что значит «засеять» набор записей) и
инфраструктурную обвязку (как безопасно получить эксклюзивный доступ к БД на время сидирования). Причина —
буквальное требование задачи: «unit-тесты механизма сидирования на fake-репозитории». Advisory lock существует только
на живом соединении PostgreSQL, поэтому его нельзя протестировать без БД (он и тестируется в `test-infra`), а
идемпотентность/upsert/неудаление — это чистая логика работы с репозиторием через протокол, и её тестируем без БД
через fake, как любой другой сервис в проекте.

```python
# utils/seeding.py
@dataclass(frozen=True)
class SeedSource[T: Entity]:
    path: Path                              # src/seeds/<name>.json
    parse_row: Callable[[dict[str, Any]], T]  # валидирует и строит сущность (обычно T.model_validate)


async def seed_from_json[T: Entity](source: SeedSource[T], repository: UpsertRepository[T]) -> None:
    """DB-агностичная часть: читает JSON, валидирует, вызывает repository.upsert_many. Тестируется на fake."""
    rows = json.loads(source.path.read_text(encoding="utf-8"))
    await repository.upsert_many([source.parse_row(row) for row in rows])


SEEDING_LOCK_KEY = "moneyhelper:seeding"


async def run_seeding(engine: AsyncEngine, definitions: Sequence[SeedDefinition]) -> None:
    """Инфраструктурная часть: один advisory lock на весь набор источников, вызывается из lifespan."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT pg_advisory_lock(hashtext(:key))"), {"key": SEEDING_LOCK_KEY})
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            for definition in definitions:
                await seed_from_json(definition.source, definition.repository_factory(session))
            await session.commit()
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": SEEDING_LOCK_KEY})
```

`UpsertRepository[T]` — минимальный протокол с единственным методом `upsert_many`, которому соответствует
`CurrencyRepository` (структурная типизация, дополнительного наследования не требуется). `SeedDefinition` — пара
`(source, repository_factory)`, где `repository_factory: Callable[[AsyncSession], UpsertRepository[T]]`; для валют —
`SeedDefinition(source=CURRENCY_SEED_SOURCE, repository_factory=CurrencyRepository)`. Список определений (сейчас — из
одного элемента) собирается в `seeds/currencies.py` и передаётся в `run_seeding` из `main.py`: новая справочная
таблица добавляет новый `SeedDefinition` в список, не трогая `utils/seeding.py` (открытость/закрытость).

**Advisory lock — реализация и выбор blocking-варианта.** Лок берётся на отдельном, не разделяемом пулом соединении
(`engine.connect()` — сессионный advisory lock живёт, пока держится это конкретное соединение asyncpg) и всегда
снимается в `finally`; при аварийном обрыве соединения PostgreSQL сам освобождает сессионные локи. Используется
блокирующий `pg_advisory_lock`, а не `pg_try_advisory_lock`: при параллельном старте нескольких реплик вторая просто
дожидается, пока первая закончит (сидирование — доли секунды, три upsert), и после этого сама проходит по уже
неизменным данным без реального эффекта. `pg_try_advisory_lock` потребовал бы обвязки retry/backoff при неудаче —
на старте приложения это лишняя сложность ради экономии долей секунды ожидания. Ключ — не сырое число, а
`hashtext('moneyhelper:seeding')`: один общий лок на весь процесс сидирования (не по таблице), потому что порядок и
атомарность между разными `SeedDefinition` тоже важны (обновление даже нескольких таблиц не должно чередоваться
между репликами). Строковый ключ читается в коде понятнее магического `bigint`-константы.

**Через что именно идёт SQL.** Сессия оборачивает `AsyncConnection`, полученный из `AsyncEngine` с диалектом
`postgresql+asyncpg` (`settings.database_url`) — то есть физически лок и все запросы идут через драйвер `asyncpg`,
как того требует правило задачи «через asyncpg», но API — `SQLAlchemy Core/`text()``, а не пакет `asyncpg` напрямую
(в отличие от `tests/infrastructure/database.py`, который использует `asyncpg.connect()` для административной
операции создания тестовой БД до применения миграций — там ещё нет engine с прикладными настройками). Здесь
прикладной engine уже есть (`utils/database.py`), и использовать его — меньше дублирования конфигурации подключения,
а `CurrencyRepository`, вызываемый внутри `seed_from_json`, работает с обычной `AsyncSession`, как и везде в проекте
— не нужно заводить отдельную реализацию репозитория «для сидирования».

### Upsert по `id`, без удаления — обоснование политики

Сидирование обновляет `code`/`name`/`decimal_places` у существующей записи при совпадении `id` и добавляет новую при
отсутствии; запись, чей `id` пропал из JSON, **не удаляется**. Причины:
1. `currencies.id` — внешний ключ будущих кошельков (задача 008); удаление валюты, на которую ссылается хотя бы один
   кошелёк, либо упадёт по FK (если `RESTRICT`), либо молча оборвёт данные пользователя (если `CASCADE`) — оба
   исхода недопустимы для операции, которая выполняется автоматически при каждом старте приложения без участия
   человека.
2 Случайная опечатка или преждевременное удаление строки в JSON при разработке не должны необратимо стирать
   исторические данные при следующем деплое — восстановить удалённую валюту (и связанные с ней ссылки) сложнее, чем
   держать в БД запись, которой временно нет в сиде.
3. Явное удаление валюты (если оно когда-либо понадобится) — решение конкретного разработчика в конкретный момент,
   а не побочный эффект правки списка. Такая операция вне рамок задачи 006 и должна быть отдельным осознанным
   действием (ручная миграция или будущий административный сценарий), а не автоматическим следствием сидирования.

### Настройка и отключение в тестах

`Settings.seeding_enabled: bool = Field(default=True, alias="SEEDING_ENABLED")`. В `lifespan` (`main.py`):

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.seeding_enabled:
        await run_seeding(engine, SEED_DEFINITIONS)
    yield
    await close_database()
```

`tests/conftest.py` уже переопределяет окружение до импорта `settings` (`SENTRY_ENABLED=false`, `CORS_ORIGINS=...`);
туда же добавляется `os.environ["SEEDING_ENABLED"] = "false"` — тем самым `TestClient(app)` в smoke-тестах поднимает
полный `lifespan`, но не обращается к БД, и `make test`/голый `pytest` остаются без зависимости от БД, как того
требует AGENTS.md. `.env.example` получает `SEEDING_ENABLED=true` (значение по умолчанию для разработки не меняется
относительно дефолта в коде — переменная документируется явно, как остальные флаги).

### API — только чтение

`GET /api/currencies` — единственный эндпоинт. Постраничный ответ `Page[CurrencyOut]` по общей конвенции пагинации
проекта: при трёх записях `total=3` и один запрос с дефолтными `limit=20`/`offset=0` вернёт их все, но эндпоинт не
делает исключения из конвенции ради текущего маленького объёма — конвенция должна остаться единообразной для всех
списочных эндпоинтов, которые появятся в задачах 008–012. Сортировка — по `code` (детерминированный, стабильный для
тестов и UI порядок; не по `id`, у которого нет содержательного смысла для пользователя).

### Тесты

- **unit** (`tests/unit/`): `FakeCurrencyRepository` (в `tests/fakes/`, аналог `InMemoryRepository`, но с
  `upsert_many` вместо `add`) + `seed_from_json` — идемпотентность повторного вызова с тем же JSON (число записей и
  их поля не меняются), обновление изменённого поля (`name`/`decimal_places`) по совпавшему `id`, отсутствие удаления
  записи, чей `id` убрали из переданного набора; `CurrencyService.list_currencies` на fake (пагинация, `total`);
  `Settings.seeding_enabled` (значение по умолчанию, чтение из окружения).
- **smoke** (`tests/smoke/`): `/api/currencies` зарегистрирован в OpenAPI (дополнение к
  `test_auth_routes_are_registered`); приложение стартует через `TestClient(app)` с `SEEDING_ENABLED=false` без
  обращения к БД (уже гарантируется общим `conftest.py`, отдельного теста на «не стучится в БД» не требуется — при
  реальной попытке подключения smoke и так упадёт, так как БД в CI `quality` нет).
- **infrastructure** (`tests/infrastructure/`, `make test-infra`): `CurrencyRepository.upsert_many` на реальной БД
  (вставка, обновление по `id`, отсутствие удаления — те же сценарии, что в unit, но через настоящий `ON CONFLICT`);
  `run_seeding` целиком (после вызова в БД оказываются три валюты с ожидаемыми полями; повторный вызов не создаёт
  дублей). Проверка advisory lock: открыть отдельное соединение, вручную взять `pg_advisory_lock(hashtext(...))` с
  тем же ключом, запустить `run_seeding` в фоне (`asyncio.create_task` или отдельный поток) и убедиться, что он не
  завершается, пока лок не отпущен (`pg_try_advisory_lock` с того же ключа с другого соединения возвращает `false`,
  пока первый лок удержан) — так честная проверка параллельного старта не требует реально поднимать две реплики
  приложения одновременно.

## Risks / Trade-offs

- [Невалидная запись в JSON (не проходит `Currency`/pydantic) роняет `lifespan`] → осознанно: тихий частичный
  справочник хуже, чем приложение, которое не стартует с понятной ошибкой в логе при деплое.
- [Общий один advisory lock на всё сидирование, а не по таблице] → при росте числа справочников старт чуть дольше
  ждёт лока у реплик, стартующих параллельно; на объёме «несколько маленьких JSON-справочников» это доли секунды,
  не проблема.
- [`code = upper(code)` на уровне БД, а не только в приложении] → сидер и так пишет коды в верхнем регистре;
  ограничение — подстраховка от будущей ручной правки данных в обход сидирования, симметрично `ck_users_email_lowercase`.
- [Нет soft delete/аудита изменений справочника] → вне рамок задачи; JSON в git уже даёт историю изменений состава
  валют на уровне репозитория, отдельная таблица аудита не нужна, пока нет требования показывать её пользователю.
- [`SEEDING_ENABLED=false` в тестах может разойтись с реальным поведением в проде, если кто-то забудет включить его
  в `.env` окружения] → значение по умолчанию в коде `true`; выключение — только в `tests/conftest.py`, а не общий
  дефолт настройки.

## Migration Plan

1. Добавить миграцию `<дата>_0003_currencies.py` (`make be-makemigrations msg="add currencies table"`, вручную
   свериться со сгенерированным DDL — ограничения `CHECK` иногда требуют ручной правки) и применить (`make
   be-migrate`).
2. Задать `SEEDING_ENABLED=true` в `.env` окружений (или полагаться на дефолт `true` в коде).
3. При следующем старте приложения `lifespan` заполнит `currencies` тремя записями; повторные старты (в том числе
   нескольких реплик одновременно) идемпотентны.
4. Откат: `alembic downgrade -1` удаляет таблицу `currencies`; поскольку на неё пока никто не ссылается (кошельки —
   задача 008), откат безопасен только до появления FK на `currencies.id` — после задачи 008 откат этой миграции уже
   потребует сначала откатить зависимые.

## Open Questions

Нет открытых вопросов — все вопросы, поставленные в `docs/tasks/006_currencies_seeding.md`, решены выше (формат
JSON, начальный набор валют, политика upsert/no-delete, advisory lock).
