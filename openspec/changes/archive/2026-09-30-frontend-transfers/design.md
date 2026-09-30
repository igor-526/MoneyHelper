## Context

Backend-капабилити `transfers` (011) уже реализована и заархивирована: `Transaction` стала ногозависимой
(`legs: list[TransactionLeg]`), появился статический маршрут `POST /api/transactions/topups` (регистрируется
раньше параметризованных `/{transaction_id}` — деталь backend, фронтенд просто вызывает готовый URL) и отдельная
сущность `Transfer` с полным CRUD `/api/transfers*` (`from_wallet_id`, `to_wallet_id`, `currency_id`, `amount`,
`occurred_at`; фильтры списка — только `wallet_id`/`date_from`/`date_to`, сортировка `occurred_at DESC` уже на
backend). Три frontend-фундамента, от которых зависит эта задача, — `frontend-shell` (013), `frontend-wallets`
(014), `frontend-categories` (015) — и прямая зависимость `frontend-transactions` (016) уже реализованы и
заархивированы.

Design.md изменения 016 явно фиксирует задел на эту задачу (раздел «Non-Goals»): «Пополнения с несколькими
ногами и переводы между кошельками — задача 017», «Отображение нескольких ног в карточке операции — задел на
017 (здесь единственный случай — ровно одна нога)». Тип `Transaction.legs` уже массив, `TransactionCard` (016)
уже устроен как компонент, резолвящий отображаемые данные из пропов, а не делающий собственные запросы — эта
задача продолжает ту же архитектуру, а не переписывает её.

Все решения по объёму и границам этой задачи уже приняты оркестратором в
`docs/tasks/017_frontend_topups_transfers.md` и не пересматриваются здесь; этот документ фиксирует точные
сигнатуры и механику реализации, по образцу `design.md` изменения `frontend-transactions` (016).

## Goals / Non-Goals

**Goals:**
- Пополнение многовалютного кошелька одной формой, строящей поля сумм динамически по числу валют выбранного
  кошелька (`TopupForm`, новый компонент внутри `features/transactions/`, не отдельная фича — пополнение создаёт
  ту же сущность `Transaction`).
- Отображение ВСЕХ ног операции в `TransactionCard` (закрывает задел 016) и блокировка редактирования многоногих
  операций (backend может заменить операцию по `PUT` только ровно одной ногой — редактирование через обычную
  форму молча схлопнуло бы пополнение до одной валюты).
- «Добавить»-меню на `TransactionsPage` из трёх пунктов вместо одной кнопки создания: доход/расход, пополнение,
  переход к переводам.
- Полноценный раздел переводов между собственными кошельками (`features/transfers/`) по образцу
  `features/wallets`/`features/categories`, с учётом отличий переводов (реальная серверная пагинация, как у
  `features/transactions`, поскольку список переводов тоже растёт без ограничения; валюта — пересечение наборов
  валют двух кошельков).
- Маршрут `/transfers` без пункта `navItems` — точка входа только со страницы «Операции».
- Всё покрыто тестами (`FakeApiClient`), по mobile-first правилам AGENTS.md.

**Non-Goals:**
- Конвертация валют внутри перевода — backend её не поддерживает (`TransferCreate.currency_id` — одна валюта).
- Редактирование пополнения на месте — только просмотр в списке и удаление; форма редактирования пополнения не
  делается (см. `## MODIFIED Requirements` капабилити `frontend-transactions` в specs).
- Отдельный пункт навигации (`navItems`) для переводов — бюджет нижней панели (5 пунктов) занят решением 013/016
  и зарезервирован под «Аналитику» (018).
- Подсказка/предпросмотр implied-курса между валютами пополнения по мере ввода сумм — не требуется постановкой
  задачи (открытый вопрос задачи 017, закрыт как «не делаем» — постановка задачи не требует).
- Расширение `CurrencyPicker` (013/016) — проп `allowedIds` уже есть, эта задача только использует его для
  пересечения валют двух кошельков, без изменений самого компонента.
