## Context

Frontend (013–018) целиком построен на 18 data-хуках, каждый сам строит путь `/api/...` и владеет константой
`*_QUERY_KEY` (`useWallets`, `useCreateWallet`, `useUpdateWallet`, `useDeleteWallet`, `useCategories`,
`useCreateCategory`, `useUpdateCategory`, `useDeleteCategory`, `useTransactions`, `useWalletBalances`,
`useCreateTransaction`, `useUpdateTransaction`, `useDeleteTransaction`, `useCreateTopup`, `useCreateTransfer`,
`useDeleteTransfer`, `useTransfers`, `useUpdateTransfer`, `useAnalytics`). Backend (020) перевёл все эти пути под
`/api/workspaces/{workspace_id}/...` — ни один из 18 хуков сейчас не работает. Сессия (`useSession`) — обычный
TanStack Query без контекста (`shared/api/ApiClientProvider.tsx` — единственный существующий пример Context +
хук-обёртка с явным `throw`, если хук вызван вне провайдера — прямой образец для `WorkspaceContext`).

## Goals / Non-Goals

**Goals:**
- Все 18 хуков и их ~30 тестов работают против новых путей backend, с `workspace_id` и в пути, и в ключе кэша.
- Текущий воркспейс — синхронно доступен любому потребителю ниже точки входа маршрутов, без «мигания» пустым
  состоянием при уже известном (из `localStorage`) воркспейсе.
- Переключение воркспейса не показывает данные предыдущего (закэшированные под другим ключом) и не требует
  перезагрузки страницы.
- Курс кошелька (021) и комментарий операции (022) видны и редактируемы в UI.

**Non-Goals:**
- Совместный доступ к воркспейсу, роли.
- Ручной выбор целевой валюты для `WalletRateCard` — фиксированная (первая по коду).
- Единая переиспользуемая обёртка для тестов hooks — сохраняется существующий локальный `setup()` на файл (см.
  Decision 5), не вводится новый общий test-helper.

## Decisions

### 1. `WorkspaceContext` — React Context, не TanStack Query

**Решение:** `features/workspaces/WorkspaceContext.tsx` — `createContext<string | null>(null)` +
`useCurrentWorkspaceId(): string`, кидающий `Error`, если вызван вне провайдера (буквальный образец
`ApiClientProvider.tsx`). Значение контекста устанавливает `RequireWorkspace` (Decision 2), а не отдельный
`<WorkspaceProvider>` — тот же приём, что `RequireAuth`, который сам решает, что рендерить, без отдельного
провайдера сессии.

**Отвергнутая альтернатива: TanStack Query, как `useSession`.** Отвергнута — сессия читается один раз наверху
дерева маршрутов; `workspace_id` нужен синхронно ~20 разным потребителям ниже (каждый data-хук), и через Query
пришлось бы либо прокидывать `workspaceId` пропом через всю цепочку компонентов, либо всё равно читать глобальный
кэш Query из каждого хука — Context для маршрутного параметра такого рода ближе к идиоме React, чем Query.

### 2. `RequireWorkspace` — обёртка ниже `RequireAuth`, сама решает что рендерить

**Решение:** `features/workspaces/RequireWorkspace.tsx`, применяется в `app/routes.tsx` между `RequireAuth` и
`AppLayout`:
```tsx
<RequireAuth>
  <RequireWorkspace>
    <AppLayout />
  </RequireWorkspace>
</RequireAuth>
```
Компонент: `useWorkspaces()` (список); `useState<string | null>` инициализируется из `workspaceStorage.get()`
(Decision 3) при монтировании. Пока список грузится — тот же `FullscreenSpinner`-приём, что в `RequireAuth`. После
загрузки:
- Список пуст → рендерит `EmptyState` (`shared/ui`) с формой создания первого воркспейса прямо на месте (без
  отдельного маршрута — тот же принцип, что «Онбординг с пустыми данными», 002_roadmap.md).
- Текущий id не задан или не входит в список (устаревший/удалённый) → список воркспейсов для выбора (простой
  `List`/`Radio.Group` карточек, клик — выбор).
- Иначе → `WorkspaceContext.Provider value={workspaceId}`, оборачивающий `children`; функция `setWorkspaceId`
  (обновляет и `useState`, и `workspaceStorage.set`) передаётся вниз не через сам `WorkspaceContext` (он хранит
  только `string`, по образцу `ApiClientProvider`, отдающего только клиент, не сеттер), а через отдельный
  `WorkspaceActionsContext` (`{ switchWorkspace(id: string): void }`), который читает `WorkspacesSection`
  (Decision 6) в «Настройках» — переключение воркспейса нужно только там, не в каждом потребителе данных.

