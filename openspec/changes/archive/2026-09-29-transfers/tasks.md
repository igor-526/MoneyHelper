## 1. Сущности и протоколы

- [x] 1.1 `backend/src/core/entities/transaction.py` — добавить `TransactionLeg(BaseModel)`: `currency_id: UUID`,
      `amount: Decimal`; заменить `Transaction.currency_id`/`amount` на `legs: tuple[TransactionLeg, ...]`; экспорт
      `TransactionLeg` в `core/entities/__init__.py`
- [x] 1.2 `backend/src/core/entities/transfer.py` — `Transfer(Entity, TimestampMixin)`: `user_id: UUID`,
      `from_wallet_id: UUID`, `to_wallet_id: UUID`, `currency_id: UUID`, `amount: Decimal`, `occurred_at:
      datetime`; экспорт в `core/entities/__init__.py`
- [x] 1.3 `backend/src/core/protocols/balance_contributor.py` — протокол `BalanceContributor`: `async def
      balance_delta(self, wallet_id: UUID, user_id: UUID) -> dict[UUID, Decimal]: ...`; экспорт в
      `core/protocols/__init__.py`
- [x] 1.4 `backend/src/core/protocols/repositories/transaction_repository.py` — обновить протокол под ноги:
      `add(transaction: Transaction)`, `get_by_id`, `list`/`count` (без изменений сигнатуры фильтров),
      `update(transaction_id, user_id, *, wallet_id, category_id, legs: Sequence[TransactionLeg], occurred_at,
      now)`, `delete`; переименовать `balances(...)` → `balance_delta(...)` (та же сигнатура)
- [x] 1.5 `backend/src/core/protocols/repositories/transfer_repository.py` — новый протокол `TransferRepository`:
      `add`, `get_by_id(transfer_id, user_id)`, `list(user_id, *, wallet_id, date_from, date_to, limit, offset)`,
      `count(user_id, *, те же фильтры)`, `update(transfer_id, user_id, *, from_wallet_id, to_wallet_id,
      currency_id, amount, occurred_at, now)`, `delete(transfer_id, user_id)`, `balance_delta(wallet_id, user_id)`;
      экспорт в `core/protocols/repositories/__init__.py` и `core/protocols/__init__.py`

## 2. Сервисы и unit-тесты

- [x] 2.1 `backend/src/core/services/money_validation.py` — чистая функция `ensure_amount_precision(amount:
      Decimal, currency: Currency) -> None` (проверка числа знаков после запятой по `decimal_places`, `ClientError`
      без округления); вынесена из `TransactionService._validate_transaction_input`
- [x] 2.2 `backend/src/core/services/transaction.py` — обновить под ноги: `create_transaction`/`update_transaction`
      строят `Transaction` с `legs=(TransactionLeg(currency_id=..., amount=...),)`; приватный `_validate_leg_amount`
      (загрузка валюты + `ensure_amount_precision`), используется и обычным созданием, и пополнением; новый метод
      `create_topup(user_id, *, wallet_id, category_id, legs, occurred_at)`: категория обязана быть `income`
      (`ClientError`), набор валют `legs` обязан ровно совпадать с `wallet.currency_ids` без дублей (`ClientError`
      с перечислением отсутствующих/лишних валют), проверка каждой ноги через `_validate_leg_amount`;
      `get_wallet_balances`/`balances` убрать из `TransactionService` (переезжают в `BalanceService`, п. 2.4)
- [x] 2.3 `backend/src/core/services/transfer.py` — `TransferService(transfers: TransferRepository, wallets:
      WalletRepository, currencies: CurrencyRepository, clock: Clock, ids: IdGenerator)`: `create_transfer`,
      `get_transfer`, `list_transfers`, `update_transfer`, `delete_transfer`; валидация — `from_wallet_id !=
      to_wallet_id` (`ClientError`), оба кошелька существуют и принадлежат пользователю (`NotFoundError`),
      `currency_id` входит в `currency_ids` обоих кошельков (`ClientError`), сумма положительна и не превышает
      знаков валюты (`ensure_amount_precision`), `date_from <= date_to` в `list_transfers` (`ClientError`)
- [x] 2.4 `backend/src/core/services/balance.py` — `BalanceService(wallets: WalletRepository, contributors:
      Sequence[BalanceContributor])`: `get_wallet_balances(wallet_id, user_id)` — проверка владения кошельком
      (`NotFoundError`), суммирование `balance_delta` со всех `contributors`, достраивание нулей по всем
      `wallet.currency_ids`
