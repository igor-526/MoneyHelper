## Context

Скелет вертикального среза (сущность → протокол → репозиторий → сервис → API → тесты) уже задан задачами 008
(`wallets`) и 009 (`categories`) — задача 010 переиспользует его, но добавляет то, чего раньше не было:

- Первая сущность, ссылающаяся сразу на два чужих агрегата пользователя (`wallets`, `categories`) — раньше только
  `wallets` ссылался на чужой репозиторий (`CurrencyRepository.missing_ids`), но не на другую пользовательскую
  сущность.
- Первое денежное поле, дошедшее до API/БД, — `core/schemas/money.py` (`Money`) и `models/types.py` (`MONEY`) уже
  существуют (заготовлены заранее), но ни один эндпоинт их ещё не использовал.
- Первая таблица с `ON DELETE RESTRICT` от новой сущности к уже существующим (`wallets`, `categories`) — раньше
  `RESTRICT` был только от M2M-таблицы к глобальному справочнику валют (`wallet_currencies.currency_id`).
- Первый агрегирующий запрос (баланс) вместо простого CRUD/списка.
- Явно предписанное «Объёмом» задачи 010 разделение на две таблицы («операции и ноги»), при том что на уровне
  домена и API для этой задачи используется плоская форма (одна нога на операцию).

Уже готовы и переиспользуются без изменений: `core/entities/base.py` (`Entity`, `TimestampMixin`),
`core/schemas/pagination.py` (`Page`, `PageParams`), `core/schemas/money.py` (`Money` — до 24 цифр, 8 знаков, в
JSON строка), `models/types.py` (`MONEY` — `NUMERIC(24, 8)`), `core/exceptions/base.py` (`ClientError`,
`NotFoundError`, `AlreadyExistsError` — новый нужен только `ConflictError`), `depends/auth.py`
(`get_current_user`), паттерн `CategoryListParams(PageParams)` (пагинация + доп. query-параметры в одной модели,
см. `api/schemas/category.py`) как образец для фильтров списка операций.

## Goals / Non-Goals

**Goals:**
- CRUD операций пользователя: создание, чтение одной и списка (фильтры, пагинация, сортировка), полная замена
  (`PUT`), физическое удаление.
- Валидация: кошелёк и категория существуют и принадлежат пользователю; валюта операции входит в набор валют
  кошелька; сумма положительна и не превышает число знаков валюты (без округления).
- Баланс по кошельку и валюте — агрегированный расчёт на лету, без кэша, по всем валютам кошелька (включая
  нулевые).
- Изоляция по владельцу — тот же принцип, что в `wallets`/`categories`.
- Защита `wallets`/`categories` от удаления при наличии операций (`ON DELETE RESTRICT` + `ConflictError`, 409).

**Non-Goals:**
- Несколько ног на одну операцию (многовалютные пополнения), переводы между кошельками — задача 011.
- Аналитика — задача 012.
- Кэширование баланса.
- Частичное обновление (`PATCH`).
- Ручной порядок отображения операций.
- Frontend UI операций и балансов.

## Decisions

### Плоская модель на уровне домена/API, две таблицы на уровне БД

**Решение:** `Transaction(Entity, TimestampMixin)` — плоская сущность без вложенного списка «ног»:

```python
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.entities.base import Entity, TimestampMixin


class Transaction(Entity, TimestampMixin):
    user_id: UUID
    wallet_id: UUID
    category_id: UUID
    currency_id: UUID
    amount: Decimal
    occurred_at: datetime
```

На уровне БД — ровно то, что явно требует «Объём» задачи 010 («таблицы операций и ног»): `transactions` (шапка
операции) и `transaction_legs` (валюта + сумма, составной `PrimaryKeyConstraint(transaction_id, currency_id)`, по
образцу `wallet_currencies`). Для задачи 010 у операции всегда ровно одна строка в `transaction_legs` — это
инвариант, который поддерживает `TransactionService` (одна нога создаётся/заменяется в той же транзакции БД, что
и шапка), а не ограничение схемы: составной PK допускает несколько строк на `transaction_id`, что и есть
осознанный задел под многовалютные пополнения задачи 011 — та расширит `TransactionRepository`/`TransactionService`
до работы со списком ног, не трогая схему БД.

