## Context

Задача 011 продолжает вертикальный срез, заложенный задачами 008 (`wallets`), 009 (`categories`) и 010
(`transactions`, заархивирована — `openspec/changes/archive/2026-09-29-transactions/`). design.md изменения
`transactions` явно предсказал именно эту задачу в разделе Migration Plan → «Задел на будущее»:

> `transaction_legs` расширится до реального использования нескольких строк на `transaction_id` (многовалютные
> пополнения) — схема уже это допускает, изменится только `TransactionService`/`TransactionRepository`, не
> таблица; появится сущность/сценарий «перевод между кошельками» — вероятно, пара операций или отдельная
> сущность, решается в design.md задачи 011.

Это прямое обоснование решений ниже: 011 не меняет схему `transactions`/`transaction_legs` (только код репозитория/
сервиса), и явно выбирает «отдельная сущность» для перевода — см. Decisions.

Уже готово и переиспользуется без изменений: `core/entities/base.py` (`Entity`, `TimestampMixin`),
`core/schemas/pagination.py` (`Page`, `PageParams`), `core/schemas/money.py` (`Money`), `models/types.py` (`MONEY`),
`core/exceptions/base.py` (`ClientError`, `NotFoundError`, `ConflictError` — уже существует с 010, новых
источников не добавляет, только новую точку возникновения), `WalletRepository._load_currency_ids_map` (паттерн
батч-загрузки дочерних строк без N+1 через `JOIN currencies ORDER BY currencies.code`, прямой прецедент для
агрегации ног операции).

## Goals / Non-Goals

**Goals:**
- Пополнение многовалютного кошелька: одна операция (`Transaction`) с несколькими «ногами», покрывающими ровно
  набор валют кошелька; курс между валютами пополнения выводится из сохранённых сумм, не хранится отдельно.
- Перевод между кошельками одного пользователя в одной валюте, без конвертации, при наличии этой валюты у обоих
  кошельков.
- CRUD `transfers` по образцу `transactions`: создание, чтение одной/списка (фильтр по кошельку, пагинация),
  полная замена, физическое удаление, изоляция по владельцу.
- Баланс кошелька учитывает вклад и операций, и переводов — через общий протокол-стратегию, без ветвления по типу
  источника.
- `Transaction`/`TransactionOut` переходят на ногозависимую форму (`legs`), закрывая задел 010; обычное создание/
  обновление операции (одна нога) остаётся с тем же плоским телом запроса.

**Non-Goals:**
- Конвертация валют внутри перевода — перевод это одна и та же сумма в одной валюте, перемещённая между
  кошельками.
- Редактирование пополнения через `PUT /api/transactions/{id}` — `PUT` остаётся плоским (одна нога); изменить
  пополнение можно только удалением и созданием заново через `POST /api/transactions/topups`.
- Внешние источники курсов валют.
- Хранение курса пополнения отдельным полем/сущностью.
- Аналитика — задача 012.
- Кэширование баланса — по-прежнему агрегирующий запрос на лету.
- Частичное обновление (`PATCH`).

## Decisions

### 1. `Transaction` — ногозависимая сущность; `TransactionLeg` как value-object без собственного `id`

**Решение:**

```python
# core/entities/transaction.py
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from core.entities.base import Entity, TimestampMixin


class TransactionLeg(BaseModel):
    currency_id: UUID
    amount: Decimal


class Transaction(Entity, TimestampMixin):
    user_id: UUID
    wallet_id: UUID
    category_id: UUID
    legs: tuple[TransactionLeg, ...]
    occurred_at: datetime
```

`TransactionLeg` не наследует `Entity` — строка `transaction_legs`, а не отдельная адресуемая сущность (у неё нет
собственного `id`, только составной PK `(transaction_id, currency_id)` в БД); точная аналогия с тем, почему
`WalletCurrency` не стала отдельной сущностью в design.md `wallets`. `Transaction.legs` — `tuple`, а не `list`, по
уже принятому в проекте паттерну неизменяемых коллекций на сущностях (`Wallet.currency_ids: tuple[UUID, ...]`).

Это ровно тот рефакторинг, который design.md `transactions` отложил как «Альтернатива (отвергнута для 010, но не
навсегда)» — тогда `TransactionLeg` был бы кодом без назначения (список всегда из одного элемента); теперь у
списка появляется второй потребитель (пополнение), и вложенность оправдана.

