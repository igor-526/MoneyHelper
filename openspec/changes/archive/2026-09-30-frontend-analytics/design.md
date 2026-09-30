## Context

Backend-капабилити `analytics` (012) уже реализована и заархивирована: единственный read-эндпоинт
`GET /api/analytics` (`AnalyticsQueryParams` → `AnalyticsOut`) требует ОДНОВРЕМЕННО `display_currency`,
`date_from`, `date_to`, `group_by` и принимает опциональные сужающие фильтры (`wallet_id`, `category_id`,
`currency_id`, `type`). Внутри backend три оси группировки оформлены стратегиями `AnalyticsDimension` за
протоколом, зарегистрированными в одном реестре `DIMENSIONS: dict[str, AnalyticsDimension]`
(`core/services/analytics_dimensions.py`) — расширение новым срезом добавляет запись в реестр, а не ветку `if`.
Это прямой архитектурный прецедент для frontend: подпись корзины тоже резолвится по `group_by`, и естественный
способ сделать это без ветвления — свой реестр резолверов на стороне клиента (см. «Decisions» ниже).

Пять frontend-фундаментов, от которых зависит эта задача, уже реализованы и заархивированы: `frontend-shell`
(013, `CurrencyPicker`, `EmptyState`), `frontend-wallets` (014, `useWallets`), `frontend-categories` (015,
`useCategories`), `frontend-transactions` (016, `TransactionsPage` — образец экрана с фильтрами, `Map`-резолюцией
подписей и `Segmented` для типа), `frontend-transfers` (017). Эта задача — последняя содержательная
frontend-задача дорожной карты перед чисто верификационной 019 (проверка PWA); все решения по объёму уже приняты
оркестратором в `docs/tasks/018_frontend_analytics.md` и не пересматриваются здесь — этот документ фиксирует
точные сигнатуры и механику, по образцу `design.md` изменений 016/017.

Ключевое архитектурное отличие этого экрана от всех предыдущих списков: там фильтры опциональны и список сразу
показывает что-то (полный список без фильтра). Здесь backend требует четыре обязательных параметра одновременно
— значит, до их заполнения запрос выполнять нельзя, а UI не может просто показать «весь список» по умолчанию.

## Goals / Non-Goals

**Goals:**
- Экран `/analytics`: обязательные валюта отображения/диапазон дат/срез, гейтинг запроса без кнопки отправки
  (`enabled: filters !== null`, обобщение уже применённого паттерна `useWalletBalances(walletId)`, 016).
- Опциональные сужающие фильтры (кошелёк/категория/тип/валюта операции) поверх обязательных.
- Карточки корзин без пагинации: подпись (резолвленная по `group_by`), доход и расход, сортировка по подписи.
- Предупреждение о `unconverted_currencies`.
- Пункт `navItems` «Аналитика» и маршрут `/analytics`.
- Покрытие тестами (`FakeApiClient`), mobile-first, по правилам `AGENTS.md`.

**Non-Goals:**
- Графики и экспорт — вне рамок и backend (012), и этой задачи (постановка задачи, «Вне рамок»).
- Переводы в аналитике — backend их не учитывает, frontend не делает собственной агрегации сверх ответа backend.
- Пагинация корзин — backend отдаёт весь список одним ответом.
- Кнопка «Показать»/«Применить фильтры» — запрос реактивен.
- Расширение `CurrencyPicker`/`EmptyState`/иконок — используются как есть, без изменения контрактов 013.

## Decisions

### Структура файлов

```
frontend/src/features/analytics/
  Analytics.ts                     # типы: GroupBy, AnalyticsBucket, AnalyticsResult, AnalyticsFilters
  useAnalytics.ts / .test.ts        # запрос GET /api/analytics, enabled: filters !== null
  buildAnalyticsFilters.ts / .test.ts   # чистая функция: состояние страницы -> AnalyticsFilters | null
  useBucketLabelResolvers.ts / .test.ts # реестр резолверов подписи корзины по group_by
  AnalyticsBucketCard.tsx / .test.tsx
  AnalyticsPage.tsx / .test.tsx

frontend/src/app/navItems.ts       # изменён: пункт «Аналитика»
frontend/src/app/routes.tsx        # изменён: маршрут /analytics
```
`buildAnalyticsFilters` и `useBucketLabelResolvers` — отдельные файлы, а не код внутри `AnalyticsPage.tsx`: та же
причина, по которой в проекте `parseApiError`/`resolveTheme` живут отдельно от компонентов (AGENTS.md, «Логика —
в hooks и чистых функциях... не в JSX») — обе единицы логики проверяются unit-тестами без рендера компонента.