- Переиспользуемый общий компонент выбора кошелька в `shared/ui` — тот же принцип YAGNI, что и в 016; и
  `TopupForm`, и `TransferForm` используют простой `Select` из `useWallets()`, как и `TransactionForm`.

## Decisions

### Структура файлов

```
frontend/src/features/transactions/         # расширение существующей фичи (016)
  TopupForm.tsx                              # новый
  TopupForm.test.tsx                         # новый
  useCreateTopup.ts                          # новый
  useCreateTopup.test.ts                     # новый
  TransactionCard.tsx                        # изменён: все ноги, блокировка редактирования
  TransactionCard.test.tsx                   # изменён
  TransactionsPage.tsx                       # изменён: «Добавить»-меню, ссылка «Переводы»
  TransactionsPage.test.tsx                  # изменён

frontend/src/features/transfers/             # новая фича
  Transfer.ts                                # тип Transfer, TransferFormValues
  useTransfers.ts / .test.ts                 # список, реальная серверная пагинация
  useCreateTransfer.ts / .test.ts
  useUpdateTransfer.ts / .test.ts
  useDeleteTransfer.ts / .test.ts
  TransferForm.tsx / .test.tsx               # create/update, пересечение валют
  TransferCard.tsx / .test.tsx
  TransfersPage.tsx / .test.tsx

frontend/src/app/routes.tsx                  # изменён: маршрут /transfers
```

Каждый hook — отдельный файл с тестом рядом (по образцу `features/wallets`/`features/categories`/
`features/transactions`) — SOLID S. `app/navItems.ts` не меняется (п. 6 постановки задачи).

### `TopupForm` и `useCreateTopup` — динамические поля сумм

```ts
// features/transactions/Transaction.ts — дополнение
/** Тело запроса `TopupCreate`. */
export interface TopupFormValues {
  wallet_id: string;
  category_id: string;
  legs: TransactionLeg[]; // { currency_id, amount }, порядок — wallet.currency_ids
  occurred_at?: string;
}
```

```ts
// features/transactions/useCreateTopup.ts
export function useCreateTopup() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: TopupFormValues) => api.post<Transaction>("/api/transactions/topups", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSACTIONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
```
Та же двойная инвалидация, что и у трёх мутаций операций (016) — пополнение меняет баланс кошелька. Импорт
`TRANSACTIONS_QUERY_KEY`/`WALLET_BALANCES_QUERY_KEY` — внутри одной фичи `features/transactions`, не
кросс-фичевый.

**Вложенные поля сумм.** `TopupForm` держит суммы в одном объектном поле `Form` `amounts`, адресуемом путём
`["amounts", currencyId]` (antd `Form` поддерживает вложенные пути имён как массив):

```ts
interface TopupFormFields {
  wallet_id: string;
  category_id: string;
  /** currency_id -> строка суммы; ключи — ровно currency_ids выбранного кошелька. */
  amounts: Record<string, string>;
  occurred_at?: Dayjs;
}

const KNOWN_FIELDS = ["wallet_id", "category_id"] as const;
```

Рендер полей сумм — цикл по `selectedWallet?.currency_ids ?? []` (`selectedWallet` — из `useWallets()` по
текущему `wallet_id` формы, тот же приём, что и в `TransactionForm`):
```tsx
{(selectedWallet?.currency_ids ?? []).map((currencyId) => {
  const currency = currencyById.get(currencyId);
  return (
    <Form.Item
      key={currencyId}
      name={["amounts", currencyId]}
      label={`Сумма (${currency?.code ?? "…"})`}
      rules={[{ required: true, message: "Введите сумму" }]}
    >
      <MoneyInput value="" onChange={() => {}} decimalPlaces={currency?.decimalPlaces} />
    </Form.Item>
  );
})}
```
Смена кошелька сбрасывает `amounts` целиком (тот же принцип, что сброс `currency_id` при смене кошелька в
`TransactionForm`, 016):
```ts
const handleWalletChange = (value: string) => {
  form.setFieldsValue({ wallet_id: value, amounts: {} });
};
```
Без выбранного кошелька (`selectedWallet === undefined`) полей сумм нет вовсе — пользователь обязан выбрать
кошелёк первым (тот же порядок полей, что и в `TransactionForm`).

