## 1. Тип `Transfer` и hooks списка/мутаций

- [x] 1.1 Создать `frontend/src/features/transfers/Transfer.ts` с типами `Transfer` (форма `TransferOut`: `id`,
      `from_wallet_id`, `to_wallet_id`, `currency_id`, `amount`, `occurred_at`, `created_at`, `updated_at`, без
      camelCase-маппинга) и `TransferFormValues` (тело `TransferCreate`/`TransferUpdate`), design.md
- [x] 1.2 Реализовать `useTransfers` в `frontend/src/features/transfers/useTransfers.ts`: константы
      `TRANSFERS_QUERY_KEY = ["transfers"]`, `DEFAULT_PAGE_SIZE = 20`, тип `TransferFilters` (`walletId`,
      `dateFrom`, `dateTo`), функция `transfersQueryKey(filters, pagination)`, `useQuery` с
      `GET /api/transfers` (query: `wallet_id`, `date_from`, `date_to`, `limit`, `offset`), возвращает весь
      `Page<Transfer>` (design.md); написать `useTransfers.test.ts` (`FakeApiClient`: загрузка без фильтров,
      каждый фильтр по отдельности, комбинация фильтров, разные `offset`/`limit` кешируются раздельно, ошибка)
- [x] 1.3 Реализовать `useCreateTransfer` в `frontend/src/features/transfers/useCreateTransfer.ts`
      (`useMutation`, `POST /api/transfers`, `meta: { silent: true }`, локальная константа
      `WALLET_BALANCES_QUERY_KEY = ["wallet-balances"]` — НЕ импорт из `features/transactions`, design.md,
      раздел «Три мутации переводов»; `onSuccess` → инвалидация `TRANSFERS_QUERY_KEY` и
      `WALLET_BALANCES_QUERY_KEY`) и `useCreateTransfer.test.ts`
- [x] 1.4 Реализовать `useUpdateTransfer` в `frontend/src/features/transfers/useUpdateTransfer.ts` (вход
      `{ id, values }`, `PUT /api/transfers/{id}`, `meta: { silent: true }`, та же двойная инвалидация) и
      `useUpdateTransfer.test.ts`
- [x] 1.5 Реализовать `useDeleteTransfer` в `frontend/src/features/transfers/useDeleteTransfer.ts`
      (`DELETE /api/transfers/{id}`, без `meta.silent`/`onError`, по образцу `useDeleteTransaction`), та же
      двойная инвалидация, и `useDeleteTransfer.test.ts`

## 2. `useCreateTopup`

- [x] 2.1 Дополнить `frontend/src/features/transactions/Transaction.ts` типом `TopupFormValues` (тело
      `TopupCreate`: `wallet_id`, `category_id`, `legs: TransactionLeg[]`, необязательный `occurred_at`)
- [x] 2.2 Реализовать `useCreateTopup` в `frontend/src/features/transactions/useCreateTopup.ts` (`useMutation`,
      `POST /api/transactions/topups`, `meta: { silent: true }`, `onSuccess` → инвалидация
      `TRANSACTIONS_QUERY_KEY` и `WALLET_BALANCES_QUERY_KEY`, импортированных из `useTransactions`/
      `useWalletBalances` этой же фичи, design.md) и `useCreateTopup.test.ts` (успех вызывает обе инвалидации,
      тело запроса содержит `legs` в переданном порядке, ошибка не вызывает глобальный toast сама по себе)

## 3. `TopupForm`

- [x] 3.1 Реализовать `frontend/src/features/transactions/TopupForm.tsx`: пропы `{ open, onClose }` (только
      создание, без режима редактирования — design.md, Non-Goals); поля `Form` (`TopupFormFields`): `wallet_id`
      (`Select` из `useWallets()`), `category_id` (`Select` из `useCategories("income")`), `amounts` (объектное
      поле `Record<string, string>`, адресуемое путём `["amounts", currencyId]`), `occurred_at` (antd
      `DatePicker showTime`, необязателен); контейнер — `Drawer`/`Modal` по `useIsMobile()` (design.md)
