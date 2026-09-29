## Context

Скелет вертикального среза (сущность → протокол → репозиторий → сервис → API → тесты) уже задан задачами 006
(`currencies-seeding`), `backend-auth`, `iconpack` и, ближе всего по духу, задачей 008 (`wallets`). Задача 009
переиспользует этот скелет и во многом проще `wallets`:

- `wallets` — первая M2M-связь в проекте (кошелёк ↔ валюты через junction-таблицу) и первая зависимость сервиса от
  чужого репозитория (`CurrencyRepository.missing_ids`).
- `categories` — плоская сущность без ссылок на другие агрегаты: одна таблица, один репозиторий, сервис без
  внешних зависимостей, кроме `Clock`/`IdGenerator`. Единственное новое усложнение относительно `wallets` —
  составной `UniqueConstraint(user_id, type, name)` и первый в проекте закрытый enum (`CategoryType`).

Уже готовы и переиспользуются без изменений: `core/entities/base.py` (`Entity`, `TimestampMixin`),
`core/schemas/icon.py` (`IconName`), `core/schemas/pagination.py` (`Page`, `PageParams`), `core/exceptions/base.py`
(`NotFoundError`, `AlreadyExistsError` — новых типов исключений не требуется), `depends/auth.py`
(`get_current_user`, без обращения к БД), паттерн `UserRepository.add()` (перехват `IntegrityError` →
`AlreadyExistsError`) как образец для уникальности на уровне БД.

## Goals / Non-Goals

**Goals:**
- CRUD категорий пользователя: создание, чтение одной и списка (с пагинацией и опциональным фильтром по типу),
  полная замена (`PUT`), физическое удаление.
- Изоляция по владельцу — каждый метод репозитория, работающий с конкретной категорией, фильтрует по
  `category_id` И `user_id` в одном запросе; «не найдено» и «чужая категория» неотличимы снаружи (`NotFoundError`,
  404).
- Уникальность названия в пределах типа (`user_id`, `type`, `name`) — обеспечивается БД, а не предварительной
  проверкой в сервисе; нарушение даёт 409 (`AlreadyExistsError`).
- Тип категории — закрытый набор из двух значений (`income`/`expense`), валидируется на уровне Pydantic (422/400)
  и защищён в БД `CheckConstraint`.
- Иконка категории валидируется реестром `IconName` (007).
- Детерминированный порядок: список категорий — `created_at ASC, id ASC`.

**Non-Goals:**
- Иерархия категорий (подкатегории) — задача 009 явно определяет плоский список.
- Защита категории от удаления при наличии операций — таблицы операций ещё нет (010).
- Набор категорий по умолчанию для нового пользователя — вне рамок этой задачи (см. Decisions).
- Регистронезависимая уникальность названия.
- Ручной порядок отображения категорий (sort/reorder).
- Частичное обновление (`PATCH`).
- Frontend UI категорий.

## Decisions

### `CategoryType` — Python-перечисление, а не свободная строка

**Решение:** первый в проекте закрытый enum на два значения:

```python
from enum import Enum


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
```

Размещается в `core/entities/category.py` рядом с сущностью `Category`, экспортируется из
`core/entities/__init__.py`. Pydantic/FastAPI нативно поддерживают Python-enum как тип поля: автоматическая
валидация входа, `type` в OpenAPI отображается как перечисление значений, а не произвольная строка, при ошибке —
422 от Pydantic → 400 через уже существующий `validation_error_handler` (`api/errors.py`). Тот же тип
переиспользуется как query-параметр фильтра `GET /api/categories?type=...`.

**Альтернатива (отвергнута): `type: str` с валидацией `Literal["income", "expense"]` или ручным `field_validator`.**
Отвергнута — `Literal` даёт то же поведение, что и `Enum`, но без именованных констант для переиспользования в
коде (`CategoryType.INCOME` читаемее и безопаснее при рефакторинге, чем строковый литерал, рассыпанный по сервису,
репозиторию и тестам); ручной `field_validator` — дублирование того, что `Enum` даёт из коробки. Раз в проекте
впервые появляется закрытый набор значений такого рода, он должен стать первым прецедентом enum-подхода, а не
очередным вариантом ручной валидации строки.

