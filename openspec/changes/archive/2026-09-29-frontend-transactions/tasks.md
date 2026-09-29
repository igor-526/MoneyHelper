## 1. Расширение `CurrencyPicker` (`allowedIds`)

- [x] 1.1 Добавить в `frontend/src/shared/ui/CurrencyPicker/CurrencyPicker.tsx` необязательный проп
      `allowedIds?: string[]` в `CurrencyPickerBaseProps`; отфильтровать список `options` до валют, чьи `id`
      входят в `allowedIds`, когда проп передан, иначе оставить полный список (design.md, раздел «`CurrencyPicker`
      — расширение `allowedIds`»)
- [x] 1.2 Дополнить `frontend/src/shared/ui/CurrencyPicker/CurrencyPicker.test.tsx` новыми сценариями: список опций
      без `allowedIds` совпадает с полным списком валют (регресс существующего поведения), список опций с
      `allowedIds` содержит только переданные id — для одиночного и множественного режимов
- [x] 1.3 Убедиться, что `WalletForm` (`frontend/src/features/wallets/WalletForm.tsx`) не требует изменений — проп
      `allowedIds` не передаётся, существующие тесты `WalletForm.test.tsx` остаются зелёными без правок

## 2. Тип `Transaction` и hooks списка/мутаций

- [x] 2.1 Создать `frontend/src/features/transactions/Transaction.ts` с типами `TransactionLeg`, `Transaction`
      (форма `TransactionOut`: `id`, `wallet_id`, `category_id`, `legs`, `occurred_at`, `created_at`,
      `updated_at`), `TransactionFormValues` (тело `TransactionCreate`/`TransactionUpdate`: `wallet_id`,
      `category_id`, `currency_id`, `amount`, необязательный `occurred_at`) и `WalletBalance` (форма
      `WalletBalanceOut`), без camelCase-маппинга (design.md)
- [x] 2.2 Реализовать `useTransactions` в `frontend/src/features/transactions/useTransactions.ts`: константы
      `TRANSACTIONS_QUERY_KEY = ["transactions"]`, `DEFAULT_PAGE_SIZE = 20`, тип `TransactionFilters`, функция
      `transactionsQueryKey(filters, pagination)`, `useQuery` с `GET /api/transactions` (query: `wallet_id`,
      `category_id`, `type`, `date_from`, `date_to`, `limit`, `offset`), возвращает весь `Page<Transaction>` (не
      только `items` — нужен `total` для пагинации), и `useTransactions.test.ts` (`FakeApiClient`: загрузка без
      фильтров, каждый фильтр по отдельности передаётся в query, комбинация фильтров, разные `offset`/`limit`
      кешируются раздельными ключами, состояние ошибки)
- [x] 2.3 Реализовать `useCreateTransaction` в `frontend/src/features/transactions/useCreateTransaction.ts`
      (`useMutation`, `POST /api/transactions`, `meta: { silent: true }`, `onSuccess` → `invalidateQueries` по
      `TRANSACTIONS_QUERY_KEY` И по `WALLET_BALANCES_QUERY_KEY`) и `useCreateTransaction.test.ts` (успех вызывает
      обе инвалидации, ошибка не вызывает глобальный toast сама по себе — `silent`)
- [x] 2.4 Реализовать `useUpdateTransaction` в `frontend/src/features/transactions/useUpdateTransaction.ts` (вход
      `{ id, values }`, `PUT /api/transactions/{id}`, `meta: { silent: true }`, та же двойная инвалидация) и
      `useUpdateTransaction.test.ts`
- [x] 2.5 Реализовать `useDeleteTransaction` в `frontend/src/features/transactions/useDeleteTransaction.ts`
      (`DELETE /api/transactions/{id}`, **без** `meta: { silent: true }` и без `onError` — по образцу
      `useDeleteWallet`/`useDeleteCategory`, design.md), `onSuccess` → та же двойная инвалидация, и
      `useDeleteTransaction.test.ts` (успех инвалидирует оба кэша; ошибка не обрабатывается локально)

## 3. `useWalletBalances`

- [x] 3.1 Реализовать `useWalletBalances` в `frontend/src/features/transactions/useWalletBalances.ts`:
      `WALLET_BALANCES_QUERY_KEY = ["wallet-balances"]`, `useQuery` с `queryKey: [...WALLET_BALANCES_QUERY_KEY,
      walletId]`, `GET /api/wallets/{walletId}/balances`, `enabled: walletId !== undefined` (design.md)
