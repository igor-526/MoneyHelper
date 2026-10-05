## Why

Backend (задачи 025, 029) перевёл кошелёк на одну валюту: `WalletOut.currency_id` вместо `currency_ids`, баланс —
один объект `{currency_id, balance}`, `GET .../rates` — без query-параметров и с другой формой ответа. Frontend
всё ещё работает с несколькими валютами кошелька и несовместим с API.

## What Changes

- **BREAKING (контракт)** Тип `Wallet`/`WalletFormValues`: `currency_ids: string[]` → `currency_id: string`.
- `WalletForm`: одиночный выбор валюты вместо мультивыбора; при смене валюты кошелька с операциями или переводами
  (409 от backend) ошибка показывается у поля валюты и toast-ом.
- `WalletCard`: одна валюта кошелька — один чип с кодом.
- `WalletBalanceCard`/`useWalletBalances`: ответ — один объект `{currency_id, balance}`, баланс одной суммой.
- `WalletRateCard`/`useWalletRates`: минимальная совместимая правка под новый `GET .../rates` (полноценная
  переделка — задача 035).
- Минимальная совместимая правка форм операций, пополнения и перевода (`TransactionForm`, `TopupForm`,
  `TransferForm`) под `wallet.currency_id`, чтобы приложение собиралось и не падало; их переделка — 033/034.

## Capabilities

### New Capabilities

### Modified Capabilities

- `frontend-wallets`: карточка и форма кошелька с одной валютой, блокировка смены валюты по 409, курс по новому
  контракту.

## Impact

- `frontend/src/features/wallets/*`, `frontend/src/features/transactions/{WalletBalanceCard,useWalletBalances,Transaction,TransactionForm,TopupForm}`,
  `frontend/src/features/transfers/TransferForm.tsx` и их тесты.
- API: `/wallets` (`currency_id`), `/wallets/{id}/balances` (один объект), `/wallets/{id}/rates` (новая форма).
