## Context

Задача 012 — финальная задача дорожной карты (этап 7), зависит от 011 (`transfers`, реализована и заархивирована —
`openspec/changes/archive/2026-09-29-transfers/`). Она закрывает единственный оставшийся пробел вертикального
среза «доходы/расходы»: пользователь видит сводку по периоду, кошельку, категории и валюте, в единой валюте
отображения.

**Ключевая проблема и её решение (зафиксировано оркестратором, не переоткрывается).** В системе нет ни одного
явного источника обменного курса (внешние курсы — вне рамок 010/011/012). Единственное место, где курс между двумя
валютами когда-либо фиксируется, — «ноги» многовалютных пополнений (`POST /api/transactions/topups`, 011): design.md
`transfers`, Decision 6, явно предсказал это использование («курс воспроизводим... например, в аналитике 012»).
Пополнение с ногами 10 000 RUB и 780 CNY неявно кодирует курс `780 / 10000` CNY за RUB (или обратно). «Курс всегда
средний за диапазон анализа» (`docs/tasks/012_analytics.md`, уже решено) означает: пересчёт суммы операции в валюту
отображения требует усреднения курса между парой валют по всем пополнениям пользователя с ногами в обеих валютах
за тот же диапазон дат, что и сам запрос аналитики.

Уже готово и переиспользуется без изменений: `core/entities/transaction.py` (`Transaction`, `TransactionLeg` —
value-object без собственного `id`, прямой прецедент для новых read-моделей этой задачи), `core/entities/category.py`
(`CategoryType`), `core/schemas/money.py` (`Money`), `core/protocols/balance_contributor.py` (прямой прецедент
«вариант поведения — за узким протоколом, реестр в `depends/`»), `TransactionRepository.balance_delta` (прецедент
агрегирующего метода, добавленного прямо в существующий протокол репозитория без выделения нового файла),
`WalletRepository._load_currency_ids_map` (прецедент батч-загрузки без N+1, использован уже дважды — 010/011).

## Goals / Non-Goals

**Goals:**
- Единственный эндпоинт `GET /api/analytics`, возвращающий суммы доходов/расходов пользователя за явный диапазон
  дат, в валюте отображения, по одной из трёх осей группировки (`wallet`/`category`/`currency`).
- Курс — среднее арифметическое курсов, выведенных из ног пополнений пользователя за тот же диапазон; валюты без
  курса исключаются из сумм, а не искажают их подстановкой курса `1` и не ломают весь запрос ошибкой.
- Округление — один раз, над уже просуммированным итогом корзины, до `decimal_places` валюты отображения.
- Агрегация — в `AnalyticsService` на Python (двухфазный расчёт: сначала курсы, затем конвертация и группировка),
  репозиторий отдаёт только плоские нетронутые строки.
- Три оси группировки — стратегии за протоколом `AnalyticsDimension`, реестр в одном месте, без `if/elif`.
- Изоляция по владельцу — как в фильтрации операций, так и в усреднении курса: чужие данные никогда не участвуют
  ни в числителе, ни в знаменателе.

**Non-Goals:**
- Внешние источники курсов валют — единственный источник, как и в 011, — ноги пополнений.
- Графики, экспорт — frontend/отдельные задачи.
- Произвольная гранулярность периода (день/неделя/месяц) как ось группировки — «период» лишь обязательный фильтр
  `date_from`/`date_to`, задача не специфицирует гранулярность бакетов.
- Zero-fill пустых корзин — набор кошельков/категорий/валют, участвующих в аналитике, открытое множество (в
  отличие от `wallet.currency_ids` — известного конечного множества в балансе 011), поэтому пустые корзины не
  подставляются нулевой строкой.
- Переводы (`transfers`) — не доход и не расход, у перевода нет категории, включение исказило бы категорийный и
  типовой срез. Аналитика охватывает только `transactions`.
- Несколько эндпоинтов под разные срезы — один параметризованный эндпоинт проще и полностью покрывает три оси.
- Кэширование результата — агрегирующий запрос на лету, тот же принцип, что у баланса (011).

## Decisions

### 1. Формула среднего курса и место его использования

