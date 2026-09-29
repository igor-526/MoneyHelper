## 1. Сущность и протоколы

- [x] 1.1 `backend/src/core/entities/transaction.py` — `Transaction(Entity, TimestampMixin)`: `user_id: UUID`,
      `wallet_id: UUID`, `category_id: UUID`, `currency_id: UUID`, `amount: Decimal`, `occurred_at: datetime`;
      экспорт в `core/entities/__init__.py`
- [x] 1.2 `backend/src/core/protocols/repositories/transaction_repository.py` — протокол `TransactionRepository`:
      `add`, `get_by_id(transaction_id, user_id)`, `list(user_id, *, wallet_id, category_id, type, date_from,
      date_to, limit, offset)`, `count(user_id, *, те же фильтры)`, `update(transaction_id, user_id, *, wallet_id,
      category_id, currency_id, amount, occurred_at, now)`, `delete(transaction_id, user_id)`,
      `balances(wallet_id, user_id) -> dict[UUID, Decimal]`; экспорт в `core/protocols/repositories/__init__.py` и
      `core/protocols/__init__.py`
- [x] 1.3 Добавить в `core/protocols/repositories/currency_repository.py` метод
      `get_by_id(currency_id: UUID) -> Currency | None`
- [x] 1.4 Добавить `ConflictError(ClientError)` (`status_code = 409`) в `core/exceptions/base.py`, экспортировать
      в `core/exceptions/__init__.py`

## 2. Сервис и unit-тесты

- [x] 2.1 `backend/src/core/services/transaction.py` — `TransactionService(transactions: TransactionRepository,
      wallets: WalletRepository, categories: CategoryRepository, currencies: CurrencyRepository, clock: Clock,
      ids: IdGenerator)`: `create_transaction`, `get_transaction`, `list_transactions`, `update_transaction`,
      `delete_transaction`, `get_wallet_balances`; проверка существования и принадлежности кошелька/категории
      (`NotFoundError`), проверка `currency_id in wallet.currency_ids` (`ClientError`), проверка числа знаков
      суммы по `Currency.decimal_places` (`ClientError`, без округления), проверка `date_from <= date_to` в
      `list_transactions` (`ClientError`); `get_wallet_balances` — после проверки владения кошельком дополняет
      результат `TransactionRepository.balances` нулями по всем `wallet.currency_ids` (порядок берётся из уже
      отсортированного по коду валюты `wallet.currency_ids`)
- [x] 2.2 `tests/fakes/transaction_repository.py` — `InMemoryTransactionRepository`, реализующая протокол
      (фильтрация по `user_id` и опционально `wallet_id`/`category_id`/`type`/`date_from`/`date_to`, сортировка
      `occurred_at DESC, id DESC`, расчёт `balances` в памяти)
- [x] 2.3 Дополнить `tests/fakes/currency_repository.py` (`InMemoryCurrencyRepository`) методом `get_by_id`
- [x] 2.4 `tests/unit/test_transaction_service.py`: создание операции (успех с датой и без даты — используется
      `Clock.now()`); отклонение валюты не из набора кошелька; отклонение суммы с превышением знаков валюты;
      отклонение неположительной суммы (если не отсечено схемой раньше); `get_transaction`/`update_transaction`/
      `delete_transaction` для чужой/несуществующей операции — везде `NotFoundError`; отклонение чужого/
      несуществующего `wallet_id`/`category_id` при создании и обновлении; `update_transaction` полностью заменяет
      поля; `list_transactions` — фильтры по `wallet_id`/`category_id`/`type`/датам и их комбинации, отклонение
      `date_from > date_to`; `get_wallet_balances` — нули по кошельку без операций, корректная сумма
      доходов/расходов, раздельные балансы по валютам, `NotFoundError` на чужой/несуществующий кошелёк

## 3. Модели, миграция, репозиторий

- [x] 3.1 `backend/src/models/transaction.py` — таблицы `transactions` (FK `user_id → users.id ON DELETE CASCADE`,
      `wallet_id → wallets.id ON DELETE RESTRICT`, `category_id → categories.id ON DELETE RESTRICT`) и
      `transaction_legs` (составной PK `(transaction_id, currency_id)`, FK `transaction_id → transactions.id ON
      DELETE CASCADE`, FK `currency_id → currencies.id ON DELETE RESTRICT`, колонка `amount` типа `MONEY`,
      `CheckConstraint("amount > 0", name="ck_transaction_legs_amount_positive")`); импорт в `models/__init__.py`
