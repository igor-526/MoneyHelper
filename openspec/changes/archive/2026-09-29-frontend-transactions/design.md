## Context

Backend-капабилити `transactions` (010, доработана в 011 до ногозависимой формы) и три frontend-фундамента уже
реализованы и заархивированы: `frontend-shell` (013, `CurrencyPicker`, `IconPicker`, `MoneyInput`, `EmptyState`,
тип `Page<T>`, `useIsMobile`), `frontend-wallets` (014, кошельки: карточки + единая форма create/update +
удаление `Popconfirm` + hooks TanStack Query), `frontend-categories` (015, категории: та же архитектура плюс
фильтр по типу и field-level 409 на дубль имени). Эта задача комбинирует кирпичи всех трёх и добавляет то, чего
раньше не было ни в одном frontend-экране, — реальную серверную пагинацию, потому что список операций
потенциально растёт без ограничения (в отличие от справочных по объёму кошельков/категорий/валют).

Backend-контракт (`backend/src/api/schemas/transaction.py`, `backend/src/api/transactions.py`,
`backend/src/api/schemas/balance.py`, `backend/src/api/balances.py`):
`POST /api/transactions` → 201 `TransactionOut`; `GET /api/transactions` → `Page[TransactionOut]`
(`TransactionListParams` — `PageParams` плюс опциональные `wallet_id`, `category_id`, `type`, `date_from`,
`date_to`), сортировка `occurred_at DESC, id DESC` уже на backend; `GET /api/transactions/{id}` → `TransactionOut`;
`PUT /api/transactions/{id}` → `TransactionOut` (та же валидация тела, что и `POST`, `TransactionUpdate =
TransactionCreate` — только полная замена ровно одной ноги); `DELETE /api/transactions/{id}` → 204.
`TransactionCreate`/`TransactionUpdate`: `wallet_id`, `category_id`, `currency_id` (`UUID`), `amount` (`Money`,
`gt=0`, сериализуется JSON-строкой), `occurred_at` (`datetime | None`, backend подставляет текущее время сервера,
если не передан). `TransactionOut` дополнительно: `id`, `legs: [{currency_id, amount}]` (ровно один элемент для
операций, созданных этой формой — эндпоинт `/topups` с несколькими ногами создаёт отдельная задача 017, вне рамок
здесь), `created_at`, `updated_at`. `GET /api/wallets/{wallet_id}/balances` → `list[WalletBalanceOut]`
(`{currency_id, balance}`) по всем валютам кошелька, включая нулевые, без кэша на backend.

Все решения по объёму и границам этой задачи уже приняты оркестратором в
`docs/tasks/016_frontend_transactions.md` и не пересматриваются здесь; этот документ фиксирует точные сигнатуры и
механику реализации, по образцу `design.md` изменений `frontend-wallets`/`frontend-categories`.

## Goals / Non-Goals

**Goals:**
- Лента операций карточками (кошелёк, категория с индикатором типа, сумма+валюта, дата) с РЕАЛЬНОЙ серверной
  пагинацией (`antd Pagination`, размер страницы 20 — как `PageParams` на backend) и фильтрами (кошелёк, категория,
  тип, диапазон дат), каждый фильтр и смена страницы — часть `queryKey`; смена любого фильтра сбрасывает
  пагинацию на первую страницу.
- Один компонент `TransactionForm` для создания и редактирования: кошелёк → тип-переключатель (только сужает
  список категорий, не отправляется в теле) → категория → валюта (ограничена набором кошелька через новый проп
  `CurrencyPicker.allowedIds`) → сумма (`MoneyInput`, знаки — из валюты) → дата (необязательна).
- Обратно совместимое расширение `CurrencyPicker` новым опциональным пропом `allowedIds?: string[]`.
- Карточка баланса выбранного кошелька по валютам (`useWalletBalances`), видимая только при конкретном фильтре
  «кошелёк».
