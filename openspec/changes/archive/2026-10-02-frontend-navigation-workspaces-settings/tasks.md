## 1. Удаление «Главной» и статуса backend

- [x] 1.1 Удалить `features/health`, пункт «Главная» из `navItems`, индексный маршрут заменить на
  `<Navigate to="/wallets" replace />` в `routes.tsx`
- [x] 1.2 Обновить тесты оболочки (`App.test.tsx`, `AppLayout.test.tsx`, `sessionExpiry.test.tsx`): убрать проверки
  `/health`, добавить: `/` → «Кошельки», 4 пункта навигации без «Главная», мобильный и десктопный режимы

## 2. Воркспейсы: валюта

- [x] 2.1 `Workspace`/`WorkspaceFormValues`: добавить `currency_id`; обновить `DEFAULT_WORKSPACE` и фикстуры тестов
- [x] 2.2 `WorkspaceForm`: поле `CurrencyPicker` (обязательное), в режиме редактирования — блокировка при наличии
  кошельков (`useWorkspaceHasWallets`), `currency_id` в `KNOWN_FIELDS`; тесты формы и хука
- [x] 2.3 `WorkspacesSection`: код валюты в строке воркспейса, текст подтверждения удаления; тесты

## 3. Перенос в «Настройки» и индикатор

- [x] 3.1 Добавить карточку «Воркспейсы» с `WorkspacesSection` в `SettingsPage`
- [x] 3.2 `useCurrentWorkspace` и `WorkspaceBadge`; встроить в `DesktopShell` (шапка) и `MobileShell` (полоса над
  контентом); тесты индикатора, включая обновление после переключения
- [x] 3.3 Тест `RequireWorkspace`: первый воркспейс создаётся с валютой

## 4. Документация и проверка

- [x] 4.1 `AGENTS.md`: убрать `health` из структуры frontend
- [x] 4.2 Проверить в браузере (десктоп и телефон): регистрация/вход, создание воркспейса с валютой, нет «Главной» и
  статуса backend, `/` → «Кошельки», управление в «Настройках», индикатор, консоль без ошибок
- [x] 4.3 QualityGate: `make format`, `make lint`, `make test` проходят
