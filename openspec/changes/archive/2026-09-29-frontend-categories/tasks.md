## 1. Тип `Category` и hooks данных

- [x] 1.1 Создать `frontend/src/features/categories/Category.ts` с типом `CategoryType` (`"income" | "expense"`),
      типом `Category` (форма `CategoryOut`: `id`, `type`, `name`, `icon`, `created_at`, `updated_at`) и типом
      `CategoryFormValues` (`type`, `name`, `icon`), без camelCase-маппинга (design.md, раздел «`Category`»)
- [x] 1.2 Реализовать `useCategories` в `frontend/src/features/categories/useCategories.ts` (`useQuery`,
      `CATEGORIES_QUERY_KEY = ["categories"]`, `categoryQueryKey(type)` → `[...CATEGORIES_QUERY_KEY, type ?? "all"]`,
      `GET /api/categories` через `useApiClient`, `query: { type, limit: 100, offset: 0 }`, возвращает `page.items`
      без маппинга) и `useCategories.test.ts` (`FakeApiClient`: успешная загрузка без фильтра, загрузка с фильтром
      `type` передаёт его в query, разные значения `type` кешируются раздельными ключами, состояние ошибки)
- [x] 1.3 Реализовать `useCreateCategory` в `frontend/src/features/categories/useCreateCategory.ts` (`useMutation`,
      `POST /api/categories`, `meta: { silent: true }`, `onSuccess` → `invalidateQueries({ queryKey:
      CATEGORIES_QUERY_KEY })`) и `useCreateCategory.test.ts` (успех вызывает инвалидацию кэша по префиксу, ошибка
      не вызывает глобальный toast сама по себе — `silent`)
- [x] 1.4 Реализовать `useUpdateCategory` в `frontend/src/features/categories/useUpdateCategory.ts` (`useMutation`,
      вход `{ id, values }`, `PUT /api/categories/{id}`, `meta: { silent: true }`, `onSuccess` → инвалидация того
      же `queryKey` по префиксу) и `useUpdateCategory.test.ts`
- [x] 1.5 Реализовать `useDeleteCategory` в `frontend/src/features/categories/useDeleteCategory.ts` (`useMutation`,
      вход `id`, `DELETE /api/categories/{id}`, **без** `meta: { silent: true }` и без `onError` — 409 показывает
      `error.detail` через `MESSAGE_BUILDERS.conflict` глобального обработчика, по образцу `useDeleteWallet`,
      design.md), `onSuccess` → инвалидация того же `queryKey`, и `useDeleteCategory.test.ts` (успех инвалидирует
      кэш; ошибка не обрабатывается локально)

## 2. `CategoryForm`

- [x] 2.1 Реализовать `frontend/src/features/categories/CategoryForm.tsx`: пропы `{ open, onClose, defaultType?,
      category? }` (design.md), поля `type` (`Segmented`, опции «Доход»/«Расход», обязательное), `name` (`Input`,
      обязательное), `icon` (`IconPicker`, обязательное); контейнер — `Drawer` на телефоне / `Modal` на широком
      экране по `useIsMobile()`
- [x] 2.2 Реализовать безусловный вызов `useCreateCategory()`/`useUpdateCategory()` и выбор мутации по наличию
      `category` в `handleSubmit`; `useEffect` на `open`/`category` — `form.setFieldsValue(...)` значениями
      категории при редактировании (без запроса `GET /api/categories/{id}`), либо `form.setFieldsValue({ type:
      defaultType ?? "income", name: "", icon: undefined })` при создании
- [x] 2.3 Реализовать обработку ошибок отправки: `meta: { silent: true }` уже задан в hook'ах, `onError` формы —
      `kind === "validation"` → `applyFieldErrors(apiError, ["type", "name", "icon"])` + `form.setFields` +
      `toast.error(toastMessage)`; **`kind === "conflict"` → `form.setFields([{ name: "name", errors:
      ["Категория с таким названием уже существует в этом типе"] }])` без toast**, по образцу `RegisterPage`
      (НЕ по образцу `useDeleteWallet`); иначе → `toast.error(resolveErrorMessage(apiError))`; `onSuccess` —
      `toast.success(...)`, `onClose()`