**Уточнение при реализации:** если воркспейс ровно один, а сохранённого/валидного id нет — он выбирается
автоматически (`useEffect`, без участия пользователя), без показа списка выбора из одного пункта. Это не меняет
поведение при 0 или ≥2 воркспейсах, просто устраняет бессмысленный лишний клик в самом частом случае (один
воркспейс на пользователя). Тот же эффект неявно нужен и тестам оболочки (`renderApp`/`withSession`) — маршрутные
тесты, не имеющие отношения к воркспейсам, не должны упираться в экран выбора.

**Отвергнутая альтернатива: редирект на отдельный маршрут `/workspaces/pick`.** Отвергнута — воркспейсы не имеют
собственного постоянного URL (как и логика `RequireAuth`, которая не редиректит на «страницу проверки сессии»);
пустое состояние/выбор рендерятся `RequireWorkspace` inline, ровно там, где сейчас был бы `AppLayout`.

### 3. `workspaceStorage` — `localStorage`, буквальный образец `localThemeStorage`

**Решение:** `features/workspaces/workspaceStorage.ts`, ключ `moneyhelper.workspace`, структура (`get`/`set`,
try/catch, тихий откат при недоступном хранилище) — копия `shared/ui/theme/storage.ts::localThemeStorage`. Второе
исключение из правила «в localStorage — только предпочтение интерфейса» (первое — тема, AGENTS.md): выбор
последнего открытого воркспейса — тоже предпочтение интерфейса, не данные пользователя.

### 4. Перенос 18 существующих хуков — единый механический паттерн

**Решение:** для каждого файла — два изменения:
1. Путь: `"/api/wallets"` → путём с шаблонной строкой `` `/api/workspaces/${workspaceId}/wallets` `` (и т. п. для
   остальных пяти capability); `workspaceId = useCurrentWorkspaceId()` — новая первая строка тела хука.
2. Ключ кэша: каждая экспортируемая `*_QUERY_KEY`-константа (`as const` массив) становится функцией
   `xxxQueryKey(workspaceId: string)`, возвращающей `["wallets", workspaceId] as const` и т. п.; хуки, что сейчас
   строят производный ключ (`[...WALLETS_QUERY_KEY, ...]`), берут `workspaceId` тем же вызовом
   `useCurrentWorkspaceId()` и передают его в функцию.

Полный список (файл → что меняется, помимо общего паттерна выше):

| Файл | Путь до | Путь после | Ключ кэша |
|---|---|---|---|
| `wallets/useWallets.ts` | `/api/wallets` | `/api/workspaces/{id}/wallets` | `WALLETS_QUERY_KEY` → `walletsQueryKey(id)` |
| `wallets/useCreateWallet.ts` | `/api/wallets` | `/api/workspaces/{id}/wallets` | инвалидация `walletsQueryKey(id)` |
| `wallets/useUpdateWallet.ts` | `/api/wallets/{id}` | `/api/workspaces/{wsId}/wallets/{id}` | инвалидация `walletsQueryKey(wsId)` |
| `wallets/useDeleteWallet.ts` | `/api/wallets/{id}` | `/api/workspaces/{wsId}/wallets/{id}` | инвалидация `walletsQueryKey(wsId)` |
| `categories/useCategories.ts` | `/api/categories` | `/api/workspaces/{id}/categories` | `CATEGORIES_QUERY_KEY` → `categoriesQueryKey(id)`, `categoryListKey(id, type)` |
| `categories/useCreateCategory.ts` | `/api/categories` | `/api/workspaces/{id}/categories` | инвалидация `categoriesQueryKey(id)` |
| `categories/useUpdateCategory.ts` | `/api/categories/{id}` | `/api/workspaces/{wsId}/categories/{id}` | инвалидация `categoriesQueryKey(wsId)` |
| `categories/useDeleteCategory.ts` | `/api/categories/{id}` | `/api/workspaces/{wsId}/categories/{id}` | инвалидация `categoriesQueryKey(wsId)` |
| `transactions/useTransactions.ts` | `/api/transactions` | `/api/workspaces/{id}/transactions` | `TRANSACTIONS_QUERY_KEY` → `transactionsQueryKey(id)` |
| `transactions/useWalletBalances.ts` | `/api/wallets/{walletId}/balances` | `/api/workspaces/{id}/wallets/{walletId}/balances` | `WALLET_BALANCES_QUERY_KEY` → `walletBalancesQueryKey(id)` |
| `transactions/useCreateTransaction.ts` | `/api/transactions` | `/api/workspaces/{id}/transactions` | инвалидация `transactionsQueryKey(id)`, `walletBalancesQueryKey(id)`; тело запроса + `comment` (022) |
| `transactions/useUpdateTransaction.ts` | `/api/transactions/{id}` | `/api/workspaces/{wsId}/transactions/{id}` | то же + `comment` |
| `transactions/useDeleteTransaction.ts` | `/api/transactions/{id}` | `/api/workspaces/{wsId}/transactions/{id}` | инвалидация, как выше |
| `transactions/useCreateTopup.ts` | `/api/transactions/topups` | `/api/workspaces/{id}/transactions/topups` | то же + `comment` |
| `transfers/useCreateTransfer.ts` | `/api/transfers` | `/api/workspaces/{id}/transfers` | своя локальная копия `WALLET_BALANCES_QUERY_KEY` тоже становится `walletBalancesQueryKey(id)` (та же функция, что в 4., не импорт — сохраняется существующий запрет кросс-импорта между `transactions`/`transfers`, каждая фича определяет свою копию) |
| `transfers/useDeleteTransfer.ts` | `/api/transfers/{id}` | `/api/workspaces/{wsId}/transfers/{id}` | то же |
| `transfers/useTransfers.ts` | `/api/transfers` | `/api/workspaces/{id}/transfers` | `TRANSFERS_QUERY_KEY` → `transfersQueryKey(id)` |
| `transfers/useUpdateTransfer.ts` | `/api/transfers/{id}` | `/api/workspaces/{wsId}/transfers/{id}` | инвалидация, как выше |
| `analytics/useAnalytics.ts` | `/api/analytics` | `/api/workspaces/{id}/analytics` | `ANALYTICS_QUERY_KEY` → `analyticsQueryKey(id)` |

