## 1. Сущность и протокол

- [x] 1.1 `backend/src/core/entities/category.py` — `CategoryType(str, Enum)` (`INCOME = "income"`,
      `EXPENSE = "expense"`) и `Category(Entity, TimestampMixin)`: `user_id: UUID`, `type: CategoryType`,
      `name: str`, `icon: str`; экспорт обоих в `core/entities/__init__.py`
- [x] 1.2 `backend/src/core/protocols/repositories/category_repository.py` — протокол `CategoryRepository`: `add`,
      `get_by_id(category_id, user_id)`, `list(user_id, *, type, limit, offset)`, `count(user_id, *, type)`,
      `update(category_id, user_id, *, type, name, icon, now)`, `delete(category_id, user_id)`; экспорт в
      `core/protocols/repositories/__init__.py` и `core/protocols/__init__.py`

## 2. Сервис и unit-тесты

- [x] 2.1 `backend/src/core/services/category.py` — `CategoryService(categories: CategoryRepository, clock: Clock,
      ids: IdGenerator)`: `create_category`, `get_category`, `list_categories`, `update_category`,
      `delete_category`; `NOT_FOUND_MESSAGE = "Категория не найдена"`, `NotFoundError` при отсутствии/чужой
      категории (единообразно для get/update/delete); без предварительной проверки уникальности — её обеспечивает
      репозиторий через `IntegrityError` → `AlreadyExistsError`
- [x] 2.2 `tests/fakes/category_repository.py` — `InMemoryCategoryRepository`, реализующая протокол (фильтрация по
      `user_id` и опционально `type`, сортировка `created_at, id`, эмуляция `AlreadyExistsError` при дубле
      `(user_id, type, name)` в `add`/`update`)
- [x] 2.3 `tests/unit/test_category_service.py`: создание категории обоих типов; `get_category`/
      `update_category`/`delete_category` для чужой или несуществующей категории — везде `NotFoundError`;
      `update_category` полностью заменяет `type`/`name`/`icon`; `list_categories` возвращает только категории
      заданного `user_id`, с фильтром по `type` и без него; `create_category`/`update_category` пробрасывают
      `AlreadyExistsError` от репозитория при дубле названия в пределах типа

## 3. Модель, миграция, репозиторий

- [x] 3.1 `backend/src/models/category.py` — таблица `categories` (FK `user_id → users.id ON DELETE CASCADE`,
      `type` — `String(10)` + `CheckConstraint("type IN ('income', 'expense')",
      name="ck_categories_type_valid")`, `name` — `String(100)`, `icon` — `String(50)`, составной
      `UniqueConstraint("user_id", "type", "name", name="uq_categories_user_id_type_name")`); импорт в
      `models/__init__.py`
- [x] 3.2 Миграция `backend/src/migration/versions/20260929_0005_categories.py` (`revision = "20260929_0005"`,
      `down_revision = "20260929_0004"`): создание таблицы `categories` с ограничениями из 3.1; `downgrade` —
      `drop_table("categories")` (`make be-makemigrations msg="categories"`, затем ручная сверка со схемой из
      design.md)
- [x] 3.3 `backend/src/repositories/category.py` — реализация `CategoryRepository` на SQLAlchemy Core: `add` и
      `update` оборачивают `INSERT`/`UPDATE` в `try/except IntegrityError` → `raise AlreadyExistsError("Категория
      с таким названием уже существует среди категорий этого типа") from exc` (по образцу
      `UserRepository.add()`); `get_by_id`/`update`/`delete` фильтруют по `category_id` И `user_id` в одном
      запросе; `list`/`count` добавляют `WHERE type = ...` только если `type` передан; `list` сортирует
      `created_at ASC, id ASC`

## 4. Схемы, API, зависимости

- [x] 4.1 `backend/src/api/schemas/category.py` — `CategoryCreate`/`CategoryUpdate` (`type: CategoryType`; `name`
      непустой после strip, максимум 100 символов; `icon: IconName`); `CategoryOut` (`id`, `type`, `name`, `icon`,
      `created_at`, `updated_at`, `from_attributes=True`)
- [x] 4.2 `backend/src/api/categories.py` — роутер `/api/categories`, тег `Categories`, все маршруты под
      `Depends(get_current_user)`: `POST` → 201, `GET` (`Annotated[PageParams, Query()]` + опциональный
      `type: CategoryType | None = None`) → `Page[CategoryOut]`, `GET /{category_id}` → 200/404,
      `PUT /{category_id}` → 200/404/409, `DELETE /{category_id}` → 204/404
- [x] 4.3 `backend/src/depends/category.py` — `get_category_repository(session)`,
      `get_category_service(categories, clock, ids)`
- [x] 4.4 Подключить `categories_router` в `backend/src/main.py` рядом с `wallets_router`

## 5. API-, smoke- и инфраструктурные тесты

- [x] 5.1 `tests/api/test_categories.py` — CRUD через `TestClient` + `app.dependency_overrides`
      (`get_category_repository`, `get_current_user`): успешные create/get/list/put/delete для обоих типов; коды
      ошибок валидации (400: пустое имя, неизвестная иконка, невалидный `type`); 409 на дубль названия в пределах
      того же типа при создании и при переименовании через `PUT`; успешное создание одноимённой категории другого
      типа (201); 404 на несуществующий `category_id`; 401 без access-cookie
- [x] 5.2 `tests/api/test_categories.py` — фильтр по типу: `GET /api/categories?type=income`/`?type=expense`
      возвращает только категории этого типа; без параметра — категории обоих типов
- [x] 5.3 `tests/api/test_categories.py` — **тест изоляции пользователей**: категория пользователя A недоступна
      пользователю B через `GET`/`PUT`/`DELETE /api/categories/{category_id}` (везде 404, не 403); список
      `GET /api/categories` пользователя B не содержит категорий пользователя A; одноимённые категории одного типа
      у разных пользователей не конфликтуют (у каждого пользователя своя уникальность)
- [x] 5.4 Дополнить `tests/smoke/test_app_smoke.py` — пять путей `/api/categories*` зарегистрированы в
      OpenAPI-схеме
- [x] 5.5 `tests/infrastructure/test_category_repository.py` (маркер `infrastructure`, фикстура `db_session`):
      `add`/`get_by_id`/`list`/`count`/`update`/`delete` на реальной БД; `list`/`count` с фильтром по `type` и без
      него; `list` отсортирован `created_at, id`; изоляция по `user_id` — `get_by_id`/`update`/`delete` с чужим
      `user_id` возвращают `None`/`False`
- [x] 5.6 `tests/infrastructure/test_category_repository.py` — **уникальность**: повторная вставка
      `(user_id, type, name)` через `add` поднимает `AlreadyExistsError`; переименование через `update` в занятое
      в пределах того же типа название поднимает `AlreadyExistsError`; одинаковое название допустимо для другого
      `type` того же пользователя и для того же `type` другого пользователя
- [x] 5.7 `tests/infrastructure/test_category_repository.py` — **CheckConstraint на `type`**: попытка вставить
      строку с `type`, отличным от `income`/`expense`, напрямую через `Core insert` завершается ошибкой БД
- [x] 5.8 `tests/infrastructure/test_category_repository.py` — **cascade delete**: удаление пользователя (`users`)
      удаляет его категории (проверить прямым запросом к таблице `categories`)

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test` (backend unit + smoke)
- [x] 6.4 `make test-infra` (backend infrastructure, включая новые тесты `category_repository`)