- [x] 3.2 Написать `useWalletBalances.test.ts`: запрос не выполняется при `walletId === undefined`, успешная
      загрузка возвращает список балансов, разные `walletId` кешируются раздельными ключами, состояние ошибки

## 4. `TransactionForm`

- [x] 4.1 Реализовать `frontend/src/features/transactions/TransactionForm.tsx`: пропы `{ open, onClose,
      transaction? }`; поля antd `Form` (`TransactionFormFields`): `wallet_id` (`Select` из `useWallets()`),
      `category_id` (`Select` из `useCategories(type)`), `currency_id` (`CurrencyPicker` с
      `allowedIds={selectedWallet?.currency_ids}`), `amount` (`MoneyInput` с `decimalPlaces` из `useCurrencies()`
      по `currency_id`), `occurred_at` (antd `DatePicker showTime`, необязателен); тип-переключатель (`Segmented`
      «Доход»/«Расход») — локальный `useState<CategoryType>`, вне `Form`, не входит в тело запроса; контейнер —
      `Drawer` на телефоне / `Modal` на широком экране по `useIsMobile()` (design.md)
- [x] 4.2 Реализовать сброс `category_id` при смене типа и сброс `currency_id` при смене `wallet_id`; `useEffect`
      на `open`/`transaction` — при редактировании находит тип текущей категории в `useCategories(undefined)`
      (полный список) и предзаполняет переключатель и поля формы значениями операции (`transaction.legs[0]` для
      `currency_id`/`amount`, `dayjs(transaction.occurred_at)` для `occurred_at`), при создании — сброс к типу
      «Доход» и пустым полям
- [x] 4.3 Реализовать безусловный вызов `useCreateTransaction()`/`useUpdateTransaction()` и выбор мутации по
      наличию `transaction` в `handleSubmit`; сборку `TransactionFormValues` из `TransactionFormFields`
      (`occurred_at: fields.occurred_at?.toISOString()`, поле `type` не входит в отправляемое тело)
- [x] 4.4 Реализовать обработку ошибок отправки: `KNOWN_FIELDS = ["wallet_id", "category_id", "currency_id",
      "amount", "occurred_at"]`, `onError` — `kind === "validation"` → `applyFieldErrors(apiError, KNOWN_FIELDS)` +
      `form.setFields` + `toast.error(toastMessage)` (покрывает и per-field ошибки Pydantic, и текстовые бизнес-
      правила backend — валюта не из набора кошелька, превышение знаков суммы — без специальных веток, design.md);
      иначе → `toast.error(resolveErrorMessage(apiError))`; `onSuccess` — `toast.success(...)`, `onClose()`
- [x] 4.5 Написать `TransactionForm.test.tsx`: создание дохода и расхода (успех добавляет операцию, тело запроса
      не содержит поле типа), редактирование (поля и переключатель типа предзаполнены по данным операции, включая
      вычисление типа по `category_id`), смена типа сбрасывает `category_id`, смена кошелька сбрасывает
      `currency_id`, список валют в `CurrencyPicker` ограничен набором выбранного кошелька, ошибка валидации по
      полю остаётся в форме и не закрывает её, текстовая ошибка бизнес-правила backend (например «валюта не входит
      в набор валют кошелька») показывается toast без падения формы, `Drawer` на телефоне / `Modal` на широком
      экране (мок `matchMedia`, по образцу `WalletForm.test.tsx`)

## 5. `TransactionCard`, `WalletBalanceCard` и список с фильтрами и пагинацией

- [x] 5.1 Реализовать `frontend/src/features/transactions/TransactionCard.tsx`: пропы `{ transaction, walletName,
      category, currencyCode, onEdit }` (design.md); `Card` с названием кошелька, `Icon`+названием категории+`Tag`
      типа (локальная таблица `TYPE_TAG`), суммой (`transaction.legs[0].amount`) и кодом валюты, отформатированной
      датой `occurred_at`; кнопки «Редактировать» (`onClick={() => onEdit(transaction)}`) и «Удалить»
      (`Popconfirm` + собственный вызов `useDeleteTransaction()`)
- [x] 5.2 Написать `TransactionCard.test.tsx`: рендер всех полей карточки, нажатие «Редактировать» вызывает
      `onEdit` с этой операцией, подтверждение `Popconfirm` вызывает `DELETE /api/transactions/{id}`, отмена не
      вызывает запрос, рендер при `walletName`/`category`/`currencyCode === undefined` (данные ещё не резолвлены)
