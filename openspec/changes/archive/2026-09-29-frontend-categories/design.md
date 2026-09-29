## Context

Backend-капабилити `categories` (009) и frontend-фундамент `frontend-shell` (013) уже реализованы и заархивированы.
013 подготовил кирпичи, которые нужны и этому экрану: `IconPicker` (выбор из закрытого `BUSINESS_ICON_NAMES`,
`Drawer`/`Modal` по `useIsMobile`), `EmptyState` (пустой список с действием) и тип `Page<T>`. Прямой прецедент —
уже реализованный и заархивированный `frontend-wallets` (014): почти идентичная по структуре сущность (карточки +
единая форма create/update + удаление с `Popconfirm` + hooks на TanStack Query). Этот документ повторяет
архитектуру 014 везде, где сущности совпадают, и фиксирует точки, где категория отличается от кошелька: фильтр по
типу в списке и hook'е, поле `type` вместо `currency_ids`/`CurrencyPicker`, и — главное отличие в обработке ошибок
— 409 на дубль названия при создании/редактировании обрабатывается **на уровне поля формы**, а не общим toast
(в отличие от `useDeleteWallet`, где 409 идёт через глобальный обработчик без изменений). Все решения по объёму и
границам этой задачи уже приняты оркестратором в `docs/tasks/015_frontend_categories.md` и не пересматриваются
здесь; этот документ фиксирует точные сигнатуры и механику реализации, по образцу `design.md` изменения
`frontend-wallets`.

Backend-контракт (`backend/src/api/schemas/category.py`, `backend/src/api/categories.py`):
`POST /api/categories` → 201 `CategoryOut`; `GET /api/categories` → `Page[CategoryOut]` (`CategoryListParams` —
`PageParams` плюс опциональный `type: CategoryType | None`); `GET /api/categories/{id}` → `CategoryOut`;
`PUT /api/categories/{id}` → `CategoryOut` (та же валидация тела, что и `POST`, `CategoryUpdate = CategoryCreate`);
`DELETE /api/categories/{id}` → 204 или 409 (`ConflictError`, если есть операции). Список отсортирован
`created_at ASC, id ASC` уже на backend. `CategoryCreate`/`CategoryUpdate`: `type` (`CategoryType`, значения
`"income"`/`"expense"`), `name` (непустой после `strip()`, ≤ 100 символов), `icon` (`IconName`). `CategoryOut`
дополнительно отдаёт `id`, `created_at`, `updated_at`. Название уникально в паре `user_id`+`type`
(`UniqueConstraint`) — дубль в пределах того же типа даёт 409 `AlreadyExistsError`; та же пара «пользователь + имя»
в **другом** типе конфликтом не является.

## Goals / Non-Goals

**Goals:**
- Список категорий карточками (иконка, название, индикатор типа) одним запросом без клиентской пагинации, с
  фильтром по типу («доход»/«расход»/«все»), по образцу `useWallets` (014) с добавлением параметра фильтра.
- Один компонент `CategoryForm` для создания и редактирования, открывающийся в `Drawer`/`Modal` поверх списка.
- Удаление с подтверждением через `Popconfirm`, 409 при категории с операциями обрабатывается уже существующим
  глобальным обработчиком ошибок без специального кода (та же логика, что у `useDeleteWallet`, 014).
- 409 на дубль названия в пределах типа при создании/редактировании — field-level ошибка на поле `name`, по
  образцу `RegisterPage` (`kind === "conflict"` → `form.setFields`), явно **не** по образцу `useDeleteWallet`.
- Кэш TanStack Query с `queryKey`, зависящим от фильтра типа, инвалидируемым по префиксу всеми тремя мутациями.
- Точка входа на `/categories` со страницы «Настройки» (без пункта `navItems`) и маршрут под `RequireAuth`.
- Всё покрыто тестами (`FakeApiClient`), по mobile-first правилам AGENTS.md.

**Non-Goals:**
- Иерархия категорий — backend хранит плоский список.
- Набор категорий по умолчанию для нового пользователя — backend не сидирует категории.
- Пункт `navItems` «Категории» — бюджет 5 пунктов занят и зарезервирован под 016/018.
- Отдельные маршруты для форм (`/categories/new` и т. п.).
- Серверная/клиентская постраничная пагинация в UI списка категорий.
- Правки `shared/ui/icons.ts` — иконка `"coins"` для пустого состояния уже есть в `BUSINESS_ICONS`.