### `AnalyticsResult`/`AnalyticsBucket` — без camelCase-маппинга (как предписано)

```ts
// features/analytics/Analytics.ts
export type GroupBy = "wallet" | "category" | "currency";

/** Форма элемента `buckets` ответа backend (`AnalyticsBucketOut`) — без camelCase-маппинга. */
export interface AnalyticsBucket {
  group_key: string;
  income: string;
  expense: string;
}

/** Форма ответа backend (`AnalyticsOut`) — без camelCase-маппинга, тот же принцип, что у `Wallet`/`Transaction`. */
export interface AnalyticsResult {
  display_currency_id: string;
  buckets: AnalyticsBucket[];
  unconverted_currencies: string[];
}
```

### `AnalyticsFilters` — camelCase, конвенция фильтров GET, а не тела запроса

`AnalyticsFilters` — вход `useAnalytics`, а не форма ответа, поэтому на него действует другая, уже существующая в
проекте конвенция: GET-фильтры (`TransferFilters`/`TransactionFilters`, camelCase, явно маппятся на snake_case
внутри `queryFn`) в отличие от тел POST/PUT-запросов (`TransactionFormValues`/`TopupFormValues`, snake_case без
маппинга, потому что уходят в `JSON.stringify` как есть). `AnalyticsQueryParams` backend — это набор GET query-
параметров, а не JSON body, значит для него действует первая конвенция:

```ts
// features/analytics/Analytics.ts (продолжение)
import type { CategoryType } from "@/features/categories/Category";

/** Вход `useAnalytics`: три обязательных поля запроса + сужающие опциональные. camelCase — как `TransferFilters`. */
export interface AnalyticsFilters {
  displayCurrencyId: string;
  dateFrom: string;
  dateTo: string;
  groupBy: GroupBy;
  walletId?: string;
  categoryId?: string;
  currencyId?: string;
  type?: CategoryType;
}
```
Это единственное отступление от буквального прочтения постановки задачи («Тип `AnalyticsResult`/`AnalyticsBucket`
— без camelCase-маппинга») — постановка называет именно эти два типа (форму ответа), не `AnalyticsFilters`;
данное решение продолжает уже существующую в проекте границу между «типами ответа» и «типами GET-фильтров»
внутри одной и той же фичи `transfers` (`Transfer` без маппинга, `TransferFilters` camelCase), а не изобретает
новую.

### `useAnalytics(filters: AnalyticsFilters | null)` — гейтинг без кнопки отправки

```ts
// features/analytics/useAnalytics.ts
export const ANALYTICS_QUERY_KEY = ["analytics"] as const;

/** `enabled: filters !== null` — то же обобщение паттерна `useWalletBalances(walletId)` (016) на составной вход:
 *  запрос не выполняется, пока не заполнены все обязательные поля (постановка задачи, п. 2). */
export function useAnalytics(filters: AnalyticsFilters | null) {
  const api = useApiClient();
  return useQuery({
    queryKey: [...ANALYTICS_QUERY_KEY, filters],
    queryFn: ({ signal }) =>
      // Ненулевое утверждение `filters!` безопасно: `enabled` ниже гарантирует, что TanStack Query никогда не
      // вызовет `queryFn` при `filters === null`. Перенос этой гарантии в типы queryFn (а не повторная проверка
      // в рантайме) — тот же принцип единственного места ответственности за гейтинг, что и в `useWalletBalances`.
      api.get<AnalyticsResult>("/api/analytics", {
        query: {
          display_currency: filters!.displayCurrencyId,
          date_from: filters!.dateFrom,
          date_to: filters!.dateTo,
          group_by: filters!.groupBy,
          wallet_id: filters!.walletId,
          category_id: filters!.categoryId,
          currency_id: filters!.currencyId,
          type: filters!.type,
        },
        signal,
      }),
    enabled: filters !== null,
  });
}
```
Ошибки (неизвестная валюта отображения, `date_from` позже `date_to`) НЕ передают `meta: { silent: true }` —
здесь нет `antd Form` (это панель фильтров, не форма отправки), поэтому нет и `applyFieldErrors`, которому
`silent` обычно сопутствует; ошибка идёт через обычный глобальный toast, тот же принцип, что у `useWallets`/
`useTransactions` при ошибке загрузки списка (постановка задачи, п. 6 и раздел «Обработка ошибок»).

### `AnalyticsFilters` на странице — единый объект с опциональными полями + отдельная проверка полноты