**Сборка `legs` на отправке** — в порядке `wallet.currency_ids` (постановка задачи, п. 3):
```ts
const handleSubmit = (fields: TopupFormFields) => {
  const payload: TopupFormValues = {
    wallet_id: fields.wallet_id,
    category_id: fields.category_id,
    legs: (selectedWallet?.currency_ids ?? []).map((currencyId) => ({
      currency_id: currencyId,
      amount: fields.amounts[currencyId],
    })),
    occurred_at: fields.occurred_at?.toISOString(),
  };
  // ... createTopup.mutate(payload, { onSuccess, onError })
};
```
Категория — `Select` из `useCategories("income")` (только доходные, а не полный список с фильтром на клиенте —
тот же приём, что и `useCategories(type)` в `TransactionForm`, backend всё равно проверяет `category.type ===
"income"` для `/topups`). Дата — `DatePicker showTime`, необязательна, как в `TransactionForm`.

**Обработка ошибок — `KNOWN_FIELDS = ["wallet_id", "category_id"]`, осознанно узкий список.** Ошибки backend по
конкретным ногам (Pydantic `legs.0.amount` и подобные) и текстовые бизнес-правила («неполный/избыточный набор
валют пополнения», «категория не является доходной») не привязываются к конкретному динамическому полю суммы —
`applyFieldErrors(apiError, KNOWN_FIELDS)` относит любое поле, не входящее в `KNOWN_FIELDS`, в `rest` → toast
(текст вида «Проверьте заполнение формы: legs.0.amount: <текст>» или текст бизнес-правила как есть). Это то же
самое расширение существующего общего механизма, что уже применено в `TransactionForm` (016) для текстовых
бизнес-правил backend, только сознательно не пытающееся адресовать ошибку конкретному динамическому полю —
привязка `legs.{i}.amount` к конкретному `Form.Item` требовала бы парсить путь ошибки Pydantic и сопоставлять
индекс `i` с порядком `currency_ids`, что: (а) не покрыто существующим `applyFieldErrors` (он работает с плоским
именем поля, не с путём), (б) для формы, где поля сумм и так все видны одновременно на экране (в отличие от
многошаговых форм), не даёт пользователю дополнительной информации сверх текста в toast — пользователь и так
видит все суммы разом и может сопоставить текст ошибки с полями сам. Это осознанное ограничение объёма,
зафиксированное явно в постановке задачи (п. 3).

Контейнер — `Drawer` на телефоне / `Modal` на широком экране по `useIsMobile()`, буквально по образцу
`TransactionForm`/`WalletForm`.

### `TransactionCard` — отображение всех ног, блокировка редактирования

Прежний проп `currencyCode: string | undefined` (резолвленный родителем код валюты единственной ноги) заменяется
на `currencyCodeById: Map<string, string>` — карточка теперь сама резолвит код валюты каждой ноги, а не только
первой:

```ts
export interface TransactionCardProps {
  transaction: Transaction;
  walletName: string | undefined;
  category: { name: string; icon: string; type: CategoryType } | undefined;
  currencyCodeById: Map<string, string>;
  onEdit: (transaction: Transaction) => void;
}
```
Это минимальное изменение контракта (не расширение через новый опциональный проп, а замена, потому что
одиночного резолвленного кода уже недостаточно для отображения нескольких ног) — `TransactionsPage` и так уже
строит `currencyCodeById` через `useMemo` (016, «резолвит отображаемые данные из пропов»), поэтому родителю
достаточно передать уже существующую карту целиком вместо резолюции одного значения перед вызовом.

Рендер суммы:
```tsx
{transaction.legs.length === 1 ? (
  <Typography.Text>
    {transaction.legs[0].amount} {currencyCodeById.get(transaction.legs[0].currency_id) ?? "…"}
  </Typography.Text>
) : (
  <Flex vertical gap={4}>
    {transaction.legs.map((leg) => (
      <Typography.Text key={leg.currency_id}>
        {leg.amount} {currencyCodeById.get(leg.currency_id) ?? "…"}
      </Typography.Text>
    ))}
  </Flex>
)}
```

