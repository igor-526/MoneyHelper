## 1. Сущности и протоколы

- [x] 1.1 `backend/src/core/entities/analytics.py` — новые value-объекты (не `Entity`, по образцу `TransactionLeg`):
      `LegRecord` (`wallet_id: UUID`, `category_id: UUID`, `currency_id: UUID`, `amount: Decimal`,
      `category_type: CategoryType`), `TopupLegRecord` (`transaction_id: UUID`, `currency_id: UUID`,
      `amount: Decimal`); экспорт обоих в `core/entities/__init__.py`
- [x] 1.2 `backend/src/core/protocols/analytics_dimension.py` — протокол `AnalyticsDimension` (`def key(self,
      record: LegRecord) -> UUID: ...`); экспорт в `core/protocols/__init__.py`
- [x] 1.3 `backend/src/core/protocols/repositories/transaction_repository.py` — добавить в протокол
      `TransactionRepository` два новых метода (по образцу уже существующего `balance_delta`, добавленного прямо в
      этот протокол в 011): `list_legs_for_analytics(user_id, *, date_from, date_to, wallet_id, category_id,
      currency_id, type) -> list[LegRecord]`, `list_topup_legs_for_rates(user_id, *, date_from, date_to) ->
      list[TopupLegRecord]`

## 2. Сервисы и unit-тесты

- [x] 2.1 `backend/src/core/services/analytics_dimensions.py` — реализации `WalletDimension`, `CategoryDimension`,
      `CurrencyDimension` (каждая — один метод `key`, возвращающий соответствующее поле `LegRecord`); реестр
      `DIMENSIONS: dict[str, AnalyticsDimension]`
- [x] 2.2 `backend/src/core/services/analytics.py` — `AnalyticsService(transactions: TransactionRepository,
      currencies: CurrencyRepository)`: метод `get_analytics(user_id, *, display_currency_id, date_from, date_to,
      group_by, wallet_id, category_id, currency_id, type) -> tuple[list[tuple[UUID, Decimal, Decimal]],
      list[UUID]]` — валидация `date_from <= date_to` (`ClientError`), валидация `display_currency_id`
      (`CurrencyRepository.get_by_id`, `ClientError` при `None`), выборка `list_legs_for_analytics`, усреднение
      курса по `list_topup_legs_for_rates` (приватный метод `_average_rates`), конвертация неокруглённых сумм,
      группировка через `DIMENSIONS[group_by]`, сбор `unconverted_currencies`, округление итога каждой корзины
      один раз (`ROUND_HALF_UP`, `decimal_places` валюты отображения) — приватная функция модуля
- [x] 2.3 `tests/fakes/transaction_repository.py` — добавить в `InMemoryTransactionRepository` реализации
      `list_legs_for_analytics` и `list_topup_legs_for_rates` (фильтрация по `user_id`+датам+опциональным
      фильтрам; пополнение — операция с `len(transaction.legs) > 1`)
- [x] 2.4 `tests/unit/test_analytics_service.py` — новый: группировка по `wallet`/`category`/`currency`; конвертация
      по среднему курсу одного пополнения (воспроизводимый пример 10 000/780, как в specs); усреднение курса по
      нескольким пополнениям (простое среднее, не средневзвешенное); валюта отображения не требует похода за
      курсом; отсутствие курса — исключение из сумм + `unconverted_currencies`, без ошибки всего запроса; валюта с
      найденным курсом не попадает в `unconverted_currencies`; округление итога корзины один раз (сценарий,
      демонстрирующий разницу с округлением по каждой операции); `income`/`expense` всегда оба присутствуют при
      фильтре `type`; пустые корзины не включаются; переводы не учитываются (fake-репозиторий переводов не
      использован сервисом вовсе — тест подтверждает, что `AnalyticsService` не зависит от `TransferRepository`);
      `date_from`/`date_to` обязательны и валидируются (`date_from > date_to` → `ClientError`); неизвестная
      `display_currency_id` → `ClientError`; фильтры `wallet_id`/`category_id`/`currency_id`/`type` сужают набор
      операций, но не набор пополнений для усреднения курса; изоляция по владельцу — чужие операции не участвуют в
      суммах, чужое пополнение не влияет на курс текущего пользователя