`AnalyticsPage` хранит состояние фильтров как единый объект, где ВСЕ поля (включая три обязательных) —
независимо заполняемые, потому что пользователь взаимодействует с тремя разными контролами (`CurrencyPicker`,
`RangePicker`, `Segmented`) в любом порядке — в отличие, например, от `TransferForm` (017), где выбор исходного и
целевого кошелька последовательно зависим (смена одного сбрасывает другое). Дискриминированный тип потребовал бы
2^3 вариантов частичной заполненности с одинаковым поведением рендера во всех них (все три контрола всегда на
экране одновременно, независимо от того, что уже заполнено) — то есть не давал бы никакой выгоды от
exhaustiveness-проверки компилятора, только ритуал. Поэтому — единый объект плюс чистая функция, вычисляющая
`AnalyticsFilters | null`:

```ts
// features/analytics/buildAnalyticsFilters.ts
type TypeFilter = "all" | CategoryType;

export interface AnalyticsPageState {
  displayCurrencyId: string | undefined;
  dateRange: [Dayjs, Dayjs] | null;
  groupBy: GroupBy | undefined;
  walletId: string | undefined;
  categoryId: string | undefined;
  currencyId: string | undefined;
  type: TypeFilter;
}

export const INITIAL_ANALYTICS_STATE: AnalyticsPageState = {
  displayCurrencyId: undefined,
  dateRange: null,
  groupBy: undefined,
  walletId: undefined,
  categoryId: undefined,
  currencyId: undefined,
  type: "all",
};

/** Единственное место, решающее «все обязательные поля заполнены» — используется и для гейтинга запроса, и для
 *  выбора между `Alert` «недостаточно данных» и списком корзин (одно вычисление, не два независимых условия). */
export function buildAnalyticsFilters(state: AnalyticsPageState): AnalyticsFilters | null {
  if (state.displayCurrencyId === undefined || state.dateRange === null || state.groupBy === undefined) {
    return null;
  }
  return {
    displayCurrencyId: state.displayCurrencyId,
    dateFrom: state.dateRange[0].startOf("day").toISOString(),
    dateTo: state.dateRange[1].endOf("day").toISOString(),
    groupBy: state.groupBy,
    walletId: state.walletId,
    categoryId: state.categoryId,
    currencyId: state.currencyId,
    type: state.type === "all" ? undefined : state.type,
  };
}
```
`AnalyticsPage` вызывает `const filters = useMemo(() => buildAnalyticsFilters(state), [state]);`, передаёт его в
`useAnalytics(filters)` и одновременно использует `filters === null` как единственное условие показа `Alert`
«недостаточно данных» — гейтинг запроса и решение об `Alert` читают одно и то же вычисление, не два похожих
условия, рискующих разойтись.

### Реестр резолверов подписи корзины — `Record<GroupBy, (key: string) => string | undefined>`

По образцу backend `DIMENSIONS` (см. «Context»): реестр строится из трёх `Map`, а не ветвлением `if group_by ===
...`:

```ts
// features/analytics/useBucketLabelResolvers.ts
export function useBucketLabelResolvers(): Record<GroupBy, (key: string) => string | undefined> {
  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories(undefined);
  const { data: currencies = [] } = useCurrencies();

  const walletNameById = useMemo(() => new Map(wallets.map((w) => [w.id, w.name])), [wallets]);
  const categoryNameById = useMemo(() => new Map(categories.map((c) => [c.id, c.name])), [categories]);
  const currencyCodeById = useMemo(() => new Map(currencies.map((c) => [c.id, c.code])), [currencies]);

  return useMemo(
    () => ({
      wallet: (key: string) => walletNameById.get(key),
      category: (key: string) => categoryNameById.get(key),
      currency: (key: string) => currencyCodeById.get(key),
    }),
    [walletNameById, categoryNameById, currencyCodeById],
  );
}
```
`useCategories(undefined)` — полный список категорий (доход и расход), без фильтра по типу: подпись корзины при
`group_by = "category"` резолвится независимо от типа категории (постановка задачи, п. 4 — «единый простой рендер
карточки независимо от активного `group_by`»). Расширение новым срезом в будущем — новая запись в этом реестре
и в `DIMENSIONS` backend параллельно, не новая ветка `if`.

### Сортировка и рендер карточек — по подписи, без иконки/тега типа