## Decisions

### Структура файлов

```
frontend/src/features/categories/
  Category.ts                 # тип Category (форма CategoryOut), CategoryType, CategoryFormValues
  useCategories.ts             # useQuery(GET /api/categories?type=...), CATEGORIES_QUERY_KEY
  useCategories.test.ts
  useCreateCategory.ts
  useCreateCategory.test.ts
  useUpdateCategory.ts
  useUpdateCategory.test.ts
  useDeleteCategory.ts
  useDeleteCategory.test.ts
  CategoryForm.tsx
  CategoryForm.test.tsx
  CategoryCard.tsx
  CategoryCard.test.tsx
  CategoriesPage.tsx
  CategoriesPage.test.tsx
```

Каждый hook — отдельный файл с тестом рядом (по образцу `features/wallets`) — SOLID S: одна мутация, одна причина
для изменения.

### `Category` — без camelCase-маппинга, тот же принцип, что и `Wallet` (014)

```ts
export type CategoryType = "income" | "expense";

/** Форма ответа backend (`CategoryOut`) — без camelCase-маппинга, тот же принцип, что и `Wallet` (design.md 014). */
export interface Category {
  id: string;
  type: CategoryType;
  name: string;
  icon: string;
  created_at: string;
  updated_at: string | null;
}

/** Форма тела запроса `CategoryCreate`/`CategoryUpdate`; совпадает с именами полей формы. */
export interface CategoryFormValues {
  type: CategoryType;
  name: string;
  icon: string;
}
```

`created_at`/`updated_at` нигде не отображаются и не используются (сортировка уже на backend), поэтому маппинг в
camelCase не вводится — то же обоснование, что зафиксировано для `Wallet` в `design.md` 014 (в отличие от
`Currency.decimal_places` → `decimalPlaces`, который действительно нужен на camelCase-стороне для `MoneyInput`):
здесь маппинг не снимает реальной проблемы, только добавляет код ради единообразия ради единообразия (YAGNI).

### `CATEGORIES_QUERY_KEY`, `categoryQueryKey(type)` и `useCategories(type)`

```ts
export const CATEGORIES_QUERY_KEY = ["categories"] as const;

function categoryQueryKey(type: CategoryType | undefined) {
  return [...CATEGORIES_QUERY_KEY, type ?? "all"] as const;
}

/** Персональный объём категорий пользователя мал, поэтому одной страницы с максимальным limit достаточно. */
export function useCategories(type: CategoryType | undefined) {
  const api = useApiClient();
  return useQuery({
    queryKey: categoryQueryKey(type),
    queryFn: async ({ signal }) => {
      const page = await api.get<Page<Category>>("/api/categories", {
        query: { type, limit: 100, offset: 0 },
        signal,
      });
      return page.items;
    },
  });
}
```

`type: undefined` не попадает в query-строку (`FetchApiClient.buildUrl` отбрасывает `undefined`/`null` до
сериализации — тот же механизм, что уже используется в `useWallets`/`useCurrencies`), поэтому backend получает
запрос без фильтра и отдаёт все категории пользователя. `queryKey` включает `type ?? "all"` третьим элементом:
фильтры «доход», «расход» и «все» кешируются раздельно и не затирают друг друга при переключении `Segmented`.
`GET /api/categories` требует авторизации, но ошибка загрузки показывается стандартным глобальным toast — `meta:
{ silent: true }` не передаётся, как и в `useWallets`.

### Три мутации: `useCreateCategory`/`useUpdateCategory`/`useDeleteCategory`

