## Context

Скелет вертикального среза (сущность → протокол → репозиторий → сервис → API → тесты) уже задан задачами 006
(`currencies-seeding`) и `backend-auth`. Задача 008 переиспользует этот скелет, но добавляет то, чего у валют не
было — владельца и связь многие-ко-многим:

- `currencies` — глобальный справочник без владельца, читается всеми одинаково.
- `wallets` — принадлежит пользователю (`user_id`), должна быть изолирована между пользователями на уровне
  каждого SQL-запроса, а не проверкой владения после `SELECT`.
- Кошелёк ссылается на одну или несколько валют из справочника `currencies` — первая M2M-связь в проекте.

Уже готовы и переиспользуются без изменений: `core/entities/base.py` (`Entity`, `TimestampMixin`),
`core/schemas/icon.py` (`IconName` — первый реальный потребитель, до этого использовался только в собственном
unit-тесте задачи 007), `core/schemas/pagination.py` (`Page`, `PageParams`), `core/exceptions/base.py`
(`ClientError`, `NotFoundError` — новых типов исключений не требуется), `depends/auth.py` (`get_current_user`,
без обращения к БД).

## Goals / Non-Goals

**Goals:**
- CRUD кошельков пользователя: создание, чтение одного и списка (с пагинацией), полная замена (`PUT`), физическое
  удаление.
- Изоляция по владельцу — каждый метод репозитория, работающий с конкретным кошельком, фильтрует по `wallet_id` И
  `user_id` в одном запросе; «не найдено» и «чужой кошелёк» неотличимы снаружи (`NotFoundError`, 404).
- Проверка существования валют перед записью — неизвестный `currency_id` возвращает `ClientError` (400) с понятным
  сообщением, а не 500 от нарушения FK.
- Иконка кошелька валидируется реестром `IconName` (007).
- Детерминированный порядок: список кошельков — `created_at ASC, id ASC`; `currency_ids` внутри кошелька — по коду
  валюты.

**Non-Goals:**
- Защита кошелька от удаления при наличии операций — таблицы операций ещё нет (010).
- Ограничение смены набора валют кошелька с историей операций — та же причина.
- Ручной порядок отображения кошельков (sort/reorder).
- Частичное обновление (`PATCH`).
- Frontend UI кошельков.

## Decisions

### Валюты — часть сущности `Wallet`, не отдельный агрегат

**Решение:** `Wallet(Entity, TimestampMixin)` хранит `currency_ids: tuple[UUID, ...]` прямо в сущности:

```python
from uuid import UUID

from core.entities.base import Entity, TimestampMixin


class Wallet(Entity, TimestampMixin):
    user_id: UUID
    name: str
    icon: str
    currency_ids: tuple[UUID, ...]
```

`tuple`, а не `list`, — сущности в проекте иммутабельны по значению как pydantic-модели (сравнение по значению,
хешируемость не требуется, но неизменяемость поля списка предотвращает случайную мутацию `currency_ids` в
вызывающем коде после того, как сервис вернул сущность).

**Альтернатива (отвергнута): отдельная сущность `WalletCurrency`/собственный сервис для набора валют.** Отвергнута
— набор валют кошелька не имеет самостоятельного жизненного цикла вне кошелька (нельзя создать, прочитать или
удалить «валюту кошелька» в отрыве от самого кошелька; изменение набора валют — часть операции «обновить
кошелёк», не отдельный сценарий использования). Заведение отдельного протокола/сервиса ради этого нарушило бы
«не создавай лишних слоёв там, где это неоправданно» (тот же принцип, что уже применялся в `iconpack` при отказе
от таблицы иконок).

### Две таблицы в одной миграции, разные политики `ON DELETE`

**Решение:**

```python
wallets = Table(
    "wallets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("icon", String(50), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
)

wallet_currencies = Table(
    "wallet_currencies",
    metadata,
    Column("wallet_id", UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
    Column("currency_id", UUID(as_uuid=True), ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=False),
    PrimaryKeyConstraint("wallet_id", "currency_id"),
)
```

