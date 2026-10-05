## 1. Домен и протоколы

- [x] 1.1 Убрать `currency_id` из сущности `Transfer`
- [x] 1.2 Убрать `currency_id` из `TransferRepository.update` (протокол); `balance_delta` сохраняет контракт `BalanceContributor`

## 2. Сервис

- [x] 2.1 `TransferService`: валюта выводится из кошельков, отдельная проверка одинаковой валюты кошельков (400), точность суммы по валюте кошельков

## 3. БД и репозиторий

- [x] 3.1 Модель `transfers` без `currency_id`
- [x] 3.2 Миграция Alembic `20261002_0012`: сброс `transfers`, удаление `currency_id`, downgrade
- [x] 3.3 `repositories/transfer.py`: без `currency_id` (маппинг, insert, update, `balance_delta` без фильтра по валюте)

## 4. API

- [x] 4.1 Схемы `TransferCreate` (`extra="forbid"`, без `currency_id`) и `TransferOut` (без `currency_id`); роутер переводов

## 5. Тесты

- [x] 5.1 Fake-репозиторий и все тесты, создающие `Transfer`/payload с `currency_id`
- [x] 5.2 Unit-тесты `TransferService` (разные валюты, одна валюта, точность, update) и баланс переводов
- [x] 5.3 API-тесты (400 при разных валютах и при `currency_id`, ответ без `currency_id`, баланс обоих кошельков, перевод не влияет на курс)
- [x] 5.4 Smoke-тест и infrastructure-тесты (репозиторий, баланс, миграция `0012` upgrade/downgrade)

## 6. Проверка

- [x] 6.1 `make format`, `make lint`, `make -C backend test`, `make -C backend test-infra`, `make test`
