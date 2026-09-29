## Context

Backend-капабилити `wallets` (008) и frontend-фундамент `frontend-shell` (013) уже реализованы и заархивированы.
013 подготовил именно те кирпичи, которые нужны этому экрану: `CurrencyPicker` (одиночный/множественный выбор
валюты поверх `GET /api/currencies`), `IconPicker` (выбор из закрытого `BUSINESS_ICON_NAMES`, `Drawer`/`Modal` по
`useIsMobile`), `EmptyState` (пустой список с действием) и тип `Page<T>`. Все решения по объёму и границам этой
задачи уже приняты оркестратором в `docs/tasks/014_frontend_wallets.md` и не пересматриваются здесь; этот документ
фиксирует точные сигнатуры и механику реализации, по образцу `design.md` изменения `frontend-shell`.

Backend-контракт (`backend/src/api/schemas/wallet.py`, `backend/src/api/wallets.py`):
`POST /api/wallets` → 201 `WalletOut`; `GET /api/wallets` → `Page[WalletOut]` (`PageParams`: `limit` 1..100,
по умолчанию 20, `offset`); `GET /api/wallets/{id}` → `WalletOut`; `PUT /api/wallets/{id}` → `WalletOut` (та же
валидация тела, что и `POST`, `WalletUpdate = WalletCreate`); `DELETE /api/wallets/{id}` → 204 или 409
(`ConflictError`, если есть операции). Список отсортирован `created_at ASC, id ASC` уже на backend.
`WalletCreate`/`WalletUpdate`: `name` (непустой после `strip()`, ≤ 100 символов), `icon` (`IconName`),
`currency_ids` (непустой список UUID без дублей). `WalletOut` дополнительно отдаёт `id`, `created_at`,
`updated_at`.

## Goals / Non-Goals

**Goals:**
- Список кошельков карточками (иконка, название, валюты чипами) одним запросом без клиентской пагинации, по
  образцу `useCurrencies` (013).
- Один компонент `WalletForm` для создания и редактирования, открывающийся в `Drawer`/`Modal` поверх списка.
- Удаление с подтверждением через `Popconfirm`, 409 при кошельке с операциями обрабатывается уже существующим
  глобальным обработчиком ошибок без специального кода.
- Пункт навигации «Кошельки» и маршрут `/wallets` под `RequireAuth`.
- Кэш TanStack Query с единым `queryKey`, инвалидируемым всеми тремя мутациями.
- Всё покрыто тестами (`FakeApiClient`), по mobile-first правилам AGENTS.md.

**Non-Goals:**
- Баланс кошелька по валютам (016).
- Переводы между кошельками (017).
- Отдельные маршруты для форм (`/wallets/new` и т. п.).
- Серверная/клиентская постраничная пагинация в UI списка кошельков.
- Правки `shared/ui/icons.ts` — иконка `"wallet"` для пункта навигации уже есть в `BUSINESS_ICONS`.

## Decisions

### Структура файлов

```
frontend/src/features/wallets/
  Wallet.ts                 # тип Wallet (форма WalletOut), WalletFormValues
  useWallets.ts              # useQuery(GET /api/wallets), WALLETS_QUERY_KEY
  useWallets.test.ts
  useCreateWallet.ts
  useCreateWallet.test.ts
  useUpdateWallet.ts
  useUpdateWallet.test.ts
  useDeleteWallet.ts
  useDeleteWallet.test.ts
  WalletForm.tsx
  WalletForm.test.tsx
  WalletCard.tsx
  WalletCard.test.tsx
  WalletsPage.tsx
  WalletsPage.test.tsx
```

Каждый hook — отдельный файл с тестом рядом (по образцу `shared/ui/CurrencyPicker/useCurrencies.ts` и
`features/settings/useLogout.ts`), а не один общий файл со всеми мутациями: SOLID S — одна мутация, одна причина
для изменения.

### `Wallet` — без camelCase-маппинга, в отличие от `Currency`

```ts
export interface Wallet {
  id: string;
  name: string;
  icon: string;
  currency_ids: string[];
  created_at: string;
  updated_at: string | null;
}
```

