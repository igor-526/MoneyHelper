## Why

Пользователь ведёт доходы и расходы по своим кошелькам — до сих пор в приложении есть только справочники кошельков
(008) и категорий (009), но нет самих операций и балансов. Задача 010 закрывает backend для доходов и расходов:
создание, чтение, полную замену и удаление операции, список с фильтрами и пагинацией, баланс по кошельку и валюте.
Обе зависимости (008 — кошельки, 009 — категории) уже реализованы и заархивированы, дорожная карта готова к этому
шагу.

## What Changes

- Новая доменная сущность `Transaction` (`core/entities/transaction.py`): `id`, `user_id`, `wallet_id`,
  `category_id`, `currency_id`, `amount: Decimal`, `occurred_at: datetime`, `created_at`, `updated_at`. Модель
  плоская — без list-обёртки «ног» на уровне домена/API (обоснование в design.md).
- Две новые таблицы БД в одной миграции Alembic (`revision = "20260929_0006"`, `down_revision = "20260929_0005"`):
  - `transactions` — `id`, `user_id` (FK → `users.id`, `ON DELETE CASCADE`), `wallet_id` (FK → `wallets.id`,
    `ON DELETE RESTRICT`), `category_id` (FK → `categories.id`, `ON DELETE RESTRICT`), `occurred_at`, `created_at`,
    `updated_at`;
  - `transaction_legs` — составной `PrimaryKeyConstraint(transaction_id, currency_id)`, `transaction_id` (FK →
    `transactions.id`, `ON DELETE CASCADE`), `currency_id` (FK → `currencies.id`, `ON DELETE RESTRICT`), `amount`
    (колонка `MONEY`, `CheckConstraint("amount > 0")`). Для задачи 010 у операции ровно одна нога — это правило
    сервиса, не ограничение БД (задел под многовалютные пополнения задачи 011).
- Тип операции (доход/расход) не хранится на `transactions` отдельным полем — определяется через JOIN с
  `categories.type`; единственный источник истины.
- Узкий протокол `TransactionRepository` (`core/protocols/repositories/transaction_repository.py`) и его
  реализация на SQLAlchemy Core (`repositories/transaction.py`): `add`, `get_by_id`, `list` (фильтры `wallet_id`,
  `category_id`, `type`, `date_from`, `date_to`; сортировка `occurred_at DESC, id DESC`), `count`, `update` (полная
  замена), `delete`, `balances` (агрегированный баланс по кошельку и валюте) — каждый метод, работающий с
  конкретной операцией, фильтрует по `transaction_id` И `user_id` в одном SQL-запросе.
- Новый метод в `CurrencyRepository`/протоколе (`core/protocols/repositories/currency_repository.py`,
  `repositories/currency.py`): `get_by_id(currency_id) -> Currency | None` — нужен `TransactionService`, чтобы
  проверить число знаков после запятой в `amount` по `decimal_places` валюты.
- `TransactionService` (`core/services/transaction.py`): сценарии создания, чтения (одной и списка с фильтрами и
  пагинацией), обновления (полная замена), удаления операции и расчёта баланса по кошельку; валидация — кошелёк и
  категория существуют и принадлежат пользователю, валюта операции входит в набор валют кошелька, сумма
  положительна и не превышает число знаков валюты, диапазон дат (`date_from <= date_to`).
- Баланс по кошельку и валюте вычисляется на лету агрегирующим SQL-запросом, без кэширования: `GET
  /api/wallets/{wallet_id}/balances` (тег `Transactions`) возвращает список `{currency_id, balance}` по всем
  валютам кошелька (включая нулевой баланс), отсортированный по коду валюты.
- API-схемы (`api/schemas/transaction.py`): `TransactionCreate`/`TransactionUpdate` (одинаковая форма, `occurred_at`
  опционален при создании — по умолчанию `Clock.now()`), `TransactionOut`, `WalletBalanceOut`.
- Эндпоинты (`api/transactions.py`, тег `Transactions`, все под `Depends(get_current_user)`):
  `POST /api/transactions`, `GET /api/transactions` (пагинация, фильтры, сортировка `occurred_at DESC, id DESC`),
  `GET /api/transactions/{transaction_id}`, `PUT /api/transactions/{transaction_id}`,
  `DELETE /api/transactions/{transaction_id}`, `GET /api/wallets/{wallet_id}/balances`.
- `depends/transaction.py` — сборка `TransactionRepository`/`TransactionService` (зависит от `WalletRepository`,
  `CategoryRepository`, `CurrencyRepository`); подключение роутеров в `main.py`.
