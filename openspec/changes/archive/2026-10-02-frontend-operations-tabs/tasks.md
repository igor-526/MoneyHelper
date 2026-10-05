## 1. Типы, хуки, инвалидация

- [x] 1.1 `Transaction.ts`: `TransactionFormValues` без `currency_id`; `Transfer`/`TransferFormValues` без `currency_id`
- [x] 1.2 `useTransactions` без `type`; хуки пополнений `useTopups`, `useCreateTopup` (`/topups`), `useUpdateTopup`,
  `useDeleteTopup`; тесты
- [x] 1.3 `invalidateOperationCaches` (списки, балансы, курсы, аналитика) и её вызов во всех мутациях операций; тесты

## 2. Формы и карточка

- [x] 2.1 `TransactionForm` — только расход: без типа и выбора валюты, подпись валюты кошелька; тесты
- [x] 2.2 `TopupForm`: поля сумм по `{валюта воркспейса, валюта кошелька}`, редактирование; тесты
- [x] 2.3 `TransactionCard`: без типа и блокировки редактирования, удаление через `useDelete` вида; тесты
- [x] 2.4 `TransferForm`/`TransferCard`: без валюты, «Куда» только той же валюты; тесты

## 3. Страница

- [x] 3.1 Таблица `operationKinds`, `OperationsTab`, `TransactionsPage` с вкладками и `?tab=`; тесты

## 4. Проверка

- [x] 4.1 Проверить в браузере (десктоп и iframe 390 px): пополнение RUB-кошелька (одно поле) и кошелька другой
  валюты (два поля), расход, редактирование и удаление на обеих вкладках, баланс, консоль без ошибок
- [x] 4.2 QualityGate: `make format`, `make lint`, `make test` проходят
