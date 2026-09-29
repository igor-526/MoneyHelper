## Why

Пользователь ведёт несколько кошельков в разных валютах — сейчас (010, `transactions`) можно только заводить
доходы и расходы по одному кошельку в одной валюте. Не хватает двух операций, без которых многовалютный учёт
неполон: пополнения кошелька сразу во всех его валютах (со сбором курса между ними) и перевода денег между
собственными кошельками пользователя. Задача 011 закрывает backend для обоих сценариев; зависимость (010) уже
реализована и заархивирована, дорожная карта готова к этому шагу.

## What Changes

- `Transaction` становится «ногозависимой» сущностью: новый value-object `TransactionLeg` (`currency_id`,
  `amount`), `Transaction.legs: tuple[TransactionLeg, ...]` вместо плоских `currency_id`/`amount` — ровно тот
  рефакторинг, который design.md изменения `transactions` явно предсказал и отложил как задел. `TransactionOut`
  тоже становится ногозависимой (`legs: list[TransactionLegOut]`). Тело `POST`/`PUT /api/transactions*` не
  меняется — оба по-прежнему создают/заменяют операцию ровно с одной ногой.
- **BREAKING**: форма ответа `TransactionOut` меняется — вместо плоских `currency_id`/`amount` возвращается
  `legs: list[{currency_id, amount}]`.
- Новый эндпоинт `POST /api/transactions/topups` — пополнение многовалютного кошелька: категория обязана быть
  типа `income`, ноги обязаны покрывать ровно набор валют кошелька (не больше, не меньше, без дублей). Курс между
  валютами пополнения не хранится отдельным полем — выводится из сохранённых ног при необходимости.
- Новая капабилити `transfers` — перевод между кошельками одного пользователя в одной валюте (без конвертации),
  допустим только если валюта перевода входит в набор валют обоих кошельков. Полноценный CRUD:
  `POST/GET/GET{id}/PUT{id}/DELETE{id} /api/transfers*`.
- Баланс кошелька выносится в новый `BalanceService`, компонующий вклад операций и переводов через протокол
  `BalanceContributor`. `GET /api/wallets/{wallet_id}/balances` переезжает из `api/transactions.py` в новый
  `api/balances.py` (путь и тег не меняются).
- `TransactionRepository.balances(...)` переименовывается в `balance_delta(...)` (структурное соответствие
  протоколу `BalanceContributor`); аналогичный метод добавляется в новый `TransferRepository`.
- Новая таблица `transfers` в миграции `20260929_0007` (схема `transactions`/`transaction_legs` не меняется —
  010 уже спроектировала `transaction_legs` под несколько строк на операцию).
- `WalletRepository.delete()` получает ещё один источник `ON DELETE RESTRICT` (переводы) — код перехвата
  `IntegrityError` → `ConflictError` уже общий, менять не нужно.

## Capabilities

### New Capabilities
- `transfers`: перевод денег между кошельками пользователя в одной валюте (создание, чтение одной/списка с
  фильтром по кошельку и пагинацией, полная замена, физическое удаление), изоляция данных по владельцу.

### Modified Capabilities
- `transactions`: форма ответа операции становится ногозависимой (`legs` вместо плоских `currency_id`/`amount`)
  для создания, чтения одной операции, списка операций и полного обновления; добавляется новое требование
  «Пополнение многовалютного кошелька» (`POST /api/transactions/topups`); требование «Баланс по кошельку и
  валюте» меняется — теперь учитывает вклад и операций, и переводов.
- `wallets`: требование «Удаление кошелька» уточняется — источником конфликта при удалении теперь может быть не
  только операция, но и перевод.

## Impact

- **БД**: требуется миграция Alembic `20260929_0007` — новая таблица `transfers` (`id`, `user_id`,
  `from_wallet_id`, `to_wallet_id`, `currency_id`, `amount`, `occurred_at`, `created_at`, `updated_at`,
  `CheckConstraint("amount > 0")`, `CheckConstraint("from_wallet_id <> to_wallet_id")`). Схема
  `transactions`/`transaction_legs` не меняется.
- **API**: новый эндпоинт `POST /api/transactions/topups`; новые эндпоинты `/api/transfers*` (5 штук); перенос
  (без изменения контракта) `GET /api/wallets/{wallet_id}/balances` в `api/balances.py`; **BREAKING** изменение
  формы ответа `TransactionOut` (`legs` вместо плоских полей) для всех существующих эндпоинтов операций.
- **backend/src**: `core/entities/transaction.py` (`TransactionLeg`, `Transaction.legs`), новый
  `core/entities/transfer.py`, `core/protocols/repositories/transaction_repository.py` (агрегация ног,
  `balance_delta`), новый `core/protocols/repositories/transfer_repository.py`, новый
  `core/protocols/balance_contributor.py`, `core/services/transaction.py` (ноги, `create_topup`), новый
  `core/services/transfer.py`, новый `core/services/balance.py`; `models/transaction.py` не меняется, новый
  `models/transfer.py`; `repositories/transaction.py` (агрегация ног без N+1, переименование `balances` →
  `balance_delta`), новый `repositories/transfer.py`; `api/schemas/transaction.py` (`TransactionLegOut`,
  `TopupCreate`), новый `api/schemas/transfer.py`; `api/transactions.py` (эндпоинт пополнения, порядок маршрутов),
  новый `api/transfers.py`, новый `api/balances.py`; `depends/transaction.py`, новый `depends/transfer.py`, новый
  `depends/balance.py`; `main.py` (подключение новых роутеров, замена роутера баланса); `migration/versions/`
  (новая ревизия `20260929_0007`).
- Тесты backend: unit (`core/services/transaction.py` с ногами и `create_topup`, новый
  `core/services/transfer.py`, новый `core/services/balance.py`), api (обновление `tests/api/test_transactions.py`
  под `legs`, сценарии пополнения, новый `tests/api/test_transfers.py`), smoke (регистрация новых путей),
  infrastructure (обновление `tests/infrastructure/test_transaction_repository.py` под агрегацию ног, новый
  `tests/infrastructure/test_transfer_repository.py`, дополнение `tests/infrastructure/test_wallet_repository.py`
  сценарием `ConflictError` от перевода).
- Frontend не затрагивается — задача 011 закрывает только backend.

## Non-goals

- Конвертация валют внутри перевода (перевод — одна и та же сумма в одной валюте между кошельками).
- Редактирование пополнения через `PUT /api/transactions/{id}` — только удаление и создание заново через
  `POST /api/transactions/topups`.
- Внешние источники курсов валют.
- Аналитика доходов/расходов/переводов в разрезах — задача 012.
- Частичное обновление (`PATCH`) — только полная замена через `PUT`, как и в 010.
- Кэширование баланса — по-прежнему вычисляется на лету.