**Блокировка редактирования — `disabled`-кнопка под `Tooltip`, а не скрытая кнопка.** Кнопка «Редактировать»
остаётся на месте (не пропадает из раскладки карточки — стабильный layout между многоногими и одноногими
карточками), но получает `disabled` при `transaction.legs.length > 1`, оборачивается в `Tooltip` с текстом:

> «Пополнение с несколькими валютами нельзя редактировать — удалите и создайте заново»

```tsx
const isMultiLeg = transaction.legs.length > 1;
const editButton = (
  <Button disabled={isMultiLeg} onClick={() => onEdit(transaction)}>
    Редактировать
  </Button>
);

// antd Tooltip не всплывает над disabled-элементом без обёртки — стандартный приём antd.
{isMultiLeg ? (
  <Tooltip title="Пополнение с несколькими валютами нельзя редактировать — удалите и создайте заново">
    <span>{editButton}</span>
  </Tooltip>
) : (
  editButton
)}
```
Выбрано `disabled` + `Tooltip`, а не скрытие кнопки: скрытая кнопка меняла бы раскладку карточки (кнопки
«Редактировать»/«Удалить» в одном `Flex` ряду) в зависимости от числа ног и не объясняла бы пользователю, почему
действие недоступно, — он мог бы решить, что это баг. Видимая, но заблокированная кнопка с поясняющей
подсказкой — стандартный паттерн antd для «действие временно недоступно по бизнес-правилу», уже согласуется с
общим принципом AGENTS.md «hover не должен быть единственным способом доступа к действию» (`Tooltip` на
телефоне открывается по тапу на неактивную область — сама кнопка недоступна для тапа, но подсказка не является
единственным способом узнать причину: текст один и тот же независимо от способа взаимодействия, кнопка просто
не работает, что само по себе однозначный сигнал). Кнопка «Удалить» не меняется — остаётся доступной всегда
(постановка задачи, п. 4).

### «Добавить»-меню на `TransactionsPage`

Кнопка «Создать операцию» рядом со списком заменяется на antd `Dropdown` с триггером `Button` «Добавить» и тремя
пунктами меню:

```tsx
type CreateMenuKey = "transaction" | "topup" | "transfer";

const navigate = useNavigate();
const [transactionFormOpen, setTransactionFormOpen] = useState(false);
const [topupFormOpen, setTopupFormOpen] = useState(false);

const handleCreateMenuClick = ({ key }: { key: string }) => {
  const menuKey = key as CreateMenuKey;
  if (menuKey === "transaction") setTransactionFormOpen(true);
  else if (menuKey === "topup") setTopupFormOpen(true);
  else navigate("/transfers");
};

const createMenuItems = [
  { key: "transaction", label: "Доход/расход" },
  { key: "topup", label: "Пополнение" },
  { key: "transfer", label: "Перевод" },
];

<Dropdown menu={{ items: createMenuItems, onClick: handleCreateMenuClick }}>
  <Button type="primary">Добавить</Button>
</Dropdown>
```
Пункт «Перевод» не открывает форму на этой странице — навигация на `/transfers` (постановка задачи, п. 2: «форма
перевода живёт на странице `/transfers`, не инлайном на `TransactionsPage`»). Без иконки-шеврона на триггере —
реестр UI-иконок (`shared/ui/icons.ts`) не расширяется этой задачей, а текстовая кнопка «Добавить» без иконки
достаточно однозначна на mobile-first экране.

Пустое состояние (`EmptyState`, п. 6.3 016) продолжает открывать напрямую обычную форму операции
(`transaction`-действие), а не всё меню — самый частый случай создания при пустом списке — обычная операция;
заводить то же трёхпунктовое меню в двух местах экрана было бы дублированием, а `EmptyState.action` принимает
ровно один `onClick` (YAGNI, тот же принцип, что и в 016).