**Отвергнутая альтернатива: `workspace_id` как query-параметр вместо пути.** Отвергнута — backend (020) уже
зафиксировал путь как источник правды (`GET /api/workspaces/{workspace_id}/...`), frontend просто следует ему.

### 5. Тесты хуков — точечное добавление `WorkspaceContext.Provider` в существующий локальный `wrapper`

**Решение:** каждый из ~18 тестовых файлов хуков уже определяет собственный локальный `setup()`/`wrapper` (не
существует общего shared-helper для hooks — в отличие от `renderApp` для компонентных/маршрутных тестов). В каждый
такой `wrapper` добавляется ещё один вложенный провайдер: `WorkspaceContext.Provider value={TEST_WORKSPACE_ID}`
(константа-строка, например `"workspace-1"`); ожидания путей (`api.requests[0].path`) обновляются с новым
префиксом.

**Отвергнутая альтернатива: новый общий `renderHookWithProviders` helper.** Отвергнута — вводить абстракцию,
объединяющую 18 файлов, ради задачи, которая и так требует правки каждого из них построчно (путь тоже меняется
индивидуально) — не даёт экономии, локальный `wrapper` уже используется как устоявшийся паттерн проекта.

### 6. Управление воркспейсами — секция в «Настройках», CRUD-хуки по образцу `wallets`

**Решение:** `features/workspaces/` получает полный вертикальный срез по прямому образцу `features/wallets/`:
`Workspace.ts` (тип + `WorkspaceFormValues`), `useWorkspaces.ts`, `useCreateWorkspace.ts`, `useRenameWorkspace.ts`
(`PUT`, полная замена `name` — как и на backend), `useDeleteWorkspace.ts`, `WorkspaceForm.tsx` (создание/
переименование, один компонент, по образцу `WalletForm`), `WorkspacesSection.tsx` (список в `Card`, каждая строка
— имя + «Переключить» (если не текущий) + «Переименовать» + «Удалить» с `Popconfirm`, тот же паттерн, что
`WalletCard`). `SettingsPage.tsx` получает новый `<Card title="Воркспейсы"><WorkspacesSection /></Card>`, рядом с
существующей `<Card title="Категории">`. `WorkspacesSection` использует `useContext(WorkspaceActionsContext)` для
`switchWorkspace` (Decision 2) — единственный потребитель этого контекста в приложении.

Эти хуки (`useWorkspaces`/`useCreateWorkspace`/`useRenameWorkspace`/`useDeleteWorkspace`) НЕ вызывают
`useCurrentWorkspaceId()` — `/api/workspaces*` не вложен под воркспейс (это сам справочник воркспейсов
пользователя), поэтому не участвуют в паттерне Decision 4 и не создают циклическую зависимость от контекста,
который сами же и наполняют.

### 7. `WalletRateCard` — новый компонент рядом с `WalletBalanceCard`, целевая валюта — первая по коду

