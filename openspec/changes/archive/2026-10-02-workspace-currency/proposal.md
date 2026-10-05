## Why

Валютная модель (задачи 024–035) строится вокруг опорной валюты воркспейса: в ней считаются пополнения, курсы и
аналитика. Сейчас у воркспейса валюты нет, поэтому первым шагом он получает обязательную основную валюту.

## What Changes

- `workspaces.currency_id` — обязательное поле, внешний ключ на `currencies` (`ON DELETE RESTRICT`).
- `POST /api/workspaces` принимает обязательный `currency_id`; неизвестная валюта отклоняется (400).
- `WorkspaceOut` отдаёт `currency_id`.
- `PUT /api/workspaces/{workspace_id}` кроме `name` принимает необязательный `currency_id`; смена валюты воркспейса,
  в котором есть кошельки, отклоняется (409). Переименование свободно.
- **BREAKING**: `currency_id` обязателен при создании воркспейса (клиент без него получает 400).
- Миграция Alembic очищает `wallets`, `transactions`, `transfers` (и зависимые таблицы), существующим воркспейсам
  выставляет валюту по умолчанию RUB.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

- `workspaces`: воркспейс получает основную валюту (создание, чтение, обновление, запрет смены при наличии кошельков).

## Impact

- БД: таблица `workspaces` (+ `currency_id`), миграция `20261002_0010`; данные кошельков и операций сбрасываются.
- Backend: сущность `Workspace`, протокол `WorkspaceRepository`, новый узкий протокол `WalletCounter`,
  `WorkspaceService`, `WorkspaceRepository` (SQL), модель, схемы и роутер воркспейсов, `depends/workspace.py`.
- API: `POST`/`PUT`/`GET /api/workspaces*` (контракт расширяется полем `currency_id`).
- Тесты: unit (сервис), api, smoke, infrastructure (миграция, RESTRICT).

## Вне рамок

- Frontend (задача 031).
- Пересчёт и перенос старых данных кошельков и операций (они сбрасываются).
- Валюта кошелька и пополнения (задачи 025–026).