Рядом с заголовком «Операции» — ссылка «Переводы»:
```tsx
<Flex justify="space-between" align="center">
  <Typography.Title level={3} style={{ margin: 0 }}>Операции</Typography.Title>
  <Typography.Link onClick={() => navigate("/transfers")}>Переводы</Typography.Link>
</Flex>
```

`TransactionCard` теперь получает `currencyCodeById={currencyCodeById}` вместо резолвленного `currencyCode`
одной ноги (см. выше) — единственная правка вызова `TransactionCard` внутри списка `TransactionsPage`.

### `Transfer`, `TransferFormValues` — без camelCase-маппинга

```ts
// features/transfers/Transfer.ts
/** Форма ответа backend (`TransferOut`) — без camelCase-маппинга, тот же принцип, что и `Transaction`/`Wallet`.
 *  Плоская, не ногозависимая — у перевода всегда одна валюта. */
export interface Transfer {
  id: string;
  from_wallet_id: string;
  to_wallet_id: string;
  currency_id: string;
  amount: string;
  occurred_at: string;
  created_at: string;
  updated_at: string | null;
}

/** Тело запроса `TransferCreate`/`TransferUpdate`. */
export interface TransferFormValues {
  from_wallet_id: string;
  to_wallet_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: string;
}
```

### `useTransfers(filters, pagination)` — реальная серверная пагинация

```ts
// features/transfers/useTransfers.ts
export const TRANSFERS_QUERY_KEY = ["transfers"] as const;
export const DEFAULT_PAGE_SIZE = 20;

export interface TransferFilters {
  walletId?: string;
  dateFrom?: string;
  dateTo?: string;
}

interface Pagination {
  offset: number;
  limit: number;
}

function transfersQueryKey(filters: TransferFilters, pagination: Pagination) {
  return [...TRANSFERS_QUERY_KEY, { ...filters, ...pagination }] as const;
}

/** Список переводов растёт без ограничения (как список операций, 016) — реальная серверная пагинация. */
export function useTransfers(filters: TransferFilters, pagination: Pagination) {
  const api = useApiClient();
  return useQuery({
    queryKey: transfersQueryKey(filters, pagination),
    queryFn: ({ signal }) =>
      api.get<Page<Transfer>>("/api/transfers", {
        query: {
          wallet_id: filters.walletId,
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
Возвращает весь `Page<Transfer>` (не только `items`) — `total` нужен `TransfersPage` для `antd Pagination`, тот
же приём, что и `useTransactions` (016). `DEFAULT_PAGE_SIZE` определена локально в этой фиче (не импортируется
из `features/transactions`) — тот же принцип самодостаточности фичи, что и у дублированных таблиц `TYPE_TAG`/
`FILTER_OPTIONS` в 016 (`features/<feature>` не импортируют друг у друга даже тривиальные константы).

### Три мутации переводов — инвалидация балансов без кросс-фичевого импорта

```ts
// features/transfers/useCreateTransfer.ts (аналогично useUpdateTransfer/useDeleteTransfer)
/**
 * Локальная копия ключа кэша балансов — НЕ импорт `WALLET_BALANCES_QUERY_KEY` из `features/transactions`.
 * TanStack Query сравнивает queryKey структурно (по значению массива, не по ссылке на константу), поэтому
 * инвалидация по литералу ["wallet-balances"] достигает того же эффекта, что и импортированная константа, без
 * первого в проекте прецедента кросс-фичевого импорта (features/<feature> самодостаточны, AGENTS.md).
 */
const WALLET_BALANCES_QUERY_KEY = ["wallet-balances"] as const;

export function useCreateTransfer() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: TransferFormValues) => api.post<Transfer>("/api/transfers", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSFERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: WALLET_BALANCES_QUERY_KEY });
    },
  });
}
// useUpdateTransfer — вход { id, values }, PUT /api/transfers/{id}, та же двойная инвалидация.
// useDeleteTransfer — DELETE /api/transfers/{id}, без meta.silent/onError (по образцу useDeleteTransaction, 016).
```
Перевод меняет баланс ОБОИХ кошельков (исходного и целевого) — `WALLET_BALANCES_QUERY_KEY` без уточнения
`walletId` инвалидирует все закэшированные варианты сразу, тот же принцип префиксной инвалидации, что и в 016.

### `TransferForm` — пересечение валют, сброс зависимых полей

```ts
export interface TransferFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданный `Transfer` — форма редактирования. */
  transfer?: Transfer;
}