```ts
// AnalyticsPage.tsx (фрагмент)
const resolveLabel = filters ? labelResolvers[filters.groupBy] : undefined;
const sortedBuckets = useMemo(() => {
  if (!analyticsQuery.data || !resolveLabel) return [];
  return analyticsQuery.data.buckets
    .map((bucket) => ({ bucket, label: resolveLabel(bucket.group_key) ?? "…" }))
    .sort((a, b) => a.label.localeCompare(b.label));
}, [analyticsQuery.data, resolveLabel]);
```
Сортировка по строке подписи (`localeCompare`), не по сумме — сравнение денежных сумм как чисел означало бы
`parseFloat` строки денежной суммы, что запрещено принципом «сумма всегда строка» (`api-conventions`,
`MoneyInput`); сравнение строк подписи такого нарушения не создаёт (постановка задачи, п. 4).

```tsx
// AnalyticsBucketCard.tsx
export interface AnalyticsBucketCardProps {
  label: string;
  bucket: AnalyticsBucket;
}

/** Единый простой рендер независимо от group_by — без иконки/тега типа (в отличие от TransactionCard, п. 4). */
export function AnalyticsBucketCard({ label, bucket }: AnalyticsBucketCardProps) {
  return (
    <Card>
      <Flex vertical gap={8}>
        <Typography.Text strong>{label}</Typography.Text>
        <Flex gap={16}>
          <Typography.Text type="success">Доход: {bucket.income}</Typography.Text>
          <Typography.Text type="danger">Расход: {bucket.expense}</Typography.Text>
        </Flex>
      </Flex>
    </Card>
  );
}
```
Код валюты не повторяется на каждой карточке (в отличие от `TransactionCard`, где у каждой ноги своя валюта) —
все суммы результата в одной и той же валюте отображения, поэтому её код показывается один раз над списком
карточек («Суммы в {код валюты отображения}», резолвленный через ту же `Map` валют, `"…"` при нерезолвленном
`display_currency_id`) — собственное решение этой задачи сверх буквы постановки: без него пользователь видел бы
только числа без единиц измерения на каждой карточке, а повтор кода на каждой из потенциально многих карточек
избыточен, поскольку валюта одна для всего результата.

### `Alert`-состояния экрана

Три взаимоисключающих состояния области результата, в порядке проверки:
1. `filters === null` → `Alert type="info"` с текстом **«Выберите валюту отображения, диапазон дат и срез, чтобы
   увидеть аналитику»** (буквально, постановка задачи, п. 2) — вместо списка корзин; НЕ `EmptyState` (нет единого
   действия «создать», нужно заполнить несколько независимых полей).
2. `filters !== null && analyticsQuery.isPending` → `Spin`.
3. `filters !== null && !isPending && sortedBuckets.length === 0` → `EmptyState` (иконка `"trending-up"`,
   заголовок «Нет данных за выбранный период», без кнопки действия — `action` у `EmptyState` опционален,
   постановка задачи не предполагает действия «создать» для аналитики) — собственное решение сверх буквы
   постановки: она описывает только состояние «недостаточно данных», не оговаривая явно случай «данных
   достаточно, но корзин нет» (например, диапазон дат без единой операции); при ошибке запроса `analyticsQuery.data`
   также не определён, поэтому это состояние покрывает и «ошибку без падения интерфейса» тем же путём, что и
   `TransactionsPage`/`TransfersPage` (`items ?? []` → `EmptyState`), без специального кода для ошибок.
4. Иначе → `unconverted_currencies` (`Alert type="warning"`, если не пуст) + строка «Суммы в {код}» + список
   `AnalyticsBucketCard`.

Текст предупреждения о валютах без курса — буквально **«Не удалось пересчитать суммы в валютах: {коды через
запятую} — нет курса за выбранный период»** (постановка задачи, п. 5), коды резолвятся через `Map` из
`useCurrencies()`, `"…"` для нерезолвленных, соединяются `", "`.

### Элементы управления `AnalyticsPage`

Обязательные (без значения по умолчанию):
- `CurrencyPicker` (одиночный режим, без `allowedIds`) — «Валюта отображения».
- `DatePicker.RangePicker` — диапазон дат, `dateFrom`/`dateTo` считаются как `startOf("day")`/`endOf("day")` в
  ISO, тот же приём, что в `TransactionsPage`/`TransfersPage`.
- `Segmented` с тремя опциями (`{label: "Кошелёк", value: "wallet"}`, `{label: "Категория", value: "category"}`,
  `{label: "Валюта", value: "currency"}`) — значение изначально `undefined`, `Segmented` не подсвечивает ни одну
  опцию до выбора (в отличие от опциональных фильтров-`Segmented`, у которых уже есть `defaultValue`/начальное
  значение — здесь его намеренно нет).

