## 1. Сущность `workspaces` — ядро

- [x] 1.1 `core/entities/workspace.py` — `Workspace(Entity, TimestampMixin)`: `user_id: UUID`, `name: str`.
- [x] 1.2 `core/protocols/repositories/workspace_repository.py` — протокол `WorkspaceRepository` (`add`,
      `get_by_id(workspace_id, user_id)`, `list(user_id, *, limit, offset)`, `count(user_id)`,
      `update(workspace_id, user_id, *, name, now)`, `delete(workspace_id, user_id)`), по образцу
      `wallet_repository.py`.
- [x] 1.3 `core/services/workspace.py` — `WorkspaceService`: валидация непустого `name` (после `strip()`), делегирование
      в репозиторий; `delete_workspace` — без проверки на непустоту (каскад на уровне БД).
- [x] 1.4 Unit-тесты `WorkspaceService` на fake-репозитории (`tests/fakes/`): создание, пустое название, список,
      обновление, удаление (в т. ч. непустого воркспейса — сервис не проверяет и не блокирует).

## 2. Модель БД и репозиторий `workspaces`

- [x] 2.1 `models/workspace.py` — таблица `workspaces` (`id`, `user_id` FK `users.id` `ondelete="CASCADE"`, `name`
      `String(100)`, `created_at`, `updated_at`); регистрация в `models/__init__.py`.
- [x] 2.2 `repositories/workspace.py` — реализация `WorkspaceRepository` на SQLAlchemy Core; фильтр
      `workspace_id AND user_id` в одном запросе (чужой воркспейс — `None`, не отдельная проверка).

## 3. API `/api/workspaces*` и зависимость `require_workspace`

- [x] 3.1 `core/schemas/workspace.py` — `WorkspaceCreate`, `WorkspaceUpdate`, `WorkspaceOut`.
- [x] 3.2 `depends/workspace.py` — `get_workspace_repository`, `get_workspace_service`, и новая зависимость
      `require_workspace(workspace_id, user_id=Depends(get_current_user), workspaces=Depends(get_workspace_repository))
      -> UUID`, поднимающая `NotFoundError`, если воркспейс не принадлежит текущему пользователю.
- [x] 3.3 `api/workspaces.py` — роутер `POST/GET/GET{id}/PUT{id}/DELETE{id} /api/workspaces*` под `get_current_user`,
      по образцу `api/wallets.py`.
- [x] 3.4 Unit-тесты схем/валидации при необходимости; smoke-тест эндпоинтов `/api/workspaces*` (создание, список,
      чтение, обновление, удаление, включая 404 на чужой/несуществующий воркспейс).

## 4. Миграция Alembic

- [x] 4.1 `make be-makemigrations msg="workspaces"` — сгенерировать заготовку для новой таблицы `workspaces`.
- [x] 4.2 Вручную дописать в миграцию (autogenerate этого не создаст): `TRUNCATE wallets, categories, transactions,
      transfers CASCADE` перед добавлением новых колонок (каскадно очищает `transaction_legs`, `wallet_currencies`).
- [x] 4.3 В той же миграции: добавить `workspace_id` (`NOT NULL`, FK `workspaces.id` `ondelete="CASCADE"`) на
      `wallets`, `categories`, `transactions`, `transfers`; удалить колонку `user_id` (и её FK/индексы) с этих же
      таблиц.
- [x] 4.4 Пересоздать `UniqueConstraint` категорий: `(user_id, type, name)` → `(workspace_id, type, name)`.
- [x] 4.5 `make be-migrate` локально, проверить `alembic downgrade -1` и повторный `upgrade head` (обратимость
      миграции).

## 5. Перенос `wallets` на `workspace_id`

- [x] 5.1 `core/entities/wallet.py`, `core/protocols/repositories/wallet_repository.py`,
      `core/services/wallet.py`: переименовать параметр/поле `user_id` → `workspace_id` (без изменения формы
      методов).