**Отвергнутая альтернатива: оставить `Transaction` плоской, а пополнение хранить как N отдельных `Transaction`
(по одной на валюту) с одинаковым `occurred_at`.** Отвергнута — это была бы попытка эмулировать многовалютную
операцию набором одновалютных без формальной связи между ними: ничего не мешало бы им разъехаться по времени/
удалиться по отдельности (нет транзакционной целостности «все ноги пополнения существуют или не существуют
вместе» без искусственного группирующего поля), а курс между ногами тогда пришлось бы восстанавливать по
косвенному совпадению `occurred_at`+`wallet_id`, а не по прямой связи. Составной PK `transaction_legs` уже
проектировался в 010 именно чтобы этого избежать.

### 2. Агрегация ног при чтении — один батч-запрос по всем найденным `transaction_id`, без N+1

**Решение:** прямая аналогия с `WalletRepository._load_currency_ids_map`:

```python
async def _load_legs_map(self, transaction_ids: Sequence[UUID]) -> dict[UUID, tuple[TransactionLeg, ...]]:
    if not transaction_ids:
        return {}
    rows = await self._session.execute(
        select(transaction_legs.c.transaction_id, transaction_legs.c.currency_id, transaction_legs.c.amount)
        .select_from(transaction_legs.join(currencies, transaction_legs.c.currency_id == currencies.c.id))
        .where(transaction_legs.c.transaction_id.in_(transaction_ids))
        .order_by(transaction_legs.c.transaction_id, currencies.c.code)
    )
    grouped: dict[UUID, list[TransactionLeg]] = defaultdict(list)
    for row in rows:
        grouped[row.transaction_id].append(TransactionLeg(currency_id=row.currency_id, amount=row.amount))
    return {transaction_id: tuple(legs) for transaction_id, legs in grouped.items()}


async def _load_legs(self, transaction_id: UUID) -> tuple[TransactionLeg, ...]:
    return (await self._load_legs_map([transaction_id])).get(transaction_id, ())
```

`get_by_id` вызывает `_load_legs([transaction_id])`; `list` сначала выполняет один запрос к `transactions`
(с `JOIN categories` при фильтре `type`, как раньше), затем один батч-запрос `_load_legs_map([row.id for row in
rows])` по всем найденным `id` сразу — итого не более двух запросов на страницу независимо от числа операций и
числа ног у каждой, что и требует «без N+1». Ноги отсортированы по коду валюты — тот же порядок, что уже даёт
`currency_ids` в `WalletOut`.

`add`/`update` пишут N строк в `transaction_legs` (bulk `insert(transaction_legs), [{...} for leg in
transaction.legs]`, тот же приём, что `WalletRepository._insert_currency_ids`), затем перечитывают операцию через
`get_by_id` — так вставленные ноги возвращаются уже в канонической сортировке по коду валюты без повторной
сортировки в Python (тот же приём, что `WalletRepository.add`/`.update`, возвращающие результат через
`get_by_id`/`_load_currency_ids`).

### 3. Обычное создание/обновление операции (`POST`/`PUT /api/transactions*`) — тело не меняется, всегда одна нога

**Решение:** `TransactionCreate`/`TransactionUpdate` остаются плоскими (`wallet_id`, `category_id`, `currency_id`,
`amount`, `occurred_at`). Сервис оборачивает единственную пару `currency_id`/`amount` в `legs=(TransactionLeg(...),
)` при построении сущности. `TransactionOut` — ногозависимая (`legs: list[TransactionLegOut]`) для обоих случаев:
и обычной операции (список из одного элемента), и пополнения (список из нескольких). Единый формат чтения проще
для клиента API, чем два разных response-контракта для «одной операции» в зависимости от способа создания.

**Отвергнутая альтернатива: сделать `TransactionCreate.legs: list[TransactionLegIn]` уже сейчас, приняв ровно
один элемент validator'ом.** Отвергнута — не даёт ничего новому сценарию (пополнение обязано быть отдельным
эндпоинтом из-за иной валидации, см. Decision 5) и усложняет самый частый случай использования API (одна валюта на
операцию) вложенным списком без причины. Простой плоский контракт для частого случая — осознанное сохранение
простоты, прямо предписанное задачей.