- `wallets.user_id → users.id ON DELETE CASCADE` — данные пользователя (в том числе кошельки) должны уходить
  вместе с ним; это уже установленный в проекте принцип «удаление физическое», применённый последовательно.
- `wallet_currencies.wallet_id → wallets.id ON DELETE CASCADE` — связка принадлежит кошельку целиком, это его
  собственные данные (как строки `wallet_currencies` пересобираются при `update`), удаление кошелька должно
  забирать их без явного шага в сервисе.
- `wallet_currencies.currency_id → currencies.id ON DELETE RESTRICT` — валюта глобальный справочник, у которого
  пока нет удаления вообще (006/007 его не вводили), но по умолчанию защищаем внешним ключом от появления
  «осиротевшей» привязки, если удаление валют когда-нибудь появится. `RESTRICT` — самая безопасная политика по
  умолчанию, слабее (`SET NULL`/`CASCADE`) означала бы тихую потерю валюты у существующего кошелька.
- `wallet_currencies` — чистая junction-таблица без собственного `id`: составной `PRIMARY KEY (wallet_id,
  currency_id)` одновременно первичный ключ, естественное ограничение уникальности пары и опора для `JOIN`;
  отдельный суррогатный `id` не нужен — на эту строку никто не ссылается извне.

**Альтернатива (отвергнута): `currency_ids: ARRAY(UUID)` колонка в `wallets` вместо второй таблицы.** Отвергнута
— PostgreSQL `ARRAY` не даёт декларативного FK на каждый элемент массива (проверка существования валюты стала бы
только сервисной, без защиты на уровне БД), не поддерживает `ON DELETE RESTRICT` по элементу, и `JOIN ... ORDER
BY currencies.code` для детерминированного порядка вывода потребовал бы `unnest()`. Обычная junction-таблица —
стандартный, предсказуемый способ выразить M2M в реляционной модели, соответствует «SQL или select() — только в
repositories» и не создаёт исключения из привычного паттерна ради частного случая.

### Проверка существования валют — новый метод в `CurrencyRepository`

**Решение:** `core/protocols/repositories/currency_repository.py` получает узкий метод, возвращающий именно то,
что нужно `WalletService`, чтобы сформировать сообщение об ошибке:

```python
async def missing_ids(self, currency_ids: Sequence[UUID]) -> set[UUID]:
    """Возвращает подмножество currency_ids, отсутствующее в справочнике. Пустое множество — все существуют."""
    ...
```

`WalletService` вызывает `missing_ids` перед `add`/`update`; непустой результат → `ClientError` со списком
неизвестных id в сообщении. `CurrencyRepository` (SQLAlchemy) реализует через `SELECT currency_id ... WHERE
currency_id = ANY(...)` и разность множеств в Python — одна проверка одним запросом, без `N+1`.
`CurrencyService` этот метод не вызывает: у него нет сценария, которому он бы понадобился, — это нормально,
репозиторий вправе обслуживать разных потребителей разными методами (`I` из SOLID — протокол не «god-объект», но
конкретный класс `repositories/currency.py` реализует оба используемых протоколом-потребителем подмножества).

**Альтернатива (отвергнута): `exists_all(currency_ids) -> bool`.** Рассмотрена как более простая сигнатура, но
отвергнута — при `False` сервис не может сформировать сообщение «неизвестны id: ...» без второго запроса
(повторного `SELECT`, чтобы выяснить, каких именно не хватает). `missing_ids` даёт всё необходимое за один поход
в БД и делает сообщение об ошибке содержательным без лишней цены.

### Изоляция владельца: `NotFoundError` везде, никогда `PermissionDeniedError`

