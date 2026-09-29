## 1. Сущность и протоколы

- [x] 1.1 `backend/src/core/entities/wallet.py` — `Wallet(Entity, TimestampMixin)`: `user_id: UUID`, `name: str`,
      `icon: str`, `currency_ids: tuple[UUID, ...]`; экспорт в `core/entities/__init__.py`
- [x] 1.2 `backend/src/core/protocols/repositories/wallet_repository.py` — протокол `WalletRepository`: `add`,
      `get_by_id(wallet_id, user_id)`, `list(user_id, *, limit, offset)`, `count(user_id)`,
      `update(wallet_id, user_id, *, name, icon, currency_ids, now)`, `delete(wallet_id, user_id)`; экспорт в
      `core/protocols/repositories/__init__.py` и `core/protocols/__init__.py`
- [x] 1.3 Добавить в `core/protocols/repositories/currency_repository.py` метод `missing_ids(currency_ids: Sequence[UUID]) -> set[UUID]`
      (возвращает подмножество, отсутствующее в справочнике)

## 2. Сервис и unit-тесты

- [x] 2.1 `backend/src/core/services/wallet.py` — `WalletService(wallets: WalletRepository, currencies: CurrencyRepository)`:
      `create_wallet`, `get_wallet`, `list_wallets`, `update_wallet`, `delete_wallet`; проверка `missing_ids` перед
      `add`/`update` → `ClientError` с перечислением неизвестных id; `NotFoundError` при отсутствии/чужом кошельке
      (единообразно для get/update/delete)
- [x] 2.2 `tests/fakes/wallet_repository.py` — `InMemoryWalletRepository`, реализующая протокол (фильтрация по
      `user_id`, сортировка `created_at, id`)
- [x] 2.3 Дополнить `tests/fakes/currency_repository.py` (`InMemoryCurrencyRepository`) методом `missing_ids`
- [x] 2.4 `tests/unit/test_wallet_service.py`: создание с одной/несколькими валютами; отклонение неизвестной
      валюты (`ClientError`, сообщение содержит id); `get_wallet`/`update_wallet`/`delete_wallet` для чужого или
      несуществующего кошелька — везде `NotFoundError`; `update_wallet` полностью заменяет набор валют; `list_wallets`
      возвращает только кошельки заданного `user_id`

## 3. Модели, миграция, репозиторий

- [x] 3.1 `backend/src/models/wallet.py` — таблицы `wallets` (FK `user_id → users.id ON DELETE CASCADE`) и
      `wallet_currencies` (составной PK `(wallet_id, currency_id)`, FK `wallet_id → wallets.id ON DELETE CASCADE`,
      FK `currency_id → currencies.id ON DELETE RESTRICT`); импорт в `models/__init__.py`
- [x] 3.2 Миграция `backend/src/migration/versions/20260929_0004_wallets.py` (`revision = "20260929_0004"`,
      `down_revision = "20260929_0003"`): создание `wallets`, затем `wallet_currencies`; `downgrade` — обратный
      порядок (`make be-makemigrations msg="wallets"`, затем ручная сверка со схемой из design.md)
- [x] 3.3 `backend/src/repositories/currency.py` — реализация `missing_ids` (один `SELECT ... WHERE currency_id = ANY(...)`,
      разность множеств)
- [x] 3.4 `backend/src/repositories/wallet.py` — реализация `WalletRepository` на SQLAlchemy Core: `get_by_id`/`list`
      читают `currency_ids` через `JOIN wallet_currencies/currencies ORDER BY currencies.code`; `list` сортирует
      `created_at ASC, id ASC`; `update` — `UPDATE wallets ... RETURNING` (None при 0 строк), затем `DELETE
      FROM wallet_currencies WHERE wallet_id = ...` и `INSERT` нового набора, без коммита (коммитит `get_session`)

## 4. Схемы, API, зависимости

- [x] 4.1 `backend/src/api/schemas/wallet.py` — `WalletCreate`/`WalletUpdate` (`name` непустой после strip,
      максимум 100 символов; `icon: IconName`; `currency_ids: list[UUID]` непустой без дублей, валидатор Pydantic
      до похода в БД); `WalletOut` (`id`, `name`, `icon`, `currency_ids: list[UUID]`, `created_at`, `updated_at`,
      `from_attributes=True`)
- [x] 4.2 `backend/src/api/wallets.py` — роутер `/api/wallets`, тег `Wallets`, все маршруты под
      `Depends(get_current_user)`: `POST` → 201, `GET` (`Annotated[PageParams, Query()]`) → `Page[WalletOut]`,
      `GET /{wallet_id}` → 200/404, `PUT /{wallet_id}` → 200/404, `DELETE /{wallet_id}` → 204/404
- [x] 4.3 `backend/src/depends/wallet.py` — `get_wallet_repository(session)`, `get_wallet_service(wallets, currencies)`
      (зависит от `WalletRepository` и `CurrencyRepository`) — **отклонение**: `WalletService` также получает
      `Clock`/`IdGenerator` (нужны для `id`/`created_at`/`updated_at`), см. отчёт
- [x] 4.4 Подключить `wallets_router` в `backend/src/main.py` рядом с `currencies_router`/`icons_router`

## 5. API-, smoke- и инфраструктурные тесты

- [x] 5.1 `tests/api/test_wallets.py` — CRUD через `TestClient` + `app.dependency_overrides` (`get_wallet_repository`,
      `get_currency_repository`, `get_current_user`): успешные create/get/list/put/delete; коды ошибок валидации
      (400: пустое имя, неизвестная иконка, пустой/с дублями `currency_ids`, неизвестная валюта); 404 на
      несуществующий `wallet_id`; 401 без access-cookie
- [x] 5.2 `tests/api/test_wallets.py` (или отдельный тест в том же файле) — **тест изоляции пользователей**: кошелёк
      пользователя A недоступен пользователю B через `GET`/`PUT`/`DELETE /api/wallets/{wallet_id}` (везде 404, не
      403); список `GET /api/wallets` пользователя B не содержит кошельков пользователя A
- [x] 5.3 Дополнить `tests/smoke/test_app_smoke.py` — пять путей `/api/wallets*` зарегистрированы в OpenAPI-схеме
- [x] 5.4 `tests/infrastructure/test_wallet_repository.py` (маркер `infrastructure`, фикстура `db_session`):
      `add`/`get_by_id`/`list`/`count`/`update`/`delete` на реальной БД; `list` сортирован `created_at, id`;
      `currency_ids` в ответе отсортированы по коду валюты; **изоляция по `user_id`** — `get_by_id`/`update`/`delete`
      с чужим `user_id` возвращают `None`/`False`
- [x] 5.5 `tests/infrastructure/test_wallet_repository.py` — **cascade delete**: удаление строки `wallets` удаляет
      связанные строки `wallet_currencies` (проверить прямым запросом к таблице)
- [x] 5.6 `tests/infrastructure/test_wallet_repository.py` — **RESTRICT на неизвестную/удаляемую валюту**: попытка
      вставить `wallet_currencies` с несуществующим `currency_id` завершается ошибкой БД (внешний ключ), не тихим
      успехом
- [x] 5.7 `tests/infrastructure/test_currency_repository.py` — unit/infra-тест `missing_ids`: известные id дают
      пустое множество, смесь известных и неизвестных — только неизвестные

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test` (backend unit + smoke)
- [x] 6.4 `make test-infra` (backend infrastructure, включая новые тесты `wallet_repository`)