- [x] 2.5 `tests/fakes/transaction_repository.py` — обновить `InMemoryTransactionRepository` под `legs`
      (`add`/`update`/`get_by_id`/`list` работают со списком ног), переименовать `balances` → `balance_delta`
- [x] 2.6 `tests/fakes/transfer_repository.py` — новый `InMemoryTransferRepository`, реализующий
      `TransferRepository` (фильтрация по `user_id`, `wallet_id` — совпадение с `from_wallet_id` ИЛИ
      `to_wallet_id`, `date_from`/`date_to`; сортировка `occurred_at DESC, id DESC`; `balance_delta` — расчёт в
      памяти)
- [x] 2.7 `tests/unit/test_transaction_service.py` — обновить существующие тесты под `legs`; добавить тесты
      `create_topup`: успех с полным набором валют многовалютного кошелька; отклонение при неполном наборе валют;
      отклонение при избыточном наборе валют; отклонение при повторяющейся валюте в ногах; отклонение категории не
      типа `income`; отклонение неположительной/превышающей знаки суммы в одной из ног; отклонение чужого/
      несуществующего `wallet_id`/`category_id`; удалить тесты `get_wallet_balances` (переезжают в п. 2.9)
- [x] 2.8 `tests/unit/test_transfer_service.py` — создание перевода (успех с датой и без даты); отклонение
      перевода самому себе; отклонение при отсутствии общей валюты у кошельков; отклонение валюты, не входящей в
      набор валют одного из кошельков (при наличии общей валюты, но переданной другой); отклонение
      неположительной/превышающей знаки суммы; отклонение чужого/несуществующего `from_wallet_id`/`to_wallet_id`;
      `get_transfer`/`update_transfer`/`delete_transfer` для чужого/несуществующего перевода — `NotFoundError`;
      `update_transfer` полностью заменяет поля; `list_transfers` — фильтр по `wallet_id` (совпадение с
      `from_wallet_id` ИЛИ `to_wallet_id`), по датам, отклонение `date_from > date_to`
- [x] 2.9 `tests/unit/test_balance_service.py` — новый: `get_wallet_balances` с одним `contributor` (нули по
      кошельку без вклада, корректная сумма); с несколькими `contributors` (вклад суммируется по валютам);
      `NotFoundError` на чужой/несуществующий кошелёк

## 3. Модели, миграция, репозитории

- [x] 3.1 `backend/src/models/transfer.py` — таблица `transfers`: `id`, `user_id` (FK `users.id`, `ON DELETE
      CASCADE`), `from_wallet_id`/`to_wallet_id` (FK `wallets.id`, `ON DELETE RESTRICT`), `currency_id` (FK
      `currencies.id`, `ON DELETE RESTRICT`), `amount` (`MONEY`), `occurred_at`, `created_at`, `updated_at`,
      `CheckConstraint("amount > 0", name="ck_transfers_amount_positive")`,
      `CheckConstraint("from_wallet_id <> to_wallet_id", name="ck_transfers_different_wallets")`; импорт в
      `models/__init__.py`
- [x] 3.2 Миграция `backend/src/migration/versions/20260929_0007_transfers.py` (`revision = "20260929_0007"`,
      `down_revision = "20260929_0006"`): создание `transfers`; `downgrade` — `drop_table("transfers")`
      (`make be-makemigrations msg="transfers"`, затем ручная сверка со схемой из design.md)
- [x] 3.3 `backend/src/repositories/transaction.py` — обновить под ноги: `_load_legs_map(transaction_ids)`/
      `_load_legs(transaction_id)` (батч-запрос `transaction_legs JOIN currencies ORDER BY transaction_id,
      currencies.code`, по образцу `WalletRepository._load_currency_ids_map`); `add`/`update` пишут N строк
      `transaction_legs` bulk-`insert`, затем перечитывают операцию через `get_by_id` для канонического порядка;
      `get_by_id`/`list` агрегируют ноги без N+1 (один запрос к `transactions`, один батч-запрос к
      `transaction_legs` по всем найденным `transaction_id`); переименовать `balances` → `balance_delta`