- Новое исключение `ConflictError(ClientError)` (`status_code = 409`, `core/exceptions/base.py`) — отдельно от
  `AlreadyExistsError` (та означает конфликт уникальности при создании, эта — «нельзя удалить/изменить, ресурс
  используется»).
- **Модификация существующего поведения**: `WalletRepository.delete()` и `CategoryRepository.delete()` теперь
  перехватывают `IntegrityError` от `ON DELETE RESTRICT` (появившегося с `transactions`) и поднимают
  `ConflictError` (409) вместо необработанного 500. Требование «Удаление» в спецификациях `wallets` и `categories`
  меняется соответственно.
- Unit-тесты сервиса (fake-репозитории), API-тесты (включая изоляцию между пользователями, RESTRICT-сценарии через
  409 на удаление кошелька/категории с операциями), smoke-тест регистрации эндпоинтов, инфраструктурные тесты
  репозитория (реальная БД: каскад удаления ноги, `RESTRICT` на удаление кошелька/категории/валюты с операциями,
  корректность расчёта баланса, изоляция по `user_id`).

Затрагивается API: шесть новых эндпоинтов (`/api/transactions*`, `/api/wallets/{wallet_id}/balances`) и изменение
кода ответа `DELETE /api/wallets/{id}`/`DELETE /api/categories/{id}` (200/204 → 409 при наличии операций). **БД
затрагивается: требуется миграция Alembic** (две новые таблицы `transactions`, `transaction_legs`).

## Capabilities

### New Capabilities
- `transactions`: доходы и расходы пользователя по кошелькам (создание, чтение одной/списка с фильтрами,
  пагинацией и сортировкой по дате операции, полное обновление, физическое удаление), баланс по кошельку и валюте
  на лету, изоляция данных по владельцу.

### Modified Capabilities
- `wallets`: требование «Удаление кошелька» — было безусловное удаление, теперь 409, если по кошельку есть
  операции.
- `categories`: требование «Удаление категории» — было безусловное удаление, теперь 409, если по категории есть
  операции.

## Impact

- `backend/src`: `core/entities/transaction.py` (сущность), `core/protocols/repositories/transaction_repository.py`
  (протокол), `core/services/transaction.py` (сервис), `core/exceptions/base.py` (`ConflictError`),
  `models/transaction.py` (таблицы `transactions`, `transaction_legs`, импорт в `models/__init__.py`),
  `repositories/transaction.py` (реализация), `api/schemas/transaction.py`
  (`TransactionCreate`/`TransactionUpdate`/`TransactionOut`/`WalletBalanceOut`), `api/transactions.py` (роутеры),
  `depends/transaction.py` (сборка зависимостей), `main.py` (подключение роутеров); точечные изменения
  `core/protocols/repositories/currency_repository.py`/`repositories/currency.py` (новый метод `get_by_id`),
  `repositories/wallet.py`/`repositories/category.py` (`delete()` → перехват `IntegrityError` → `ConflictError`) и
  `migration/versions/` (новая миграция `20260929_0006`).
- Тесты backend: unit (`core/services/transaction.py` на fake-репозиториях), api (`tests/api/test_transactions.py`
  — CRUD, коды ошибок, изоляция; дополнение `tests/api/test_wallets.py`/`test_categories.py` сценарием 409 при
  удалении с операциями), smoke (регистрация шести новых путей), infrastructure
  (`tests/infrastructure/test_transaction_repository.py` — каскад/RESTRICT, баланс, изоляция; дополнение
  `tests/infrastructure/test_wallet_repository.py`/`test_category_repository.py` сценарием `ConflictError`).
- Frontend не затрагивается — задача 010 закрывает только backend; UI операций — отдельная будущая задача.

## Non-goals

- Многовалютные пополнения (несколько ног на одну операцию) и переводы между кошельками — задача 011; таблица
  `transaction_legs` технически допускает несколько строк на операцию, но для 010 это не используется.
- Аналитика доходов/расходов в разрезах — задача 012.
- Кэширование баланса — баланс всегда вычисляется на лету агрегирующим запросом.
- Частичное обновление (`PATCH`) — только полная замена через `PUT`.
- Округление суммы до знаков валюты — запрещено: превышение числа знаков — ошибка 400, а не тихое округление.
- Ручной порядок отображения операций — список сортируется по `occurred_at DESC, id DESC`.
- Frontend-интерфейс операций и балансов — отдельная будущая задача.