- [x] 3.2 Миграция `backend/src/migration/versions/20260929_0006_transactions.py` (`revision = "20260929_0006"`,
      `down_revision = "20260929_0005"`): создание `transactions`, затем `transaction_legs`; `downgrade` —
      обратный порядок (`make be-makemigrations msg="transactions"`, затем ручная сверка со схемой из design.md)
- [x] 3.3 `backend/src/repositories/currency.py` — реализация `get_by_id` (`SELECT ... WHERE id = :currency_id`)
- [x] 3.4 `backend/src/repositories/wallet.py` — `delete()` оборачивается в `try/except IntegrityError` →
      `raise ConflictError("Кошелёк нельзя удалить: есть операции") from exc`
- [x] 3.5 `backend/src/repositories/category.py` — `delete()` оборачивается в `try/except IntegrityError` →
      `raise ConflictError("Категорию нельзя удалить: есть операции") from exc`
- [x] 3.6 `backend/src/repositories/transaction.py` — реализация `TransactionRepository` на SQLAlchemy Core:
      `add`/`update` пишут строку `transactions` и ровно одну строку `transaction_legs` в одной транзакции сессии;
      `list`/`count` строят запрос с `JOIN categories` (для фильтра `type`), опциональными `WHERE` по
      `wallet_id`/`category_id`/`date_from`/`date_to`; `list` сортирует `occurred_at DESC, id DESC`; `balances` —
      один агрегирующий `SELECT ... GROUP BY transaction_legs.currency_id` с `JOIN transactions, categories`,
      `CASE WHEN categories.type = 'income' THEN amount ELSE -amount END`, `WHERE wallet_id = ... AND user_id = ...`

## 4. Схемы, API, зависимости

- [x] 4.1 `backend/src/api/schemas/transaction.py` — `TransactionCreate`/`TransactionUpdate` (`wallet_id: UUID`,
      `category_id: UUID`, `currency_id: UUID`, `amount: Money` с `Field(gt=0)`, `occurred_at: datetime | None =
      None`); `TransactionOut` (`id`, `wallet_id`, `category_id`, `currency_id`, `amount`, `occurred_at`,
      `created_at`, `updated_at`, `from_attributes=True`); `TransactionListParams(PageParams)` (`wallet_id: UUID |
      None`, `category_id: UUID | None`, `type: CategoryType | None`, `date_from: datetime | None`, `date_to:
      datetime | None`, по образцу `CategoryListParams`); `WalletBalanceOut` (`currency_id: UUID`, `balance:
      Money`)
- [x] 4.2 `backend/src/api/transactions.py` — роутер `router` (`/api/transactions`, тег `Transactions`), все
      маршруты под `Depends(get_current_user)`: `POST` → 201, `GET` (`Annotated[TransactionListParams, Query()]`)
      → `Page[TransactionOut]`, `GET /{transaction_id}` → 200/404, `PUT /{transaction_id}` → 200/400/404,
      `DELETE /{transaction_id}` → 204/404; второй роутер `wallet_balances_router` (тег `Transactions`, без
      `prefix`) с маршрутом `GET /api/wallets/{wallet_id}/balances` → `list[WalletBalanceOut]`, 200/404
- [x] 4.3 `backend/src/depends/transaction.py` — `get_transaction_repository(session)`,
      `get_transaction_service(transactions, wallets, categories, currencies, clock, ids)` (зависит от
      `WalletRepository`, `CategoryRepository`, `CurrencyRepository` через уже существующие `depends/wallet.py`/
      `depends/category.py`/`depends/currency.py`)
- [x] 4.4 Подключить `router` (транзакции) и `wallet_balances_router` (баланс) из `api/transactions.py` в
      `backend/src/main.py` рядом с `wallets_router`/`categories_router`

## 5. API-, smoke- и инфраструктурные тесты