- [x] 3.4 `backend/src/repositories/transfer.py` — реализация `TransferRepository` на SQLAlchemy Core: `add`,
      `get_by_id(transfer_id, user_id)`, `list`/`count` (фильтр `wallet_id` — `OR(from_wallet_id == wallet_id,
      to_wallet_id == wallet_id)`, `date_from`/`date_to`, сортировка `occurred_at DESC, id DESC`), `update` (полная
      замена), `delete`, `balance_delta(wallet_id, user_id)` (агрегирующий `SELECT currency_id, SUM(CASE WHEN
      to_wallet_id = :wallet_id THEN amount ELSE -amount END) ... WHERE user_id = :user_id AND (from_wallet_id =
      :wallet_id OR to_wallet_id = :wallet_id) GROUP BY currency_id`)

## 4. Схемы, API, зависимости

- [x] 4.1 `backend/src/api/schemas/transaction.py` — `TransactionLegOut` (`currency_id: UUID`, `amount: Money`);
      `TransactionOut` — заменить `currency_id`/`amount` на `legs: list[TransactionLegOut]`;
      `TransactionCreate`/`TransactionUpdate` — без изменений (плоские); `TransactionLegIn` (`currency_id: UUID`,
      `amount: Money = Field(gt=0)`); `TopupCreate` (`wallet_id: UUID`, `category_id: UUID`, `legs:
      list[TransactionLegIn]`, `occurred_at: datetime | None = None`); убрать `WalletBalanceOut` (переезжает в
      п. 4.2)
- [x] 4.2 `backend/src/api/schemas/balance.py` — новый файл: `WalletBalanceOut` (`currency_id: UUID`, `balance:
      Money`), перенесённый из `api/schemas/transaction.py`
- [x] 4.3 `backend/src/api/schemas/transfer.py` — `TransferCreate`/`TransferUpdate` (`from_wallet_id: UUID`,
      `to_wallet_id: UUID`, `currency_id: UUID`, `amount: Money = Field(gt=0)`, `occurred_at: datetime | None =
      None`); `TransferOut` (`id`, `from_wallet_id`, `to_wallet_id`, `currency_id`, `amount`, `occurred_at`,
      `created_at`, `updated_at`, `from_attributes=True`); `TransferListParams(PageParams)` (`wallet_id: UUID |
      None`, `date_from: datetime | None`, `date_to: datetime | None`)
- [x] 4.4 `backend/src/api/transactions.py` — добавить `POST /topups` (регистрируется РАНЬШЕ `GET/PUT/DELETE
      /{transaction_id}` в файле — см. design.md), вызывает `TransactionService.create_topup`, 201; обновить
      сериализацию существующих обработчиков под `TransactionOut.legs`; убрать `wallet_balances_router` и
      обработчик баланса (переезжают в `api/balances.py`)
- [x] 4.5 `backend/src/api/balances.py` — новый файл: `wallet_balances_router = APIRouter(tags=["Transactions"])`,
      `GET /api/wallets/{wallet_id}/balances` → `list[WalletBalanceOut]`, зависит от `BalanceService`
- [x] 4.6 `backend/src/api/transfers.py` — роутер `router` (`/api/transfers`, тег `Transfers`), все маршруты под
      `Depends(get_current_user)`: `POST` → 201, `GET` (`Annotated[TransferListParams, Query()]`) → `Page
      [TransferOut]`, `GET /{transfer_id}` → 200/404, `PUT /{transfer_id}` → 200/400/404, `DELETE /{transfer_id}`
      → 204/404
- [x] 4.7 `backend/src/depends/transaction.py` — добавить сборку зависимостей `create_topup` (без изменений
      сигнатуры `get_transaction_service`, метод уже на существующем сервисе); убрать сборку баланса (переезжает в
      `depends/balance.py`)
- [x] 4.8 `backend/src/depends/transfer.py` — новый файл: `get_transfer_repository(session)`,
      `get_transfer_service(transfers, wallets, currencies, clock, ids)`
- [x] 4.9 `backend/src/depends/balance.py` — новый файл: `get_balance_service(wallets, transactions, transfers) ->
      BalanceService` — собирает `BalanceService(wallets, [transactions, transfers])`
- [x] 4.10 `backend/src/main.py` — подключить `transfers_router` (`api/transfers.py`) и `balances_router`
      (`api/balances.py`) вместо прежнего `wallet_balances_router` из `api/transactions.py`

## 5. API-, smoke- и инфраструктурные тесты