- Удаление с подтверждением через `Popconfirm`, без специальной обработки 409 (операции ничто не блокирует
  удалять), по образцу `useDeleteWallet`/`useDeleteCategory` — для единообразия и на случай будущих правил.
- Обработка ошибок отправки — существующий паттерн `kind === "validation"` → `applyFieldErrors` + toast, без новых
  веток для бизнес-правил backend.
- Три мутации инвалидируют кэш операций и кэш балансов кошелька по префиксу.
- Точка входа — пункт `navItems` «Операции» (`/transactions`) между «Кошельки» и «Настройки», маршрут под
  `RequireAuth`.
- Всё покрыто тестами (`FakeApiClient`), по mobile-first правилам AGENTS.md.

**Non-Goals:**
- Пополнения с несколькими ногами и переводы между кошельками — задача 017.
- Отображение нескольких ног в карточке операции — задел на 017 (здесь единственный случай — ровно одна нога).
- Баланс по всем кошелькам сразу — backend не даёт единого запроса; при «Все кошельки» карточка не показывается.
- Отдельные маршруты для форм создания/редактирования.
- Переиспользуемый `shared/ui`-компонент выбора кошелька — только один потребитель в этой задаче.
- Специальная обработка бизнес-правил backend (валюта не из набора кошелька, превышение знаков, неположительная
  сумма) — покрыта существующим общим механизмом без изменений.
- Синхронизация фильтров списка с URL (`useSearchParams`) — фильтры и пагинация живут в локальном состоянии
  `TransactionsPage`, как и фильтр категорий (015); постановка задачи URL-параметры не требует.

## Decisions

### Структура файлов

```
frontend/src/features/transactions/
  Transaction.ts                    # тип Transaction, TransactionLeg, TransactionFormValues, WalletBalance
  useTransactions.ts                # useQuery(GET /api/transactions?...), TRANSACTIONS_QUERY_KEY
  useTransactions.test.ts
  useCreateTransaction.ts
  useCreateTransaction.test.ts
  useUpdateTransaction.ts
  useUpdateTransaction.test.ts
  useDeleteTransaction.ts
  useDeleteTransaction.test.ts
  useWalletBalances.ts              # useQuery(GET /api/wallets/{id}/balances), WALLET_BALANCES_QUERY_KEY
  useWalletBalances.test.ts
  TransactionForm.tsx
  TransactionForm.test.tsx
  TransactionCard.tsx
  TransactionCard.test.tsx
  WalletBalanceCard.tsx             # карточка баланса выбранного кошелька по валютам
  WalletBalanceCard.test.tsx
  TransactionsPage.tsx              # фильтры, пагинация, сборка списка, состояние формы, карточка баланса
  TransactionsPage.test.tsx
```

Каждый hook — отдельный файл с тестом рядом (по образцу `features/wallets`/`features/categories`) — SOLID S.
`WalletBalanceCard` вынесен отдельным компонентом (а не инлайном в `TransactionsPage`) — своя ответственность
(показ баланса), собственный тест, `TransactionsPage` не разрастается.

### `CurrencyPicker` — расширение `allowedIds?: string[]`

```ts
interface CurrencyPickerBaseProps {
  placeholder?: string;
  disabled?: boolean;
  /** Ограничивает список опций переданными id валют. При отсутствии — список полный (текущее поведение). */
  allowedIds?: string[];
}
```

Реализация: `const currencies = allData.filter((c) => props.allowedIds === undefined || props.allowedIds.includes(c.id))`,
дальше построение `options` не меняется. Это **безопасное расширение, а не поломка контракта**: новый проп
опционален, отсутствие пропа не меняет поведение ни для одного существующего потребителя (`WalletForm` проп не
передаёт и продолжает получать полный список), фильтрация — чистая проекция уже загруженных данных
`useCurrencies()`, без изменения источника данных, режима загрузки/ошибки или формы `value`/`onChange` в обоих
вариантах (`multiple`/одиночный). Именно поэтому это оформлено как `## MODIFIED Requirements` капабилити
`frontend-shell` в specs (полный текст требования «Выбор валюты — `CurrencyPicker`» скопирован из
`openspec/specs/frontend-shell/spec.md` и дополнен новым сценарием), а не как новое требование в
`frontend-transactions`: сам компонент и его контракт принадлежат `frontend-shell`, эта задача лишь расширяет его
поведение — тот же принцип, по которому меняется существующий, а не заводится параллельный компонент.