### 4. Общая логика проверки одной ноги — выделена в модуль-функцию, используется и `create_transaction`, и
`create_topup`, и `TransferService`

**Решение:** проверка «сумма не превышает число знаков валюты» (без округления) идентична везде, где в проект
попадает пара «валюта + сумма» — обычная операция, пополнение, перевод. Выносится в чистую функцию без побочных
зависимостей:

```python
# core/services/money_validation.py
from decimal import Decimal

from core.entities import Currency
from core.exceptions import ClientError


def ensure_amount_precision(amount: Decimal, currency: Currency) -> None:
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < 0 and -exponent > currency.decimal_places:
        raise ClientError(
            f"Сумма содержит больше {currency.decimal_places} знаков после запятой, "
            f"допустимых для валюты {currency.code}"
        )
```

`TransactionService` получает приватный метод-обёртку, объединяющий загрузку валюты и эту проверку:

```python
async def _validate_leg_amount(self, currency_id: UUID, amount: Decimal) -> Currency:
    currency = await self._currencies.get_by_id(currency_id)
    if currency is None:
        raise ClientError("Неизвестная валюта операции")
    ensure_amount_precision(amount, currency)
    return currency
```

`create_transaction`/`update_transaction` вызывают его один раз (после проверки `currency_id in
wallet.currency_ids`); `create_topup` вызывает его в цикле по всем ногам (после проверки полноты набора валют —
Decision 5). `TransferService` использует `ensure_amount_precision` напрямую (своя загрузка валюты, свой набор
проверок — «валюта входит в оба кошелька», не «входит в один»). Общая часть (декларативная проверка знаков) не
дублируется; специфичная часть (что именно проверяется на принадлежность) остаётся в каждом сервисе, потому что
это разные бизнес-правила, не разные реализации одного и того же.

**Отвергнутая альтернатива: общий класс `LegValidator` с методом `validate(wallet, currency_id, amount)`,
внедряемый как зависимость во все три сервиса.** Отвергнута — единственная действительно общая операция (проверка
знаков) уже умещается в одну чистую функцию без состояния; обёртывание её в класс с DI добавило бы протокол и
точку сборки в `depends/` ради возможности подменить логику, которая нигде не варьируется (`ensure_amount_precision`
не имеет альтернативных реализаций и не нуждается в моке — она уже тестируется как чистая функция). Это
нарушило бы тот же принцип YAGNI, которым в design.md `transactions` была отклонена преждевременная
`TransactionLeg`.

### 5. `POST /api/transactions/topups` — валидация полноты набора валют, категория обязана быть `income`

**Решение:** новый метод `TransactionService.create_topup(user_id, *, wallet_id, category_id, legs, occurred_at)`:

```python
async def create_topup(
    self, user_id: UUID, *, wallet_id: UUID, category_id: UUID, legs: Sequence[TransactionLegIn], occurred_at: datetime | None
) -> Transaction:
    wallet = await self._wallets.get_by_id(wallet_id, user_id)
    if wallet is None:
        raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
    category = await self._categories.get_by_id(category_id, user_id)
    if category is None:
        raise NotFoundError(CATEGORY_NOT_FOUND_MESSAGE)
    if category.type is not CategoryType.INCOME:
        raise ClientError("Пополнение возможно только с категорией дохода")
    self._ensure_legs_match_wallet_currencies(wallet, legs)
    for leg in legs:
        await self._validate_leg_amount(leg.currency_id, leg.amount)
    now = self._clock.now()
    transaction = Transaction(
        id=self._ids.new(),
        user_id=user_id,
        wallet_id=wallet_id,
        category_id=category_id,
        legs=tuple(TransactionLeg(currency_id=leg.currency_id, amount=leg.amount) for leg in legs),
        occurred_at=occurred_at if occurred_at is not None else now,
        created_at=now,
    )
    return await self._transactions.add(transaction)
```