interface TransferFormFields {
  from_wallet_id: string;
  to_wallet_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: Dayjs;
}

const KNOWN_FIELDS = [
  "from_wallet_id",
  "to_wallet_id",
  "currency_id",
  "amount",
  "occurred_at",
] as const;
```

Целевой кошелёк исключает текущий исходный из своих опций (простая клиентская проверка, backend всё равно
провалидирует `from_wallet_id != to_wallet_id`):
```tsx
<Form.Item name="to_wallet_id" label="Куда" rules={[{ required: true, message: "Выберите кошелёк" }]}>
  <Select
    options={wallets
      .filter((wallet) => wallet.id !== fromWalletId)
      .map((wallet) => ({ value: wallet.id, label: wallet.name }))}
    onChange={handleToWalletChange}
  />
</Form.Item>
```

Пересечение валют — `useMemo` по выбранным кошелькам:
```ts
const fromWallet = wallets.find((wallet) => wallet.id === fromWalletId);
const toWallet = wallets.find((wallet) => wallet.id === toWalletId);

const commonCurrencyIds = useMemo(() => {
  if (!fromWallet || !toWallet) return undefined;
  return fromWallet.currency_ids.filter((id) => toWallet.currency_ids.includes(id));
}, [fromWallet, toWallet]);
```
Пока оба кошелька не выбраны, `commonCurrencyIds === undefined` → `CurrencyPicker` получает `allowedIds`
неопределённым (полный список валют, как и в `TransactionForm`/`TopupForm` до выбора кошелька — пользователь
естественно выбирает кошельки раньше по порядку полей). Когда оба выбраны и пересечение пусто, поле выбора
валюты заменяется предупреждающим текстом:

```tsx
{fromWallet && toWallet && commonCurrencyIds?.length === 0 ? (
  <Form.Item label="Валюта">
    <Typography.Text type="warning">У этих кошельков нет общей валюты</Typography.Text>
  </Form.Item>
) : (
  <Form.Item name="currency_id" label="Валюта" rules={[{ required: true, message: "Выберите валюту" }]}>
    <CurrencyPicker value={undefined} onChange={() => {}} allowedIds={commonCurrencyIds} />
  </Form.Item>
)}
```
Точный текст предупреждения — «У этих кошельков нет общей валюты» (постановка задачи, п. 5, буквально). Кнопка
отправки формы остаётся отключённой в этом состоянии естественным образом — antd `Form` не даёт отправить форму,
если обязательное поле `currency_id` не зарегистрировано текущим рендером (при замене `Form.Item` на предупреждение
поле `currency_id` не участвует в текущем дереве полей, и `handleSubmit` получит `fields.currency_id ===
undefined`); дополнительная явная блокировка кнопки не требуется — тот же эффект достигается декларативно через
условный рендер, без ручного отслеживания «валидна ли форма» отдельным `useState`.

Сброс зависимых полей:
```ts
const handleFromWalletChange = (value: string) => {
  const currentToWalletId = form.getFieldValue("to_wallet_id");
  form.setFieldsValue({
    from_wallet_id: value,
    // смена исходного кошелька, совпадающая с текущим целевым, сбрасывает целевой (постановка задачи, п. 5)
    to_wallet_id: currentToWalletId === value ? undefined : currentToWalletId,
    currency_id: undefined,
  });
};