### `Transaction`, `TransactionLeg`, `WalletBalance` — без camelCase-маппинга

```ts
/** Форма ответа backend (`TransactionLegOut`). */
export interface TransactionLeg {
  currency_id: string;
  amount: string;
}

/**
 * Форма ответа backend (`TransactionOut`) — без camelCase-маппинга, тот же принцип, что и `Wallet`/`Category`
 * (design.md 014/015). Ногозависимая: `legs` — массив из одного элемента для операций, созданных этой формой
 * (см. Non-Goals); карточка/форма всегда работают с `transaction.legs[0]`.
 */
export interface Transaction {
  id: string;
  wallet_id: string;
  category_id: string;
  legs: TransactionLeg[];
  occurred_at: string;
  created_at: string;
  updated_at: string | null;
}

/** Тело запроса `TransactionCreate`/`TransactionUpdate`. `type` НЕ входит — backend его не принимает. */
export interface TransactionFormValues {
  wallet_id: string;
  category_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: string;
}

/** Форма элемента ответа backend (`WalletBalanceOut`). */
export interface WalletBalance {
  currency_id: string;
  balance: string;
}
```

### `TRANSACTIONS_QUERY_KEY`, `transactionsQueryKey(...)` и `useTransactions(filters, pagination)`

```ts
export const TRANSACTIONS_QUERY_KEY = ["transactions"] as const;
export const DEFAULT_PAGE_SIZE = 20;

export interface TransactionFilters {
  walletId?: string;
  categoryId?: string;
  type?: CategoryType;
  dateFrom?: string; // ISO, начало выбранного дня
  dateTo?: string;   // ISO, конец выбранного дня
}

interface Pagination {
  offset: number;
  limit: number;
}

function transactionsQueryKey(filters: TransactionFilters, pagination: Pagination) {
  return [...TRANSACTIONS_QUERY_KEY, { ...filters, ...pagination }] as const;
}

/** В отличие от useWallets/useCategories — список растёт без ограничения, поэтому реальная серверная пагинация. */
export function useTransactions(filters: TransactionFilters, pagination: Pagination) {
  const api = useApiClient();
  return useQuery({
    queryKey: transactionsQueryKey(filters, pagination),
    queryFn: ({ signal }) =>
      api.get<Page<Transaction>>("/api/transactions", {
        query: {
          wallet_id: filters.walletId,
          category_id: filters.categoryId,
          type: filters.type,
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          limit: pagination.limit,
          offset: pagination.offset,
        },
        signal,
      }),
  });
}
```

`useTransactions` возвращает **весь `Page<Transaction>`**, а не только `items` (в отличие от `useWallets`/
`useCategories`, где `total`/`limit`/`offset` не нужны потребителю) — `TransactionsPage` использует `total` для
`antd Pagination`. `undefined`-поля объекта `query` не попадают в query-строку (`FetchApiClient.buildUrl`), так что
незаданные фильтры не отправляются, backend отдаёт неотфильтрованный (по этому измерению) список.

`queryKey` третьим элементом содержит объединённый объект `{ walletId, categoryId, type, dateFrom, dateTo, offset,
limit }` — ровно то, что указано в постановке задачи (пункт 8): TanStack Query сравнивает объекты в `queryKey`
структурно, поэтому каждая уникальная комбинация фильтров и страницы кешируется отдельно, а инвалидация по
префиксу `TRANSACTIONS_QUERY_KEY` (без уточнения) обновляет все варианты разом.

