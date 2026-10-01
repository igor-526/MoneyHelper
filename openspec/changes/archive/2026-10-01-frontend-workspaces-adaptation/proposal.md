## Why

Backend уже сломал frontend (020): все пути кошельков/категорий/операций/переводов/аналитики/балансов переехали
под `/api/workspaces/{workspace_id}/...`. Frontend сейчас не работает против текущего backend. Заодно на backend
появились средний курс кошелька (021) и комментарии операций (022), которые ещё нигде не видны в UI.

## What Changes

- **BREAKING (для самого frontend, не для API)**: все существующие data-хуки кошельков, категорий, операций
  (включая пополнения), переводов, аналитики и баланса кошелька перестраивают путь запроса и ключ TanStack Query
  под текущий воркспейс — без этого frontend не работает вообще.
- Новая фича `workspaces`: React Context с текущим `workspace_id` (не TanStack Query — обоснование в design.md),
  сохранение выбора в `localStorage`, экран/состояние выбора и создания воркспейса, управление воркспейсами
  (список, создание, переименование, удаление, переключение) в разделе «Настройки».
- Новый компонент `WalletRateCard` — курс многовалютного кошелька рядом с существующим `WalletBalanceCard`.
- Поле комментария в форме операции/пополнения; отображение комментария в карточке операции.

## Capabilities

### New Capabilities
- `frontend-workspaces`: текущий воркспейс (Context, `localStorage`), маршрутная защита `RequireWorkspace`,
  пустое состояние без воркспейсов, управление воркспейсами в «Настройках».

### Modified Capabilities
- `frontend-wallets`: пути запросов под воркспейс; новый `WalletRateCard`.
- `frontend-categories`: пути запросов под воркспейс.
- `frontend-transactions`: пути запросов под воркспейс; поле и отображение комментария.
- `frontend-transfers`: пути запросов под воркспейс.
- `frontend-analytics`: пути запросов под воркспейс.
- `frontend-auth`: защищённые маршруты дополнительно оборачиваются `RequireWorkspace` между `RequireAuth` и
  `AppLayout` — уточнение при написании specs: этот механизм описан в требовании «Публичные и защищённые
  маршруты» capability `frontend-auth` (не `frontend-app-shell`, которая описывает структуру проекта, а не
  маршрутную защиту).

## Impact

- **API**: не меняется (020/021/022 уже реализованы на backend) — меняется только то, как frontend к нему
  обращается.
- **Frontend, новые файлы**: `features/workspaces/*` (Context, hooks CRUD, `RequireWorkspace`, UI выбора/управления),
  `features/wallets/WalletRateCard.tsx` (+hook), поле комментария в `features/transactions/{TransactionForm,
  TopupForm}.tsx`.
- **Frontend, изменяемые файлы**: 18 существующих data-хуков (`features/{wallets,categories,transactions,
  transfers,analytics}/use*.ts`) и их ~30 тестов — путь запроса и ключ кэша получают `workspace_id`; `app/
  routes.tsx` — вложенный `RequireWorkspace`; `features/settings/SettingsPage.tsx` — новая секция управления
  воркспейсами.
- Точный список затрагиваемых хуков — в design.md (раздел «Перенос существующих хуков»), без сокращений.