Опциональные сужающие (сентинел «Все …», буквально по постановке задачи, п. 3):
- `Select` «Кошелёк» — `ALL_WALLETS` → «Все кошельки», опции из `useWallets()`.
- `Select` «Категория» — `ALL_CATEGORIES` → «Все категории», опции из `useCategories(undefined)` (полный список,
  без фильтра по типу — та же независимость фильтров, что в `TransactionsPage`).
- `Select` «Тип» — `ALL_TYPES` → «Все типы», опции «Доход»/«Расход» (`CategoryType`); здесь `Select`, а не
  `Segmented`, как у одноимённого фильтра в `TransactionsPage` — постановка задачи прямо предписывает «те же
  паттерны `Select` с сентинелом» для всех четырёх сужающих фильтров этого экрана одним перечислением, а не
  единообразие с конкретным виджетом `TransactionsPage`; четыре однотипных `Select` в одной панели сужающих
  фильтров визуально последовательнее, чем три `Select` и один `Segmented` вперемешку.
- `Select` «Валюта операции» — `ALL_CURRENCIES` → «Все валюты», опции из `useCurrencies()`, обычный `Select` (не
  `CurrencyPicker` — его контракт одиночного режима не поддерживает сентинел «все», постановка задачи, п. 3).

Любое изменение любого поля (обязательного или сужающего) обновляет состояние страницы; `useMemo` пересчитывает
`filters`, `useAnalytics` реагирует реактивно через `queryKey`, включающий весь объект `filters` — без ручной
инвалидации.

## Risks / Trade-offs

- [`filters!` внутри `queryFn` — ненулевое утверждение вместо сужения типа] → риск рассинхронизации с `enabled`
  при будущей правке; смягчается тем, что оба выражения находятся в одном литерале конфигурации `useQuery` в
  одном файле, и комментарий явно объясняет зависимость (тот же приём уже принят в `useWalletBalances`, где
  подобная зависимость между `enabled` и телом `queryFn` неявна через шаблонную строку, а не явное утверждение).
- [`AnalyticsFilters` camelCase, а не snake_case, как буквально сказано о «типе `AnalyticsResult`/
  `AnalyticsBucket`»] → риск того, что читатель постановки задачи ожидает единообразия camelCase-запрета на все
  типы фичи; смягчается тем, что это разграничение (ответ без маппинга / GET-фильтры camelCase) уже существует в
  проекте между `Transfer` и `TransferFilters` внутри одной фичи `transfers` — не новый прецедент.
- [Отсутствие кнопки действия у `EmptyState` состояния «Нет данных за выбранный период»] → пользователь может не
  понять, что делать дальше; смягчается тем, что подпись состояния явно называет причину (диапазон/фильтры), а
  сами элементы управления фильтрами остаются на экране и доступны для немедленного изменения, без необходимости
  переходить куда-то ещё.
- [Четыре `Select` сужающих фильтра в одну визуальную панель, без группировки] → на телефоне панель фильтров
  становится длинной (3 обязательных + 4 опциональных контрола); смягчается тем, что все контролы — стандартная
  высота ≥ 44 px (тема antd, AGENTS.md) и вертикальный `Flex`, тот же паттерн, что уже используется в
  `TransactionsPage` с четырьмя контролами фильтров без выноса в `Drawer`/аккордеон.

## Migration Plan

Backend, база данных и миграции Alembic **не меняются** — используется уже готовый и заархивированный
`GET /api/analytics` (012) без изменений контракта. Изменение затрагивает только новые файлы внутри
`frontend/src/features/analytics/` и точечные правки `frontend/src/app/navItems.ts` (новый пункт «Аналитика»
между «Операции» и «Настройки») и `frontend/src/app/routes.tsx` (новый маршрут `/analytics` под `RequireAuth`).
Разворачивания/отката на уровне инфраструктуры не требуется — обычный деплой frontend-сборки. Существующие
разделы (`wallets`, `categories`, `transactions`, `transfers`, `settings`) не трогаются.

## Open Questions

Нет — все решения по объёму и границам приняты оркестратором в `docs/tasks/018_frontend_analytics.md`; открытые
вопросы самой постановки задачи (формат диапазона дат, визуальное сочетание дохода/расхода в карточке) закрыты
здесь как «`RangePicker` без времени в UI» и «два `Typography.Text` (`success`/`danger`) рядом в одной карточке»
соответственно (см. «Decisions» выше). Точные сигнатуры и механика, не зафиксированные явно в постановке
(структура `AnalyticsFilters`/`AnalyticsPageState`, точный реестр резолверов, состояние «данных нет» отдельно от
«недостаточно фильтров», строка «Суммы в {код}», выбор `Select` вместо `Segmented` для сужающего фильтра типа),
зафиксированы и обоснованы в разделе «Decisions» выше.
