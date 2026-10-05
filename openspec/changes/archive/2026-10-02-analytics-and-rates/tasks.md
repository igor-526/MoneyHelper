## 1. Протоколы и репозитории

- [x] 1.1 Протокол `WalletCurrencyReader` (`get_currency_ids`) в `core/protocols/repositories` и экспорт
- [x] 1.2 `get_currency_ids` в SQL- и in-memory-репозиториях кошельков
- [x] 1.3 `list_topup_legs_for_rates` по категории `income` с необязательными `wallet_id`/`date_from`/`date_to`
  (протокол, SQL, fake)

## 2. Сервисы

- [x] 2.1 `AnalyticsService`: валюта отображения по умолчанию и допустимые значения, одна нога в валюте кошелька
- [x] 2.2 `WalletRateService`: курс кошелька (`rate` / `1` / `null`), квантование до 10 знаков

## 3. API и сборка зависимостей

- [x] 3.1 Схемы и роутер аналитики (`display_currency` необязателен), `depends/analytics.py`
- [x] 3.2 Схема и роутер `GET .../rates` без параметров, `depends/wallet_rate.py`

## 4. Тесты

- [x] 4.1 Unit-тесты `AnalyticsService` и `WalletRateService`
- [x] 4.2 API-тесты аналитики и курса кошелька, smoke-тест
- [x] 4.3 Infrastructure-тесты репозиториев (`list_topup_legs_for_rates`, `get_currency_ids`)

## 5. Проверки

- [x] 5.1 `make format`, `make lint`, `make -C backend test`, `make -C backend test-infra`, `make test`