- [x] 2.4 Написать `CategoryForm.test.tsx`: создание для обоих типов (успех добавляет категорию, форма
      закрывается), редактирование (поля предзаполнены значениями переданной `category`, успех обновляет данные),
      ошибка валидации по полю (`type`/`name`/`icon`) остаётся в форме и не закрывает её, **конфликт имени (409)
      показывает сообщение именно на поле `name`, форма не закрывается, глобальный toast не вызывается**,
      предзаполнение `type` из `defaultType` при создании, `Drawer` на телефоне / `Modal` на широком экране (мок
      `matchMedia`, по образцу `WalletForm.test.tsx`)

## 3. `CategoryCard` и список с фильтром

- [x] 3.1 Реализовать `frontend/src/features/categories/CategoryCard.tsx`: пропы `{ category, onEdit }`
      (design.md); `Card` с `Icon`, названием, `Tag` с индикатором типа (`color="success"`/«Доход» для `income`,
      `color="error"`/«Расход» для `expense`, через таблицу `TYPE_TAG`, без цепочки `if`), кнопки «Редактировать»
      (`onClick={() => onEdit(category)}`) и «Удалить» (`Popconfirm` + собственный вызов `useDeleteCategory()`)
- [x] 3.2 Написать `CategoryCard.test.tsx`: рендер иконки/названия/индикатора типа для обоих типов, нажатие
      «Редактировать» вызывает `onEdit` с этой категорией, подтверждение в `Popconfirm` вызывает `DELETE
      /api/categories/{id}`, отмена подтверждения не вызывает запрос

## 4. `CategoriesPage`

- [x] 4.1 Реализовать `frontend/src/features/categories/CategoriesPage.tsx`: состояние фильтра `FilterValue =
      "all" | CategoryType` (по умолчанию `"all"`), `Segmented` над списком с опциями «Все»/«Доход»/«Расход»,
      `useCategories(filter === "all" ? undefined : filter)`, состояние `formState` (`{ open, category? }`) для
      кнопки «Создать категорию» (передаёт `defaultType` от активного фильтра) и кнопок «Редактировать» карточек,
      единственный `<CategoryForm>` на странице
- [x] 4.2 Реализовать состояния экрана: индикатор загрузки на `categoriesQuery.isPending`, фильтр остаётся видимым
      всегда (design.md), `EmptyState` (`icon: "coins"`, заголовок, действие «Создать категорию») при пустом
      отфильтрованном списке, иначе — кнопка «Создать категорию» + список `CategoryCard` в порядке ответа backend
      (без клиентской пересортировки)
- [x] 4.3 Написать `CategoriesPage.test.tsx`: загрузка и рендер списка карточек с индикаторами типа, переключение
      `Segmented`-фильтра меняет отображаемый набор и повторно запрашивает `GET /api/categories` с нужным `type`,
      пустой отфильтрованный список показывает `EmptyState` при видимом фильтре, кнопка действия открывает форму
      создания с предзаполненным `defaultType`, кнопка «Редактировать» карточки открывает форму с ожидаемыми
      пропами, ошибка загрузки показывает toast (общий обработчик)

## 5. Маршрут и точка входа

- [x] 5.1 Добавить маршрут `{ path: "categories", element: <CategoriesPage /> }` в защищённое поддерево
      `frontend/src/app/routes.tsx` (внутри существующего `RequireAuth`), **без** изменений `app/navItems.ts`
- [x] 5.2 Добавить `Card title="Категории"` в `frontend/src/features/settings/SettingsPage.tsx` вторым блоком
      (после «Тема оформления», перед «Смена пароля», design.md) со ссылкой-кнопкой «Открыть» (`react-router
      Link` на `/categories`)

## 6. Интеграционные и сквозные тесты

- [x] 6.1 Обновить/дополнить тест `SettingsPage` (по образцу существующих тестов секций страницы): блок
      «Категории» виден и ссылка ведёт на `/categories`
- [x] 6.2 Проверить тестом, что прямой переход на `/categories` без сессии перенаправляет на `/login` (по образцу
      существующих тестов `RequireAuth` для `/wallets`)

## 7. QualityGate

- [x] 7.1 `make format`
- [x] 7.2 `make lint`
- [x] 7.3 `make test`
- [x] 7.4 `openspec validate frontend-categories --strict` и `openspec validate --all --strict`