**Альтернатива (отвергнута): value-object `TransactionLeg` и `Transaction.legs: tuple[TransactionLeg, ...]` на
уровне сущности/API уже сейчас.** Отвергнута — для 010 список всегда из одного элемента, и вся оболочка списка
(итерация, валидация «ровно один элемент», разворачивание в API-схеме) была бы кодом без назначения: он ничего не
делает сегодня и добавляет косвенность на каждом слое (сущность, схема, сервис) ради возможности, которая
появится только в 011. Это прямое нарушение YAGNI и уже устоявшегося в проекте принципа «не создавай лишних
слоёв там, где это неоправданно» (тот же аргумент, что отклонил отдельную сущность `WalletCurrency` в design.md
`wallets`). Когда 011 реально введёт несколько ног, `TransactionLeg` появится вместе с этой задачей — расширение
через новый код, а не правка работающего (`O` из SOLID).

### `ON DELETE RESTRICT` от `transactions` к `wallets`/`categories`, `CASCADE` к `users`, `RESTRICT` от `transaction_legs.currency_id`

**Решение:**

```python
transactions = Table(
    "transactions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("wallet_id", UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False),
    Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
)

transaction_legs = Table(
    "transaction_legs",
    metadata,
    Column("transaction_id", UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
    Column("currency_id", UUID(as_uuid=True), ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=False),
    Column("amount", MONEY, nullable=False),
    PrimaryKeyConstraint("transaction_id", "currency_id"),
    CheckConstraint("amount > 0", name="ck_transaction_legs_amount_positive"),
)
```

- `transactions.user_id → users.id ON DELETE CASCADE` — собственные данные пользователя, уходят вместе с ним
  (тот же принцип, что у `wallets.user_id`/`categories.user_id`).
- `transactions.wallet_id → wallets.id ON DELETE RESTRICT` и `transactions.category_id → categories.id ON DELETE
  RESTRICT` — история операций не должна теряться или обесцениваться при удалении кошелька/категории. `RESTRICT`
  заставляет пользователя сначала разобраться с операциями (удалить их или дождаться будущей функции переноса),
  прежде чем можно будет удалить кошелёк/категорию, — данные о прошлых доходах/расходах не исчезают неявно и не
  остаются с оборванной ссылкой.
- `transaction_legs.transaction_id → transactions.id ON DELETE CASCADE` — нога принадлежит операции целиком, это
  её собственные данные (как `wallet_currencies.wallet_id → wallets.id`).
- `transaction_legs.currency_id → currencies.id ON DELETE RESTRICT` — тот же принцип защиты глобального
  справочника, что уже применён в `wallet_currencies.currency_id`.

**Альтернатива (отвергнута): `CASCADE` от `transactions` к `wallets`/`categories` (удаление кошелька/категории
удаляет все операции).** Отвергнута — это была бы тихая потеря финансовой истории пользователя одним кликом
«удалить кошелёк». Для справочных сущностей (кошельки, категории) физическое каскадное удаление уместно (данные
самого пользователя), но для операций, ссылающихся на них, каскад стирает историю без явного подтверждения этого
конкретно — RESTRICT явно требует от пользователя (или будущего UI) разобраться с операциями сначала. Также
`RESTRICT` — уже установленный в проекте паттерн защиты «важных» данных от каскадной потери (`wallet_currencies
.currency_id`, задел на это же решение зафиксирован в design.md `wallets`/`categories` как открытый вопрос для
задачи 010).

**Альтернатива (отвергнута): `SET NULL`.** Отвергнута — `wallet_id`/`category_id` не `nullable` по построению
(операция без кошелька или категории бессмысленна), `SET NULL` потребовал бы сделать поля опциональными и добавить
отдельную логику для операций-сирот, которой продукт не описывает.

### Тип операции — не отдельное поле, а вычисляется через `categories.type`

**Решение:** `transactions` не хранит `type` (`income`/`expense`). Фильтрация по типу (`GET
/api/transactions?type=...`) и расчёт баланса используют `JOIN transactions.category_id = categories.id` и читают
`categories.type`.