**Решение:** для каждой валюты `source`, встретившейся среди отфильтрованных операций и отличной от валюты
отображения `target = display_currency`, курс `rate(source → target)` — простое среднее арифметическое (не
средневзвешенное) значений `target_leg.amount / source_leg.amount` по всем операциям-пополнениям пользователя
(транзакциям с >1 ногой — само наличие нескольких строк `transaction_legs` на `transaction_id` уже есть признак
пополнения, отдельного поля/флага не заводится) за диапазон `[date_from, date_to]` запроса аналитики, у которых
есть нога и в `source`, и в `target`. Если `leg.currency_id == display_currency_id` — курс тривиально `1`, поход
за курсом не нужен (эта валюта не попадает в множество запрашиваемых курсов).

**Отвергнутая альтернатива: средневзвешенное по сумме ноги.** Отвергнута — задача явно говорит «курс всегда
средний», без указания на взвешивание; простое среднее также проще для пользователя как ментальная модель («среднее
за период») и не требует решения, по какой из двух сумм ноги взвешивать (по `source` или по `target` — эти веса
дали бы разный результат).

### 2. Отсутствие курса для пары валют — исключение сумм из итога, `unconverted_currencies` в ответе

**Решение:** если для валюты `source` в диапазоне нет ни одного пополнения с ногой и в `source`, и в
`display_currency` — суммы операций в этой валюте исключаются из группировки целиком (не участвуют ни в `income`,
ни в `expense` ни одной корзины). Валюта добавляется в `AnalyticsOut.unconverted_currencies` (список без дублей).
Запрос не завершается ошибкой — единственная неконвертируемая валюта не должна ломать отчёт по остальным.

**Отвергнутая альтернатива: подставлять курс `1`.** Отвергнута оркестратором явно — исказило бы суммы (валюты с
существенно разным номиналом типично не равны 1:1).

**Отвергнутая альтернатива: 400 на весь запрос.** Отвергнута — один пользователь с операциями в валюте, которую он
ни разу не пополнял с конвертацией в диапазоне, не должен терять доступ к отчёту по остальным валютам.

### 3. Округление — один раз, над суммой корзины

**Решение:** конвертация (`leg.amount * rate`) и суммирование по корзинам группировки выполняются в полной точности
`Decimal` (без округления на промежуточных шагах). Округление до `decimal_places` валюты отображения выполняется
ровно один раз — отдельно для `income` и для `expense` каждой корзины, после того как все ноги этой корзины уже
просуммированы. Правило округления — `ROUND_HALF_UP` (`Decimal.quantize`), тот же метод, которым обычно ожидаются
округлённые денежные суммы в пользовательских интерфейсах; проект пока не вводил отдельной денежной политики
округления (010/011 явно запрещают округление вводимых сумм, но не описывают производные/агрегированные суммы —
первый такой случай).

**Отвергнутая альтернатива: округлять каждую ногу перед суммированием.** Отвергнута прямым указанием задачи —
ошибки округления накапливались бы по большому числу мелких операций (классическая проблема «смерти от тысячи
округлений»), особенно заметно при суммировании сотен операций в валюте с малым числом знаков после запятой.

### 4. `date_from`/`date_to` — оба обязательные query-параметры

**Решение:** оба параметра обязательны (без умолчания «за всё время»), потому что диапазон определяет не только
фильтр операций, но и то, какие пополнения участвуют в усреднении курса — необъявленный диапазон сделал бы
семантику курса неопределённой. `date_from` позже `date_to` — `ClientError` (400), тот же паттерн, что уже
применён в `GET /api/transactions`/`GET /api/transfers`.

**Отвергнутая альтернатива: `date_from`/`date_to` опциональны, по умолчанию «за всё время».** Отвергнута — открытый
вопрос задачи 012 «границы диапазона» закрыт именно требованием их обязательности, поскольку диапазон анализа —
не просто фильтр, а часть смысла запроса (курс для другого диапазона был бы другим числом).

### 5. Агрегация — в `AnalyticsService` на Python, не декларативным SQL

**Решение:** репозиторий отдаёт плоские, ещё не сгруппированные строки — сначала все подходящие «ноги» операций
(`list_legs_for_analytics`), отдельно все ноги пополнений для усреднения курса (`list_topup_legs_for_rates`).
Двухфазный расчёт (сначала усреднить курсы пар валют по пополнениям, затем пересчитать и просуммировать операции
по этим курсам) на SQL потребовал бы CTE с оконными функциями, нечитаемых и не тестируемых на fake-репозиториях
без реальной БД. Вся арифметика — в `AnalyticsService`, тестируемая юнит-тестами на `InMemoryTransactionRepository`.