```ts
export function useCreateCategory() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (values: CategoryFormValues) => api.post<Category>("/api/categories", values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });
}

export function useUpdateCategory() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: CategoryFormValues }) =>
      api.put<Category>(`/api/categories/${id}`, values),
    meta: { silent: true },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });
}

export function useDeleteCategory() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<undefined>(`/api/categories/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
    },
  });
}
```

Инвалидация всеми тремя мутациями идёт по `CATEGORIES_QUERY_KEY` (`["categories"]`), **без** уточнения `type`:
TanStack Query инвалидирует по префиксу ключа, поэтому все варианты `["categories", "all"]`/`["categories",
"income"]`/`["categories", "expense"]` обновляются одним вызовом — тот же принцип, что уже описан в постановке
задачи (раздел «Ключевые решения», пункт 6).

`useCreateCategory`/`useUpdateCategory` — `meta: { silent: true }`: и 400 по полям (`applyFieldErrors`), и 409 на
дубль названия обрабатывает сама форма (см. `CategoryForm` ниже), по образцу `useCreateWallet`/`useUpdateWallet` —
но, в отличие от них, здесь `onError` формы **обязателен** и обрабатывает не только `validation`, но и `conflict`.
`useDeleteCategory` — **без** `meta: { silent: true }` и без `onError`, буквально по образцу `useDeleteWallet`
(014): единственная специфичная ошибка удаления — 409 «есть операции», её уже показывает
`MESSAGE_BUILDERS.conflict` глобального обработчика. Разная обработка одного и того же кода ошибки (409) в разных
мутациях одной фичи — осознанное решение, а не непоследовательность: смысл 409 разный (дубль имени — ошибка
конкретного поля формы; категория занята операциями — не относится ни к одному полю формы удаления, которого и не
существует).

### `CategoryForm` — один компонент для создания и редактирования, с field-level обработкой 409

```ts
export interface CategoryFormProps {
  open: boolean;
  onClose: () => void;
  /** Тип по умолчанию для новой категории (текущий фильтр списка, если он не «все»). Игнорируется при редактировании. */
  defaultType?: CategoryType;
  /** `undefined` — форма создания; заданная `Category` — форма редактирования, поля предзаполняются её значениями. */
  category?: Category;
}

const KNOWN_FIELDS = ["type", "name", "icon"] as const;
const NAME_CONFLICT_MESSAGE = "Категория с таким названием уже существует в этом типе";
```

Внутри — тот же механизм, что и `WalletForm`: безусловный вызов `useCreateCategory()`/`useUpdateCategory()`,
выбор `.mutate` по наличию `category` в `handleSubmit`; `useEffect` на `open`/`category` —
`form.setFieldsValue({ type: category.type, name: category.name, icon: category.icon })` при редактировании
(значения берутся из уже загруженного элемента списка, **без** `GET /api/categories/{id}`), иначе
`form.setFieldsValue({ type: defaultType ?? "income", name: "", icon: undefined })` при создании — тип
предзаполняется текущим фильтром списка, если он задан (`"income"`/`"expense"`), или `"income"` при фильтре «все»
(первое значение `CategoryType`, произвольный, но детерминированный выбор по умолчанию).

```tsx
<Form form={form} layout="vertical" onFinish={handleSubmit} disabled={mutation.isPending}>
  <Form.Item name="type" label="Тип" rules={[{ required: true, message: "Выберите тип" }]}>
    <Segmented
      options={[
        { label: "Доход", value: "income" },
        { label: "Расход", value: "expense" },
      ]}
    />
  </Form.Item>
  <Form.Item name="name" label="Название" rules={[{ required: true, message: "Введите название" }]}>
    <Input maxLength={100} />
  </Form.Item>
  <Form.Item name="icon" label="Иконка" rules={[{ required: true, message: "Выберите иконку" }]}>
    <IconPicker value={undefined} onChange={() => {}} />
  </Form.Item>
  <Form.Item style={{ marginBottom: 0 }}>
    <Button type="primary" htmlType="submit" block loading={mutation.isPending}>
      {category ? "Сохранить" : "Создать"}
    </Button>
  </Form.Item>