**Альтернатива (отвергнута): денормализованное поле `transactions.type`, копируемое из категории при
создании/обновлении.** Отвергнута — создаёт ровно ту рассинхронизацию, которую задача 010 явно просит исключить
(«категория должна соответствовать типу операции»): если у операции было бы собственное поле `type`, привязка
операции к категории могла бы разойтись с ним при любой правке в обход валидации сервиса (прямое изменение БД,
будущий баг), а само это поле как раз было бы «дубликатом истины». Без него утверждение задачи верно по
построению — рассинхронизироваться нечему. Цена — обязательный `JOIN` на фильтре по типу и на балансе вместо
плоского `WHERE`; для персонального приложения с некрупным датасетом это не проблема производительности, а
`categories.id` — первичный ключ, `JOIN` дешёвый.

### Баланс — агрегирующий запрос на лету, без кэша

**Решение:** `TransactionRepository.balances(wallet_id, user_id) -> dict[UUID, Decimal]` строит баланс одним
запросом:

```sql
SELECT tl.currency_id, SUM(CASE WHEN c.type = 'income' THEN tl.amount ELSE -tl.amount END)
FROM transaction_legs tl
JOIN transactions t ON t.id = tl.transaction_id
JOIN categories c ON c.id = t.category_id
WHERE t.wallet_id = :wallet_id AND t.user_id = :user_id
GROUP BY tl.currency_id
```

`TransactionService.get_wallet_balances` сначала проверяет кошелёк через `WalletRepository.get_by_id(wallet_id,
user_id)` (404, если чужой/не существует), затем достраивает нулевые балансы, **переиспользуя уже отсортированный
по коду валюты `wallet.currency_ids`** (эта сортировка уже реализована в `WalletRepository.get_by_id`/`list` для
008 через `JOIN wallet_currencies/currencies ORDER BY currencies.code`):

```python
balances = await self._transactions.balances(wallet_id, user_id)
return [(currency_id, balances.get(currency_id, Decimal("0"))) for currency_id in wallet.currency_ids]
```

Так порядок ответа `GET /api/wallets/{wallet_id}/balances` (по коду валюты, как у `currency_ids` в `WalletOut`)
получается бесплатно — без второго `JOIN currencies` и без повторной сортировки в `TransactionRepository`.

**Альтернатива (отвергнута): кэшированный баланс (материализованное поле/таблица, инвалидируемая при
изменении операций).** Отвергнута оркестратором — открытый вопрос задачи 010 закрыт в пользу «на лету»: нет
проблемы инвалидации кэша (баланс всегда синхронен с операциями), датасет персонального приложения небольшой
(один пользователь — десятки/сотни операций, не миллионы), а кэш добавил бы отдельный механизм согласованности
(что произойдёт при удалении/изменении операции, при удалении кошелька) ради оптимизации, которая пока не нужна —
нарушение принципа проекта «без лишних абстракций сверх необходимого».

**Альтернатива (отвергнута): считать баланс только по валютам, встречавшимся в операциях (без явных нулей).**
Отвергнута оркестратором — по всем валютам кошелька нагляднее для пользователя и проще фронтенду (не нужно
объединять список валют кошелька со списком балансов на клиенте).

### `GET /api/wallets/{wallet_id}/balances` — маршрут в файле, логически принадлежащем `transactions`

**Решение:** эндпоинт технически размещается в `api/transactions.py` (там же, где `TransactionService`, от
которого он зависит), но по HTTP-пути принадлежит кошельку. `api/transactions.py` объявляет два роутера:

```python
router = APIRouter(prefix="/api/transactions", tags=["Transactions"])
wallet_balances_router = APIRouter(tags=["Transactions"])


@wallet_balances_router.get("/api/wallets/{wallet_id}/balances", response_model=list[WalletBalanceOut])
async def get_wallet_balances(
    wallet_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> list[WalletBalanceOut]: ...
```

`main.py` подключает оба роутера рядом (`transactions_router`, `wallet_balances_router`), оба из одного модуля.
`wallet_balances_router` объявлен без `prefix`, а маршрут задаёт полный путь `/api/wallets/{wallet_id}/balances`
явно — FastAPI не требует, чтобы путь роутера совпадал с директорией/модулем, где он объявлен.

**Альтернатива (отвергнута): разместить маршрут в `api/wallets.py`, где живёт `wallets_router` с совпадающим
префиксом `/api/wallets`.** Отвергнута — обработчик зависел бы от `TransactionService`
(`core/services/transaction.py`), а `api/wallets.py` тогда импортировал бы зависимости чужой сущности, нарушая `S`
из SOLID (файл роутера кошельков отвечал бы за два разных сценария использования — CRUD кошельков и агрегацию
операций). Путь URL — деталь HTTP-адресации, а не сигнал о том, в каком файле должен жить обработчик; код,
работающий с операциями, логичнее держать рядом с остальным кодом операций.