**Обоснование производительности.** Тот же аргумент, что уже многократно применён в design.md `transactions`/
`transfers`: датасет персонального приложения (сотни/тысячи операций у одного пользователя) делает построение
Python-словарей и суммирование в памяти дешёвой операцией, не проблемой производительности.

**Отвергнутая альтернатива: агрегирующий `SELECT ... GROUP BY` с курсом, вычисленным оконной функцией в CTE.**
Отвергнута оркестратором явно (открытый вопрос задачи «агрегация на стороне БД или в сервисе» закрыт в пользу
сервиса) — такой запрос пришлось бы разбить на две логические фазы (курсы пар валют → пересчёт операций) в одном
SQL-выражении, что радикально увеличило бы сложность запроса ради оптимизации, которая не нужна при таком объёме
данных, и сделало бы логику курса непроверяемой без реальной БД (нарушение «SQL — только в `repositories`, бизнес-
правила — в `core/services`, тестируемые на fake-репозиториях» из AGENTS.md).

### 6. Три оси группировки — стратегии `AnalyticsDimension` за протоколом, реестр `dict[str, AnalyticsDimension]`

**Решение:**

```python
# core/protocols/analytics_dimension.py
from typing import Protocol
from uuid import UUID

from core.entities import LegRecord


class AnalyticsDimension(Protocol):
    def key(self, record: LegRecord) -> UUID: ...
```

Три реализации — тривиальные классы, возвращающие соответствующее поле `LegRecord`:

```python
# core/services/analytics_dimensions.py
from core.entities import LegRecord
from core.protocols import AnalyticsDimension


class WalletDimension:
    def key(self, record: LegRecord) -> UUID:
        return record.wallet_id


class CategoryDimension:
    def key(self, record: LegRecord) -> UUID:
        return record.category_id


class CurrencyDimension:
    def key(self, record: LegRecord) -> UUID:
        return record.currency_id


DIMENSIONS: dict[str, AnalyticsDimension] = {
    "wallet": WalletDimension(),
    "category": CategoryDimension(),
    "currency": CurrencyDimension(),
}
```

`AnalyticsService` выбирает нужную стратегию через `DIMENSIONS[group_by]` (значение `group_by` уже ограничено
`Literal["wallet", "category", "currency"]` на уровне API-схемы — `KeyError` в сервисе невозможен). Добавление новой
оси в будущем — новый класс-реализация + запись в словаре, без правки `AnalyticsService` (`O` из SOLID, прямое
требование задачи).

**Размещение реализаций отдельно от протокола.** `core/protocols/` — только интерфейсы (по структуре AGENTS.md);
три реализации и их реестр вынесены в собственный модуль `core/services/analytics_dimensions.py`, а не в
`core/services/analytics.py` вместе с `AnalyticsService` — раздельная ответственность (`S` из SOLID): один модуль
отвечает «как выбрать поле для группировки», другой — «как усреднить курс, сконвертировать и просуммировать»; та
же логика, что уже развела `core/services/money_validation.py` (чистая функция) и `core/services/transaction.py`
(сервис, использующий её).

**Отвергнутая альтернатива: `if/elif group_by == "wallet": ...` внутри `AnalyticsService`.** Отвергнута — прямое
нарушение `O` из SOLID и явное предписание задачи 012 («срезы оформляются через стратегии за протоколами»),
идентичное по духу тому, как оформлен `BalanceContributor` для источников баланса в 011.

### 7. Новые read-методы репозитория и `LegRecord`/`TopupLegRecord` — где живут, что возвращают

**Решение:** два новых метода добавлены прямо в существующий протокол `core/protocols/repositories/
transaction_repository.py` (`TransactionRepository`) — тот же приём, что уже применён для `balance_delta` в 011
(метод, нужный не всем потребителям протокола, добавлен в протокол репозитория напрямую, а не вынесен в отдельный
узкий протокол: `TransactionService` их не вызывает, но `AnalyticsService` зависит от того же протокола
`TransactionRepository`, что и `TransactionService`, — двух совместимых потребителей одного репозитория без
разнородных типов, в отличие от `BalanceContributor`, который специально абстрагирует разнородные источники —
`TransactionRepository` и `TransferRepository` — под один интерфейс для `BalanceService.contributors`; здесь такой
разнородности нет, аналитика читает только из `TransactionRepository`).

