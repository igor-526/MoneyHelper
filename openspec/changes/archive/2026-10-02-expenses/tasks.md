## 1. Сервис и схемы

- [x] 1.1 `TransactionService`: убрать `currency_id`, валюта ноги — `wallet.currency_id`, удалить проверку
  совпадения валют
- [x] 1.2 `api/schemas/transaction.py`: убрать `currency_id` из `TransactionCreate`, `extra="forbid"`;
  `api/transactions.py` без передачи валюты

## 2. Тесты

- [x] 2.1 Unit-тесты `TransactionService`: расход без валюты в валюте кошелька, точность по валюте кошелька
- [x] 2.2 API-тесты `/transactions` и адаптация остальных API-тестов (баланс, аналитика, курс) под тело без
  `currency_id`; отклонение лишнего `currency_id`
- [x] 2.3 Smoke-тест контракта расхода (создание без валюты, одна нога в валюте кошелька)
- [x] 2.4 Infrastructure-тесты: расход одной ногой через репозиторий, фильтры `wallet_id`/`category_id`/даты,
  пагинация, изоляция

## 3. Проверка

- [x] 3.1 `make format`, `make lint`, `make -C backend test`, `make -C backend test-infra`, `make test`
