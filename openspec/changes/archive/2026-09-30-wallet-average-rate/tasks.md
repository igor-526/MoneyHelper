## 1. Общая функция усреднения курса

- [x] 1.1 `core/services/rate_averaging.py` — чистая функция `average_rates(topup_legs, target_id, source_ids) ->
      dict[UUID, Decimal]`, перенос алгоритма из `AnalyticsService._average_rates` без изменения поведения.
- [x] 1.2 Unit-тесты `average_rates` (несколько исходных валют, валюта без подходящих транзакций, пустой список
      ног, несколько транзакций с одной и той же парой валют — среднее, а не последнее значение).
- [x] 1.3 Рефакторинг `AnalyticsService._average_rates` на вызов `average_rates`; прогнать существующие тесты
      `AnalyticsService` — обязаны остаться зелёными без изменений сценариев (чистый рефакторинг).

## 2. Репозиторий — ноги пополнений одного кошелька

- [x] 2.1 `core/protocols/repositories/transaction_repository.py` — новый метод
      `list_topup_legs_for_wallet_rates(workspace_id, wallet_id) -> list[TopupLegRecord]`.
- [x] 2.2 `repositories/transaction.py` — SQL-реализация (фильтр `workspace_id` И `wallet_id`, только ноги
      транзакций с более чем одной ногой — тот же признак пополнения, что у `list_topup_legs_for_rates`).
- [x] 2.3 `tests/fakes/transaction_repository.py` — реализация метода для fake-репозитория.

## 3. Схема `Rate`

- [x] 3.1 `core/schemas/rate.py` — тип `Rate` (`Decimal`, `max_digits=28`, `decimal_places=10`,
      `PlainSerializer` в строку, тот же паттерн, что `Money`).

## 4. `WalletRateService`

- [x] 4.1 `core/services/wallet_rate.py::WalletRateService(transactions, wallets)` —
      `get_wallet_rates(wallet_id, workspace_id, *, target_currency_id)`: проверка существования кошелька
      (`NotFoundError`), проверка `target_currency_id in wallet.currency_ids` (`ClientError`), расчёт курсов через
      `average_rates`, округление каждого курса до 10 знаков (`ROUND_HALF_UP`), список `unrated_currency_ids`.
- [x] 4.2 Unit-тесты на fake-репозиториях: успешный расчёт (2 и 3+ валюты), усреднение по нескольким пополнениям,
      валюта без пополнений → `unrated_currency_ids`, кошелёк с одной валютой → пустой результат,
      `target_currency_id` не из валют кошелька → `ClientError`, чужой/несуществующий кошелёк → `NotFoundError`.

## 5. API и зависимости

- [x] 5.1 `core/schemas/wallet_rate.py` (или рядом с существующими схемами кошелька) — `WalletRatesOut`
      (`target_currency_id`, `rates: list[{currency_id, rate: Rate}]`, `unrated_currency_ids`).
- [x] 5.2 `depends/wallet_rate.py` — `get_wallet_rate_service`.
- [x] 5.3 `api/wallet_rates.py` (или метод в `api/wallets.py`, если так принято ближайшим соседним прецедентом
      `api/balances.py`) — `GET /api/workspaces/{workspace_id}/wallets/{wallet_id}/rates` под
      `Depends(require_workspace)`.
- [x] 5.4 Smoke-тест эндпоинта: успешный запрос, отсутствие `target_currency_id` (400), чужой воркспейс/кошелёк
      (404), запрос без аутентификации (401).

## 6. QualityGate

- [x] 6.1 `make format`, затем `make lint`, затем `make test` — все проходят подряд.
- [x] 6.2 `docs/tasks/021_wallet_average_rate.md` — заполнить раздел «Статус» по итогам реализации.