### Три мутации

```ts
export function useCreateTransaction() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: TransactionFormValues) => api.post<Transaction>("/api/transactions", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSACTIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
// useUpdateTransaction — та же форма, что useUpdateWallet: вход { id, values }, PUT /api/transactions/{id},
// та же двойная инвалидация.

/** Без meta.silent и без onError — 409 у операций не возникает, но паттерн useDeleteWallet/useDeleteCategory
 *  сохранён для единообразия и на случай будущих правил (постановка задачи, пункт 5). */
export function useDeleteTransaction() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<undefined>(`/api/transactions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSACTIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
```

Инвалидация балансов вместе с операциями — любое создание/изменение/удаление операции меняет сумму хотя бы одной
валюты хотя бы одного кошелька (баланс вычисляется backend на лету по операциям и переводам, без кэша); связывать
эти два кэша в каждой из трёх мутаций дешевле и надёжнее, чем полагаться на ручное обновление каждого экрана,
который показывает баланс, и не требует знать, какой именно кошелёк затронут, — `WALLET_BALANCES_QUERY_KEY` без
уточнения `walletId` инвалидирует все варианты сразу (тот же принцип префиксной инвалидации, что и у самого списка
операций).

### `useWalletBalances(walletId)`

```ts
export const WALLET_BALANCES_QUERY_KEY = ["wallet-balances"] as const;

/** enabled: false при отсутствующем walletId — карточка баланса не показывается при фильтре «Все кошельки». */
export function useWalletBalances(walletId: string | undefined) {
  const api = useApiClient();
  return useQuery({
    queryKey: [...WALLET_BALANCES_QUERY_KEY, walletId],
    queryFn: ({ signal }) => api.get<WalletBalance[]>(`/api/wallets/${walletId}/balances`, { signal }),
    enabled: walletId !== undefined,
  });
}
```

### `TransactionForm` — один компонент, тип-переключатель локален и не отправляется

```ts
export interface TransactionFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданная `Transaction` — форма редактирования. */
  transaction?: Transaction;
}

/** Внутренние поля antd Form: occurred_at — Dayjs (не строка), тип — НЕ поле Form (локальный useState). */
interface TransactionFormFields {
  wallet_id: string;
  category_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: Dayjs;
}