- [x] 5.1 `tests/api/test_transactions.py` — обновить существующие сценарии под `legs` в ответе (create/get/list/
      put); добавить тесты `POST /api/transactions/topups`: успех с полным набором валют многовалютного кошелька;
      воспроизводимость курса по сохранённым ногам (сравнение отношения сумм двух ног); 400 при неполном/
      избыточном/повторяющемся наборе валют; 400 при категории не типа `income`; 400 при неположительной/
      превышающей знаки сумме в одной из ног; 404 на чужой/несуществующий `wallet_id`/`category_id`; 401 без
      access-cookie; тест маршрутизации — `POST /api/transactions/topups` не воспринимается как
      `POST /api/transactions/{transaction_id}` (несуществующий метод/путь для параметризованного маршрута)
- [x] 5.2 `tests/api/test_transactions.py` — тест: `PUT /api/transactions/{id}` на операции-пополнении с
      несколькими нотами заменяет их одной ногой (см. сценарий в specs/transactions/spec.md)
- [x] 5.3 Убрать из `tests/api/test_transactions.py` тесты `GET /api/wallets/{wallet_id}/balances` (переезжают в
      `tests/api/test_balances.py`, п. 5.4), добавить туда же тест учёта переводов в балансе
- [x] 5.4 `tests/api/test_balances.py` — новый: перенесённые тесты баланса (нули по кошельку без операций/
      переводов, доходы/расходы, разделение по валютам, 404 на чужой/несуществующий кошелёк) плюс новый сценарий
      «баланс учитывает перевод» (зачисление увеличивает баланс, списание уменьшает)
- [x] 5.5 `tests/api/test_transfers.py` — новый: CRUD через `TestClient` + `app.dependency_overrides`: успешные
      create/get/list/put/delete; 400 при отсутствии общей валюты, переводе самому себе, неположительной/
      превышающей знаки сумме; 404 на несуществующий/чужой `from_wallet_id`/`to_wallet_id`/`transfer_id`; 401 без
      access-cookie; фильтр `wallet_id` (совпадение с `from_wallet_id` ИЛИ `to_wallet_id`); фильтр по датам;
      пагинация; сортировка `occurred_at DESC, id DESC`; изоляция пользователей (404, не 403, во всех сценариях)
- [x] 5.6 Дополнить `tests/api/test_wallets.py` — `DELETE /api/wallets/{wallet_id}` возвращает 409, если по
      кошельку есть перевод (кошелёк и перевод не удаляются)
- [x] 5.7 Дополнить `tests/smoke/test_app_smoke.py` — новые пути (`POST /api/transactions/topups`,
      `/api/transfers*`, `/api/wallets/{wallet_id}/balances` под новым роутером) зарегистрированы в OpenAPI-схеме
- [x] 5.8 `tests/infrastructure/test_transaction_repository.py` — обновить под ноги: `add`/`get_by_id`/`update`
      с несколькими ногами на реальной БД (в т. ч. батч-агрегация `list` без N+1 — проверить число выполненных
      запросов или явно проверить корректность результата на нескольких операциях с разным числом ног); переименовать
      тесты `balances` → `balance_delta`
- [x] 5.9 `tests/infrastructure/test_transfer_repository.py` — новый (маркер `infrastructure`, фикстура
      `db_session`): `add`/`get_by_id`/`list`/`count`/`update`/`delete` на реальной БД; `list`/`count` с фильтром
      `wallet_id`/`date_from`/`date_to`; сортировка `occurred_at DESC, id DESC`; изоляция по `user_id`; `RESTRICT`
      — попытка удалить кошелёк/валюту, на которые ссылается перевод, завершается `IntegrityError`;
      `CheckConstraint` — попытка вставить перевод с `amount <= 0` или с `from_wallet_id == to_wallet_id` напрямую
      через `Core insert` завершается ошибкой БД; `balance_delta` корректно агрегирует зачисления и списания
- [x] 5.10 Дополнить `tests/infrastructure/test_wallet_repository.py` — `delete()` поднимает `ConflictError` при
      наличии связанного перевода (реальная БД, `RESTRICT` от `transfers.from_wallet_id`/`to_wallet_id`)

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test` (backend unit + smoke)
- [x] 6.4 `make test-infra` (backend infrastructure, включая новые/обновлённые тесты `transaction_repository`,
      `transfer_repository`, дополненный `wallet_repository`)
