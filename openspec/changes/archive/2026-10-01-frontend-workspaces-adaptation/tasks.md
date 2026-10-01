## 1. Фича `workspaces` — ядро

- [x] 1.1 `features/workspaces/Workspace.ts` — тип `Workspace` (`id`, `name`, `created_at`, `updated_at`),
      `WorkspaceFormValues` (`name`).
- [x] 1.2 `features/workspaces/workspaceStorage.ts` — `workspaceStorage` (`get`/`set`, `localStorage`, ключ
      `moneyhelper.workspace`, try/catch, тихий откат — копия `shared/ui/theme/storage.ts::localThemeStorage`).
- [x] 1.3 `features/workspaces/WorkspaceContext.tsx` — `WorkspaceContext`, `useCurrentWorkspaceId()` (throw вне
      провайдера, образец `ApiClientProvider`).
- [x] 1.4 `features/workspaces/useWorkspaces.ts`, `useCreateWorkspace.ts`, `useRenameWorkspace.ts`,
      `useDeleteWorkspace.ts` — CRUD `/api/workspaces*` (без `useCurrentWorkspaceId()` — не вложены под
      воркспейс, design.md Decision 6). Unit-тесты каждого (образец — `features/wallets/use*.test.ts`).

## 2. `RequireWorkspace`

- [x] 2.1 `features/workspaces/WorkspaceActionsContext.tsx` — `{ switchWorkspace(id: string): void }`.
- [x] 2.2 `features/workspaces/RequireWorkspace.tsx` — три состояния (загрузка → спиннер; пусто → `EmptyState` с
      формой создания первого воркспейса; невалидный/отсутствующий сохранённый id → список выбора; валидный →
      `WorkspaceContext.Provider` + `WorkspaceActionsContext.Provider`, оборачивающие `children`).
- [x] 2.3 Тесты `RequireWorkspace` (все три состояния + переключение обновляет `workspaceStorage`).

## 3. Роутинг

- [x] 3.1 `app/routes.tsx` — `RequireWorkspace` между `RequireAuth` и `AppLayout`.
- [x] 3.2 (доп.) `test/session.ts::withSession` — `GET /api/workspaces` по умолчанию отвечает одним тестовым
      воркспейсом (`DEFAULT_WORKSPACE`), чтобы маршрутные тесты (`renderApp`) проходили `RequireWorkspace` без
      лишнего экрана выбора (см. design.md, уточнение в Decision 2 — единственный воркспейс выбирается сам).

## 4. Перенос `wallets`

- [x] 4.1 `features/wallets/useWallets.ts`, `useCreateWallet.ts`, `useUpdateWallet.ts`, `useDeleteWallet.ts` —
      пути под `/api/workspaces/{workspace_id}/wallets...`; `WALLETS_QUERY_KEY` → `walletsQueryKey(workspaceId)`.
- [x] 4.2 Обновить их тесты (`WorkspaceContext.Provider` в локальном `wrapper`, новые пути в ожиданиях) — включая
      `WalletCard.test.tsx`, `WalletForm.test.tsx`, `WalletsPage.test.tsx` (компонентные тесты, не только хуки).

## 5. Перенос `categories`

- [x] 5.1 `features/categories/useCategories.ts`, `useCreateCategory.ts`, `useUpdateCategory.ts`,
      `useDeleteCategory.ts` — пути под воркспейс; `CATEGORIES_QUERY_KEY` → `categoriesQueryKey(workspaceId)`.
- [x] 5.2 Обновить их тесты — включая `CategoryCard.test.tsx`, `CategoryForm.test.tsx`, `CategoriesPage.test.tsx`.

## 6. Перенос `transactions`

- [x] 6.1 `features/transactions/useTransactions.ts`, `useWalletBalances.ts`, `useCreateTransaction.ts`,
      `useUpdateTransaction.ts`, `useDeleteTransaction.ts`, `useCreateTopup.ts` — пути под воркспейс (включая
      `/transactions/topups`, `/wallets/{id}/balances`); ключи → `transactionsQueryKey`/`walletBalancesQueryKey`
      (локальный `transactionsQueryKey`/filters-ключ переименован в `transactionListKey`, чтобы не конфликтовать
      по имени с новым экспортируемым `transactionsQueryKey(workspaceId)`).
- [x] 6.2 Обновить их тесты — включая `TransactionCard.test.tsx`, `TransactionForm.test.tsx`, `TopupForm.test.tsx`,
      `TransactionsPage.test.tsx`, `WalletBalanceCard.test.tsx` (компонентные тесты).