**Решение:** каждый метод `WalletRepository`, оперирующий конкретным кошельком (`get_by_id`, `update`, `delete`),
принимает и `wallet_id`, и `user_id` и фильтрует по обоим `WHERE wallet_id = :id AND user_id = :user_id` в одном
запросе. Если строка не найдена — репозиторий возвращает `None`/`False`, сервис поднимает `NotFoundError` (404).
Никогда не выполняется отдельный `SELECT` «существует ли кошелёк» с последующей проверкой владельца в Python и
никогда не поднимается `PermissionDeniedError` (403).

**Обоснование.** 403 на чужой `wallet_id` подтвердил бы постороннему пользователю, что такой кошелёк вообще
существует (просто не у него), — утечка информации о чужих данных через код ответа. 404 для «не существует» и
«существует, но чужой» неотличимы снаружи, что и требуется: пользователь не должен узнавать о чужих `id` даже
косвенно. Фильтрация по обоим полям в одном `WHERE`, а не «`SELECT` по id → проверка `user_id` в сервисе», —
дополнительно закрывает TOCTOU-щель и держит бизнес-правило «данные пользователя изолированы» на уровне запроса,
а не на честном слове вызывающего кода (тот же принцип, что уже описан в AGENTS.md: «каждый запрос к
пользовательским данным фильтруется по владельцу»).

### Порядок `currency_ids` в ответе — `JOIN` с сортировкой по коду валюты

**Решение:** при чтении кошелька (`get_by_id`, `list`) репозиторий получает `currency_ids` через `JOIN
wallet_currencies ON wallet_currencies.currency_id = currencies.id ORDER BY currencies.code`, а не в порядке
вставки/PK. Тот же принцип детерминированного человекочитаемого порядка, что уже используется в
`CurrencyRepository.list` (`ORDER BY currencies.code`).

**Альтернатива (отвергнута): порядок вставки (`ORDER BY wallet_currencies.currency_id`) или без сортировки.**
Отвергнута — порядок вставки не несёт смысла для пользователя (зависит от истории `PUT`-запросов, а не от
содержания), а отсутствие сортировки в PostgreSQL не гарантирует стабильного порядка между вызовами вообще (без
`ORDER BY` СУБД не обязана возвращать строки в одном и том же порядке). Сортировка по коду валюты — тот же
принцип, что уже принят для списка валют, и предсказуема для клиента API.

### Порядок списка кошельков — `created_at ASC, id ASC`

**Решение:** `GET /api/wallets` сортирует по `created_at ASC`, затем `id ASC` как детерминированный tie-breaker
(две записи с одинаковым `created_at` — крайне маловероятно на практике с точностью `timestamptz`, но `ORDER BY`
без полного tie-breaker не гарантирует стабильную пагинацию между запросами).

**Альтернатива (отвергнута): ручной порядок (поле `sort_order`/`position`).** Отвергнута — задача 008 явно не
включает функцию ручного упорядочивания («Объём» задачи её не перечисляет, открытый вопрос закрыт оркестратором:
вне рамок). Добавление поля порядка сейчас было бы нереализуемой функциональностью без API для её изменения —
мёртвое поле в схеме.

### `WalletRepository.update` — полная замена в одной транзакции

**Решение:** сигнатура протокола:

```python
class WalletRepository(Protocol):
    async def add(self, wallet: Wallet) -> Wallet: ...
    async def get_by_id(self, wallet_id: UUID, user_id: UUID) -> Wallet | None: ...
    async def list(self, user_id: UUID, *, limit: int, offset: int) -> list[Wallet]: ...
    async def count(self, user_id: UUID) -> int: ...
    async def update(
        self, wallet_id: UUID, user_id: UUID, *, name: str, icon: str, currency_ids: Sequence[UUID], now: datetime
    ) -> Wallet | None: ...
    async def delete(self, wallet_id: UUID, user_id: UUID) -> bool: ...
```

