## 1. Домен и протоколы

- [x] 1.1 Добавить `currency_id: UUID` в сущность `Workspace`
- [x] 1.2 Добавить узкий протокол `WalletCounter` (`core/protocols/repositories/wallet_counter.py`) и экспортировать его
- [x] 1.3 Обновить протокол `WorkspaceRepository.update` (параметр `currency_id`)

## 2. Сервис

- [x] 2.1 `WorkspaceService`: зависимости `CurrencyRepository` и `WalletCounter`; проверка валюты при создании
- [x] 2.2 `WorkspaceService.update_workspace`: необязательный `currency_id`, запрет смены при наличии кошельков (`ConflictError`), проверка существования валюты

## 3. БД и репозиторий

- [x] 3.1 Модель `workspaces`: столбец `currency_id` (FK `ON DELETE RESTRICT`)
- [x] 3.2 Миграция Alembic `20261002_0010`: очистка данных, RUB по умолчанию, NOT NULL, FK, downgrade
- [x] 3.3 `repositories/workspace.py`: `currency_id` в маппинге, `add` и `update`

## 4. API и сборка зависимостей

- [x] 4.1 Схемы: `currency_id` в `WorkspaceCreate`/`WorkspaceOut`, отдельный `WorkspaceUpdate` с необязательным `currency_id`
- [x] 4.2 Роутер `api/workspaces.py` и `depends/workspace.py` (сборка сервиса)

## 5. Тесты

- [x] 5.1 Fakes: `InMemoryWorkspaceRepository` (`currency_id`), `InMemoryWalletRepository` как `WalletCounter`; обновить существующие тесты, создающие `Workspace`
- [x] 5.2 Unit-тесты `WorkspaceService` (создание, неизвестная валюта, смена с кошельками и без, переименование)
- [x] 5.3 API-тесты воркспейсов (обязательность `currency_id`, ответ, 409, 400)
- [x] 5.4 Smoke-тест: схема OpenAPI содержит `currency_id` у воркспейса
- [x] 5.5 Infrastructure-тесты: репозиторий с `currency_id`, RESTRICT, миграция (RUB по умолчанию, очистка данных)

## 6. QualityGate

- [x] 6.1 `make format`
- [x] 6.2 `make lint`
- [x] 6.3 `make test`
- [x] 6.4 `make test-infra`