const handleToWalletChange = (value: string) => {
  form.setFieldsValue({ to_wallet_id: value, currency_id: undefined });
};
```
Смена ЛЮБОГО из двух кошельков сбрасывает `currency_id` — тот же принцип сброса зависимых полей, что уже в
`TransactionForm`/`TopupForm` (сброс `currency_id`/`amounts` при смене кошелька).

Предзаполнение при редактировании (`useEffect` на `open`/`transfer`) — буквально по образцу `TransactionForm`:
`from_wallet_id`, `to_wallet_id`, `currency_id`, `amount`, `occurred_at: dayjs(transfer.occurred_at)`; при
создании — сброс всех полей к `undefined`/`""`.

Обработка ошибок — тот же паттерн `kind === "validation"` → `applyFieldErrors(apiError, KNOWN_FIELDS)` +
`form.setFields` + `toast.error(toastMessage)`, что и `TransactionForm` (016): текстовые бизнес-правила backend
(отсутствие общей валюты, совпадение кошельков, перевод самому себе) попадают в `rest` → toast без специальных
веток — тот же аргумент SOLID O, что уже обоснован в design.md 016.

Контейнер — `Drawer`/`Modal` по `useIsMobile()`.

### `TransferCard`

```ts
export interface TransferCardProps {
  transfer: Transfer;
  fromWalletName: string | undefined;
  toWalletName: string | undefined;
  currencyCode: string | undefined;
  onEdit: (transfer: Transfer) => void;
}
```
Владеет своей мутацией удаления (`useDeleteTransfer()`), по образцу `TransactionCard`/`WalletCard`. Рендер —
`Card`: строка «{fromWalletName} → {toWalletName}» (тире `"…"` для нерезолвленных значений, тот же приём, что и
`TransactionCard`), строка суммы + код валюты, дата (`occurred_at`, `dayjs`-формат `DD.MM.YYYY HH:mm`), кнопки
«Редактировать»/«Удалить» под `Popconfirm` — без блокировки редактирования (у перевода всегда ровно одна
валюта, задел 016 про многоногие операции переводов не касается).

### `TransfersPage`

```ts
const ALL_WALLETS = "all";