```python
# core/protocols/repositories/transaction_repository.py (дополнение)
async def list_legs_for_analytics(
    self,
    user_id: UUID,
    *,
    date_from: datetime,
    date_to: datetime,
    wallet_id: UUID | None,
    category_id: UUID | None,
    currency_id: UUID | None,
    type: CategoryType | None,
) -> list[LegRecord]: ...

async def list_topup_legs_for_rates(
    self, user_id: UUID, *, date_from: datetime, date_to: datetime
) -> list[TopupLegRecord]: ...
```

`LegRecord`/`TopupLegRecord` — новые value-объекты в `core/entities/analytics.py` (не `Entity` — как и
`TransactionLeg`, у них нет собственного `id`/`created_at`, это плоские проекции строк для чтения, а не
персистентные сущности со своим жизненным циклом):

```python
# core/entities/analytics.py
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from core.entities.category import CategoryType


class LegRecord(BaseModel):
    wallet_id: UUID
    category_id: UUID
    currency_id: UUID
    amount: Decimal
    category_type: CategoryType


class TopupLegRecord(BaseModel):
    transaction_id: UUID
    currency_id: UUID
    amount: Decimal
```

**Обоснование размещения в `core/entities/`, а не в `core/services/analytics.py`.** Прямой прецедент —
`TransactionLeg` (тоже не `Entity`, тоже `BaseModel` без `id`) уже живёт в `core/entities/transaction.py`, а не в
`core/services/transaction.py`, потому что пересекает границу репозиторий → сервис — обе стороны (протокол
репозитория и сервис) должны его импортировать без нарушения направления зависимостей (`core/protocols` не может
зависеть от `core/services`). Размещение в `core/entities` — нейтральная точка, откуда оба слоя импортируют без
цикла, та же причина, по которой там же остались `TransactionLeg`/`CategoryType`.

**SQL `list_legs_for_analytics`** (`repositories/transaction.py`) — обычная плоская выборка, `JOIN categories`
всегда (тип категории нужен для разбиения на `income`/`expense` в каждой корзине), опциональные фильтры условиями
`WHERE`, без `GROUP BY`/пагинации (нужны все строки):

```python
query = (
    select(
        transactions.c.wallet_id,
        transactions.c.category_id,
        transaction_legs.c.currency_id,
        transaction_legs.c.amount,
        categories.c.type,
    )
    .select_from(
        transaction_legs.join(transactions, transactions.c.id == transaction_legs.c.transaction_id).join(
            categories, categories.c.id == transactions.c.category_id
        )
    )
    .where(
        transactions.c.user_id == user_id,
        transactions.c.occurred_at >= date_from,
        transactions.c.occurred_at <= date_to,
    )
)
# + опционально .where(transactions.c.wallet_id == wallet_id), .where(transactions.c.category_id == category_id),
#   .where(transaction_legs.c.currency_id == currency_id), .where(categories.c.type == type)
```

Фильтры `wallet_id`/`category_id`/`currency_id`/`type` — тот же лёгкий контракт «просто `WHERE`», что уже принят
`TransactionListParams` (несуществующий `id` даёт пустой результат, не ошибку); никакой отдельной проверки
существования/принадлежности этих фильтров нет — единственное исключение по задаче, `display_currency`,
валидируется в `AnalyticsService` через `CurrencyRepository.get_by_id`, потому что от него зависит вся семантика
ответа (валюта, в которую всё пересчитывается), а не просто сужение выборки.

**SQL `list_topup_legs_for_rates`** — подзапрос `GROUP BY transaction_id HAVING COUNT(*) > 1` на `transaction_id`
пользователя в диапазоне, затем выборка строк `transaction_legs` по найденным `transaction_id` (оконная функция в
`WHERE` невозможна в PostgreSQL напрямую — она обязана быть в `SELECT`/подзапросе, поэтому выбран вариант
`GROUP BY ... HAVING`, явно предложенный задачей как один из двух эквивалентных путей):

