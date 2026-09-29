## Why

Пользователь ведёт доходы и расходы через собственные категории (продукты, транспорт, зарплата и т. п.) — без
справочника категорий задача 010 (доходы и расходы) не может ссылаться на категорию операции. Задача 009 закрывает
backend-справочник категорий пользователя: у каждой категории есть владелец, тип (доход/расход), название и иконка
(из реестра 007), данные разных пользователей изолированы. Обе зависимости (005 — авторизация, 007 — iconpack) уже
реализованы и заархивированы, дорожная карта готова к этому шагу.

## What Changes

- Новая доменная сущность `Category` (`core/entities/category.py`): `id`, `user_id`, `type`, `name`, `icon`,
  `created_at`, `updated_at`. Тип — закрытый Python-перечисление `CategoryType(str, Enum)` (`INCOME = "income"`,
  `EXPENSE = "expense"`) — первый enum-тип в проекте.
- Новая таблица БД `categories` в одной миграции Alembic (`revision = "20260929_0005"`,
  `down_revision = "20260929_0004"`): `id`, `user_id` (FK → `users.id`, `ON DELETE CASCADE`), `type` (`String` +
  именованный `CheckConstraint`), `name`, `icon`, `created_at`, `updated_at`, составной
  `UniqueConstraint(user_id, type, name)` — название категории уникально в пределах пары «пользователь + тип».
- Узкий протокол `CategoryRepository` (`core/protocols/repositories/category_repository.py`) и его реализация на
  SQLAlchemy Core (`repositories/category.py`): `add`, `get_by_id`, `list` (с опциональным фильтром по `type`),
  `count`, `update` (полная замена `type`/`name`/`icon`), `delete` — каждый метод, работающий с конкретной
  категорией, фильтрует по `category_id` И `user_id` в одном SQL-запросе (изоляция владельца на уровне
  репозитория). `add`/`update` перехватывают `IntegrityError` от составного `UniqueConstraint` и поднимают
  `AlreadyExistsError` (409) — по образцу `UserRepository.add()`.
- `CategoryService` (`core/services/category.py`): сценарии создания, чтения (одной и списка с фильтром по типу),
  обновления (полная замена) и удаления категории; единообразный `NotFoundError` (404) для «не найдено» и
  «принадлежит другому пользователю» (без `PermissionDeniedError`). В отличие от `WalletService`, у сервиса нет
  зависимости от репозитория внешней сущности — у категории нет ссылки на другой агрегат, которую нужно было бы
  проверять перед записью.
- API-схемы (`api/schemas/category.py`): `CategoryCreate`/`CategoryUpdate` (одинаковая форма, `PUT` — только полная
  замена, `PATCH` вне рамок), `CategoryOut`; `type: CategoryType` (нативная Pydantic-валидация enum), `icon`
  использует переиспользуемый `IconName` (007).
- Эндпоинты (`api/categories.py`, префикс `/api/categories`, тег `Categories`, все под
  `Depends(get_current_user)`): `POST /api/categories`, `GET /api/categories` (пагинация `Page[CategoryOut]`,
  опциональный query-параметр `type` для фильтра, только категории текущего пользователя, сортировка
  `created_at ASC, id ASC`), `GET /api/categories/{category_id}`, `PUT /api/categories/{category_id}`,
  `DELETE /api/categories/{category_id}`.
- `depends/category.py` — сборка `CategoryRepository`/`CategoryService`; подключение `categories_router` в
  `main.py`.
- Unit-тесты сервиса (fake-репозитории), API-тесты (`TestClient` + `dependency_overrides`, включая тест изоляции
  между двумя пользователями), smoke-тест регистрации эндпоинтов, инфраструктурные тесты репозитория (реальная БД:
  уникальность `(user_id, type, name)`, `CheckConstraint` на `type`, cascade delete при удалении пользователя,
  изоляция по `user_id` на уровне SQL).

Затрагивается API: пять новых эндпоинтов `/api/categories*`. **БД затрагивается: требуется миграция Alembic**
(одна новая таблица `categories`). Новый enum `CategoryType` вводится в `core/entities`. Существующие
таблицы/эндпоинты не меняются.

## Capabilities

### New Capabilities
- `categories`: справочник категорий доходов и расходов пользователя (создание, чтение одной/списка с
  пагинацией и фильтром по типу, полное обновление, физическое удаление), изоляция данных по владельцу,
  уникальность названия в пределах типа категории, иконка из реестра Lucide.

### Modified Capabilities
<!-- Требования существующих спецификаций не меняются. -->

## Impact

- `backend/src`: `core/entities/category.py` (сущность `Category`, enum `CategoryType`),
  `core/protocols/repositories/category_repository.py` (протокол), `core/services/category.py` (сервис),
  `models/category.py` (таблица `categories`, импорт в `models/__init__.py`), `repositories/category.py`
  (реализация), `api/schemas/category.py` (`CategoryCreate`/`CategoryUpdate`/`CategoryOut`), `api/categories.py`
  (роутер), `depends/category.py` (сборка зависимостей), `main.py` (подключение `categories_router`);
  `migration/versions/` (новая миграция `20260929_0005`).
- Тесты backend: unit (`core/services/category.py` на fake-репозиториях, включая единообразный `NotFoundError` и
  фильтр по типу), api (`tests/api/test_categories.py` — CRUD, коды ошибок включая 409 на дубль названия, изоляция
  между пользователями), smoke (регистрация пяти новых путей), infrastructure
  (`tests/infrastructure/test_category_repository.py` — уникальность `(user_id, type, name)`, `CheckConstraint`
  на `type`, cascade delete при удалении пользователя, изоляция по `user_id`, детерминированный порядок `list`).
- Frontend не затрагивается — задача 009 закрывает только backend-справочник категорий; UI категорий вне рамок
  этой задачи (появится в последующих задачах дорожной карты).

## Non-goals

- Иерархия категорий (подкатегории) — задача 009 явно определяет плоский список.
- Доходы и расходы, привязанные к категории (задача 010) — таблицы операций ещё нет, запрет/каскад при удалении
  категории с операциями нечем реализовывать сейчас; удаление в этой задаче безусловное и физическое.
- Набор категорий по умолчанию для нового пользователя — «Объём» задачи 009 этого не перечисляет; пользователь
  создаёт свои категории сам через CRUD.
- Регистронезависимая уникальность названия — сравнение точное, как и везде в проекте сейчас.
- Частичное обновление (`PATCH`) — в этой задаче только полная замена через `PUT`.
- Ручной порядок отображения категорий (sort/reorder) — список сортируется детерминированно по `created_at`,
  затем `id`.
- Frontend-интерфейс категорий (список, форма создания/редактирования) — отдельная будущая задача.