**Решение:** `features/wallets/useWalletRates.ts` (`GET .../wallets/{walletId}/rates?target_currency_id=...`,
ключ `["wallet-rates", workspaceId, walletId, targetCurrencyId]`) + `features/wallets/WalletRateCard.tsx` —
рендерится в `TransactionsPage` рядом с `WalletBalanceCard` (то же место, тот же триггер — выбранный в фильтре
кошелёк), только если у кошелька больше одной валюты (`wallet.currency_ids.length > 1`); `target_currency_id` —
`wallet.currency_ids[0]` (backend уже отдаёт `currency_ids` отсортированными по коду валюты, см. `wallets` spec,
сценарий «Валюты кошелька отсортированы по коду» — переиспользуется без доп. сортировки на frontend). Строки —
«1 CNY ≈ 12.8205 RUB» на валюту из `rates`; валюты из `unrated_currency_ids` — отдельная строка «нет данных для
курса» (без падения компонента).

**Отвергнутая альтернатива: показывать курс в `WalletCard` (список кошельков).** Отвергнута — курс требует
`target_currency_id`, определённого только когда у кошелька больше одной валюты и известен порядок валют; список
кошельков (`WalletsPage`) не место, где пользователь сравнивает конкретный кошелёк с его же балансом — этим местом
уже единообразно служит `TransactionsPage`/`WalletBalanceCard`.

### 8. Комментарий операции — поле в форме, строка в карточке

**Решение:** `TransactionFormFields`/`TransactionFormValues`/`TopupFormValues`/`Transaction` (`features/
transactions/Transaction.ts`) получают `comment?: string` (форма) / `comment: string | null` (ответ backend, как у
`updated_at`). `TransactionForm.tsx` и `TopupForm.tsx`: `Form.Item name="comment" label="Комментарий"
rules={[{ max: 1000, message: "Не более 1000 символов" }]}><Input.TextArea rows={2} maxLength={1000}
showCount /></Form.Item>`, добавляется в `KNOWN_FIELDS`, в оба варианта `setFieldsValue` (пустая строка при
создании, `transaction.comment ?? undefined` при редактировании — antd `Form` не любит `null`). `TransactionCard`:
`{transaction.comment ? <Typography.Text type="secondary">{transaction.comment}</Typography.Text> : null}` сразу
после блока `legs`, до строки даты.

## Risks / Trade-offs

- [Изменение затрагивает ~18 хуков + ~30 их тестов + новую фичу `workspaces` из ~8 файлов — самая большая
  frontend-задача проекта] → механическая часть (перенос путей/ключей) однотипна и проверяема построчно по
  таблице Decision 4; тесты ловят несовпадение путей сразу.
- [`WorkspaceActionsContext` — второй React Context в приложении, тогда как `ApiClientProvider` был единственным
  прецедентом] → минимальный риск: тот же понятный, ограниченный по потребителям паттерн (один провайдер, один
  явный `useContext`-хук с `throw`), не «господствующий» контекст, торчащий во все компоненты.
- [`WalletRateCard` может показать `unrated_currency_ids` при ещё не введённых пополнениях] → ожидаемо и уже
  предусмотрено текстом «нет данных для курса», а не ошибкой/пустым экраном.

## Migration Plan

1. `features/workspaces/`: `Workspace.ts`, `workspaceStorage.ts`, `WorkspaceContext.tsx`
   (`useCurrentWorkspaceId`), `useWorkspaces.ts`, `useCreateWorkspace.ts`, `useRenameWorkspace.ts`,
   `useDeleteWorkspace.ts` + их unit-тесты.
2. `features/workspaces/RequireWorkspace.tsx` (+ `WorkspaceActionsContext`) + тесты (пусто → форма создания;
   невалидный сохранённый id → список выбора; валидный → рендерит `children` с контекстом).
3. `app/routes.tsx` — `RequireWorkspace` между `RequireAuth` и `AppLayout`.
4. Перенос 18 хуков + их тестов по таблице Decision 4, по одному capability за раз (`wallets` →
   `categories` → `transactions` → `transfers` → `analytics`), с прогоном затронутых тестов после каждого.
5. `WorkspaceForm.tsx`, `WorkspacesSection.tsx`, включение в `SettingsPage.tsx` + тесты.
6. `useWalletRates.ts`, `WalletRateCard.tsx`, включение в `TransactionsPage.tsx` + тесты.
7. Комментарий: `Transaction.ts`, `TransactionForm.tsx`, `TopupForm.tsx`, `TransactionCard.tsx` + тесты.
8. QualityGate (`make format`, `make lint`, `make test`); ручная проверка в браузере (по образцу 019) —
   создание воркспейса, переключение, что данные не смешиваются, курс и комментарий видны.

## Open Questions

Нет.