Реализация `update` в одной сессии: `UPDATE wallets SET name=..., icon=..., updated_at=... WHERE id=... AND
user_id=... RETURNING ...` (если строк 0 — кошелёк не найден/чужой, сразу `None`, без лишних запросов), затем
`DELETE FROM wallet_currencies WHERE wallet_id=...` и `INSERT` нового набора. Репозиторий не коммитит — транзакция
управляется `utils.database.get_session` (commit в конце запроса, rollback при исключении), поэтому частичное
применение (обновили `wallets`, но не успели пересобрать `wallet_currencies`) невозможно: либо весь запрос
целиком, либо откат при любом исключении внутри.

**Альтернатива (отвергнута): вычислять diff (добавить/удалить только изменившиеся валюты).** Отвергнута — задача
явно определяет `PUT` как полную замену (вопрос 2 закрыт: партиального `PATCH` нет), а diff усложнил бы
реализацию (нужно сравнивать текущий и новый наборы) ради оптимизации, которая не нужна: наборы валют кошелька —
маленькие (обычно 1–3 записи), `DELETE`+`INSERT` всего набора не создаёт измеримой нагрузки и проще читается.

### Валидация входных схем — Pydantic-валидатор до похода в БД

**Решение:** `WalletCreate`/`WalletUpdate` (одна форма для создания и полной замены):

```python
class WalletCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: IconName
    currency_ids: list[UUID]

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name не может быть пустым")
        return stripped

    @field_validator("currency_ids")
    @classmethod
    def validate_currency_ids(cls, value: list[UUID]) -> list[UUID]:
        if not value:
            raise ValueError("currency_ids не может быть пустым списком")
        if len(set(value)) != len(value):
            raise ValueError("currency_ids не должен содержать дубликаты")
        return value
```

`WalletUpdate = WalletCreate` (алиас типа) — форма запроса идентична, `PUT` делает полную замену тех же трёх
полей; отдельный класс не добавил бы новых полей/правил, а два одинаковых класса разошлись бы при будущей правке.
Отклонение пустого списка и дублей — на уровне Pydantic (422 до похода в БД), а не в сервисе: это форма данных,
не бизнес-правило (существование `currency_id` в справочнике — уже бизнес-правило, оно в `WalletService`, потому
что требует обращения к репозиторию).

**Альтернатива (отвергнута): `WalletUpdate` как отдельный класс, дублирующий поля `WalletCreate`.** Отвергнута —
задача прямо указывает «одинаковая форма»; дублирование трёх полей и двух валидаторов нарушило бы DRY без
причины, раз семантика запроса одна и та же (полная замена).

### Эндпоинты и `depends/wallet.py`

`api/wallets.py`, по образцу `api/currencies.py`, но с `Depends(get_current_user)` на каждом маршруте и
`user_id: Annotated[UUID, Depends(get_current_user)]`, передаваемым в сервис явным аргументом (как того требует
AGENTS.md: «сервисы получают user_id явным аргументом»):

```python
router = APIRouter(prefix="/api/wallets", tags=["Wallets"])

@router.post("", response_model=WalletOut, status_code=201)
@router.get("", response_model=Page[WalletOut])
@router.get("/{wallet_id}", response_model=WalletOut)
@router.put("/{wallet_id}", response_model=WalletOut)
@router.delete("/{wallet_id}", status_code=204)
```

`depends/wallet.py`:

```python
def get_wallet_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> WalletRepository:
    return SqlWalletRepository(session)

def get_wallet_service(
    wallets: Annotated[WalletRepository, Depends(get_wallet_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
) -> WalletService:
    return WalletService(wallets, currencies)
```

`WalletService` зависит от двух узких протоколов (`WalletRepository`, `CurrencyRepository`), а не от одного
«god»-репозитория, — соответствует `I`/`D` из SOLID: сервис использует ровно те методы, которые ему нужны
(`missing_ids` у `CurrencyRepository`, шесть методов `WalletRepository`), и ни один из протоколов не знает о
существовании другого.

## Risks / Trade-offs