- [x] 3.2 Реализовать динамический рендер полей сумм — цикл по `selectedWallet?.currency_ids ?? []`
      (`selectedWallet` — из `useWallets()` по текущему `wallet_id`), каждое поле `Form.Item name={["amounts",
      currencyId]}` с `MoneyInput` и `decimalPlaces` этой валюты, подписанное её кодом; смена `wallet_id`
      сбрасывает `amounts` целиком (`form.setFieldsValue({ wallet_id: value, amounts: {} })`, design.md)
- [x] 3.3 Реализовать сборку `legs` на отправке в порядке `wallet.currency_ids`
      (`(selectedWallet?.currency_ids ?? []).map((currencyId) => ({ currency_id: currencyId, amount:
      fields.amounts[currencyId] }))`) и вызов `useCreateTopup()` с построенным `TopupFormValues`
- [x] 3.4 Реализовать обработку ошибок отправки: `KNOWN_FIELDS = ["wallet_id", "category_id"]` (осознанно узкий
      список — design.md, раздел «Обработка ошибок»), `onError` — `kind === "validation"` →
      `applyFieldErrors(apiError, KNOWN_FIELDS)` + `form.setFields` + `toast.error(toastMessage)` (покрывает и
      ошибки по конкретным ногам, и текстовые бизнес-правила backend — неполный/избыточный набор валют,
      категория не дохода — единым механизмом без специальных веток); иначе → `toast.error(resolveErrorMessage(...))`;
      `onSuccess` — `toast.success(...)`, `onClose()`
- [x] 3.5 Написать `TopupForm.test.tsx`: выбор кошелька строит поля сумм по числу его валют, смена кошелька
      сбрасывает введённые суммы и перестраивает поля, категория предлагает только доходные, успешное создание
      отправляет `legs` в порядке `currency_ids` кошелька, текстовая ошибка бизнес-правила (неполный/избыточный
      набор валют, категория не дохода) показывается toast без падения формы, ошибка по `wallet_id`/`category_id`
      остаётся в форме, `Drawer` на телефоне / `Modal` на широком экране (мок `matchMedia`)

## 4. `TransactionCard` — многоногое отображение и блокировка редактирования

- [x] 4.1 Заменить проп `currencyCode: string | undefined` на `currencyCodeById: Map<string, string>` в
      `frontend/src/features/transactions/TransactionCard.tsx` (design.md, раздел «TransactionCard»)
- [x] 4.2 Реализовать рендер суммы: одна строка «сумма код» при `transaction.legs.length === 1`, список строк
      (одна на каждую ногу) при `transaction.legs.length > 1`
- [x] 4.3 Реализовать блокировку кнопки «Редактировать» при `transaction.legs.length > 1`: `disabled`-кнопка
      под `Tooltip` с текстом «Пополнение с несколькими валютами нельзя редактировать — удалите и создайте
      заново» (обёртка `<span>` вокруг `disabled`-кнопки внутри `Tooltip`, design.md); кнопка «Удалить» остаётся
      доступной без изменений
- [x] 4.4 Обновить `frontend/src/features/transactions/TransactionCard.test.tsx`: рендер одной ноги (регресс),
      рендер нескольких ног (список строк с суммами всех валют), кнопка «Редактировать» недоступна и показывает
      подсказку при нескольких ногах, кнопка «Редактировать» кликабельна и вызывает `onEdit` при одной ноге,
      кнопка «Удалить» кликабельна в обоих случаях

## 5. `TransactionsPage` — «Добавить»-меню и ссылка «Переводы»

- [x] 5.1 Заменить кнопку «Создать операцию» на antd `Dropdown` с триггером `Button` «Добавить» и тремя
      пунктами меню («Доход/расход», «Пополнение», «Перевод») в `frontend/src/features/transactions/TransactionsPage.tsx`
      (design.md, раздел «"Добавить"-меню»); пункт «Доход/расход» открывает существующий `TransactionForm`,
      пункт «Пополнение» открывает новый `TopupForm`, пункт «Перевод» — `navigate("/transfers")`
      (`react-router-dom`)
