## Why

Решение пользователя: статус backend и «Главная» не нужны, а управление воркспейсами должно жить в «Настройках».
Кроме того, backend (024) требует обязательную основную валюту воркспейса (`currency_id`), а frontend её не знает:
форма создания воркспейса падает с 400. Задача 031 из дорожной карты.

## What Changes

- Удалить `features/health` (страница-заглушка со статусом backend, запрос `GET /health`) и пункт навигации «Главная»;
  `navItems` содержит 4 пункта: «Кошельки», «Операции», «Аналитика», «Настройки».
- Корневой маршрут `/` перенаправляет на `/wallets` («Кошельки»).
- Вернуть `WorkspacesSection` в «Настройки» (обратный перенос относительно `frontend-workspaces-home`).
- Тип `Workspace` получает `currency_id`; форма создания воркспейса (в «Настройках» и на экране
  `RequireWorkspace` без воркспейсов) требует валюту из справочника (`CurrencyPicker`); у существующего воркспейса
  валюта показывается, а редактируется, только пока в нём нет кошельков.
- Добавить в оболочку (шапка на широком экране, верхняя полоса на телефоне) индикатор текущего воркспейса со ссылкой
  на «Настройки».
- **BREAKING** (для пользователя): пропадает пункт «Главная» и страница статуса backend.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

- `frontend-app-shell`: убрать требование «Страница-заглушка и проверка backend», добавить «Корневой маршрут и
  навигация» (`/` → `/wallets`, 4 пункта, без статуса backend).
- `frontend-workspaces`: управление воркспейсами переезжает в «Настройки» и получает валюту; добавляются требования
  «Валюта воркспейса в формах» и «Индикатор текущего воркспейса».
- `frontend-wallets`: позиция пункта «Кошельки» в навигации (первый, перед «Операции»).

## Impact

- Код: `frontend/src/app` (`routes.tsx`, `navItems.ts`, `layout/*`, тесты), `features/health` (удаляется),
  `features/settings/SettingsPage.tsx`, `features/workspaces/*` (`Workspace`, `WorkspaceForm`, `WorkspacesSection`,
  новые `WorkspaceBadge`, `useCurrentWorkspace`, `useWorkspaceHasWallets`), `test/session.ts`.
- API: используются существующие `POST/PUT /api/workspaces` с `currency_id`, `GET /api/currencies`,
  `GET /api/workspaces/{id}/wallets`. Backend не меняется.
- Документация: `AGENTS.md` (структура frontend: убрать `health`).