const KNOWN_FIELDS = ["wallet_id", "category_id", "currency_id", "amount", "occurred_at"] as const;
```

Тип-переключатель (`Segmented`, «Доход»/«Расход») — `const [type, setType] = useState<CategoryType>("income")`,
**вне** antd `Form`: он не входит в тело запроса (backend не принимает отдельное поле типа — тип определяется
исключительно `category_id`), только сужает опции `Select` категории через `useCategories(type)`. Отдельный
`useCategories(undefined)` (полный список, кешируется отдельным ключом `["categories", "all"]`, как уже
предусмотрено `useCategories` из 015) используется для поиска типа текущей категории при открытии формы на
редактирование — без него нельзя вычислить начальное значение переключателя по `transaction.category_id`.

```ts
useEffect(() => {
  if (!open) return;
  if (transaction) {
    const currentCategory = allCategories.find((c) => c.id === transaction.category_id);
    setType(currentCategory?.type ?? "income");
    form.setFieldsValue({
      wallet_id: transaction.wallet_id,
      category_id: transaction.category_id,
      currency_id: transaction.legs[0].currency_id,
      amount: transaction.legs[0].amount,
      occurred_at: dayjs(transaction.occurred_at),
    });
  } else {
    setType("income");
    form.setFieldsValue({
      wallet_id: undefined,
      category_id: undefined,
      currency_id: undefined,
      amount: "",
      occurred_at: undefined,
    });
  }
}, [open, transaction, allCategories, form]);
```

Переключение `Segmented` пользователем сбрасывает `category_id` (`onChange={(value) => { setType(value);
form.setFieldValue("category_id", undefined); }}`) — прежде выбранная категория могла не принадлежать новому типу.
Аналогично выбор кошелька (`wallet_id` `Select`, простой, без переиспользуемого пикера — см. Non-Goals) сбрасывает
`currency_id` (`onChange={(value) => { form.setFieldsValue({ wallet_id: value, currency_id: undefined }); }}`) —
прежде выбранная валюта могла не входить в набор нового кошелька.

Поля формы:
- `wallet_id` — `Select` из `useWallets()` (`options: wallets.map(w => ({ value: w.id, label: w.name }))`).
- `category_id` — `Select` из `useCategories(type)`.
- `currency_id` — `CurrencyPicker` с `allowedIds={selectedWallet?.currency_ids}` (`selectedWallet` — найден в
  `useWallets()` по текущему `wallet_id` формы); если кошелёк ещё не выбран, `allowedIds` не передаётся (полный
  список валют, но `wallet_id` обязателен раньше по порядку полей — пользователь естественно выбирает сначала
  кошелёк).
- `amount` — `MoneyInput` с `decimalPlaces={currencyById.get(currency_id)?.decimalPlaces}` (`currencyById` —
  `Map` из `useCurrencies()`, тот же приём, что уже применён в `WalletsPage`).
- `occurred_at` — antd `DatePicker showTime`, не обязателен.

Отправка (`handleSubmit(fields: TransactionFormFields)`):
```ts
const payload: TransactionFormValues = {
  wallet_id: fields.wallet_id,
  category_id: fields.category_id,
  currency_id: fields.currency_id,
  amount: fields.amount,
  occurred_at: fields.occurred_at?.toISOString(),
};
```
`type` в `payload` отсутствует — он никогда не был полем `Form`, поэтому в `fields` его нет.

Обработка ошибок — буквально `WalletForm` (не `CategoryForm`: конфликтов 409 у операций нет, см. Non-Goals):
```ts
const onError = (submitError: unknown) => {
  const apiError = toApiError(submitError);
  if (apiError.kind === "validation") {
    const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
    for (const [name, errors] of Object.entries(byField)) {
      form.setFields([{ name: name as keyof TransactionFormFields, errors }]);
    }
    toast.error(toastMessage);
    return;
  }
  toast.error(resolveErrorMessage(apiError));
};
```

**Почему специальная обработка бизнес-правил backend не нужна**: `parseApiError` (`shared/api/parseApiError.ts`)
превращает и per-field ошибки Pydantic (`detail` — массив `{loc, msg}`), и обычные `ClientError` с текстовым
`detail` (например «Валюта операции не входит в набор валют кошелька», «Сумма превышает допустимое число знаков
после запятой для этой валюты») в `ApiError` с `kind: "validation"` — в первом случае с заполненным `fieldErrors`,
во втором — с пустым `fieldErrors` и непустым `detail`. `applyFieldErrors` уже обрабатывает оба случая одинаково:
известные поля (`byField`) уходят в `form.setFields`, а всё, что не привязано к конкретному известному полю
(включая целиком текстовый `detail` бизнес-правила), попадает в `rest` → `toastMessage` («Проверьте заполнение
формы: <текст правила>»). Пользователь видит текст ошибки backend как есть, без специального кода для конкретных
правил — тот же самый путь `kind === "validation"` → `applyFieldErrors`, что уже используется в `WalletForm`/
`CategoryForm` для обычных ошибок по полям. Заводить отдельную ветку `if (apiError.detail.includes("валюта"))` или
подобную было бы дублированием уже работающего общего механизма и нарушением SOLID O (расширение через `if` вместо
уже существующей точки расширения).

Контейнер — `Drawer`/`Modal` по `useIsMobile()`, буквально по образцу `WalletForm`/`CategoryForm`.

### `TransactionCard` — резолвит отображаемые данные из пропов, сама владеет удалением

```ts
export interface TransactionCardProps {
  transaction: Transaction;
  walletName: string | undefined;
  category: { name: string; icon: string; type: CategoryType } | undefined;
  currencyCode: string | undefined;
  onEdit: (transaction: Transaction) => void;
}