- [x] 5.1 `tests/api/test_transactions.py` — CRUD через `TestClient` + `app.dependency_overrides`: успешные
      create/get/list/put/delete; коды ошибок валидации (400: валюта не из набора кошелька, превышение знаков
      суммы, неположительная сумма, `date_from > date_to`); 404 на несуществующий/чужой `wallet_id`/`category_id`
      при создании и обновлении; 404 на несуществующий `transaction_id`; 401 без access-cookie
- [x] 5.2 `tests/api/test_transactions.py` — фильтры и сортировка: `wallet_id`, `category_id`, `type`,
      `date_from`/`date_to` по отдельности и в комбинации; список без фильтров отсортирован `occurred_at DESC, id
      DESC`; пагинация по умолчанию и недопустимые `limit`/`offset`
- [x] 5.3 `tests/api/test_transactions.py` — **тест изоляции пользователей**: операция пользователя A недоступна
      пользователю B через `GET`/`PUT`/`DELETE /api/transactions/{transaction_id}` (везде 404, не 403); список
      `GET /api/transactions` пользователя B не содержит операций пользователя A
- [x] 5.4 `tests/api/test_transactions.py` — баланс `GET /api/wallets/{wallet_id}/balances`: ноль по кошельку без
      операций (по всем его валютам), корректный расчёт при доходах/расходах, раздельные балансы для
      многовалютного кошелька, 404 на чужой/несуществующий `wallet_id`
- [x] 5.5 Дополнить `tests/api/test_wallets.py` — `DELETE /api/wallets/{wallet_id}` возвращает 409, если по
      кошельку есть операция (кошелёк и операция не удаляются)
- [x] 5.6 Дополнить `tests/api/test_categories.py` — `DELETE /api/categories/{category_id}` возвращает 409, если
      по категории есть операция (категория и операция не удаляются)
- [x] 5.7 Дополнить `tests/smoke/test_app_smoke.py` — шесть новых путей (`/api/transactions*`,
      `/api/wallets/{wallet_id}/balances`) зарегистрированы в OpenAPI-схеме
- [x] 5.8 `tests/infrastructure/test_transaction_repository.py` (маркер `infrastructure`, фикстура `db_session`):
      `add`/`get_by_id`/`list`/`count`/`update`/`delete` на реальной БД; `list`/`count` с каждым фильтром и их
      комбинацией; `list` отсортирован `occurred_at DESC, id DESC`; изоляция по `user_id` —
      `get_by_id`/`update`/`delete` с чужим `user_id` возвращают `None`/`False`
- [x] 5.9 `tests/infrastructure/test_transaction_repository.py` — **каскад и RESTRICT**: удаление операции удаляет
      связанную строку `transaction_legs` (проверить прямым запросом); попытка вставить операцию с несуществующим
      `wallet_id`/`category_id`/`currency_id` в ноге завершается `IntegrityError`; попытка удалить кошелёк/
      категорию/валюту, на которые ссылается операция, завершается `IntegrityError`
- [x] 5.10 `tests/infrastructure/test_transaction_repository.py` — **CheckConstraint на сумму**: попытка вставить
      строку `transaction_legs` с `amount <= 0` напрямую через `Core insert` завершается ошибкой БД
- [x] 5.11 `tests/infrastructure/test_transaction_repository.py` — **баланс**: агрегирующий запрос `balances`
      корректно суммирует доходы/расходы и разделяет валюты на реальной БД
- [x] 5.12 Дополнить `tests/infrastructure/test_wallet_repository.py` — `delete()` поднимает `ConflictError` при
      наличии связанной операции (реальная БД, `RESTRICT` от `transactions.wallet_id`)
- [x] 5.13 Дополнить `tests/infrastructure/test_category_repository.py` — `delete()` поднимает `ConflictError` при
      наличии связанной операции (реальная БД, `RESTRICT` от `transactions.category_id`)
- [x] 5.14 `tests/infrastructure/test_currency_repository.py` — тест `get_by_id`: существующий id возвращает
      `Currency`, несуществующий — `None`

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test` (backend unit + smoke)
- [x] 6.4 `make test-infra` (backend infrastructure, включая новые тесты `transaction_repository` и дополненные
      `wallet_repository`/`category_repository`/`currency_repository`)