`_ensure_legs_match_wallet_currencies` сравнивает `{leg.currency_id for leg in legs}` с `set(wallet.currency_ids)`:
при несовпадении собирает отсутствующие (`wallet_currency_ids - leg_currency_ids`) и лишние
(`leg_currency_ids - wallet_currency_ids`) множества и поднимает `ClientError` с сообщением, перечисляющим оба (по
кодам валют, не по `id`, для читаемости — требует по одному `get_by_id` на упомянутую валюту, объём — единицы
валют кошелька, не проблема производительности). Дубли в `legs` (одна и та же валюта дважды) обнаруживаются тем же
сравнением множеств как «лишняя» валюта, если задвоить — не даст пройти проверке равенства, что ошибочно засчитает
дубль как «отсутствие» второй уникальной валюты; поэтому длина `legs` дополнительно сверяется с длиной множества
валют: `len(legs) != len({leg.currency_id for leg in legs})` → отдельная явная ошибка «валюта в пополнении указана
более одного раза», проверяется до сравнения множеств.

**Механизм оформления — метод сервиса, не отдельный класс-стратегия.** Задача допускала оба варианта
(«`create_topup`, ИЛИ выделенный компонент-стратегия»). Выбран метод на существующем `TransactionService`:
пополнение не вариант поведения, между которыми переключаются во время выполнения (как источники баланса —
Decision 7, где стратегия оправдана, потому что список `contributors` действительно один интерфейс с несколькими
одновременно активными реализациями) — это единственный, всегда один и тот же сценарий использования, тесно
привязанный к тем же зависимостям (`TransactionRepository`, `WalletRepository`, `CategoryRepository`,
`CurrencyRepository`, `Clock`, `IdGenerator`), что и остальные методы `TransactionService`. Выделение в отдельный
класс потребовало бы либо дублировать эти зависимости, либо передавать `TransactionService` в конструктор нового
класса — оба варианта хуже прямого метода без выигрыша в тестируемости (unit-тест метода сервиса на
fake-репозиториях ничем не отличается от unit-теста отдельного класса).

**Отвергнутая альтернатива: разрешить частичный набор валют, конвертируя недостающие по последнему известному
курсу.** Отвергнута — открытый вопрос задачи 011 «расчёт курса при частичных ногах» закрыт запретом самого
сценария: раз частичные ноги запрещены валидацией, вопрос о курсе для них не возникает (см. также Decision 6 —
курс вообще не хранится отдельно, а выводится из полного набора ног).

### 6. Курс пополнения не хранится — выводится из ног при необходимости

**Решение:** сохранённые ноги (валюта + сумма по каждой) сами являются достаточным представлением курса: курс
между любой парой валют пополнения — отношение их сумм (`leg_a.amount / leg_b.amount`), вычислимое на чтении,
если когда-то понадобится (например, в аналитике 012). Никакого поля `rate`, никакой отдельной сущности/таблицы.

**Обоснование.** Формулировки задачи 011 — «курс выводится из ног» (Контекст) и «курс воспроизводим по сохранённым
ногам» (Критерии готовности) — говорят именно это: воспроизводимость гарантируется самими данными, дополнительное
хранение стало бы дублирующим источником истины (тот же аргумент, что в design.md `transactions` отклонил
денормализованное поле `transactions.type` — курс как «производное» от ног значение расходился бы с ногами при
любой правке в обход валидации).

**Отвергнутая альтернатива: поле `Transaction.rate: Decimal | None`, заполняемое только для пополнений.**
Отвергнута — оркестратором прямо запрещено («Не добавляй поле `rate` нигде»), и по существу избыточно: курс всегда
вычислим из `legs`, отдельное поле обязано было бы либо пересчитываться при каждом изменении ног (усложнение
`update`, которого для пополнений и так нет — Decision 3), либо рисковать рассинхронизацией.

### 7. Перевод между кошельками — отдельная сущность/таблица `transfers`, не пара связанных операций

**Решение:** новый вертикальный срез `transfers` по образцу `transactions`, но проще (одна таблица, без «ног» —
перевод всегда одна валюта, одна сумма):

```python
# models/transfer.py
transfers = Table(
    "transfers",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("from_wallet_id", UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False),
    Column("to_wallet_id", UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False),
    Column("currency_id", UUID(as_uuid=True), ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=False),
    Column("amount", MONEY, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
    CheckConstraint("from_wallet_id <> to_wallet_id", name="ck_transfers_different_wallets"),
)
```

`user_id → users.id ON DELETE CASCADE` (собственные данные пользователя, как везде); `from_wallet_id`/
`to_wallet_id → wallets.id ON DELETE RESTRICT` (история перемещений денег не должна тихо теряться при удалении
кошелька — тот же принцип, что `transactions.wallet_id`); `currency_id → currencies.id ON DELETE RESTRICT` (защита
глобального справочника, как везде).