```python
topup_ids = (
    select(transaction_legs.c.transaction_id)
    .select_from(transaction_legs.join(transactions, transactions.c.id == transaction_legs.c.transaction_id))
    .where(
        transactions.c.user_id == user_id,
        transactions.c.occurred_at >= date_from,
        transactions.c.occurred_at <= date_to,
    )
    .group_by(transaction_legs.c.transaction_id)
    .having(func.count() > 1)
)
rows = await self._session.execute(
    select(transaction_legs.c.transaction_id, transaction_legs.c.currency_id, transaction_legs.c.amount).where(
        transaction_legs.c.transaction_id.in_(topup_ids)
    )
)
```

Оба метода фильтруют по `transactions.c.user_id == user_id` — та же изоляция по владельцу, что и везде; чужое
пополнение никогда не попадает в `list_topup_legs_for_rates` текущего пользователя, поэтому не может повлиять на
усреднённый курс (явный сценарий в specs/analytics/spec.md).

### 8. `AnalyticsService` — алгоритм, зависимости, возвращаемый тип

**Решение:**

```python
# core/services/analytics.py
class AnalyticsService:
    def __init__(self, transactions: TransactionRepository, currencies: CurrencyRepository) -> None:
        self._transactions = transactions
        self._currencies = currencies

    async def get_analytics(
        self,
        user_id: UUID,
        *,
        display_currency_id: UUID,
        date_from: datetime,
        date_to: datetime,
        group_by: str,
        wallet_id: UUID | None,
        category_id: UUID | None,
        currency_id: UUID | None,
        type: CategoryType | None,
    ) -> tuple[list[tuple[UUID, Decimal, Decimal]], list[UUID]]:
        if date_from > date_to:
            raise ClientError("date_from не может быть позже date_to")
        display_currency = await self._currencies.get_by_id(display_currency_id)
        if display_currency is None:
            raise ClientError("Неизвестная валюта отображения")

        legs = await self._transactions.list_legs_for_analytics(
            user_id, date_from=date_from, date_to=date_to,
            wallet_id=wallet_id, category_id=category_id, currency_id=currency_id, type=type,
        )
        needed = {leg.currency_id for leg in legs} - {display_currency_id}
        rates = await self._average_rates(user_id, display_currency_id, needed, date_from, date_to) if needed else {}

        dimension = DIMENSIONS[group_by]
        totals: dict[UUID, list[Decimal]] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
        unconverted: set[UUID] = set()
        for leg in legs:
            if leg.currency_id == display_currency_id:
                converted = leg.amount
            elif leg.currency_id in rates:
                converted = leg.amount * rates[leg.currency_id]
            else:
                unconverted.add(leg.currency_id)
                continue
            bucket = totals[dimension.key(leg)]
            bucket[0 if leg.category_type is CategoryType.INCOME else 1] += converted

        buckets = [
            (key, _round(income, display_currency.decimal_places), _round(expense, display_currency.decimal_places))
            for key, (income, expense) in totals.items()
        ]
        return buckets, sorted(unconverted, key=str)

    async def _average_rates(
        self, user_id: UUID, target_id: UUID, source_ids: set[UUID], date_from: datetime, date_to: datetime
    ) -> dict[UUID, Decimal]:
        topup_legs = await self._transactions.list_topup_legs_for_rates(user_id, date_from=date_from, date_to=date_to)
        legs_by_transaction: dict[UUID, dict[UUID, Decimal]] = defaultdict(dict)
        for leg in topup_legs:
            legs_by_transaction[leg.transaction_id][leg.currency_id] = leg.amount
        samples: dict[UUID, list[Decimal]] = defaultdict(list)
        for legs_map in legs_by_transaction.values():
            if target_id not in legs_map:
                continue
            for source_id in source_ids:
                if source_id in legs_map:
                    samples[source_id].append(legs_map[target_id] / legs_map[source_id])
        return {source_id: sum(values) / len(values) for source_id, values in samples.items()}
```

`_round` — `Decimal.quantize(Decimal(1).scaleb(-decimal_places), rounding=ROUND_HALF_UP)`, приватная функция модуля
(единственный потребитель — сам сервис, не выносится в `money_validation.py`, у которого другая ответственность —
отклонение, а не округление).

**Возвращаемый тип — кортежи, не Pydantic-схема.** `AnalyticsService.get_analytics` возвращает
`tuple[list[tuple[UUID, Decimal, Decimal]], list[UUID]]`, а не DTO-класс наподобие `AnalyticsBucketOut` — прямой
повтор уже принятого в проекте паттерна `BalanceService.get_wallet_balances() -> list[tuple[UUID, Decimal]]`
(`core/services/balance.py`): роутер сам собирает `AnalyticsBucketOut`/`AnalyticsOut` из плоских кортежей (см.
`api/balances.py`). Так `core/services` не зависит от API-схем (направление зависимостей `api → depends → core`
не нарушается лишний раз новым DTO).