const TYPE_TAG: Record<CategoryType, { label: string; color: "success" | "error" }> = {
  income: { label: "Доход", color: "success" },
  expense: { label: "Расход", color: "error" },
};
```

`walletName`/`category`/`currencyCode` вычисляются родителем (`TransactionsPage`) через `Map` из уже загруженных
`useWallets()`/`useCategories(undefined)`/`useCurrencies()` — тот же приём, что `WalletsPage` уже применяет для
кодов валют кошелька; `TransactionCard` не делает собственных дополнительных запросов на резолюцию (только
`useDeleteTransaction()` для удаления, по образцу `WalletCard`/`CategoryCard`). `TYPE_TAG` — локальная копия
таблицы из `CategoryCard` (015), не импорт из `features/categories`: в проекте нет прецедента импорта одной
фичи из другой (`features/<feature>` самодостаточны, `app` → `features` → `shared`), а сама таблица — три строки
без логики, дублирование дешевле кросс-фичевой связанности. Рендер — `Card`: строка кошелька, строка
`Icon(category.icon)` + название категории + `Tag` типа, строка суммы (`transaction.legs[0].amount`) + код валюты,
дата (`occurred_at`, отформатированная через `dayjs`), кнопки «Редактировать»/«Удалить» под `Popconfirm`, буквально
по образцу `WalletCard`/`CategoryCard`.

### `WalletBalanceCard` — баланс кошелька по валютам

```ts
export interface WalletBalanceCardProps {
  walletId: string;
  /** Map id → код валюты, из уже загруженного useCurrencies() (та же техника, что и в TransactionCard). */
  currencyCodeById: Map<string, string>;
}
```

Вызывает `useWalletBalances(walletId)` сама (единственный потребитель, владение данными внутри компонента —
аналогично тому, как `WalletCard`/`CategoryCard` владеют своей мутацией удаления); рендерит `Card` со списком
`{code}: {balance}` по каждому элементу ответа (включая нулевые балансы — backend их не исключает). Состояние
загрузки — `Spin` внутри карточки; ошибка загрузки — карточка не рендерится, ошибка уходит в глобальный toast (без
`meta.silent`, как и `useWallets`/`useCategories`).

### `TransactionsPage` — фильтры, пагинация, сборка списка, карточка баланса

```ts
const ALL_WALLETS = "all";
const ALL_CATEGORIES = "all";
type TypeFilter = "all" | CategoryType;

interface FiltersState {
  walletId: string | undefined;      // undefined = «Все кошельки»
  categoryId: string | undefined;    // undefined = «Все категории»
  type: TypeFilter;                  // "all" = без фильтра
  dateRange: [Dayjs, Dayjs] | null;  // null = без фильтра
}