</Form>
```

`Segmented` выбран вместо `Radio.Group` — тот же компонент, что уже применяется для фильтра списка (единообразие
в пределах фичи), с двумя опциями (без «все» — тип категории обязателен, «все» имеет смысл только как значение
фильтра списка, не как значение поля формы). `Form.Item` подставляет `value`/`onChange` автоматически, как и
`IconPicker` в `WalletForm` (014).

Обработка ошибок отправки — расширение паттерна `RegisterPage`/`WalletForm` третьей веткой:

```ts
const onError = (submitError: unknown) => {
  const apiError = toApiError(submitError);

  if (apiError.kind === "validation") {
    const { byField, toastMessage } = applyFieldErrors(apiError, KNOWN_FIELDS);
    for (const [name, errors] of Object.entries(byField)) {
      form.setFields([{ name: name as keyof CategoryFormValues, errors }]);
    }
    toast.error(toastMessage);
    return;
  }
  if (apiError.kind === "conflict") {
    form.setFields([{ name: "name", errors: [NAME_CONFLICT_MESSAGE] }]);
    return;
  }
  toast.error(resolveErrorMessage(apiError));
};
```

**Текст сообщения о конфликте — фиксированная строка `NAME_CONFLICT_MESSAGE`, не `apiError.detail` backend**, по
образцу `RegisterPage` (`"Такой email уже зарегистрирован"` — тоже собственный текст, не `apiError.detail`).
Обоснование: `AlreadyExistsError` на backend (`core/exceptions`) — общее исключение уникальности без гарантии
формулировки, специфичной для пары «имя + тип» (в отличие от `ConflictError` при удалении, чьё сообщение
формируется сервисом specifично под операцию и уже готово для показа как есть). Собственный текст на frontend даёт
контроль над формулировкой независимо от того, как backend сформулирует `detail` этого исключения, и явно называет
причину («в этом типе»), которую пользователь иначе мог бы не связать с уже существующей категорией другого типа с
тем же именем. `RegisterPage` не показывает toast при `conflict` (только ошибка поля) — `CategoryForm` повторяет
это: `return` без `toast.error`, поле формы уже достаточно заметно.

`onSuccess`: `toast.success(...)`, `onClose()`. Контейнер — `Drawer`/`Modal` по `useIsMobile()`, буквально по
образцу `WalletForm`.

### `CategoryCard` — индикатор типа, сама владеет удалением

```ts
export interface CategoryCardProps {
  category: Category;
  onEdit: (category: Category) => void;
}

const TYPE_TAG: Record<CategoryType, { label: string; color: "success" | "error" }> = {
  income: { label: "Доход", color: "success" },
  expense: { label: "Расход", color: "error" },
};
```

`TYPE_TAG` — таблица вариантов, не цепочка `if`/тернарник (AGENTS.md, SOLID O). `color="success"`/`color="error"`
— именованные пресеты темы antd (семантические токены), не хардкод hex, разрешено правилом AGENTS.md про токены
(та же оговорка, что и в постановке задачи). Рендер — `Card`: `Icon`(`category.icon`) + `Typography.Text`
(`category.name`) + `Tag color={TYPE_TAG[category.type].color}` (`TYPE_TAG[category.type].label`) в шапке; внизу
кнопки «Редактировать»/«Удалить» под `Popconfirm`, буквально по образцу `WalletCard` (014), включая владение
`useDeleteCategory()` без callback `onDelete` (успешное удаление инвалидирует список, карточка пропадает сама).

### `CategoriesPage` — фильтр, сборка списка, состояние формы

```ts
type FilterValue = "all" | CategoryType;

const FILTER_OPTIONS: { label: string; value: FilterValue }[] = [
  { label: "Все", value: "all" },
  { label: "Доход", value: "income" },
  { label: "Расход", value: "expense" },
];

export function CategoriesPage() {
  const [filter, setFilter] = useState<FilterValue>("all");
  const categoriesQuery = useCategories(filter === "all" ? undefined : filter);
  const [formState, setFormState] = useState<{ open: boolean; category?: Category }>({ open: false });
  // ...
}
```

Разметка: `Flex vertical gap={16}` — заголовок «Категории», `Segmented options={FILTER_OPTIONS}` (фильтр всегда
виден, не скрывается в пустом состоянии — в отличие от заголовка/кнопки создания у `WalletsPage`, потому что
фильтр не «точка входа в создание», а независимый переключатель среза уже загруженного списка; пользователь должен
иметь возможность переключить фильтр, даже если текущий срез пуст, а другой — нет), далее кнопка «Создать
категорию» + список `CategoryCard` **либо** `EmptyState` (`icon: "coins"`, заголовок «Категорий пока нет»,
действие «Создать категорию»), по тому же условию `categoriesQuery.data.length === 0`, что и в `WalletsPage`. Пока
`categoriesQuery.isPending` — `Spin`. Кнопка «Создать категорию» открывает форму с `defaultType={filter === "all"
? undefined : filter}` — создаваемая категория предзаполняется типом активного фильтра. Карточки — в порядке ответа
backend (без клиентской пересортировки), буквально по образцу `WalletsPage`.

### Точка входа: `SettingsPage`

```tsx
<Card title="Категории">
  <Link to="/categories">
    <Button type="primary">Открыть</Button>
  </Link>