- [`ON DELETE RESTRICT` на `wallet_currencies.currency_id` защищает от несуществующего сегодня сценария (удаление
  валюты не реализовано)] → дешёвая защита на будущее, не требующая кода сейчас; альтернатива (без FK или
  `CASCADE`) была бы тихим повреждением данных, если удаление валют появится позже без пересмотра этого решения.
- [`update` делает `DELETE`+`INSERT` всего набора валют при каждом `PUT`, даже если реально изменилось только
  `name`] → приемлемо: наборы валют маленькие, а альтернатива (diff) усложняет код ради не существующей сейчас
  нагрузки; если станет проблемой, решение локализовано в одном методе репозитория.
- [Физическое безусловное удаление кошелька сейчас, без защиты от потери связанных данных] → осознанный выбор
  задачи 008 (см. Open Questions), задел на 010 зафиксирован ниже и в Migration Plan; риск ограничен тем, что
  таблицы операций ещё физически не существует — терять пока нечего.
- [`NotFoundError` вместо `PermissionDeniedError` на чужой `wallet_id` усложняет диагностику на стороне клиента
  (нельзя отличить «опечатался в id» от «чужой кошелёк»)] → осознанный компромисс безопасности vs. удобства
  диагностики, уже принятый как паттерн проекта (см. AGENTS.md про изоляцию пользовательских данных); frontend не
  должен и не будет полагаться на это различие.

## Migration Plan

Миграция Alembic `20260929_0004` (`down_revision = "20260929_0003"`), одна ревизия, две таблицы:
1. `create_table("wallets", ...)` — как описано в Decisions.
2. `create_table("wallet_currencies", ...)` — как описано в Decisions, после `wallets` (FK-зависимость).
3. `downgrade()` — `drop_table("wallet_currencies")`, затем `drop_table("wallets")` (обратный порядок).

Откат безопасен: на момент задачи 008 ничего, кроме кошельков, не ссылается на эти таблицы (категории 009 и
операции 010 ещё не реализованы), удаление обеих таблиц не затрагивает данные других сущностей.

**Задел на будущее (не реализуется в этой задаче).** Когда появится задача 010 («Доходы и расходы»):
- потребуется таблица операций с FK на `wallets.id`, вероятно `ON DELETE RESTRICT` — чтобы запретить удаление
  кошелька, по которому есть операции (409 `AlreadyExistsError`/отдельная ошибка на выбор 010), либо явный каскад,
  если продуктовое решение будет иным — это решает design.md задачи 010, не 008;
- `WalletService.update_wallet` может потребовать запрет удаления из набора валюты, по которой уже есть операции
  (проверка перед `DELETE FROM wallet_currencies`) — сейчас `PUT` делает полную замену без такой проверки, потому
  что истории операций, которую нужно было бы защищать, ещё не существует.

## Open Questions

Все три открытых вопроса задачи 008 (`docs/tasks/008_wallets.md`) решены оркестратором:

1. **Запрет или каскад при удалении кошелька с операциями?** Решено: таблицы операций в этой задаче ещё нет (010
   вне рамок), ограничивать нечем — удаление кошелька физическое и безусловное (по `wallet_id` + `user_id`
   владельца). Задел на будущее зафиксирован в Migration Plan: 010 потребует FK-защиту (`RESTRICT` от операций к
   `wallets`, вероятно 409).
2. **Смена набора валют у кошелька с историей?** Решено: истории операций тоже ещё нет, `PUT` делает полную замену
   набора валют (`name`, `icon`, `currency_ids`) без ограничений. Задел на будущее: 010 может потребовать запрет
   удаления из набора валюты, по которой есть операции, — вне рамок 008.
3. **Порядок отображения кошельков?** Решено: ручной sort/reorder не входит в «Объём» задачи 008. `GET
   /api/wallets` возвращает список, отсортированный по `created_at ASC`, затем `id ASC` как детерминированный
   tie-breaker.
