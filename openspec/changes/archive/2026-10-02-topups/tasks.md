## 1. Домен и протоколы

- [x] 1.1 Протокол `TopupLegsRule` и экспорт из `core/protocols`
- [x] 1.2 Протокол `WorkspaceCurrencyReader` (`get_currency_id`) и экспорт
- [x] 1.3 `validate_leg_amount` в `core/services/money_validation.py`; помощник `get_of_type` в
  `core/services/transaction_kind.py`

## 2. Сервисы

- [x] 2.1 Правила `SameCurrencyTopupLegs` и `CrossCurrencyTopupLegs` в `core/services/topup_legs.py`
- [x] 2.2 `TopupService`: создание, чтение, список, обновление, удаление
- [x] 2.3 `TransactionService`: только расходы (отклонение `income`, `get/update/delete` и список — только расходы),
  удаление `create_topup` и проверки набора ног

## 3. Репозиторий воркспейсов

- [x] 3.1 `get_currency_id` в SQL-репозитории воркспейсов

## 4. API и сборка зависимостей

- [x] 4.1 Схемы `api/schemas/topup.py`; удаление топап-схем из `api/schemas/transaction.py`, `type` из
  `TransactionListParams`
- [x] 4.2 Роутер `api/topups.py`, подключение в `main.py`; удаление `POST /transactions/topups`
- [x] 4.3 `depends/topup.py` (регистрация правил ног, сборка сервиса)

## 5. Тесты

- [x] 5.1 Fakes: `get_currency_id` в `InMemoryWorkspaceRepository`; адаптация существующих тестов (баланс,
  аналитика, операции) под запрет дохода в `/transactions`
- [x] 5.2 Unit-тесты правил ног, `TopupService`, `get_of_type`, обновлённого `TransactionService`
- [x] 5.3 API-тесты `/topups` (CRUD, ноги, категория, точность, изоляция) и обновлённые тесты `/transactions`
- [x] 5.4 Smoke-тест эндпоинтов пополнений
- [x] 5.5 Infrastructure-тесты: `get_currency_id`, пополнения через репозиторий (две ноги, замена ног, список
  `income`, изоляция воркспейсов)

## 6. Проверка

- [x] 6.1 `make format`, `make lint`, `make -C backend test`, `make -C backend test-infra`, `make test`