**Альтернатива (отвергнута): `GET /api/transactions/balances?wallet_id=...` (баланс под префиксом
`/api/transactions`).** Отвергнута оркестратором явно — путь предписан `/api/wallets/{wallet_id}/balances»,
поскольку баланс концептуально свойство кошелька с точки зрения клиента API.

### Валидация суммы: положительность и число знаков валюты — без округления

**Решение:** `amount: Money` в Pydantic-схеме (`Field(gt=0)` дополнительно к ограничениям `Money`) отклоняет
неположительные суммы на границе API (400) до похода в сервис; `CheckConstraint("amount > 0")` в БД — защита на
случай прямых изменений данных в обход API. Число знаков после запятой проверяется в `TransactionService` (нужен
поход в БД за `Currency.decimal_places`, поэтому не может быть чистой Pydantic-валидацией без контекста):

```python
currency = await self._currencies.get_by_id(currency_id)
...
exponent = amount.as_tuple().exponent
if isinstance(exponent, int) and exponent < 0 and -exponent > currency.decimal_places:
    raise ClientError(
        f"Сумма содержит больше {currency.decimal_places} знаков после запятой, допустимых для валюты {currency.code}"
    )
```

Превышение — `ClientError` (400), сумма не округляется и не обрезается.

**Альтернатива (отвергнута): тихое округление суммы до `decimal_places` валюты.** Отвергнута оркестратором —
открытый вопрос задачи 010 закрыт в пользу явной ошибки: тихое округление денежной суммы способно исказить то,
что фактически ввёл пользователь, без его ведома — неприемлемо для финансового приложения. Явная ошибка 400
позволяет клиенту показать понятное сообщение и попросить исправить ввод.

### Проверка валюты кошелька и существования кошелька/категории — в `TransactionService`, не в БД

**Решение:** `TransactionService` перед `add`/`update` вызывает `WalletRepository.get_by_id(wallet_id, user_id)` и
`CategoryRepository.get_by_id(category_id, user_id)` (оба уже возвращают `None` для чужого/несуществующего —
`NotFoundError`, 404), затем проверяет `currency_id in wallet.currency_ids` (`ClientError`, 400, если нет).
`TransactionRepository` не содержит этой бизнес-логики — только SQL.

**Обоснование.** Правило «валюта ноги обязана входить в набор валют кошелька» — бизнес-инвариант, а не
ограничение целостности данных, выразимое декларативным FK/`CheckConstraint` в PostgreSQL (нужна проверка
принадлежности значения одной колонки (`currency_id`) множеству, зависящему от другой строки в другой таблице
(`wallet_currencies` по `wallet_id`) — это не выражается обычным `CHECK`, потребовался бы триггер). Триггер
исключён тем же принципом, что уже действует в проекте («SQL или `select()` — только в `repositories`», бизнес-
правила — в `core/services`): триггер спрятал бы бизнес-логику в схему БД, недоступную для unit-тестирования на
fake-репозиториях. Это тот же паттерн, что `WalletService._ensure_currencies_exist` уже использует для проверки
существования валют.

### `NotFoundError`/`ClientError`/`ConflictError` — три разных кода на разные ситуации

**Решение:** повторяется паттерн `wallets`/`categories` — `NotFoundError` (404) для отсутствующей/чужой операции,
кошелька, категории; `ClientError` (400) для нарушения бизнес-правил при вводе (валюта не из набора кошелька,
превышение знаков после запятой, `date_from > date_to`); **новый** `ConflictError` (409, `core/exceptions/base.py`)
— отдельно от `AlreadyExistsError` (409) для другого случая: «нельзя удалить/изменить, ресурс используется
другими данными».

```python
class ConflictError(ClientError):
    status_code = 409
```

`WalletRepository.delete()`/`CategoryRepository.delete()` оборачивают `DELETE` в `try/except IntegrityError`:

```python
try:
    result = await self._session.execute(sa_delete(wallets).where(...).returning(wallets.c.id))
except IntegrityError as exc:
    raise ConflictError("Кошелёк нельзя удалить: есть операции") from exc