### БД: `String` + `CheckConstraint`, а не нативный Postgres `ENUM`

**Решение:** колонка `type` — `String` небольшой длины с именованным `CheckConstraint`, по образцу
`ck_currencies_code_uppercase` у `currencies`:

```python
Column("type", String(10), nullable=False),
...
CheckConstraint("type IN ('income', 'expense')", name="ck_categories_type_valid"),
```

**Альтернатива (отвергнута): нативный Postgres `ENUM` тип (`CREATE TYPE category_type AS ENUM (...)`).** Отвергнута
— добавление значения в нативный enum Postgres требует `ALTER TYPE ... ADD VALUE` вне транзакции (в некоторых
версиях) и отдельной миграции с особыми предосторожностями, тогда как `CheckConstraint` меняется обычным
`ALTER TABLE ... DROP CONSTRAINT / ADD CONSTRAINT` в одной миграции — проще эволюционировать. Это также
единообразно с уже принятым в проекте стилем ограничений (`currencies`), а не вводит второй способ моделировать
закрытый набор значений на уровне схемы.

### Уникальность названия в пределах типа — составной `UniqueConstraint` на БД, без предварительного `SELECT`

**Решение:** таблица `categories` получает составной `UniqueConstraint(user_id, type, name, name="uq_categories_user_id_type_name")`
(по аналогии с `unique=True` у `currencies.code`, но составной). `CategoryRepository.add()` и `.update()`
оборачивают `INSERT`/`UPDATE` в `try/except IntegrityError` → `raise AlreadyExistsError("Категория с таким
названием уже существует среди категорий этого типа") from exc`, точно как `UserRepository.add()` перехватывает
дубль email. Сервис не делает предварительного `SELECT` на существование дубля.

**Обоснование.** Так уже устроена уникальность email в проекте — БД является источником истины по уникальности, а
не сервисный слой; предварительный `SELECT` перед `INSERT` создавал бы TOCTOU-щель (два конкурентных запроса могут
оба пройти проверку и упасть на `INSERT`), а без него всё равно нужен `try/except` на случай гонки — то есть
предварительная проверка была бы чистым накладным расходом без реальной защиты. Один поход в БД, одна и та же
модель ошибок, что и у `User`.

**Альтернатива (отвергнута): проверка уникальности в сервисе (`SELECT ... WHERE user_id = ... AND type = ... AND
name = ...` перед `add`/`update`).** Отвергнута по причине выше (TOCTOU, лишний запрос, расхождение с уже принятым
паттерном `UserRepository`).

### Регистронезависимость — не требуется

**Решение:** сравнение названия точное (`name = name`), без `LOWER()`/`CITEXT`. Совпадает с тем, как в проекте
сейчас сравниваются строки везде (например `email` в `UserRepository.get_by_email` — тоже точное сравнение, хотя
и приводится к нижнему регистру на входе до сохранения; для `name` категории такой нормализации нет, потому что
задача не требует единого регистра отображения, только защиты от дублей).

**Альтернатива (отвергнута): `CITEXT`/`LOWER(name)` в уникальном индексе.** Отвергнута — вопрос закрыт
оркестратором явно («регистронезависимость не требуется»); добавление `CITEXT`-расширения или функционального
индекса ради непоставленного требования было бы преждевременным усложнением схемы.

### Физическое безусловное удаление вместо защиты внешним ключом

**Решение:** `DELETE /api/categories/{category_id}` удаляет строку `categories` безусловно, без проверки связанных
данных, ровно как `DELETE /api/wallets/{wallet_id}` в задаче 008. Таблицы операций (010) ещё не существует —
ограничивать удаление нечем.