- [x] 5.2 `models/wallet.py`, `repositories/wallet.py`: колонка и фильтр `workspace_id` вместо `user_id`.
- [x] 5.3 `api/wallets.py`: префикс роутера `/api/workspaces/{workspace_id}/wallets`; `workspace_id` через
      `Depends(require_workspace)` вместо `user_id` через `Depends(get_current_user)`.
- [x] 5.4 `depends/wallet.py`: без изменений в сборке (сигнатуры сервиса/репозитория не меняют форму).
- [x] 5.5 Обновить unit- и smoke-тесты `wallets` под новую модель (создание воркспейса в фикстурах вместо/наряду с
      пользователем, новые пути).

## 6. Перенос `categories` на `workspace_id`

- [x] 6.1 `core/entities/category.py`, протокол, `core/services/category.py`: `user_id` → `workspace_id`.
- [x] 6.2 `models/category.py` (включая `UniqueConstraint`), `repositories/category.py`.
- [x] 6.3 `api/categories.py`: префикс `/api/workspaces/{workspace_id}/categories`, `Depends(require_workspace)`.
- [x] 6.4 Обновить unit- и smoke-тесты `categories`.

## 7. Перенос `transactions` (включая пополнения) на `workspace_id`

- [x] 7.1 `core/entities/transaction.py`, протокол, `core/services/transaction.py`: `user_id` → `workspace_id`,
      включая сценарий пополнений (`create_topup`/аналог).
- [x] 7.2 `models/transaction.py`, `repositories/transaction.py` (включая батч-агрегацию ног).
- [x] 7.3 `api/transactions.py`: префикс `/api/workspaces/{workspace_id}/transactions` и
      `/api/workspaces/{workspace_id}/transactions/topups`, `Depends(require_workspace)`.
- [x] 7.4 Обновить unit- и smoke-тесты `transactions` и пополнений.

## 8. Перенос `transfers` на `workspace_id`

- [x] 8.1 `core/entities/transfer.py`, протокол, `core/services/transfer.py`: `user_id` → `workspace_id`.
- [x] 8.2 `models/transfer.py`, `repositories/transfer.py`.
- [x] 8.3 `api/transfers.py`: префикс `/api/workspaces/{workspace_id}/transfers`, `Depends(require_workspace)`.
- [x] 8.4 Обновить unit- и smoke-тесты `transfers`.

## 9. Перенос балансов на `workspace_id`

- [x] 9.1 `core/services/balance.py` (`BalanceService`, `BalanceContributor`): `user_id` → `workspace_id`.
- [x] 9.2 `api/balances.py`: путь `/api/workspaces/{workspace_id}/wallets/{wallet_id}/balances`,
      `Depends(require_workspace)`.
- [x] 9.3 Обновить unit- и smoke-тесты балансов (включая вклад переводов).

## 10. Перенос `analytics` на `workspace_id`

- [x] 10.1 `core/services/analytics.py`, `core/services/analytics_dimensions.py`: `user_id` → `workspace_id`,
      усреднение курса — только по пополнениям того же воркспейса.
- [x] 10.2 `api/analytics.py`: путь `/api/workspaces/{workspace_id}/analytics`, `Depends(require_workspace)`.
- [x] 10.3 Обновить unit- и smoke-тесты аналитики (три оси группировки, `unconverted_currencies`).

## 11. Инфраструктурные тесты изоляции

- [x] 11.1 `tests/infrastructure/` — новые сценарии изоляции между воркспейсами одного пользователя (кошельки,
      категории, операции, переводы, балансы, аналитика) — по образцу уже существующих сценариев изоляции между
      пользователями.
- [x] 11.2 `tests/infrastructure/` — каскадное удаление воркспейса чистит все вложенные таблицы (реальная БД,
      проверка `ON DELETE CASCADE`).
- [x] 11.3 `make test-infra` проходит целиком.

## 12. QualityGate и синхронизация спек

- [x] 12.1 `make format`, затем `make lint`, затем `make test` — все проходят подряд.
- [x] 12.2 `docs/tasks/020_workspaces.md` — заполнить раздел «Статус» по итогам реализации.