## 3. Репозиторий

- [x] 3.1 `backend/src/repositories/transaction.py` — реализовать `list_legs_for_analytics` (`SELECT
      transactions.wallet_id, transactions.category_id, transaction_legs.currency_id, transaction_legs.amount,
      categories.type FROM transaction_legs JOIN transactions JOIN categories WHERE user_id = :user_id AND
      occurred_at BETWEEN :date_from AND :date_to` + опциональные `WHERE` по `wallet_id`/`category_id`/
      `currency_id`/`type`, без пагинации) и `list_topup_legs_for_rates` (подзапрос `transaction_legs JOIN
      transactions WHERE user_id = :user_id AND occurred_at BETWEEN ... GROUP BY transaction_id HAVING COUNT(*) >
      1`, затем выборка строк `transaction_legs` по найденным `transaction_id`) — см. точный SQL в design.md

## 4. Схемы, API, зависимости

- [x] 4.1 `backend/src/api/schemas/analytics.py` — `AnalyticsQueryParams(BaseModel)` (не `PageParams`):
      `display_currency: UUID`, `date_from: datetime`, `date_to: datetime`, `group_by: Literal["wallet",
      "category", "currency"]`, `wallet_id: UUID | None = None`, `category_id: UUID | None = None`,
      `currency_id: UUID | None = None`, `type: CategoryType | None = None`; `AnalyticsBucketOut` (`group_key:
      UUID`, `income: Money`, `expense: Money`); `AnalyticsOut` (`display_currency_id: UUID`, `buckets:
      list[AnalyticsBucketOut]`, `unconverted_currencies: list[UUID]`)
- [x] 4.2 `backend/src/depends/analytics.py` — новый файл: `get_analytics_service(transactions:
      Annotated[TransactionRepository, Depends(get_transaction_repository)], currencies:
      Annotated[CurrencyRepository, Depends(get_currency_repository)]) -> AnalyticsService`, переиспользующий
      существующие `get_transaction_repository`/`get_currency_repository`
- [x] 4.3 `backend/src/api/analytics.py` — новый файл: `router = APIRouter(prefix="/api/analytics",
      tags=["Analytics"])`, `GET ""` под `Depends(get_current_user)`, принимает `Annotated[AnalyticsQueryParams,
      Query()]`, вызывает `AnalyticsService.get_analytics`, собирает `AnalyticsOut` из плоского результата сервиса
- [x] 4.4 `backend/src/main.py` — подключить `analytics_router` (`api/analytics.py`)

## 5. API-, smoke- и инфраструктурные тесты

- [x] 5.1 `tests/api/test_analytics.py` — новый (через `TestClient` + `app.dependency_overrides`, fake-репозитории):
      группировка по каждой из трёх осей (200, корректные `group_key`/`income`/`expense`); конвертация по
      воспроизводимому примеру (10 000/780); отсутствие курса — `unconverted_currencies` + суммы по остальным
      валютам не искажены (не 400 на весь запрос); округление итога; 400 при отсутствии `date_from`/`date_to`,
      при `date_from > date_to`, при неизвестной `display_currency`, при отсутствии `display_currency`; фильтры
      `wallet_id`/`category_id`/`currency_id`/`type`; 401 без access-cookie; изоляция пользователей — чужие
      операции не в суммах, чужое пополнение не в курсе
- [x] 5.2 `tests/smoke/test_app_smoke.py` — дополнить: `GET /api/analytics` зарегистрирован в OpenAPI-схеме
- [x] 5.3 `tests/infrastructure/test_transaction_repository.py` — дополнить: `list_legs_for_analytics` на реальной
      БД (фильтры по датам/`wallet_id`/`category_id`/`currency_id`/`type`, изоляция по `user_id`, корректный
      `category_type` через `JOIN categories`); `list_topup_legs_for_rates` на реальной БД (возвращает только ноги
      операций с >1 ногой в диапазоне, изоляция по `user_id`, операции с одной ногой не попадают в результат)

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test` (backend unit + smoke)
- [x] 6.4 `make test-infra` (backend infrastructure, включая новые тесты `list_legs_for_analytics`/
      `list_topup_legs_for_rates`)
