## 1. Инфраструктура вкладок

- [x] 1.1 `operationKinds.ts`: `OperationKind {key,label,Panel}` и `TransactionKind`; таблицы вкладок и настроек операций;
  вкладка «Перевод»; `OperationsTab`/`TransactionCard` принимают `TransactionKind`; тесты таблицы
- [x] 1.2 `TransactionsPage`: вкладки из таблицы, удалить ссылку «Переводы»; тесты
- [x] 1.3 `routes.tsx`: `/transfers` → редирект на `/transactions?tab=transfer`; тесты `App`/`AppLayout`

## 2. Переводы

- [x] 2.1 `TransfersPage` → `TransfersTab` (без заголовка), тесты
- [x] 2.2 `TransferForm`: пустое состояние с пояснением, отключение «Куда» и отправки; тесты
- [x] 2.3 `invalidateTransferCaches` в трёх мутациях; тесты

## 3. Проверка

- [x] 3.1 Браузер (десктоп и iframe 390 px): воркспейс RUB, два кошелька RUB и CNY, пополнения, перевод RUB→RUB,
  балансы, пустое состояние для CNY, редактирование и удаление перевода, консоль без ошибок
- [x] 3.2 QualityGate: `make format`, `make lint`, `make test` проходят