```

(аналогично для `categories`: «Категорию нельзя удалить: есть операции»).

**Альтернатива (отвергнута): переиспользовать `AlreadyExistsError` для обоих случаев.** Отвергнута — оба
исключения дают 409, но семантически разные события: `AlreadyExistsError` — «конфликт при создании/обновлении
из-за нарушения уникальности» (пользователь пытается создать дубликат), `ConflictError` — «конфликт при удалении/
изменении из-за того, что ресурс используется» (пользователь пытается сломать ссылочную целостность). Смешивание
затруднило бы диагностику на клиенте (одно и то же исключение означало бы разные вещи в разных эндпоинтах) и
противоречило бы уже принятому в проекте принципу «у каждой ошибки свой класс с понятной семантикой»
(`core/exceptions/base.py`). Отдельный класс — минимальная цена (три строки), сохраняющая ясность.

**Альтернатива (отвергнута): предварительная проверка «есть ли операции» в `WalletService`/`CategoryService`
перед `DELETE`.** Отвергнута — TOCTOU-щель (операция может появиться между проверкой и удалением) и лишний запрос;
перехват `IntegrityError` — тот же паттерн, что уже применяется для уникальности в `CategoryRepository.add`/
`.update`, здесь применяется симметрично для `RESTRICT`.

### Список операций — фильтры и сортировка `occurred_at DESC, id DESC`

**Решение:** `GET /api/transactions` принимает `wallet_id: UUID | None`, `category_id: UUID | None`, `type:
CategoryType | None`, `date_from: datetime | None`, `date_to: datetime | None` — одной моделью
`TransactionListParams(PageParams)`, по образцу `CategoryListParams` (Pydantic-модель как единственный
query-параметр обработчика — иначе FastAPI не разворачивает её поля в отдельные query-параметры). `date_from >
date_to` (если оба заданы) — `ClientError` (400) на уровне сервиса (сравнение двух полей одной модели не
выражается декларативным `Field`, нужен код).

Сортировка — `occurred_at DESC, id DESC` (новые сначала), а не `created_at ASC, id ASC`, принятое в
`wallets`/`categories`.

**Обоснование отклонения от `wallets`/`categories`.** Там список — небольшая справочная сущность (кошельки,
категории заводятся редко, пользователь видит и правит весь список целиком, порядок создания не важен для UX).
Список операций — лента транзакций, для которой стандартный и ожидаемый пользователем UX — как в банковской
выписке: сначала недавние. `occurred_at` (бизнес-дата операции) — более осмысленный ключ сортировки, чем
`created_at` (техническое время вставки строки), потому что пользователь может внести операцию задним числом;
`id` — детерминированный tie-breaker при равном `occurred_at`, тот же принцип, что и везде в проекте.

**Альтернатива (отвергнута): `created_at ASC, id ASC`, как в `wallets`/`categories`, ради единообразия кода.**
Отвергнута — единообразие ради единообразия здесь противоречило бы ожидаемому UX ленты операций; разные по
природе списки (справочник вводимых пользователем сущностей vs. лента событий во времени) обоснованно сортируются
по-разному, это не отступление без причины.

### `CurrencyRepository.get_by_id` — новый метод по аналогии с существующими

**Решение:**

```python
async def get_by_id(self, currency_id: UUID) -> Currency | None: ...
```

Реализация — `SELECT ... WHERE currencies.c.id == currency_id`, `LIMIT 1`. Сигнатура выбрана по прямой аналогии с
`WalletRepository.get_by_id(wallet_id, user_id)`/`CategoryRepository.get_by_id(...)`, но без `user_id` — валюты
глобальный справочник без владельца (как и у существующих `list`/`count`/`upsert_many`/`missing_ids`).

**Альтернатива (отвергнута): расширить `missing_ids` до возврата не только отсутствующих id, но и найденных
записей (`dict[UUID, Currency]`).** Отвергнута — `TransactionService` нужна ровно одна валюта за раз (валюта
конкретной операции, не множество валют кошелька, как у `WalletService`), `missing_ids` уже используется
`WalletService` с своей чёткой семантикой «что отсутствует»; смешивание двух разных сценариев использования в один
метод увеличило бы поверхность протокола без необходимости (`I` из SOLID).

## Risks / Trade-offs

- [`ON DELETE RESTRICT` от `transactions` к `wallets`/`categories` требует от пользователя удалить операции перед
  удалением кошелька/категории, но задача 010 не даёт способа массово перенести/удалить операции разом] →
  осознанный компромисс: физическое поштучное удаление уже есть (`DELETE /api/transactions/{id}`), массовые
  операции — вне рамок 010; риск ограничен тем, что это защита от потери данных, а не блокировка без выхода.
- [Тип операции вычисляется через `JOIN` на каждый запрос с фильтром по типу и на баланс, а не читается напрямую]
  → приемлемо для персонального приложения (небольшой датасет, `categories.id` — PK); при росте нагрузки решение
  локализовано в `TransactionRepository`.
- [Баланс на лету пересчитывается при каждом запросе `GET /api/wallets/{wallet_id}/balances`, а не читается из
  готового значения] → осознанный выбор (см. Decisions); один агрегирующий `GROUP BY` по строкам одного кошелька
  — дешёвый запрос при персональном объёме данных.
- [`transaction_legs` допускает несколько строк на `transaction_id` уже сейчас, хотя 010 использует только одну] →
  осознанный задел под 011; риск — инвариант «ровно одна нога» держится только в сервисе, не в схеме; смягчается
  тем, что единственная точка записи в `transaction_legs` — `TransactionRepository`, которым управляет только
  `TransactionService`.
- [`ConflictError` — новый класс исключений, у которого пока только два случая использования (`wallets`,
  `categories`)] → минимальная цена (три строки в `core/exceptions/base.py`), оправданная ясностью семантики (см.
  Decisions); не нарушает `AlreadyExistsError`, у которого своя, уже устоявшаяся семантика.

## Migration Plan

Миграция Alembic `20260929_0006` (`down_revision = "20260929_0005"`), одна ревизия, две таблицы:
1. `create_table("transactions", ...)` — FK на `users`, `wallets`, `categories` (все три уже существуют).
2. `create_table("transaction_legs", ...)` — после `transactions` (FK-зависимость), FK на `transactions`,
   `currencies`.
3. `downgrade()` — `drop_table("transaction_legs")`, затем `drop_table("transactions")` (обратный порядок).

Отдельного изменения существующих таблиц миграцией не требуется: `WalletRepository.delete()`/
`CategoryRepository.delete()` меняют только Python-код (перехват `IntegrityError`), а `ON DELETE RESTRICT`
появляется как часть FK новых таблиц `transactions`/`transaction_legs`, а не как `ALTER TABLE` на `wallets`/
`categories`.

Откат безопасен только если на момент отката в БД нет строк `transactions`/`transaction_legs` (типовое условие
любой ревизии Alembic — откат схемы, не данных); ничего, кроме операций, на эти две таблицы пока не ссылается.

**Задел на будущее (не реализуется в этой задаче).** Когда появится задача 011 («Пополнения и переводы»):
- `transaction_legs` расширится до реального использования нескольких строк на `transaction_id` (многовалютные
  пополнения) — схема уже это допускает, изменится только `TransactionService`/`TransactionRepository`, не
  таблица;
- появится сущность/сценарий «перевод между кошельками» — вероятно, пара операций или отдельная сущность,
  решается в design.md задачи 011.

## Open Questions

Все четыре открытых вопроса задачи 010 (`docs/tasks/010_transactions.md`) решены оркестратором:

1. **Баланс на лету или кэшируется?** Решено: на лету, без кэша — раздел Decisions «Баланс — агрегирующий запрос
   на лету, без кэша».
2. **Одна таблица для ног или две?** Решено: две таблицы (`transactions` + `transaction_legs`), как явно требует
   «Объём» задачи 010, при плоской форме на уровне домена/API для этой задачи — раздел Decisions «Плоская модель
   на уровне домена/API, две таблицы на уровне БД».
3. **Часовой пояс и дата операции?** Решено: `occurred_at` — `DateTime(timezone=True)` (aware datetime, как и
   `created_at`/`updated_at` во всём проекте), устанавливается клиентом в запросе или по умолчанию `Clock.now()`,
   если не передан. Отдельного вопроса часового пояса как открытой проблемы не остаётся: `timestamptz` в
   PostgreSQL хранит момент времени в UTC независимо от часового пояса клиента, конвертация в локальное время
   пользователя — забота frontend (вне рамок backend-задачи 010).
4. **Округление по знакам валюты?** Решено: без округления, превышение числа знаков — `ClientError` (400) —
   раздел Decisions «Валидация суммы: положительность и число знаков валюты — без округления».