**Отвергнутая альтернатива: перевод как пара связанных операций (`Transaction` расхода у `from_wallet_id` +
`Transaction` дохода у `to_wallet_id`).** Отвергнута — открытый вопрос задачи 011 прямо называет цену этого
варианта: `category_id` у `transactions` пришлось бы делать необязательным, либо вводить синтетическую
«служебную» категорию перевода на пользователя. Оба варианта размывают чистую семантику «категория = доход или
расход» (`categories.type` — закрытый enum ровно из этих двух значений), которую 009/010 установили как
единственный источник истины типа операции. Перевод — ни доход, ни расход (он не меняет совокупный капитал
пользователя, только его распределение между кошельками), поэтому попытка выразить его через категорию была бы
концептуальной ложью в данных, а не только неудобством API. Дополнительная цена: пара операций требовала бы
атомарной согласованности двух строк `transactions` + двух строк `transaction_legs` и логики "найти и удалить/
обновить обе разом" при `PUT`/`DELETE` перевода — сложнее, чем одна строка `transfers`.

**Отвергнутая альтернатива: `category_id` в `transactions` — nullable, `NULL` означает «перевод».** Отвергнута —
тот же аргумент, что и выше (расширение симметрии «операция = доход/расход» скрытым третьим состоянием), плюс
разрушает существующий инвариант 010 «тип операции определяется исключительно через `JOIN categories.type`»:
весь код фильтрации/баланса по типу пришлось бы дополнять веткой "категория NULL — это перевод", то есть именно
тем ветвлением по типу через `if`, которое AGENTS.md запрещает.

### 8. Один `currency_id` на перевод, без конвертации — предусловие «валюта входит в оба набора валют кошельков»

**Решение:** `TransferService.create_transfer`/`update_transfer` проверяют `currency_id in from_wallet.currency_ids
and currency_id in to_wallet.currency_ids` (`ClientError`, 400, если нет). Требование задачи «хотя бы одна общая
валюта» проверяется именно так — не отдельным вычислением пересечения множеств валют обоих кошельков, а прямой
проверкой того, что выбранная пользователем валюта — одна из общих. Если у кошельков есть общая валюта, но
пользователь передал другую (не входящую в набор одного из них) — тоже `ClientError` 400, той же проверкой.

**Отвергнутая альтернатива: перевод с разными `currency_id`/`amount` на входе и выходе, с конвертацией по
курсу.** Отвергнута — открытый вопрос задачи 011 закрыт как Non-goal: это уже сама суть механизма пополнения
(конвертация через набор ног с разными валютами), смешивать тот же приём в перевод усложнило бы обе сущности ради
сценария, который задача explicitly не просит («правила для перевода с разными валютами на входе и выходе» —
именно этот открытый вопрос, закрытый отказом от поддержки).

### 9. Баланс — `BalanceService`, компонующий вклад через протокол `BalanceContributor`

**Решение:**

```python
# core/protocols/balance_contributor.py
from decimal import Decimal
from typing import Protocol
from uuid import UUID


class BalanceContributor(Protocol):
    async def balance_delta(self, wallet_id: UUID, user_id: UUID) -> dict[UUID, Decimal]: ...
```

`TransactionRepository.balances(...)` переименовывается в `balance_delta(...)` (сигнатура и SQL не меняются —
агрегирующий запрос по `transaction_legs`/`transactions`/`categories`, тот же, что в 010) — только имя метода,
чтобы структурно удовлетворять протоколу (Python `Protocol` — структурная типизация, явного `implements` не
требуется, но совпадение имени обязательно).

`TransferRepository.balance_delta(wallet_id, user_id)` — новый агрегирующий запрос по образцу того же приёма
(`CASE WHEN ... THEN amount ELSE -amount END`, использованного в `TransactionRepository.balance_delta`):

```python
signed_amount = case((transfers.c.to_wallet_id == wallet_id, transfers.c.amount), else_=-transfers.c.amount)
query = (
    select(transfers.c.currency_id, func.sum(signed_amount).label("balance"))
    .where(
        transfers.c.user_id == user_id,
        or_(transfers.c.to_wallet_id == wallet_id, transfers.c.from_wallet_id == wallet_id),
    )
    .group_by(transfers.c.currency_id)
)
```

`core/services/balance.py`:

