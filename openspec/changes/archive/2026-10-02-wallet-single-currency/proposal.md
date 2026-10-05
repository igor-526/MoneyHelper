## Why

Валютная модель (задачи 024–035) отменяет «кошелёк с несколькими валютами»: у кошелька ровно одна валюта (она может
совпадать с основной валютой воркспейса, добавленной в `workspace-currency`). Пополнения, расходы, переводы и
аналитика в следующих задачах строятся на этом инварианте.

## What Changes

- `Wallet.currency_ids` заменяется на `Wallet.currency_id`; таблица `wallet_currencies` удаляется,
  `wallets.currency_id` — обязательный внешний ключ на `currencies` (`ON DELETE RESTRICT`).
- `POST`/`PUT /api/workspaces/{workspace_id}/wallets*` принимают `currency_id` вместо `currency_ids`; `WalletOut`
  отдаёт `currency_id`. Список валют в запросе отклоняется (400).
- `PUT` кошелька: смена `currency_id` отклоняется (409), если по кошельку есть операции или переводы.
- `GET .../wallets/{wallet_id}/balances` возвращает один объект `{currency_id, balance}` (баланс в валюте кошелька)
  вместо списка. **BREAKING**.
- `BalanceContributor.balance_delta` принимает `currency_id` и возвращает одно число `Decimal`.
- Минимальная совместимая адаптация (правила переделываются в 026–029): валюта обычной операции и перевода должна
  совпадать с валютой кошелька(ей); пополнение с несколькими ногами принимает ровно одну ногу в валюте кошелька;
  средний курс кошелька всегда пустой (у кошелька одна валюта).
- **BREAKING**: `currency_ids` в кошельке и `currency_ids`-логика операций удалены.
- Миграция Alembic `20261002_0011` сбрасывает `wallets`, `transactions`, `transfers` (данные не переносятся),
  удаляет `wallet_currencies`, добавляет `wallets.currency_id`.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

- `wallets`: одна валюта кошелька (создание, чтение, обновление с запретом смены при наличии операций, удаление, курс).
- `transactions`: валюта операции совпадает с валютой кошелька; пополнение — одна нога; баланс — одно число.
- `transfers`: валюта перевода совпадает с валютой обоих кошельков.

## Impact

- БД: `wallets` (+ `currency_id`), удаление `wallet_currencies`, миграция `20261002_0011`; данные сбрасываются.
- Backend: сущность `Wallet`, протоколы (`WalletRepository`, новый `WalletUsageChecker`, `BalanceContributor`),
  `WalletService`, `BalanceService`, `TransactionService`, `TransferService`, `WalletRateService`, репозитории
  кошельков/операций/переводов, схемы и роутеры кошельков и балансов, `depends`.
- API: `/api/workspaces/{id}/wallets*` и `.../balances` (меняется контракт).
- Тесты: unit, api, smoke, infrastructure (репозиторий, миграция, RESTRICT).

## Вне рамок

- Frontend (задача 032; до неё frontend, использующий `currency_ids`, несовместим — задачи 031–035 идут после backend).
- Правила пополнений, расходов, переводов и аналитики новой модели (026–029) — здесь только минимальная адаптация.
- Перенос старых данных (они сбрасываются).