- [x] 5.3 Реализовать `frontend/src/features/transactions/WalletBalanceCard.tsx`: пропы `{ walletId,
      currencyCodeById }`, вызывает `useWalletBalances(walletId)`, рендерит `Card` со списком «код: сумма» по
      каждой валюте (включая нулевой баланс), `Spin` во время загрузки (design.md)
- [x] 5.4 Написать `WalletBalanceCard.test.tsx`: рендер списка балансов по валютам, включая нулевой баланс,
      состояние загрузки, ошибка загрузки не приводит к падению компонента

## 6. `TransactionsPage`

- [x] 6.1 Реализовать `frontend/src/features/transactions/TransactionsPage.tsx`: состояние `FiltersState`
      (`walletId`, `categoryId`, `type`, `dateRange`, все по умолчанию «без фильтра») и `page` (1-based); элементы
      управления — `Select` «Кошелёк» (сентинел `"all"` → «Все кошельки») из `useWallets()`, `Select` «Категория»
      (сентинел `"all"` → «Все категории») из `useCategories(undefined)`, `Segmented` «Все/Доход/Расход», `antd
      RangePicker` для диапазона дат; `updateFilters(patch)` — обновляет фильтры и сбрасывает `page` на 1
      (design.md)
- [x] 6.2 Реализовать вызов `useTransactions` с вычисленными `dateFrom`/`dateTo` (`startOf("day")`/`endOf("day")`
      выбранного диапазона в ISO) и `offset = (page - 1) * DEFAULT_PAGE_SIZE`; построить `Map`-ы `walletName`,
      `category`, `currencyCode` из уже загруженных `useWallets()`/`useCategories(undefined)`/`useCurrencies()`
      (`useMemo`) для передачи в `TransactionCard`
- [x] 6.3 Реализовать условный рендер `WalletBalanceCard` только при `filters.walletId !== undefined`; состояния
      экрана — индикатор загрузки на `transactionsQuery.isPending`, `EmptyState` (`icon`, заголовок, действие
      «Создать операцию») при пустом отфильтрованном списке, иначе — кнопка «Создать операцию» + список
      `TransactionCard` + `antd Pagination` (`current={page}`, `pageSize={DEFAULT_PAGE_SIZE}`,
      `total={data.total}`, `onChange={setPage}`, без селектора размера страницы)
- [x] 6.4 Написать `TransactionsPage.test.tsx`: загрузка и рендер списка карточек, каждый фильтр по отдельности
      передаёт нужный query-параметр и сбрасывает страницу на 1 (проверить смену страницы, затем смену фильтра),
      комбинация нескольких фильтров одновременно, переключение страницы запрашивает нужный `offset`, карточка
      баланса показывается только при конкретном фильтре «Кошелёк» и не показывается при «Все кошельки», пустой
      отфильтрованный список показывает `EmptyState`, кнопка действия открывает форму создания, кнопка
      «Редактировать» карточки открывает форму с ожидаемыми пропами, ошибка загрузки показывает toast

## 7. Навигация и маршрут

- [x] 7.1 Добавить пункт `{ key: "transactions", path: "/transactions", label: "Операции", icon: "banknote" }` в
      `frontend/src/app/navItems.ts` между пунктами «Кошельки» и «Настройки»
- [x] 7.2 Добавить маршрут `{ path: "transactions", element: <TransactionsPage /> }` в защищённое поддерево
      `frontend/src/app/routes.tsx` (внутри существующего `RequireAuth`)
- [x] 7.3 Обновить/дополнить тесты навигации (по образцу существующих тестов `navItems`/`AppLayout`): пункт
      «Операции» присутствует между «Кошельки» и «Настройки», активен на `/transactions`; прямой переход на
      `/transactions` без сессии перенаправляет на `/login` (по образцу существующих тестов `RequireAuth` для
      `/wallets`/`/categories`)

## 8. Интеграционные и сквозные тесты

- [x] 8.1 Проверить тестом сквозной сценарий: создание операции из пустого списка убирает `EmptyState` и
      добавляет карточку, редактирование этой карточки обновляет её данные, удаление возвращает список к
      `EmptyState`
- [x] 8.2 Проверить тестом, что успешная мутация (создание/редактирование/удаление операции) при открытой карточке
      баланса выбранного кошелька приводит к повторному запросу `GET /api/wallets/{id}/balances`

## 9. QualityGate

- [x] 9.1 `make format`
- [x] 9.2 `make lint`
- [x] 9.3 `make test`
- [x] 9.4 `openspec validate frontend-transactions --strict` и `openspec validate --all --strict`
