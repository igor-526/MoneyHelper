## Why

Пользователь ведёт свои финансы через набор кошельков (UPay USDT, Alipay CNY, WeChatPay CNY, NihaoChina CNY,
наличные RUB и т. п.) — это базовая сущность, без которой невозможны ни доходы/расходы (010), ни аналитика.
Задача 008 закрывает справочник кошельков пользователя: у каждого кошелька есть владелец, название, иконка (из
реестра 007) и одна или несколько валют (из справочника 006), данные разных пользователей изолированы. Без этой
задачи дорожная карта не может двигаться дальше — категории (009) и операции (010) ссылаются на кошелёк.

## What Changes

- Новая доменная сущность `Wallet` (`core/entities/wallet.py`): `id`, `user_id`, `name`, `icon`,
  `currency_ids: tuple[UUID, ...]`, `created_at`, `updated_at`. Валюты — часть сущности кошелька, а не отдельный
  агрегат (вне кошелька они не имеют самостоятельного смысла в этом домене).
- Две новые таблицы БД в одной миграции Alembic (`revision = "20260929_0004"`, `down_revision = "20260929_0003"`):
  - `wallets` — `id`, `user_id` (FK → `users.id`, `ON DELETE CASCADE`), `name`, `icon`, `created_at`, `updated_at`;
  - `wallet_currencies` — чистая junction-таблица `(wallet_id FK → wallets.id ON DELETE CASCADE, currency_id FK →
    currencies.id ON DELETE RESTRICT)` с составным `PRIMARY KEY (wallet_id, currency_id)`.
- Узкий протокол `WalletRepository` (`core/protocols/repositories/wallet_repository.py`) и его реализация на
  SQLAlchemy Core (`repositories/wallet.py`): `add`, `get_by_id`, `list`, `count`, `update` (полная замена
  name/icon/набора валют), `delete` — каждый метод, работающий с конкретным кошельком, фильтрует по `wallet_id` И
  `user_id` в одном SQL-запросе (изоляция владельца на уровне репозитория).
- Новый метод в `CurrencyRepository`/протоколе (`core/protocols/repositories/currency_repository.py`,
  `repositories/currency.py`): проверка существования переданного набора `currency_id` в справочнике валют —
  используется `WalletService` перед созданием/обновлением кошелька, чтобы вернуть `ClientError` (400) вместо
  ошибки FK/500 при неизвестной валюте.
- `WalletService` (`core/services/wallet.py`): сценарии создания, чтения (одного и списка), обновления (полная
  замена), удаления кошелька; проверка существования валют перед записью; единообразный `NotFoundError` (404) для
  «не найдено» и «принадлежит другому пользователю» (без `PermissionDeniedError`, чтобы не подтверждать чужим
  пользователям существование чужого `wallet_id`).
- API-схемы (`api/schemas/wallet.py`): `WalletCreate`/`WalletUpdate` (одинаковая форма, `PUT` — только полная
  замена, `PATCH` вне рамок), `WalletOut`; `icon` использует переиспользуемый `IconName` (первое реальное
  подключение типа из задачи 007), `currency_ids` — непустой список без дублей (валидация до похода в БД).
- Эндпоинты (`api/wallets.py`, префикс `/api/wallets`, тег `Wallets`, все под `Depends(get_current_user)`):
  `POST /api/wallets`, `GET /api/wallets` (пагинация `Page[WalletOut]`, только кошельки текущего пользователя,
  сортировка `created_at ASC, id ASC`), `GET /api/wallets/{wallet_id}`, `PUT /api/wallets/{wallet_id}`,
  `DELETE /api/wallets/{wallet_id}`.
- `depends/wallet.py` — сборка `WalletRepository`/`WalletService` (сервис зависит от протоколов `WalletRepository`
  И `CurrencyRepository`); подключение `wallets_router` в `main.py`.
- Unit-тесты сервиса (fake-репозитории), API-тесты (`TestClient` + `dependency_overrides`, включая тест изоляции
  между двумя пользователями), smoke-тест регистрации эндпоинтов, инфраструктурные тесты репозитория (реальная БД:
  cascade delete `wallet_currencies` при удалении `wallets`, `RESTRICT`/ошибка при удалении валюты с активной
  привязкой, изоляция по `user_id` на уровне SQL).

Затрагивается API: пять новых эндпоинтов `/api/wallets*`. **БД затрагивается: требуется миграция Alembic** (две
новые таблицы `wallets`, `wallet_currencies`). Существующие таблицы/эндпоинты не меняются.

## Capabilities

### New Capabilities
- `wallets`: реестр кошельков пользователя (создание, чтение одного/списка с пагинацией, полное обновление,
  физическое удаление), изоляция данных по владельцу, привязка кошелька к одной или нескольким валютам из
  глобального справочника с проверкой их существования, иконка кошелька из реестра Lucide.

### Modified Capabilities
<!-- Требования существующих спецификаций не меняются. -->

## Impact

- `backend/src`: `core/entities/wallet.py` (сущность), `core/protocols/repositories/wallet_repository.py`
  (протокол), `core/services/wallet.py` (сервис), `models/wallet.py` (таблицы `wallets`, `wallet_currencies`,
  импорт в `models/__init__.py`), `repositories/wallet.py` (реализация), `api/schemas/wallet.py`
  (`WalletCreate`/`WalletUpdate`/`WalletOut`), `api/wallets.py` (роутер), `depends/wallet.py` (сборка
  зависимостей), `main.py` (подключение `wallets_router`); точечное изменение существующего
  `core/protocols/repositories/currency_repository.py` и `repositories/currency.py` (новый метод проверки
  существования валют) и `migration/versions/` (новая миграция `20260929_0004`).
- Тесты backend: unit (`core/services/wallet.py` на fake-репозиториях, включая проверку неизвестной валюты и
  единообразный `NotFoundError`), api (`tests/api/test_wallets.py` — CRUD, коды ошибок, изоляция между
  пользователями), smoke (регистрация пяти новых путей), infrastructure (`tests/infrastructure/
  test_wallet_repository.py` — cascade delete `wallet_currencies`, `RESTRICT` при попытке удалить валюту с
  привязкой, изоляция по `user_id`, детерминированный порядок `list`/`currency_ids`).
- Frontend не затрагивается — задача 008 закрывает только backend-справочник кошельков; UI кошельков вне рамок
  этой задачи (появится в последующих задачах дорожной карты).

## Non-goals

- Доходы, расходы и балансы кошелька (задача 010) — таблицы операций ещё нет, физически ограничивать удаление
  кошелька или смену набора валют нечем.
- Запрет/каскад при удалении кошелька, по которому есть операции, — станет актуальным только вместе с 010; сейчас
  удаление кошелька безусловно физическое.
- Ограничения на смену набора валют кошелька с историей операций — вне рамок по той же причине; `PUT` делает
  полную замену набора валют без ограничений.
- Ручной порядок отображения кошельков (sort/reorder) — не входит в «Объём» задачи 008; список сортируется
  детерминированно по `created_at`, затем `id`.
- Частичное обновление (`PATCH`) — в этой задаче только полная замена через `PUT`.
- Frontend-интерфейс кошельков (список, форма создания/редактирования) — отдельная будущая задача.