```python
class BalanceService:
    def __init__(self, wallets: WalletRepository, contributors: Sequence[BalanceContributor]) -> None:
        self._wallets = wallets
        self._contributors = contributors

    async def get_wallet_balances(self, wallet_id: UUID, user_id: UUID) -> list[tuple[UUID, Decimal]]:
        wallet = await self._wallets.get_by_id(wallet_id, user_id)
        if wallet is None:
            raise NotFoundError(WALLET_NOT_FOUND_MESSAGE)
        totals: dict[UUID, Decimal] = {}
        for contributor in self._contributors:
            for currency_id, delta in (await contributor.balance_delta(wallet_id, user_id)).items():
                totals[currency_id] = totals.get(currency_id, Decimal("0")) + delta
        return [(currency_id, totals.get(currency_id, Decimal("0"))) for currency_id in wallet.currency_ids]
```

`depends/balance.py` собирает `BalanceService(wallets, [transactions_repo, transfers_repo])` — список
`contributors` в одном месте (composition root), новый источник баланса добавляется расширением списка, не правкой
`BalanceService` (`O` из SOLID — прямое применение принципа «варианты поведения — через стратегии за протоколом»
к агрегации баланса, а не к видам операций, как предписано).

`GET /api/wallets/{wallet_id}/balances` переезжает из `api/transactions.py` в новый `api/balances.py` — путь и тег
(`Transactions`) не меняются, эндпоинт теперь зависит от `BalanceService`, а не от `TransactionService`. Это то же
обоснование, что в design.md `transactions` уже привело к решению «обработчик — там же, где сервис, от которого он
зависит, а не где предполагает URL»: раньше это был `TransactionService`, теперь — `BalanceService`, поэтому файл
меняется вместе со сменой зависимости.

**Отвергнутая альтернатива: `TransferService` сам суммирует баланс, вызывая `TransactionService` изнутри
(композиция сервисов вместо протокола-стратегии).** Отвергнута — прямое нарушение `D` из SOLID (сервис не должен
создавать/агрегировать другой сервис, у которого свой набор бизнес-правил и зависимостей; правильная точка сборки
— `depends/`, не внутренность сервиса) и явное предписание задачи («варианты поведения — через стратегии за
протоколами, применённая к агрегации баланса»).

**Отвергнутая альтернатива: оставить `balances(...)` без переименования, обернуть в адаптер-класс, реализующий
`BalanceContributor.balance_delta`, отдельно для `TransactionRepository`.** Отвергнута — лишний слой класса ради
переименования одного метода; `Protocol` — структурная типизация, переименование самого метода даёт то же
соответствие без дополнительного класса.