В `frontend-shell` для `Currency` был введён ручной маппинг `CurrencyDto` → `Currency` с переводом
`decimal_places` → `decimalPlaces` (обоснование — в `design.md` 013). Для `Wallet` маппинг не вводится, и это
самостоятельное решение этой задачи (не переоткрытие решения 013, а применение того же принципа к новому случаю):
- В проекте уже есть прецедент для *обратного* выбора — `User` (`features/auth/session.ts`) хранит `created_at`
  как есть, без камelCase, потому что поле не участвует в вычислениях, а только отображается/передаётся дальше.
  Ровно та же ситуация здесь: `created_at`/`updated_at` кошелька нигде не отображаются и не используются (вне
  рамок — баланс и сортировка уже на backend), а `currency_ids` используется как есть — тем же именем и той же
  формой (`string[]` c UUID), что и проп `value` `CurrencyPicker` в режиме `multiple` и поле `currency_ids` тела
  запроса `WalletCreate`/`WalletUpdate`. Маппинг здесь не снимает никакой реальной проблемы (в отличие от
  `decimal_places`, который на camelCase-стороне обязательно нужен был как `decimalPlaces` для использования в
  `MoneyInput`), а только добавляет код и файл-тест ради единообразия ради единообразия (YAGNI).
- Если в будущих задачах (015+) понадобится камelCase-поле конкретного DTO кошелька/категории — по прецеденту
  013 это будет точно такая же ручная функция рядом с hook'ом, а не общий конвертер.

### `WALLETS_QUERY_KEY` и `useWallets`

```ts
export const WALLETS_QUERY_KEY = ["wallets"] as const;

export function useWallets() {
  const api = useApiClient();
  return useQuery({
    queryKey: WALLETS_QUERY_KEY,
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<Wallet>>("/api/wallets", {
        query: { limit: 100, offset: 0 },
        signal,
      });
      return page.items;
    },
  });
}
```

`limit: 100` — максимум, допустимый `PageParams` (`le=100`), тот же принцип, что уже применён в `useCurrencies`
(013): персональный объём кошельков пользователя мал (единицы-десятки), клиентская постраничная подгрузка не
нужна. `GET /api/wallets` требует авторизации, но ошибка загрузки (кроме `unauthorized`, который отдельно
обрабатывает `RequireAuth`/глобальный обработчик) показывается стандартным глобальным toast — `meta: { silent:
true }` не передаётся, как и в `useCurrencies`.

### Три мутации: `useCreateWallet`/`useUpdateWallet`/`useDeleteWallet`

```ts
export interface WalletFormValues {
  name: string;
  icon: string;
  currency_ids: string[];
}

export function useCreateWallet() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: WalletFormValues) => api.post<Wallet>("/api/wallets", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_QUERY_KEY });
    },
  });
}

export function useUpdateWallet() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: WalletFormValues }) =>
      api.put<Wallet>(`/api/wallets/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_QUERY_KEY });
    },
  });
}