- [x] 5.2 Добавить ссылку «Переводы» рядом с заголовком «Операции» (`navigate("/transfers")` по клику)
- [x] 5.3 Обновить вызов `TransactionCard` — передавать `currencyCodeById={currencyCodeById}` вместо резолюции
      одного кода валюты по `transaction.legs[0]`
- [x] 5.4 Сохранить поведение `EmptyState.action` — открывает напрямую `TransactionForm` (обычная операция), не
      всё меню (design.md, YAGNI)
- [x] 5.5 Обновить `frontend/src/features/transactions/TransactionsPage.test.tsx`: открытие меню «Добавить»
      показывает три пункта, пункт «Доход/расход» открывает `TransactionForm`, пункт «Пополнение» открывает
      `TopupForm`, пункт «Перевод» переходит на `/transfers` без открытия формы, ссылка «Переводы» переходит на
      `/transfers`, карточки с несколькими ногами получают корректный `currencyCodeById`

## 6. `TransferForm`

- [x] 6.1 Реализовать `frontend/src/features/transfers/TransferForm.tsx`: пропы `{ open, onClose, transfer? }`;
      поля `Form` (`TransferFormFields`): `from_wallet_id` (`Select` из `useWallets()`), `to_wallet_id`
      (`Select`, опции исключают текущий `from_wallet_id`), `currency_id` (`CurrencyPicker` с `allowedIds` —
      пересечение `from_wallet.currency_ids`/`to_wallet.currency_ids`), `amount` (`MoneyInput`), `occurred_at`
      (`DatePicker showTime`, необязателен); контейнер — `Drawer`/`Modal` по `useIsMobile()` (design.md)
- [x] 6.2 Реализовать вычисление пересечения валют (`useMemo` по найденным `fromWallet`/`toWallet` из
      `useWallets()`) и условный рендер: `CurrencyPicker` с `allowedIds={commonCurrencyIds}`, если пересечение
      не пусто или кошельки ещё не оба выбраны; предупреждающий текст «У этих кошельков нет общей валюты» вместо
      поля выбора валюты, если оба кошелька выбраны и пересечение пусто (design.md, точный текст)
- [x] 6.3 Реализовать сброс зависимых полей: смена `from_wallet_id`, совпадающая с текущим `to_wallet_id`,
      сбрасывает `to_wallet_id`; смена ЛЮБОГО из двух кошельков сбрасывает `currency_id`
- [x] 6.4 Реализовать `useEffect` предзаполнения при редактировании (`open`/`transfer`) — поля `from_wallet_id`,
      `to_wallet_id`, `currency_id`, `amount`, `occurred_at: dayjs(transfer.occurred_at)`; при создании — сброс
      всех полей
- [x] 6.5 Реализовать безусловный вызов `useCreateTransfer()`/`useUpdateTransfer()` и выбор мутации по наличию
      `transfer` в `handleSubmit`; сборку `TransferFormValues` из полей формы
- [x] 6.6 Реализовать обработку ошибок отправки: `KNOWN_FIELDS = ["from_wallet_id", "to_wallet_id",
      "currency_id", "amount", "occurred_at"]`, `onError` — `kind === "validation"` →
      `applyFieldErrors(apiError, KNOWN_FIELDS)` + `form.setFields` + `toast.error(toastMessage)` (покрывает и
      ошибки по полям, и текстовые бизнес-правила — отсутствие общей валюты, совпадение кошельков — без
      специальных веток); иначе → `toast.error(resolveErrorMessage(...))`; `onSuccess` — `toast.success(...)`,
      `onClose()`
- [x] 6.7 Написать `TransferForm.test.tsx`: целевой кошелёк исключает исходный из опций, смена исходного
      кошелька на совпадающий с целевым сбрасывает целевой, валюта ограничена пересечением наборов, смена любого
      кошелька сбрасывает валюту, отсутствие общей валюты показывает предупреждающий текст вместо поля выбора,
      успешное создание, успешное редактирование с предзаполнением полей, ошибка по полю остаётся в форме,
      текстовая ошибка бизнес-правила показывается toast, `Drawer`/`Modal` по `useIsMobile()`

## 7. `TransferCard` и список переводов с фильтрами и пагинацией