</Card>
```

Новая `Card` вставляется **вторым** блоком страницы «Настройки» — после «Тема оформления», перед «Смена пароля»:
`SettingsPage` сейчас группирует пользовательские предпочтения (тема) и учётную запись (пароль, выход) отдельно от
инфраструктуры (PWA-установка, версия, последний блок); «Категории» — ссылка на раздел данных, не настройка
«Настроек» в строгом смысле, но по значимости для пользователя (частое действие) она ближе к началу страницы, чем
к учётным или инфраструктурным пунктам. Кнопка «Открыть» — не `block`: остальные интерактивные элементы страницы
(`ThemeSwitch`, `LogoutButton`) тоже не растянуты на всю ширину, `SettingsPage` уже не следует правилу «`block` на
телефоне» буквально (в отличие от `WalletsPage`/`CategoriesPage`, где `block` определяется `useIsMobile()`) —
единообразие в пределах уже существующей страницы важнее переоткрытия этого решения здесь.

### Навигация: маршрут без пункта `navItems`

```tsx
// app/routes.tsx — новый дочерний маршрут внутри уже существующего RequireAuth-поддерева, без правки navItems.ts
{ path: "categories", element: <CategoriesPage /> },
```

В отличие от `frontend-wallets` (014), этот маршрут **не** добавляется в `app/navItems.ts` — решение уже
зафиксировано оркестратором в постановке задачи (бюджет 5 пунктов нижней панели занят и зарезервирован под
«Операции»/«Аналитику», 016/018). `CategoriesPage` рендерится прямо внутри `AppLayout`/`MobileShell`/`DesktopShell`
без дополнительной обёртки, тот же принцип, что и `WalletsPage`/`SettingsPage`.

## Risks / Trade-offs

- [Фиксированный текст `NAME_CONFLICT_MESSAGE` вместо `apiError.detail`] → если backend когда-нибудь изменит смысл
  409 при создании категории (например, добавит другую причину конфликта помимо дубля имени), фронтенд покажет
  устаревшую формулировку у поля `name`; риск низкий — 409 на `POST`/`PUT /api/categories` сейчас имеет ровно одну
  причину (`AlreadyExistsError` на составной `UniqueConstraint`), задокументированную в контракте backend.
- [`Segmented`-фильтр не скрывается в пустом состоянии, в отличие от заголовка/кнопки создания `WalletsPage`] →
  небольшое расхождение с прецедентом 014; оправдано тем, что фильтр здесь — независимый переключатель среза, а не
  часть единственной точки входа в создание (см. «Decisions», `CategoriesPage`).
- [Три мутации инвалидируют по префиксу `CATEGORIES_QUERY_KEY`, не по конкретному варианту фильтра] → на телефоне
  с медленной сетью после мутации перезапросятся и неактивные варианты фильтра (например, «доход» при открытом
  «расход»), если они когда-то кешировались; риск минимален — TanStack Query перезапрашивает только уже
  смонтированные/наблюдаемые запросы, а список категорий мал.
- [`CategoryCard` сама владеет `useDeleteCategory()`, как и `WalletCard`] → та же архитектура, тот же риск и то же
  обоснование, что зафиксировано в `design.md` 014 — риска регресса нет, паттерн уже проверен в проде.

## Migration Plan

Backend, база данных и миграции Alembic **не меняются** — используется уже готовый и заархивированный API
`categories` (009) без изменений контракта. Изменение затрагивает только новые файлы внутри
`frontend/src/features/categories/` и точечные правки `frontend/src/app/routes.tsx` (новый маршрут, без изменений
`navItems.ts`) и `frontend/src/features/settings/SettingsPage.tsx` (новая `Card` — точка входа). Разворачивания/
отката на уровне инфраструктуры не требуется — обычный деплой frontend-сборки. Существующие разделы (`wallets`,
`health`, `settings`, `auth`) не трогаются, риска регресса уже работающих разделов нет.

## Open Questions

Нет — все решения по объёму и границам приняты оркестратором в `docs/tasks/015_frontend_categories.md`; точные
сигнатуры и механика реализации, включая решения, не зафиксированные явно в постановке (текст сообщения о
конфликте имени, предзаполнение типа при создании из активного фильтра, порядок и текст точки входа в
`SettingsPage`, видимость фильтра в пустом состоянии), зафиксированы и обоснованы в разделе «Decisions» выше.