export function useDeleteWallet() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<undefined>(`/api/wallets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WALLETS_QUERY_KEY });
    },
  });
}
```

`WalletFormValues` совпадает по форме с телом `WalletCreate`/`WalletUpdate` — те же имена полей (`name`, `icon`,
`currency_ids`), без промежуточного camelCase-слоя, поэтому значения `antd Form` (поля формы называются так же)
уходят в `mutationFn` без трансформации, а `applyFieldErrors` сопоставляет ошибки backend с полями формы напрямую
(см. `WalletForm` ниже) — тот же принцип, что уже применён в `RegisterPage`/`ChangePasswordForm`, где имена полей
формы совпадают с именами полей тела запроса.

`useCreateWallet`/`useUpdateWallet` — `meta: { silent: true }`: 400 по полям обрабатывает сама форма
(`applyFieldErrors`), по образцу `useRegister`. `useDeleteWallet` — **без** `meta: { silent: true }` и без
`onError`: единственная ошибка, которая может прийти при удалении (кроме общих 401/403/404/500/сеть, которые
и так покрыты дефолтным поведением), — 409 «есть операции», а `MESSAGE_BUILDERS.conflict`
(`shared/errors/messages.ts`) уже показывает `error.detail` от backend, то есть готовое понятное сообщение вроде
«Кошелёк нельзя удалить: есть операции» — писать собственный `onError` означало бы дублировать то, что уже делает
глобальный обработчик (нарушение DRY без причины). Мутация только инвалидирует список на успехе.

### `WalletForm` — один компонент для создания и редактирования

```ts
export interface WalletFormProps {
  open: boolean;
  onClose: () => void;
  /** undefined — форма создания; заданный `Wallet` — форма редактирования, поля предзаполняются его значениями. */
  wallet?: Wallet;
}
```

Внутри компонент безусловно вызывает оба hook'а мутаций (`useCreateWallet()`, `useUpdateWallet()`) и на
`handleSubmit` выбирает, какой `.mutate` вызвать, по наличию `wallet` — вызывать hook'и условно запрещено
правилами React. При изменении `open`/`wallet` (`useEffect`) форма либо `form.setFieldsValue({ name: wallet.name,
icon: wallet.icon, currency_ids: wallet.currency_ids })` (редактирование, значения берутся из уже загруженного
элемента списка — **без** отдельного `GET /api/wallets/{id}**), либо `form.resetFields()` (создание). Поля:

```tsx
<Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
  <Form.Item name="name" label="Название" rules={[{ required: true, message: "Введите название" }]}>
    <Input maxLength={100} />
  </Form.Item>
  <Form.Item name="icon" label="Иконка" rules={[{ required: true, message: "Выберите иконку" }]}>
    <IconPicker />
  </Form.Item>
  <Form.Item
    name="currency_ids"
    label="Валюты"
    rules={[{ required: true, message: "Выберите хотя бы одну валюту" }]}
  >
    <CurrencyPicker multiple />
  </Form.Item>
  <Form.Item style={{ marginBottom: 0 }}>
    <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
      {wallet ? "Сохранить" : "Создать"}
    </Button>
  </Form.Item>
</Form>
```

`IconPicker`/`CurrencyPicker` кладутся прямо в `Form.Item` без дополнительных пропов: обе сигнатуры (013) —
`onChange(value)` без обёртки в событие, поэтому antd `Form.Item` подставляет `value`/`onChange` автоматически
(тот же механизм, что уже задокументирован для `MoneyInput` в `design.md` 013); `multiple` у `CurrencyPicker`
передаётся статически в JSX, а не через `Form.Item`. Правило `required` для `currency_ids` проверяет непустой
массив (пустой массив — falsy для правила antd с `type: "array"`, дополнительная валидация не нужна).

Ошибки отправки — тот же паттерн `silent` + `applyFieldErrors`, что и `RegisterPage`:
```ts
const KNOWN_FIELDS = ["name", "icon", "currency_ids"] as const;
// onError: apiError.kind === "validation" → applyFieldErrors(apiError, KNOWN_FIELDS) → form.setFields + toast
//          иначе → toast.error(resolveErrorMessage(apiError))
```
`onSuccess`: `toast.success(...)`, `onClose()` (`form.resetFields()` не обязателен — `WalletForm` размонтирует
поля при следующем открытии через `useEffect`, но вызывается для аккуратности перед закрытием).

Контейнер — `Drawer` (`placement="bottom"`, `height="80vh"`) на телефоне / `Modal` (`width={960}`, как у
`DesktopShell`/`IconPicker`) на широком экране, выбор по `useIsMobile()` — единственная точка решения, тот же
паттерн, что уже применил `IconPicker` (013). Вложенность `Drawer`/`Modal` (форма кошелька открывает `IconPicker`,
который сам открывает свой `Drawer`/`Modal`) штатно поддерживается antd стеком z-index — отдельного решения не
требует (зафиксировано в постановке задачи).

**Альтернатива — два раздельных компонента (`WalletCreateForm`/`WalletEditForm`)** отвергнута: оба сценария на
100% используют одну и ту же структуру полей, одну и ту же валидацию (backend валидирует `POST`/`PUT` одинаково —
`WalletUpdate = WalletCreate`) и одну и ту же обработку ошибок; различается только то, какая мутация вызывается и
чем предзаполняется форма. Раздельные компоненты дублировали бы разметку и обработку ошибок ради одной строки
разницы (SOLID S/O — один компонент со связной ответственностью «форма кошелька», а не два повторяющихся друг
друга). Этот же вывод уже сделан для `CurrencyPicker` в 013 (`multiple` как дискриминант вместо двух
компонентов) — здесь применяется тот же принцип к новому случаю.

### `WalletCard` — сам владеет удалением, по образцу `LogoutButton`

```ts
export interface WalletCardProps {
  wallet: Wallet;
  /** Коды валют кошелька, в порядке `wallet.currency_ids` (backend уже отсортировал по коду). */
  currencyCodes: string[];
  onEdit: (wallet: Wallet) => void;
}
```

`WalletCard` сам вызывает `useDeleteWallet()` и оборачивает кнопку удаления в `Popconfirm` (`title="Удалить
кошелёк «{wallet.name}»?"`, `okText="Удалить"`, `okType="danger"`, `cancelText="Отмена"`,
`onConfirm={() => deleteWallet.mutate(wallet.id)}`) — успешное удаление инвалидирует общий список, и карточка
пропадает из него автоматически без обратного вызова в `WalletsPage`; отдельный callback `onDelete` не нужен
(в отличие от `onEdit`, для которого состояние «какая форма открыта» обязано жить в `WalletsPage`, потому что оно
общее с кнопкой «Создать кошелёк»). Этот выбор — по образцу уже существующего `LogoutButton`
(`features/settings/LogoutButton.tsx`), который тоже сам владеет своей мутацией, а не получает её от родителя.
`Popconfirm` — всплывающее окно подтверждения (`Popover`-подобное позиционирование), а не блокирующий оверлей на
весь экран, поэтому правило mobile-first «модальные окна на телефоне — `Drawer`, не `Modal`» на него не
распространяется (решение уже зафиксировано в постановке задачи: `Popconfirm` используется как есть, без
адаптации под `Drawer`).

Рендер карточки — `Card`: `Icon` (`wallet.icon`) + `Typography.Text` (`wallet.name`) в шапке, `Flex wrap gap={4}`
с `Tag` на каждый код валюты из `currencyCodes` (не строка через запятую — явное решение постановки), внизу два
`Button` (редактировать — `onClick={() => onEdit(wallet)}`, удалить — под `Popconfirm`), оба ≥ 44×44 px из общей
темы.

### `WalletsPage` — сборка списка, состояние формы, разрешение кодов валют

```ts
export function WalletsPage() {
  const walletsQuery = useWallets();
  const currenciesQuery = useCurrencies();
  const [formState, setFormState] = useState<{ open: boolean; wallet?: Wallet }>({ open: false });
  // ...
}
```

`WalletsPage` — единственное место, которое одновременно знает про `useWallets()` и `useCurrencies()`: коды валют
для чипов карточки разрешаются здесь один раз через `Map<string, Currency>` (`id → Currency`), построенную из
`currenciesQuery.data`, и передаются в каждый `WalletCard` уже готовым списком `currencyCodes` — если бы каждая
карточка сама вызывала `useCurrencies()`, TanStack Query дедуплицировал бы сетевой запрос (общий `queryKey`
`["currencies"]`, кэш общий с `CurrencyPicker`), но пересчёт `Map` на каждую карточку было бы лишней работой и
лишней связанностью (SOLID S — `WalletCard` не должен знать про источник данных валют, только про готовый список
кодов). Список кошельков **не** ждёт валюты синхронно с блокировкой (нет общего "AND"-гейта загрузки): пока
`currenciesQuery` ещё не ответил, каждая карточка временно показывает пустой ряд чипов (`currencyCodes = []` для
ещё не найденных `id`) — крайне маловероятное и короткое состояние, так как `useCurrencies` обычно уже прогрет
где-то ещё в приложении (тот же `queryKey`), а список валют совсем мал.

Состояние `formState` — общее и для кнопки «Создать кошелёк» (`{ open: true, wallet: undefined }`), и для кнопки
«Редактировать» каждой карточки (`{ open: true, wallet }`), и единственный `<WalletForm open={formState.open}
wallet={formState.wallet} onClose={() => setFormState({ open: false })} />` рендерится один раз на странице —
не по одной форме на карточку, иначе на телефоне могло бы открыться несколько `Drawer` одновременно.

Разметка: `Flex vertical gap={16}` — `Typography.Title level={3}` «Кошельки», кнопка «Создать кошелёк»
(`type="primary"`, `block` на телефоне — тот же переключатель `useIsMobile()`, что уже применяет `EmptyState`),
затем список. Пока `walletsQuery.isPending` — `Spin`. Если список пуст (`walletsQuery.data.length === 0`) —
`EmptyState` (`icon="wallet"`, `title="Кошельков пока нет"`, `action={{ label: "Создать кошелёк", onClick: ... }}`)
**вместо** заголовка и кнопки создания (одно место входа в создание, не два одновременно видимых). Иначе — `Flex
vertical gap={12}` с `WalletCard` на каждый элемент, в порядке, в котором пришли от backend (без клиентской
пересортировки).

### Навигация: переиспользование иконки `"wallet"`

`shared/ui/icons.ts` уже объединяет `BUSINESS_ICONS` и `UI_ICONS` в единый `ICONS` (`resolveIcon`/`Icon` резолвят
имя из объединённого списка), и `"wallet"` уже есть в `BUSINESS_ICONS` (используется как бизнес-иконка кошелька
в данных пользователя). Пункт `navItems` («Кошельки», иконка `"wallet"`) использует то же самое имя без различия
в реестре — `Icon`/`resolveIcon` не различают, вызвана ли иконка как бизнес-иконка данных или как иконка пункта
навигации, им обеим соответствует один и тот же компонент Lucide. Заводить новую запись в `UI_ICONS` (например,
дублирующую иконку кошелька под другим именем) не нужно: это не нарушает `icons.sync.test.ts` (тест сверяет
`BUSINESS_ICON_NAMES` с backend `icons.json`, `navItems` не входит в эту сверку) и не создаёт двух источников
правды для одной и той же кнопки.

```ts
// app/navItems.ts — вставляется вторым пунктом: после «Главная», перед «Настройки».
// «Настройки» остаётся последним пунктом (обычная практика мобильной навигации) — 016/018 при добавлении своих
// пунктов («Операции», «Аналитика») тоже вставляют их перед «Настройки», не после.
{ key: "wallets", path: "/wallets", label: "Кошельки", icon: "wallet" },
```

```tsx
// app/routes.tsx — новый дочерний маршрут внутри уже существующего RequireAuth-поддерева
{ path: "wallets", element: <WalletsPage /> },
```

`WalletsPage` рендерится прямо внутри `AppLayout`/`MobileShell`/`DesktopShell` без дополнительного обёрточного
`div`/`maxWidth`: `DesktopShell` уже ограничивает ширину контента (`Layout.Content`, `maxWidth: 960`), а
`MobileShell` — на всю ширину. Тот же принцип, что уже применяет `SettingsPage` (в отличие от `RegisterPage`,
которая — отдельный экран до авторизации с собственной обёрткой `maxWidth: 360`).

## Risks / Trade-offs

- [`currencyCodes` карточки может кратко показывать пустой список чипов, пока `useCurrencies` ещё не ответил] →
  риск минимален: тот же `queryKey`, что и у `CurrencyPicker`, обычно уже прогрет в приложении; если нет — чипы
  появляются сразу после ответа без перезагрузки страницы (реактивное обновление `useQuery`).
- [Один `<WalletForm>` на странице вместо формы на карточку — сложнее API компонента (проп `wallet?`), чем если
  бы каждая карточка открывала свою форму] → выбрано осознанно, чтобы исключить одновременное открытие
  нескольких `Drawer`/`Modal`; сложность компенсируется тем, что состояние формы — один `useState` на странице.
- [Отсутствие `onError` у `useDeleteWallet` означает, что 409 и любая другая ошибка удаления показываются только
  общим текстом из `MESSAGE_BUILDERS`] → это осознанное решение постановки задачи: `conflict` уже показывает
  `error.detail` backend, специального UI не требуется; если в будущем понадобится, например, предложить
  пользователю перейти к операциям кошелька прямо из сообщения об ошибке — это станет поводом для отдельного
  `onError`, не предусмотренного сейчас (YAGNI).
- [`Wallet` не мапится в camelCase, в отличие от `Currency`] → см. обоснование в разделе «Decisions»; риск
  рассинхронизации есть только если backend когда-нибудь переименует поля `WalletOut` — тогда потребуется точечная
  правка типа `Wallet`, как и сейчас потребовалась бы правка `CurrencyDto` при изменении `CurrencyOut`.

## Migration Plan

Backend, база данных и миграции Alembic **не меняются** — используется уже готовый и заархивированный API
`wallets` (008) без изменений контракта. Изменение затрагивает только новые файлы внутри
`frontend/src/features/wallets/` и точечные правки `frontend/src/app/navItems.ts`/`frontend/src/app/routes.tsx`
(добавление пункта/маршрута, без удаления существующих). Разворачивания/отката на уровне инфраструктуры не
требуется — обычный деплой frontend-сборки. Существующие разделы (`health`, `settings`, `auth`) не трогаются,
риска регресса уже работающих разделов нет.

## Open Questions

Нет — все решения по объёму и границам приняты оркестратором в `docs/tasks/014_frontend_wallets.md`; сигнатуры и
механика реализации, включая решения, не зафиксированные явно в постановке (маппинг `Wallet`, владение мутацией
удаления в `WalletCard`, единая форма на странице), зафиксированы и обоснованы в разделе «Decisions» выше.