- [x] 7.1 Реализовать `frontend/src/features/transfers/TransferCard.tsx`: пропы `{ transfer, fromWalletName,
      toWalletName, currencyCode, onEdit }`; `Card` со строкой «{fromWalletName} → {toWalletName}», суммой и
      кодом валюты, датой, кнопками «Редактировать»/«Удалить» под `Popconfirm`, собственный вызов
      `useDeleteTransfer()` (design.md, без блокировки редактирования — у перевода всегда одна валюта)
- [x] 7.2 Написать `TransferCard.test.tsx`: рендер всех полей, нажатие «Редактировать» вызывает `onEdit`,
      подтверждение `Popconfirm` вызывает `DELETE /api/transfers/{id}`, отмена не вызывает запрос, рендер при
      нерезолвленных `fromWalletName`/`toWalletName`/`currencyCode`

## 8. `TransfersPage`

- [x] 8.1 Реализовать `frontend/src/features/transfers/TransfersPage.tsx`: заголовок «Переводы», состояние
      `FiltersState` (`walletId`, `dateRange`) и `page` (1-based); элементы управления — `Select` «Кошелёк»
      (сентинел `ALL_WALLETS` → «Все кошельки») из `useWallets()`, `antd RangePicker` для диапазона дат;
      `updateFilters(patch)` сбрасывает `page` на 1 (design.md)
- [x] 8.2 Реализовать вызов `useTransfers` с вычисленными `dateFrom`/`dateTo` и `offset`; построить `Map`-ы
      `walletName`, `currencyCode` из `useWallets()`/`useCurrencies()` (`useMemo`) для передачи в `TransferCard`
- [x] 8.3 Реализовать состояния экрана — индикатор загрузки, `EmptyState` (иконка `"wallet"`, заголовок,
      действие «Создать перевод») при пустом отфильтрованном списке, иначе — кнопка «Создать перевод» + список
      `TransferCard` + `antd Pagination` (`pageSize={DEFAULT_PAGE_SIZE}`, без селектора размера страницы)
- [x] 8.4 Написать `TransfersPage.test.tsx`: загрузка и рендер списка карточек, фильтр по кошельку передаёт
      `wallet_id` и сбрасывает страницу на 1, фильтр по диапазону дат передаёт `date_from`/`date_to`,
      переключение страницы запрашивает нужный `offset`, пустой отфильтрованный список показывает `EmptyState`,
      кнопка действия открывает форму создания, кнопка «Редактировать» карточки открывает форму с ожидаемыми
      пропами, ошибка загрузки показывает toast

## 9. Маршрут

- [x] 9.1 Добавить маршрут `{ path: "transfers", element: <TransfersPage /> }` в защищённое поддерево
      `frontend/src/app/routes.tsx` (внутри существующего `RequireAuth`, рядом с `transactions`); `navItems.ts`
      не менять (design.md, п. 1 и 6 постановки задачи)
- [x] 9.2 Дополнить тесты маршрутизации (по образцу тестов `RequireAuth` для `/wallets`/`/transactions`): прямой
      переход на `/transfers` без сессии перенаправляет на `/login`; пункт `navItems`, ведущий на `/transfers`,
      отсутствует

## 10. Интеграционные и сквозные тесты

- [x] 10.1 Проверить тестом сквозной сценарий на `TransfersPage`: создание перевода из пустого списка убирает
      `EmptyState` и добавляет карточку, редактирование обновляет её данные, удаление возвращает список к
      `EmptyState`
- [x] 10.2 Проверить тестом, что успешная мутация перевода (создание/редактирование/удаление) инвалидирует кэш
      `["wallet-balances"]` — если карточка баланса кошелька (`WalletBalanceCard`, `features/transactions`)
      открыта на экране «Операции», она перезапрашивает данные
- [x] 10.3 Проверить тестом сквозной сценарий на `TransactionsPage`: создание пополнения через меню «Добавить»
      добавляет в список многоногую операцию, карточка которой отображает все её ноги и блокирует
      «Редактировать»

## 11. QualityGate

- [x] 11.1 `make format`
- [x] 11.2 `make lint`
- [x] 11.3 `make test`
- [x] 11.4 `openspec validate frontend-transfers --strict` и `openspec validate --all --strict`