**Задел на будущее (не реализуется в этой задаче).** Когда появится задача 010 («Доходы и расходы»), таблица
операций получит FK на `categories.id` — вероятно `ON DELETE RESTRICT`, чтобы запретить удаление категории, по
которой есть операции (409 `AlreadyExistsError`/отдельная ошибка на выбор 010), либо явный каскад, если
продуктовое решение будет иным. Это решает design.md задачи 010, не 009 — тот же паттерн, что уже
задокументирован в design.md изменения `wallets` для `wallet_currencies`/`wallets`.

### Набор категорий по умолчанию — вне рамок, не открытый вопрос

**Решение:** новый пользователь не получает предзаполненных категорий. Раздел «Объём» задачи 009
(`docs/tasks/009_categories.md`) перечисляет только таблицу+миграцию, CRUD, изоляцию по владельцу и тесты —
сидирование пользовательских (не глобальных) данных при регистрации в этот список не входит. Пользователь создаёт
категории сам через `POST /api/categories`.

**Обоснование.** Сидирование в проекте — механизм для *глобальных* справочников без владельца (валюты, 006), он
идемпотентен и привязан к `lifespan` приложения, а не к событию «создан новый пользователь». Набор категорий по
умолчанию был бы данными, зависящими от пользователя (создаются при регистрации, а не при старте приложения) —
принципиально другой механизм, которого сейчас в проекте нет и вводить его ради задачи 009 преждевременно: нет
даже согласованного дефолтного набора категорий в задаче или дорожной карте.

**Альтернатива (отвергнута): сидировать типовой набор категорий (например «Продукты», «Транспорт», «Зарплата») при
регистрации пользователя.** Отвергнута оркестратором — вне рамок задачи 009; при появлении такого требования это
отдельное изменение (вероятно, хук в сервисе регистрации auth, а не в `categories`).

### `CategoryService` не зависит от внешних репозиториев (в отличие от `WalletService`)

**Решение:**

```python
class CategoryService:
    def __init__(self, categories: CategoryRepository, clock: Clock, ids: IdGenerator) -> None: ...
```

`WalletService` дополнительно зависит от `CurrencyRepository`, потому что перед записью кошелька нужно проверить
существование переданных `currency_id` во *внешнем* справочнике валют (FK на чужую таблицу, которым управляет
пользователь только косвенно, выбирая существующие id). У `Category` такой внешней ссылки нет: `type` — закрытый
enum, валидируемый Pydantic на границе API без похода в БД; `icon` — валидируется `IconName` тем же образом,
тоже без БД. Единственное ограничение, требующее похода в БД, — уникальность `(user_id, type, name)`, а её
проверяет сама таблица `categories` через `UniqueConstraint`, не отдельный репозиторий. Поэтому у
`CategoryService` нет второй зависимости-протокола: I/D из SOLID соблюдены без введения неиспользуемого
интерфейса.

### Изоляция владельца: `NotFoundError` везде, никогда `PermissionDeniedError`

**Решение:** каждый метод `CategoryRepository`, оперирующий конкретной категорией (`get_by_id`, `update`,
`delete`), принимает и `category_id`, и `user_id` и фильтрует по обоим `WHERE category_id = :id AND
user_id = :user_id` в одном запросе. Если строка не найдена — репозиторий возвращает `None`/`False`, сервис
поднимает `NotFoundError` (404). Никогда не выполняется отдельный `SELECT` «существует ли категория» с
последующей проверкой владельца в Python и никогда не поднимается `PermissionDeniedError` (403) — тот же принцип,
что уже применён в `wallets` (см. design.md изменения `wallets`) и зафиксирован в AGENTS.md.

### Порядок списка категорий — `created_at ASC, id ASC`

**Решение:** `GET /api/categories` сортирует по `created_at ASC`, затем `id ASC` как детерминированный
tie-breaker — тот же принцип, что уже принят для `wallets`/`currencies`.

**Альтернатива (отвергнута): ручной порядок (поле `sort_order`/`position`).** Отвергнута — задача 009 явно не
включает функцию ручного упорядочивания.