### 10. Маршрутизация FastAPI — `POST /api/transactions/topups` регистрируется раньше `GET/PUT/DELETE
/api/transactions/{transaction_id}`

**Решение:** в `api/transactions.py` декоратор `@router.post("/topups", ...)` объявляется в коде раньше
`@router.get("/{transaction_id}", ...)`/`@router.put("/{transaction_id}", ...)`/`@router.delete("/{transaction_id}",
...)`. Starlette сопоставляет маршруты в порядке регистрации (первое совпадение побеждает); если параметризованный
маршрут объявлен раньше, `"topups"` будет ошибочно разобран как `transaction_id` первым же совпавшим маршрутом
(`GET /{transaction_id}`, если использовать этот же путь для `GET`, либо, для `POST`, конфликта с существующим
`POST ""` нет — но конфликт возникает специфично между `POST /topups` и уже существующими параметризованными
`GET/PUT/DELETE /{transaction_id}`, если бы они были объявлены с методом `POST`; на практике реальный риск —
`GET /transactions/topups`, если бы такой маршрут потребовался чтением; для `POST` риск в том, что при будущем
добавлении других статических `POST`-путей под тем же префиксом порядок объявления обязан сохраняться тем же
правилом). Правило фиксируется как общее для файла: все статические под-пути `/api/transactions/*` объявляются
раньше параметризованного `/{transaction_id}`.

### 11. `specs/wallets/spec.md` — требование «Удаление кошелька» уточняется явным перечислением источников
конфликта

**Решение:** создаётся delta `specs/wallets/spec.md`. Действующая формулировка (`openspec/specs/wallets/spec.md`)
называет источник конфликта буквально: «если по кошельку есть хотя бы одна операция (`transactions.wallet_id`)» —
это явно привязано к таблице `transactions` и не покрывает `transfers.from_wallet_id`/`to_wallet_id` по тексту
требования, даже притом что механизм (перехват `IntegrityError` в `WalletRepository.delete()`) уже общий и кода не
меняет. Формулировка правится на «если по кошельку есть хотя бы одна операция или перевод», с добавлением
сценария «Отклонение удаления кошелька с переводом» — иначе спецификация расходится с фактическим поведением
кода (у кошелька появляется второй, текстуально неописанный источник 409).

**Альтернатива (отвергнута): не создавать delta, оставить текущую формулировку.** Рассмотрена и отклонена — текст
требования (не только код) явно ссылается на конкретную таблицу (`transactions.wallet_id`) как на источник
конфликта, а не говорит обобщённо «если кошелёк используется где-либо ещё»; оставить как есть означало бы, что
спецификация перестаёт быть точным описанием поведения API после появления второго источника 409.

## Risks / Trade-offs

- [`TransactionRepository.add`/`.update` перечитывают операцию через `get_by_id` после вставки ног, чтобы получить
  канонический порядок по коду валюты] → одна дополнительная выборка на запись; тот же паттерн уже принят
  `WalletRepository.add`/`.update`, приемлем при персональном объёме данных.
- [Валидация полноты набора валют пополнения требует множества операций сравнения множеств и, в случае ошибки,
  дополнительных `get_by_id` по валютам ради читаемого сообщения] → цена — читаемость ошибки для пользователя;
  количество валют кошелька мало (единицы), не проблема производительности.
- [`transfers` — новая таблица без «ног»: перевод всегда одна валюта, что ограничивает будущее расширение до
  конвертации без новой миграции] → осознанный компромисс (Decision 8); если конвертация в переводе понадобится
  позже, потребуется новая колонка/таблица и отдельное изменение OpenSpec — не проблема этой задачи.
- [`BalanceContributor.balance_delta` вызывается последовательно по списку `contributors`, не параллельно] →
  при персональном объёме данных (один пользователь, десятки/сотни строк) последовательные лёгкие агрегирующие
  запросы не создают заметной задержки; распараллеливание — преждевременная оптимизация.
- [Ответ `TransactionOut` меняется несовместимо (`legs` вместо плоских `currency_id`/`amount`) для уже
  существующих эндпоинтов операций] → **BREAKING**, но frontend ещё не реализован (010 явно оставила UI операций
  вне рамок), поэтому реального клиента, ломающегося от этого изменения, не существует; сознательно принято как
  разовая цена рефакторинга, предсказанного design.md 010, а не как продолжающийся риск.

## Migration Plan

Миграция Alembic `20260929_0007` (`down_revision = "20260929_0006"`), одна ревизия, одна новая таблица:
1. `create_table("transfers", ...)` — FK на `users`, `wallets` (дважды — `from_wallet_id`/`to_wallet_id`),
   `currencies` (все уже существуют); `CheckConstraint` на положительность суммы и на различие кошельков.
2. `downgrade()` — `drop_table("transfers")`.

Схема `transactions`/`transaction_legs` не меняется этой миграцией — 010 уже спроектировала `transaction_legs` под
несколько строк на `transaction_id` (составной PK это допускал с самого начала); меняется только код
`TransactionRepository`/`TransactionService`/`api/schemas/transaction.py`/`api/transactions.py`.

Откат безопасен, только если на момент отката в БД нет строк `transfers` (типовое условие любой ревизии Alembic).
Ничего, кроме будущих задач (аналитика, 012), на эту таблицу пока не ссылается.

## Open Questions

Все три открытых вопроса задачи 011 (`docs/tasks/011_topups_transfers.md`) решены:

1. **Представление перевода (две связанные операции или отдельная сущность)?** Решено: отдельная сущность/таблица
   `transfers` — Decision 7.
2. **Расчёт курса при частичных ногах?** Решено: сценарий не существует — частичные ноги запрещены валидацией
   (Decision 5); курс не хранится отдельно, а выводится из полного набора ног при необходимости (Decision 6).
3. **Правила для перевода с разными валютами на входе и выходе?** Решено: не поддерживается в этой задаче —
   перевод всегда одна валюта без конвертации (Decision 8, Non-Goals).