**`group_by: str`, а не `Literal[...]` в сигнатуре сервиса.** Валидация допустимых значений уже происходит на
границе API — `AnalyticsQueryParams.group_by: Literal["wallet", "category", "currency"]` (Pydantic отклонит
недопустимое значение до вызова сервиса, 400 стандартным образом валидации тела/параметров FastAPI). `core` не
импортирует `typing.Literal` API-схемы напрямую; сервис принимает `str` и обращается к `DIMENSIONS[group_by]` —
`KeyError` невозможен на практике, потому что единственный вызывающий (роутер) всегда передаёт уже провалидированное
значение. Тот же принцип, что и с `CategoryType` в фильтре `type` — enum валидируется на границе, сервис использует
его как обычное значение.

### 9. Эндпоинт и схемы — единственный `GET /api/analytics`, без `PageParams`

**Решение:** `api/analytics.py`, `router = APIRouter(prefix="/api/analytics", tags=["Analytics"])`,
`GET ""` (единственный маршрут). Query-модель `AnalyticsQueryParams(BaseModel)` (не наследует `PageParams` —
корзины аналитики не разбиваются на страницы, это открытый, но обычно небольшой для персонального приложения
набор группировочных ключей, а не список записей):

```python
class AnalyticsQueryParams(BaseModel):
    display_currency: UUID
    date_from: datetime
    date_to: datetime
    group_by: Literal["wallet", "category", "currency"]
    wallet_id: UUID | None = None
    category_id: UUID | None = None
    currency_id: UUID | None = None
    type: CategoryType | None = None
```

Ответ:

```python
class AnalyticsBucketOut(BaseModel):
    group_key: UUID
    income: Money
    expense: Money


class AnalyticsOut(BaseModel):
    display_currency_id: UUID
    buckets: list[AnalyticsBucketOut]
    unconverted_currencies: list[UUID]
```

Роутер собирает `AnalyticsOut` из результата сервиса:

```python
@router.get("", response_model=AnalyticsOut)
async def get_analytics(
    params: Annotated[AnalyticsQueryParams, Query()],
    user_id: Annotated[UUID, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> AnalyticsOut:
    buckets, unconverted = await analytics_service.get_analytics(
        user_id,
        display_currency_id=params.display_currency,
        date_from=params.date_from,
        date_to=params.date_to,
        group_by=params.group_by,
        wallet_id=params.wallet_id,
        category_id=params.category_id,
        currency_id=params.currency_id,
        type=params.type,
    )
    return AnalyticsOut(
        display_currency_id=params.display_currency,
        buckets=[AnalyticsBucketOut(group_key=key, income=income, expense=expense) for key, income, expense in buckets],
        unconverted_currencies=unconverted,
    )
```

`depends/analytics.py` переиспользует существующие провайдеры без изменений:

```python
def get_analytics_service(
    transactions: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    currencies: Annotated[CurrencyRepository, Depends(get_currency_repository)],
) -> AnalyticsService:
    return AnalyticsService(transactions, currencies)
```

**Отвергнутая альтернатива: отдельные эндпоинты `/api/analytics/by-wallet`, `/api/analytics/by-category`,
`/api/analytics/by-currency`.** Отвергнута — задача описывает три оси одного и того же расчёта (одинаковая
фильтрация, одинаковая конвертация, различается только функция выбора ключа группировки), три роута means
дублирование query-параметров и обработчиков ради того, что уже параметризуется одним `group_by`; `О` из SOLID уже
решён на уровне стратегии (Decision 6), плодить эндпоинты поверх неё избыточно.

**Отвергнутая альтернатива: `PageParams`/пагинация корзин.** Отвергнута — число корзин ограничено числом
кошельков/категорий/валют пользователя (единицы-десятки для персонального приложения), пагинация добавила бы
сложность (два похода за `items`/`total`) без реальной пользы.

### 10. Zero-fill пустых корзин — не делается (в отличие от баланса 011)