### `CategoryRepository.update` — полная замена одним запросом

**Решение:** сигнатура протокола:

```python
class CategoryRepository(Protocol):
    async def add(self, category: Category) -> Category: ...
    async def get_by_id(self, category_id: UUID, user_id: UUID) -> Category | None: ...
    async def list(
        self, user_id: UUID, *, type: CategoryType | None, limit: int, offset: int
    ) -> list[Category]: ...
    async def count(self, user_id: UUID, *, type: CategoryType | None) -> int: ...
    async def update(
        self, category_id: UUID, user_id: UUID, *, type: CategoryType, name: str, icon: str, now: datetime
    ) -> Category | None: ...
    async def delete(self, category_id: UUID, user_id: UUID) -> bool: ...
```

Реализация `update`: `UPDATE categories SET type=..., name=..., icon=..., updated_at=... WHERE id=... AND
user_id=... RETURNING ...` в `try/except IntegrityError` (конфликт уникальности при переименовании в занятое имя
даёт 409, а не 500) — если строк 0, категория не найдена/чужая, `None` без лишних запросов. В отличие от
`WalletRepository.update` (`UPDATE` + `DELETE`/`INSERT` набора валют), здесь один `UPDATE` — нет вложенной
M2M-структуры для пересборки.

**Альтернатива (отвергнута):** нет обоснованной альтернативы — операция тривиальна (одна строка, один `UPDATE`),
не рассматривалась отдельная стратегия.

### Фильтр по типу — опциональный параметр `list`/`count`, а не отдельный метод

**Решение:** `list(user_id, *, type: CategoryType | None, limit, offset)` и `count(user_id, *, type: CategoryType |
None)` принимают `type` как опциональный keyword-параметр; `None` означает «все категории независимо от типа»,
конкретное значение добавляет `WHERE categories.c.type == type` к запросу. `GET /api/categories` пробрасывает
query-параметр `type: CategoryType | None = None` напрямую в сервис.

**Альтернатива (отвергнута): отдельные методы `list_by_type`/`list_all`.** Отвергнута — раздвоение метода на два
почти идентичных увеличивает поверхность протокола без выгоды (`I` из SOLID не требует отдельных методов там, где
разница — один опциональный предикат в `WHERE`), а вызывающий код (роутер) и так уже получает `type` как
опциональный query-параметр FastAPI.

### Схемы и роутер — по образцу `wallets`

**Решение:** `CategoryCreate`/`CategoryUpdate` (одна форма, `PUT` — полная замена):

```python
class CategoryCreate(BaseModel):
    type: CategoryType
    name: str = Field(min_length=1, max_length=100)
    icon: IconName

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name не может быть пустым")
        return stripped


CategoryUpdate = CategoryCreate
```

`api/categories.py`, по образцу `api/wallets.py`, с `Depends(get_current_user)` на каждом маршруте и `user_id`,
передаваемым в сервис явным аргументом:

```python
router = APIRouter(prefix="/api/categories", tags=["Categories"])

@router.post("", response_model=CategoryOut, status_code=201)
@router.get("", response_model=Page[CategoryOut])          # + query type: CategoryType | None, limit/offset
@router.get("/{category_id}", response_model=CategoryOut)
@router.put("/{category_id}", response_model=CategoryOut)
@router.delete("/{category_id}", status_code=204)
```

`depends/category.py`:

```python
def get_category_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> CategoryRepository:
    return SqlCategoryRepository(session)

def get_category_service(
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> CategoryService:
    return CategoryService(categories, clock, ids)
```

## Risks / Trade-offs

- [Уникальность `(user_id, type, name)` обнаруживается только на `INSERT`/`UPDATE` через `IntegrityError`, а не
  заранее] → осознанный выбор, совпадающий с уже принятым паттерном `UserRepository`; избегает TOCTOU и лишнего
  запроса, цена — необходимость перехватывать исключение в каждом методе записи (уже сделано).
