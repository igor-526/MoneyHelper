## 1. Домен и протоколы

- [x] 1.1 `Wallet.currency_ids` → `Wallet.currency_id` в сущности
- [x] 1.2 Протокол `WalletUsageChecker` (`references_wallet`) и экспорт; `WalletRepository.update` с `currency_id`
- [x] 1.3 `BalanceContributor.balance_delta(wallet_id, workspace_id, currency_id) -> Decimal`; обновить протоколы
  `TransactionRepository`/`TransferRepository` (+ `references_wallet`)

## 2. Сервисы

- [x] 2.1 `WalletService`: одна валюта, проверка существования, запрет смены при операциях/переводах (`ConflictError`)
- [x] 2.2 `BalanceService.get_wallet_balance` — одно число в валюте кошелька
- [x] 2.3 `TransactionService`/`TransferService`: валюта совпадает с валютой кошелька(ей); пополнение — одна нога
- [x] 2.4 `WalletRateService`: пустой результат, проверка `target_currency_id`

## 3. БД и репозитории

- [x] 3.1 Модель `wallets.currency_id`, удаление `wallet_currencies` из моделей
- [x] 3.2 Миграция Alembic `20261002_0011`: очистка данных, удаление `wallet_currencies`, `currency_id` NOT NULL + FK, downgrade
- [x] 3.3 `repositories/wallet.py` (без M2M), `references_wallet` и `balance_delta` в репозиториях операций и переводов

## 4. API и сборка зависимостей

- [x] 4.1 Схемы кошелька (`currency_id`, `extra="forbid"`) и баланса (один объект)
- [x] 4.2 Роутеры кошельков и балансов; `depends/wallet.py`, `depends/balance.py`, `depends/wallet_rate.py`

## 5. Тесты

- [x] 5.1 Fakes и фабрики тестов под `currency_id`; обновить существующие unit/api/smoke тесты
- [x] 5.2 Unit-тесты `WalletService` (создание, неизвестная валюта, смена с операциями/переводами и без), `BalanceService`, `WalletRateService`, операций и переводов
- [x] 5.3 API-тесты кошельков (отклонение `currency_ids`, 409, баланс-объект, курс)
- [x] 5.4 Smoke-тест: OpenAPI кошелька содержит `currency_id`, без `currency_ids`
- [x] 5.5 Infrastructure-тесты: репозиторий, RESTRICT, `references_wallet`, `balance_delta`, миграция (очистка, схема, downgrade)

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test`
- [x] 6.4 `make test-infra`