interface FiltersState {
  walletId: string | undefined; // undefined = «Все кошельки»
  dateRange: [Dayjs, Dayjs] | null;
}
```
Та же механика, что и `TransactionsPage` (016): `page` (1-based), `updateFilters` сбрасывает страницу на 1,
`dateFrom`/`dateTo` — `startOf("day")`/`endOf("day")` в ISO, `offset = (page - 1) * DEFAULT_PAGE_SIZE`. Фильтр
«Кошелёк» — `Select` с сентинелом `ALL_WALLETS` (без фильтра по категории/типу — у перевода их нет). Карты
`fromWalletName`/`toWalletName`/`currencyCode` резолвятся через `Map` из `useWallets()`/`useCurrencies()`
(`useMemo`), передаются в `TransferCard`. Кнопка «Создать перевод» открывает `TransferForm` в режиме создания.
Пустое состояние — `EmptyState` с иконкой `"wallet"` (уже существующая в реестре, ни backend, ни frontend
реестр иконок не расширяются этой задачей — тот же принцип, что и у отказа от иконки-шеврона в «Добавить»-меню).
Пагинация — `antd Pagination`, `pageSize={DEFAULT_PAGE_SIZE}` (20), без селектора размера страницы, буквально по
образцу `TransactionsPage`.

### Маршрут `/transfers`

```tsx
// app/routes.tsx — внутри существующего RequireAuth-поддерева, рядом с transactions
{ path: "transfers", element: <TransfersPage /> },
```
`app/navItems.ts` не меняется (постановка задачи, п. 1 и 6) — единственная точка входа — ссылка «Переводы» на
`TransactionsPage` и пункт «Перевод» в «Добавить»-меню (навигация без открытия формы на месте).

## Risks / Trade-offs

- [`TransactionCard.currencyCodeById` заменяет `currencyCode` — изменение контракта существующего компонента] →
  единственный потребитель — `TransactionsPage` в этой же задаче, правится одновременно; риска для внешних
  потребителей нет (кросс-фичевых импортов `TransactionCard` в проекте не существует).
- [`KNOWN_FIELDS` в `TopupForm` не включает поля `legs`/`amounts`] → ошибки backend по конкретной ноге или по
  бизнес-правилу набора валют всегда попадают в toast, а не подсвечивают конкретное поле суммы; риск принят
  осознанно постановкой задачи (п. 3) — пользователь видит текст ошибки целиком и может сопоставить его с
  видимыми на экране полями сам, все суммы кошелька и так на одном экране одновременно.
- [Блокировка редактирования многоногой операции — `disabled` + `Tooltip`, а не отдельный статус/иконка] → на
  телефоне подсказка требует тапа по неактивной кнопке, а не hover; риск минимален — сама недоступность кнопки
  (в отличие от отсутствия кнопки) уже сигнализирует пользователю, что действие заблокировано осознанно, а не
  по ошибке интерфейса.
- [Локальная копия `WALLET_BALANCES_QUERY_KEY` в `features/transfers` вместо импорта из `features/transactions`]
  → риск разъехаться при переименовании ключа в одном месте без другого; смягчается тем, что оба файла содержат
  явный комментарий с указанием на дублирование и его причину (тот же прецедент, что `TYPE_TAG`/
  `FILTER_OPTIONS` в 016 design.md) — TanStack Query сравнивает `queryKey` по значению, а не по ссылке, так что
  само дублирование безопасно, пока литерал `["wallet-balances"]` не меняется.
- [Реальная серверная пагинация — второй прецедент в frontend после `useTransactions`, теперь с независимой
  реализацией в `features/transfers`] → небольшое дублирование механики пагинации между двумя фичами; оправдано
  тем же принципом самодостаточности фич, что и у остальных дублирований этой задачи — списки операций и
  переводов растут независимо и с разными фильтрами, обобщать пагинацию в `shared/` преждевременно (YAGNI) при
  двух потребителях с разными формами фильтров.

## Migration Plan

Backend, база данных и миграции Alembic **не меняются** — используется уже готовый и заархивированный API
`transactions/topups`/`transfers` (011) без изменений контракта. Изменение затрагивает только новые файлы внутри
`frontend/src/features/transfers/`, новые файлы внутри `frontend/src/features/transactions/` (`TopupForm.tsx`,
`useCreateTopup.ts` и тесты), точечные правки `frontend/src/features/transactions/TransactionCard.tsx` (проп
`currencyCodeById` вместо `currencyCode`, отображение всех ног, блокировка редактирования),
`frontend/src/features/transactions/TransactionsPage.tsx` («Добавить»-меню, ссылка «Переводы») и
`frontend/src/app/routes.tsx` (новый маршрут `/transfers`). `frontend/src/app/navItems.ts` не меняется.
Разворачивания/отката на уровне инфраструктуры не требуется — обычный деплой frontend-сборки. Существующие
разделы (`wallets`, `categories`, `health`, `settings`, `auth`) не трогаются; в разделе «Операции» меняется
только состав действия создания и отображение карточки — риск регресса ограничен тестами `TransactionCard.test.tsx`/
`TransactionsPage.test.tsx`, покрывающими и старое поведение (одна нога), и новое (несколько ног).

## Open Questions

Нет — все решения по объёму и границам приняты оркестратором в
`docs/tasks/017_frontend_topups_transfers.md`; открытые вопросы самой постановки задачи («нужна ли подсказка
implied-курса», «как оформить в списке операций запись пополнения при переходе из раздела переводов») закрыты
здесь как «не делаем» (implied-курс — вне рамок, см. Non-Goals) и «не требуется» (постановка не предполагает
отдельного перехода из `/transfers` в конкретную запись `/transactions` — списки независимы). Точные сигнатуры и
механика реализации, не зафиксированные явно в постановке (структура `queryKey` списка переводов, сентинел
`ALL_WALLETS`, способ адресации динамических полей сумм `TopupForm`, узкий `KNOWN_FIELDS` в обработке ошибок
пополнения, точный текст предупреждения об отсутствии общей валюты, механика блокировки редактирования
многоногой операции, дублирование ключа кэша балансов вместо кросс-фичевого импорта, иконка пустого состояния
`TransfersPage`), зафиксированы и обоснованы в разделе «Decisions» выше.