- [`CheckConstraint` на `type` в БД и `Enum` на уровне Pydantic — два места, описывающих один и тот же закрытый
  набор значений] → приемлемое дублирование: `CheckConstraint` защищает данные при прямых изменениях схемы/данных
  в обход API (миграции, ручные правки), `Enum` защищает вход API; рассинхронизация возможна только при ручной
  правке одного без другого — то же дублирование уже есть между `IconName`/`ALLOWED_ICONS` и отсутствием
  проверки иконки в БД (там сознательно только на уровне приложения, здесь — на обоих уровнях, потому что набор
  значений `type` закрыт и стабилен, а список иконок обновляется чаще).
- [Физическое безусловное удаление категории сейчас, без защиты от потери связанных данных] → осознанный выбор
  задачи 009 (см. Open Questions), задел на 010 зафиксирован выше и в Migration Plan; риск ограничен тем, что
  таблицы операций ещё физически не существует — терять пока нечего.
- [`NotFoundError` вместо `PermissionDeniedError` на чужой `category_id` усложняет диагностику на стороне клиента]
  → тот же осознанный компромисс, что уже принят в `wallets` и зафиксирован в AGENTS.md.
- [Отсутствие набора категорий по умолчанию означает, что новый пользователь стартует с пустым списком и должен
  создать категории вручную перед первой операцией (010)] → осознанное решение, вне рамок 009; если станет
  проблемой продукта, это отдельное изменение (сидирование пользовательских данных при регистрации — новый
  механизм, которого сейчас в проекте нет).

## Migration Plan

Миграция Alembic `20260929_0005` (`down_revision = "20260929_0004"`), одна ревизия, одна таблица:

```python
op.create_table(
    "categories",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sa.Column("type", sa.String(length=10), nullable=False),
    sa.Column("name", sa.String(length=100), nullable=False),
    sa.Column("icon", sa.String(length=50), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("type IN ('income', 'expense')", name="ck_categories_type_valid"),
    sa.UniqueConstraint("user_id", "type", "name", name="uq_categories_user_id_type_name"),
)
```

`downgrade()` — `op.drop_table("categories")`.

Откат безопасен: на момент задачи 009 ничего, кроме категорий, не ссылается на эту таблицу (операции 010 ещё не
реализованы), удаление таблицы не затрагивает данные других сущностей.

**Задел на будущее (не реализуется в этой задаче).** Когда появится задача 010 («Доходы и расходы»), потребуется
таблица операций с FK на `categories.id`, вероятно `ON DELETE RESTRICT` — решает design.md задачи 010, не 009.

## Open Questions

Все три открытых вопроса задачи 009 (`docs/tasks/009_categories.md`) решены оркестратором:

1. **Уникальность названия в пределах типа?** Решено: составной `UniqueConstraint(user_id, type, name)` на уровне
   БД, регистронезависимость не требуется (точное сравнение строк). `CategoryRepository.add()`/`.update()`
   перехватывают `IntegrityError` → `AlreadyExistsError` («Категория с таким названием уже существует среди
   категорий этого типа»), без предварительного `SELECT` в сервисе — по образцу `UserRepository.add()`.
2. **Запрет или каскад при удалении категории с операциями?** Решено: таблица операций (010) в этой задаче ещё не
   существует, ограничивать нечем — удаление категории физическое и безусловное (по `category_id` + `user_id`
   владельца). Задел на будущее зафиксирован в Migration Plan: 010 потребует FK-защиту от `transactions` к
   `categories`.
3. **Набор категорий по умолчанию для нового пользователя?** Решено: не реализуется в этой задаче. «Объём» задачи
   009 сидирование пользовательских категорий не перечисляет — пользователь создаёт категории сам через CRUD.
   Явное решение, а не открытый вопрос на будущее: появление дефолтного набора — отдельное будущее изменение вне
   дорожной карты 003–012, если возникнет такое требование продукта.