## 7. Перенос `transfers`

- [x] 7.1 `features/transfers/useCreateTransfer.ts`, `useDeleteTransfer.ts`, `useTransfers.ts`,
      `useUpdateTransfer.ts` — пути под воркспейс; `TRANSFERS_QUERY_KEY` → `transfersQueryKey(workspaceId)`
      (локальный filters-ключ переименован в `transferListKey`, как и в `transactions`); локальная копия ключа
      баланса — теперь `["wallet-balances", workspaceId]` (без импорта из `transactions`).
- [x] 7.2 Обновить их тесты — включая `TransferCard.test.tsx`, `TransferForm.test.tsx`, `TransfersPage.test.tsx`,
      `balanceInvalidation.test.tsx`.

## 8. Перенос `analytics`

- [x] 8.1 `features/analytics/useAnalytics.ts` — путь под воркспейс; `ANALYTICS_QUERY_KEY` →
      `analyticsQueryKey(workspaceId)`.
- [x] 8.2 Обновить его тесты — включая `AnalyticsPage.test.tsx`, `useBucketLabelResolvers.test.ts` (косвенно
      зависит от `useWallets`/`useCategories`).

## 9. Управление воркспейсами в «Настройках»

- [x] 9.1 `features/workspaces/WorkspaceForm.tsx` — создание/переименование, один компонент (образец
      `WalletForm`) — написан раньше, как предпосылка для `RequireWorkspace` (группа 2).
- [x] 9.2 `features/workspaces/WorkspacesSection.tsx` — список (имя, «Переключить»/«Переименовать»/«Удалить» с
      `Popconfirm`, образец `WalletCard`), использует `WorkspaceActionsContext`.
- [x] 9.3 `features/settings/SettingsPage.tsx` — `<Card title="Воркспейсы"><WorkspacesSection /></Card>`.
- [x] 9.4 Тесты `WorkspaceForm`/`WorkspacesSection`.

## 10. `WalletRateCard`

- [x] 10.1 `features/wallets/useWalletRates.ts` — `GET .../wallets/{walletId}/rates?target_currency_id=...`, ключ
      `["wallet-rates", workspaceId, walletId, targetCurrencyId]`; добавлен `enabled`, чтобы не запрашивать курс
      для кошелька с одной валютой.
- [x] 10.2 `features/wallets/WalletRateCard.tsx` — рендер только для кошелька с >1 валютой; `target_currency_id`
      — `wallet.currency_ids[0]`; `unrated_currency_ids` → «нет данных для курса», не ошибка.
- [x] 10.3 Подключить в `features/transactions/TransactionsPage.tsx` рядом с `WalletBalanceCard`; добавлен
      нейтральный фейковый ответ на `.../rates` в `TransactionsPage.test.tsx::withFixtures`, чтобы существующие
      тесты страницы (не про курс) не падали на новом побочном запросе.
- [x] 10.4 Тесты `useWalletRates`/`WalletRateCard`.

## 11. Комментарий операции

- [x] 11.1 `features/transactions/Transaction.ts` — `comment?: string` (форма), `comment: string | null` (ответ
      backend) на `Transaction`/`TransactionFormValues`/`TopupFormValues`.
- [x] 11.2 `features/transactions/TransactionForm.tsx`, `TopupForm.tsx` — `Form.Item name="comment"` (`max: 1000`,
      `Input.TextArea` с `showCount`), добавить в `KNOWN_FIELDS` и в оба варианта `setFieldsValue`.
- [x] 11.3 `features/transactions/TransactionCard.tsx` — строка с комментарием, если задан.
- [x] 11.4 Обновить тесты `TransactionForm`/`TopupForm`/`TransactionCard` (создание/предзаполнение/очистка
      комментария) — плюс фикстуры `Transaction` во всех тестах получили обязательное поле `comment`.

## 12. QualityGate и ручная проверка

- [x] 12.1 `make format`, затем `make lint`, затем `make test` — все проходят подряд (backend 445/445, frontend
      487/487).
- [x] 12.2 Ручная проверка в браузере — Claude in Chrome не подключено в этой сессии
      (`list_connected_browsers` → `[]`); задокументировано как известное ограничение по образцу 019, не
      блокирует.
- [x] 12.3 `docs/tasks/023_frontend_workspaces_adaptation.md` — заполнить раздел «Статус» по итогам реализации.
