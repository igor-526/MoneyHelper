## 1. Типы и хуки

- [x] 1.1 `Wallet`/`WalletFormValues`: `currency_ids` → `currency_id`; обновить фикстуры тестов кошельков
- [x] 1.2 `useWalletBalances`/`WalletBalanceCard`: один объект `{currency_id, balance}`; тесты
- [x] 1.3 `useWalletRates`/`WalletRateCard`: новый контракт `GET .../rates` (минимально, до 035); тесты

## 2. Кошельки

- [x] 2.1 `WalletForm`: одиночный `CurrencyPicker`, правило «Выберите валюту», обработка 409 (поле + toast); тесты
- [x] 2.2 `WalletCard` и `WalletsPage`: один чип валюты; тесты

## 3. Минимальная совместимость 033/034

- [x] 3.1 `TransactionForm`, `TopupForm`, `TransferForm`: источник валют — `wallet.currency_id`; обновить тесты
  и фикстуры

## 4. Проверка

- [x] 4.1 Проверить в браузере (десктоп и телефон): воркспейс с валютой, создание и редактирование кошелька с одной
  валютой, список/карточки/баланс одной суммой, консоль без ошибок
- [x] 4.2 QualityGate: `make format`, `make lint`, `make test` проходят