**Решение:** корзины, для которых нет ни одной подходящей ноги в диапазоне (после всех фильтров и после
исключения неконвертируемых валют), не включаются в `buckets` нулевой записью.

**Отличие от баланса (011), где zero-fill выполняется.** `GET /api/wallets/{wallet_id}/balances` дополняет каждую
валюту из `wallet.currency_ids` — известного и небольшого фиксированного множества, полученного из одной сущности
(конкретного кошелька). У аналитики группировочный ключ — открытое множество: «все кошельки пользователя» при
`group_by=wallet` не имеют единого источника перечисления, согласованного с текущими фильтрами (`category_id`/
`currency_id`/`type` могли исключить часть кошельков из выборки заранее) — пришлось бы отдельно запрашивать полный
список кошельков/категорий/валют пользователя и решать, что значит «ноль» для комбинации фильтров, которая
структурно не может относиться к этому кошельку (например, кошелёк вообще не содержит валюту из фильтра
`currency_id`). Задача не описывает такого перечисления, поэтому создание пустых корзин было бы domain-решением
без явного запроса.

## Risks / Trade-offs

- [Курс — среднее по ВСЕМ пополнениям пользователя за диапазон, включая пополнения кошельков, не входящих в текущий
  `wallet_id`-фильтр запроса] → осознанное прямое следствие формулировки задачи («курс всегда средний за диапазон
  анализа», не «за диапазон и кошелёк»); `wallet_id`/`category_id`/`currency_id`/`type` сужают набор
  конвертируемых операций, но не набор пополнений, по которым усредняется курс — это два разных запроса к
  репозиторию с разными фильтрами, оба ограничены только `user_id`+датами (см. Decision 7).
- [`_average_rates` строит `dict[transaction_id, dict[currency_id, amount]]` в памяти по всем ногам пополнений
  пользователя за диапазон] → при персональном объёме данных (десятки/сотни пополнений) — незначительная память и
  время; тот же аргумент производительности, что уже принят в design.md `transactions`/`transfers`.
- [`list_legs_for_analytics` возвращает все подходящие строки без пагинации] → осознанно (нужны все строки для
  корректной агрегации); при персональном объёме данных не проблема, тот же аргумент, что и у остальных read-
  методов без пагинации в проекте (`balance_delta`).
- [`ROUND_HALF_UP` — новая, ранее не встречавшаяся в проекте денежная политика округления] → минимальный риск:
  единственное место применения — итоговые суммы аналитики; 010/011 сознательно избегали округления вводимых сумм,
  но не описывали производные величины, поэтому конфликта с существующим поведением нет.
- [`unconverted_currencies` вычисляется как разность множеств, включает валюту, даже если она отсутствует лишь в
  части корзин группировки (например, есть и в кошельке A, и в кошельке B, но курс не найден вовсе)] → по
  построению рейт считается на уровне пары валют, не на уровне корзины — если курса нет, валюта исключается из
  ВСЕХ корзин, а не выборочно; это соответствует тексту задачи («суммы в этой валюте исключаются») без дополнительных
  условий по корзинам.

## Migration Plan

Миграция Alembic не требуется — схема БД не меняется. Новые read-методы `TransactionRepository`
(`list_legs_for_analytics`, `list_topup_legs_for_rates`) — обычные `SELECT` по уже существующим таблицам
`transactions`/`transaction_legs`/`categories`, без новых таблиц, колонок или индексов. При необходимости
индексации под нагрузку (не требуется при текущем персональном объёме данных) это отдельное будущее изменение, не
входящее в задачу 012.

## Open Questions

Все четыре открытых вопроса задачи 012 (`docs/tasks/012_analytics.md`) решены:

1. **Что делать, если в диапазоне нет операций с курсом для пары валют?** Решено: суммы в этой валюте исключаются
   из итогов, валюта попадает в `unconverted_currencies`, запрос не отклоняется — Decision 2.
2. **Округление?** Решено: суммируются неокруглённые суммы, округление — один раз над суммой корзины,
   `ROUND_HALF_UP` — Decision 3.
3. **Границы диапазона?** Решено: `date_from`/`date_to` оба обязательны, `date_from > date_to` — `ClientError`
   (400) — Decision 4.
4. **Агрегация на стороне БД или в сервисе?** Решено: в сервисе (`AnalyticsService`, Python), репозиторий отдаёт
   только плоские строки — Decision 5.