export function TransactionsPage() {
  const [filters, setFilters] = useState<FiltersState>({
    walletId: undefined,
    categoryId: undefined,
    type: "all",
    dateRange: null,
  });
  const [page, setPage] = useState(1); // 1-based, antd Pagination

  const dateFrom = filters.dateRange?.[0].startOf("day").toISOString();
  const dateTo = filters.dateRange?.[1].endOf("day").toISOString();
  const offset = (page - 1) * DEFAULT_PAGE_SIZE;

  const transactionsQuery = useTransactions(
    {
      walletId: filters.walletId,
      categoryId: filters.categoryId,
      type: filters.type === "all" ? undefined : filters.type,
      dateFrom,
      dateTo,
    },
    { offset, limit: DEFAULT_PAGE_SIZE },
  );

  const updateFilters = (patch: Partial<FiltersState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1); // любая смена фильтра сбрасывает пагинацию на первую страницу
  };
  // ...
}
```

Элементы `Select` фильтров «Кошелёк»/«Категория» используют сентинел-значения `ALL_WALLETS`/`ALL_CATEGORIES`
(строка `"all"`) как первую опцию — antd `Select` работает со `value`, а не с `undefined` в списке опций;
обработчик `onChange` превращает сентинел обратно в `undefined` перед `updateFilters`. Фильтр «Тип» — `Segmented`
с тремя опциями («Все»/«Доход»/«Расход», по образцу `FILTER_OPTIONS` из `CategoriesPage`, 015 — та же локальная
таблица, не импорт: то же обоснование, что и у `TYPE_TAG`). Диапазон дат — antd `RangePicker` (без времени в UI,
`picker="date"`), `value={filters.dateRange}`, `onChange={(range) => updateFilters({ dateRange: range })}`.

Фильтры **не синхронизируются с URL** (`useSearchParams`) — состояние живёт локально в `TransactionsPage` и
сбрасывается при уходе с экрана, тот же принцип, что и у фильтра типа в `CategoriesPage` (015); постановка задачи
не требует сохранения фильтров между переходами или ссылки на конкретный отфильтрованный вид, поэтому `RangePicker`
и остальные фильтры всегда стартуют пустыми при повторном открытии `/transactions` — глубокая ссылка с
предзаполненными фильтрами вне рамок.

Карточка баланса (`WalletBalanceCard`) рендерится только когда `filters.walletId !== undefined`
(«Все кошельки» → карточка не рендерится вовсе, hook не вызывается за счёт `enabled` внутри `useWalletBalances`,
условный рендер в `TransactionsPage` дополнительно исключает лишний элемент DOM).

Список карточек — `transactionsQuery.data.items.map(...)`, каждой передаются резолвленные `walletName`/
`category`/`currencyCode` через `Map`, построенные из `useWallets()`/`useCategories(undefined)`/`useCurrencies()`
(`useMemo`, тот же приём, что и `currencyById` в `WalletsPage`). Порядок — как отдаёт backend (`occurred_at DESC,
id DESC`), без клиентской пересортировки. Пагинация — `antd Pagination` под списком: `current={page}`,
`pageSize={DEFAULT_PAGE_SIZE}`, `total={transactionsQuery.data?.total ?? 0}`, `onChange={setPage}`, без селектора
размера страницы (размер фиксирован постановкой задачи).

Пустое состояние (`EmptyState`, по образцу `WalletsPage`/`CategoriesPage`) показывается, когда
`transactionsQuery.data.items.length === 0` — единый текст независимо от того, пуст ли список вообще или пуст
только текущий отфильтрованный/отстраниченный срез (differentiation между «операций нет вообще» и «нет операций по
фильтру» не требуется постановкой задачи; фильтры остаются видимыми и доступными, тот же принцип, что и у
`Segmented` в `CategoriesPage`).

### Навигация: `navItems` и маршрут

```ts
// app/navItems.ts
export const navItems: readonly NavItem[] = [
  { key: "home", path: "/", label: "Главная", icon: "house" },
  { key: "wallets", path: "/wallets", label: "Кошельки", icon: "wallet" },
  { key: "transactions", path: "/transactions", label: "Операции", icon: "banknote" },
  { key: "settings", path: "/settings", label: "Настройки", icon: "settings" },
];
```

Иконка `"banknote"` уже существует в закрытом реестре `shared/ui/icons.ts` (`BUSINESS_ICONS`, синхронизирован с
`backend/src/core/icons.json`, 013) — тот же приём, что уже применён для пункта «Кошельки» (`icon: "wallet"`,
тоже бизнес-иконка): `resolveIcon`/`ICONS` объединяют `BUSINESS_ICONS` и `UI_ICONS` в одну карту, поэтому нет
разницы, из какого из двух наборов взято имя для `navItems`. Реестр иконок этой задачей не расширяется (решение
зафиксировано для кошельков/категорий в 013 и не пересматривается здесь).

```tsx
// app/routes.tsx — внутри существующего RequireAuth-поддерева
{ path: "transactions", element: <TransactionsPage /> },
```

Порядок пункта `navItems` — четвёртый из пяти (Главная, Кошельки, Операции, Настройки — бюджет 013 позволяет ещё
один пункт для «Аналитики», 018), как зафиксировано в постановке задачи.

## Risks / Trade-offs

- [`allowedIds` фильтрует уже загруженный список валют на клиенте, не делает отдельный запрос] → если справочник
  валют вырастет на порядки, фильтрация останется дешёвой (`Array.filter` по id), а `useCurrencies()` и так
  загружается одним запросом с `limit=100` — риска производительности нет при текущем и обозримом объёме
  справочника.
- [Фильтры `TransactionsPage` не синхронизированы с URL] → пользователь теряет отфильтрованный вид при обновлении
  страницы или переходе назад/вперёд; риск принят осознанно (см. «Decisions») — постановка задачи не требует
  глубоких ссылок, а фильтр категорий (015) уже установил этот же прецедент.
- [Двойная инвалидация `["transactions"]` + `["wallet-balances"]` в каждой из трёх мутаций] → на телефоне с
  медленной сетью после каждой мутации перезапросятся все смонтированные варианты обоих кэшей; риск минимален —
  TanStack Query перезапрашивает только уже наблюдаемые запросы, а экран операций и так активен в момент мутации.
- [`TransactionCard` дублирует `TYPE_TAG`/`FILTER_OPTIONS`-подобные локальные таблицы вместо импорта из
  `features/categories`] → небольшое дублирование трёх строк кода; оправдано отсутствием прецедента кросс-фичевых
  импортов в проекте (`features/<feature>` самодостаточны по структуре AGENTS.md) — избежание связанности важнее
  трёх повторяющихся строк.
- [Реальная серверная пагинация — первый прецедент в frontend] → чуть больше состояния на странице (`page` плюс
  фильтры вместо одного фильтра), чем у справочных экранов; оправдано прямым требованием постановки задачи
  («Объём», пункт «пагинация»); тестами покрываются переключение страницы и сброс на смену фильтра.

## Migration Plan

Backend, база данных и миграции Alembic **не меняются** — используется уже готовый и заархивированный API
`transactions`/`balances` (010, 011) без изменений контракта. Изменение затрагивает только новые файлы внутри
`frontend/src/features/transactions/` и точечные правки `frontend/src/app/navItems.ts` (новый пункт), `frontend/
src/app/routes.tsx` (новый маршрут) и `frontend/src/shared/ui/CurrencyPicker/CurrencyPicker.tsx` (новый опциональный
проп `allowedIds`, обратно совместимо — существующий потребитель `WalletForm` не меняется и не требует правок).
Разворачивания/отката на уровне инфраструктуры не требуется — обычный деплой frontend-сборки. Существующие разделы
(`wallets`, `categories`, `health`, `settings`, `auth`) не трогаются, риска регресса уже работающих разделов нет,
кроме нового сценария теста `CurrencyPicker` на `allowedIds` (существующие сценарии не меняются).

## Open Questions

Нет — все решения по объёму и границам приняты оркестратором в `docs/tasks/016_frontend_transactions.md`; точные
сигнатуры и механика реализации, включая решения, не зафиксированные явно в постановке (структура `queryKey`
списка, сентинел-значения фильтров «Все», отсутствие синхронизации фильтров с URL, оформление расширения
`CurrencyPicker` как `MODIFIED Requirements` капабилити `frontend-shell`, вынос `WalletBalanceCard` отдельным
компонентом, дублирование `TYPE_TAG` вместо кросс-фичевого импорта, конкретная иконка пункта навигации), зафиксированы
и обоснованы в разделе «Decisions» выше.
