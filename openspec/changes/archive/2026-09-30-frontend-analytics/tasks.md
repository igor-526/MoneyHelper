## 1. Тип `AnalyticsResult`/`AnalyticsFilters` и hook `useAnalytics`

- [x] 1.1 Создать `frontend/src/features/analytics/Analytics.ts` с типами `GroupBy`, `AnalyticsBucket` (форма
      `AnalyticsBucketOut`: `group_key`, `income`, `expense`, без camelCase-маппинга), `AnalyticsResult` (форма
      `AnalyticsOut`: `display_currency_id`, `buckets`, `unconverted_currencies`, без camelCase-маппинга) и
      `AnalyticsFilters` (вход `useAnalytics`: `displayCurrencyId`, `dateFrom`, `dateTo`, `groupBy` — обязательные;
      `walletId`, `categoryId`, `currencyId`, `type` — опциональные; camelCase, конвенция GET-фильтров, design.md)
- [x] 1.2 Реализовать `useAnalytics` в `frontend/src/features/analytics/useAnalytics.ts`: константа
      `ANALYTICS_QUERY_KEY = ["analytics"]`, `useQuery` с `GET /api/analytics` (query: `display_currency`,
      `date_from`, `date_to`, `group_by`, `wallet_id`, `category_id`, `currency_id`, `type`, явно смаппленные из
      `AnalyticsFilters`), `enabled: filters !== null`, без `meta: { silent: true }` (design.md, раздел
      «`useAnalytics`»); написать `useAnalytics.test.ts` (`FakeApiClient`: `filters === null` не выполняет запрос,
      заполнение всех обязательных полей выполняет запрос с корректными query-параметрами, каждый сужающий фильтр
      по отдельности и в комбинации передаётся как query-параметр, отсутствующий сужающий фильтр не передаётся,
      ошибка запроса не подавляется (`silent` не установлен))

## 2. `buildAnalyticsFilters` — проверка полноты обязательных полей

- [x] 2.1 Реализовать `frontend/src/features/analytics/buildAnalyticsFilters.ts`: тип `AnalyticsPageState` (три
      обязательных поля как `| undefined`/`| null`, четыре сужающих опциональных, `type: "all" | CategoryType`),
      константа `INITIAL_ANALYTICS_STATE`, чистая функция `buildAnalyticsFilters(state): AnalyticsFilters | null`,
      возвращающая `null`, если хотя бы одно из трёх обязательных полей не заполнено, иначе — собранный
      `AnalyticsFilters` (`dateFrom`/`dateTo` — `startOf("day")`/`endOf("day")` выбранного диапазона в ISO, `type:
      "all"` преобразуется в `undefined`) (design.md, раздел «единый объект с опциональными полями»)
- [x] 2.2 Написать `buildAnalyticsFilters.test.ts`: `null` при отсутствии каждого из трёх обязательных полей по
      отдельности и во всех комбинациях их отсутствия, корректный результат при заполнении всех обязательных без
      сужающих фильтров, корректный результат с каждым сужающим фильтром и их комбинацией, `type: "all"` даёт
      `type: undefined` в результате, `dateFrom`/`dateTo` равны началу первого и концу последнего выбранного дня

## 3. `AnalyticsPage` — обязательные поля и состояние «недостаточно данных»

- [x] 3.1 Реализовать каркас `frontend/src/features/analytics/AnalyticsPage.tsx`: состояние
      `useState<AnalyticsPageState>(INITIAL_ANALYTICS_STATE)`, `filters = useMemo(() =>
      buildAnalyticsFilters(state), [state])`, вызов `useAnalytics(filters)`; обязательные элементы управления —
      `CurrencyPicker` (одиночный режим) для валюты отображения, `DatePicker.RangePicker` для диапазона дат,
      `Segmented` с тремя опциями («Кошелёк»/«Категория»/«Валюта» → `wallet`/`category`/`currency`) без значения
      по умолчанию для среза (design.md)
- [x] 3.2 Реализовать состояние «недостаточно данных»: при `filters === null` — `Alert type="info"` с текстом
      «Выберите валюту отображения, диапазон дат и срез, чтобы увидеть аналитику» вместо списка корзин; при
      `filters !== null` и `analyticsQuery.isPending` — индикатор загрузки (design.md, раздел «`Alert`-состояния»)
- [x] 3.3 Написать `AnalyticsPage.test.tsx` (часть 1): рендер `Alert` «недостаточно данных» при пустом состоянии,
      незаполнение по отдельности каждого из трёх обязательных полей не выполняет запрос, заполнение всех трёх
      выполняет запрос автоматически без кнопки подтверждения, индикатор загрузки во время ожидания ответа

## 4. Опциональные сужающие фильтры

- [x] 4.1 Реализовать четыре сужающих `Select` в `AnalyticsPage.tsx`: «Кошелёк» (`ALL_WALLETS` → «Все кошельки»,
      опции из `useWallets()`), «Категория» (`ALL_CATEGORIES` → «Все категории», опции из `useCategories(undefined)`),
      «Тип» (`ALL_TYPES` → «Все типы», опции «Доход»/«Расход»), «Валюта операции» (`ALL_CURRENCIES` → «Все
      валюты», опции из `useCurrencies()`, обычный `Select`, не `CurrencyPicker`) (design.md, раздел «Элементы
      управления»)
- [x] 4.2 Дополнить `AnalyticsPage.test.tsx`: каждый сужающий фильтр по отдельности передаёт соответствующий
      query-параметр и обновляет результат, комбинация нескольких сужающих фильтров передаёт их все одновременно,
      значение «Все …» не передаёт соответствующий параметр

## 5. Резолюция подписей корзин и рендер карточек

- [x] 5.1 Реализовать `frontend/src/features/analytics/useBucketLabelResolvers.ts`: hook, строящий три `Map`
      (`useWallets()`/`useCategories(undefined)`/`useCurrencies()`) через `useMemo` и возвращающий
      `Record<GroupBy, (key: string) => string | undefined>` (design.md, раздел «Реестр резолверов подписи»)
- [x] 5.2 Написать `useBucketLabelResolvers.test.ts`: резолвер `wallet` возвращает название кошелька по id,
      резолвер `category` — название категории, резолвер `currency` — код валюты; каждый резолвер возвращает
      `undefined` для неизвестного id
- [x] 5.3 Реализовать `frontend/src/features/analytics/AnalyticsBucketCard.tsx`: пропы `{ label, bucket }`,
      единый простой рендер без иконки/тега типа — подпись, доход (`Typography.Text type="success"`) и расход
      (`Typography.Text type="danger"`), оба всегда отображаются, включая нулевые значения (design.md)
- [x] 5.4 Написать `AnalyticsBucketCard.test.tsx`: рендер подписи, дохода и расхода при ненулевых значениях,
      рендер нулевого дохода/расхода без скрытия соответствующей строки
- [x] 5.5 Реализовать в `AnalyticsPage.tsx` вычисление отсортированного списка карточек: резолюция подписи каждой
      корзины через `labelResolvers[filters.groupBy]` (`"…"` для нерезолвленных), сортировка по подписи
      (`localeCompare`), рендер `AnalyticsBucketCard` без пагинации; строка «Суммы в {код валюты отображения}» над
      списком карточек (design.md)
- [x] 5.6 Дополнить `AnalyticsPage.test.tsx`: успешный запрос с каждым `group_by` по отдельности отображает
      карточки с корректно резолвленной подписью (кошелёк/категория/валюта), карточки отображаются в алфавитном
      порядке подписи независимо от порядка ответа backend и от величины сумм, состояние «нет данных за период»
      (`EmptyState`) при пустом списке корзин после успешного запроса

## 6. Предупреждение о валютах без курса

- [x] 6.1 Реализовать в `AnalyticsPage.tsx` `Alert type="warning"` над списком карточек при непустом
      `unconverted_currencies`: текст «Не удалось пересчитать суммы в валютах: {коды через запятую} — нет курса за
      выбранный период», коды резолвлены через `Map` из `useCurrencies()`, `"…"` для нерезолвленных (design.md)
- [x] 6.2 Дополнить `AnalyticsPage.test.tsx`: предупреждение отображается с корректными кодами при непустом
      `unconverted_currencies`, предупреждение отсутствует при пустом списке

## 7. Навигация и маршрут

- [x] 7.1 Добавить пункт `{ key: "analytics", path: "/analytics", label: "Аналитика", icon: "trending-up" }` в
      `frontend/src/app/navItems.ts` между «Операции» и «Настройки»
- [x] 7.2 Добавить маршрут `{ path: "analytics", element: <AnalyticsPage /> }` в защищённое поддерево
      `frontend/src/app/routes.tsx` (внутри существующего `RequireAuth`, перед `settings`)
- [x] 7.3 Дополнить тесты маршрутизации/навигации (по образцу тестов `RequireAuth`/`navItems` для
      `/transactions`/`/wallets`): прямой переход на `/analytics` без сессии перенаправляет на `/login`; пункт
      навигации «Аналитика» присутствует между «Операции» и «Настройки», «Настройки» остаётся последним пунктом

## 8. Ошибки API

- [x] 8.1 Дополнить `AnalyticsPage.test.tsx`/`useAnalytics.test.ts`: ошибка backend (неизвестная валюта
      отображения, `date_from` позже `date_to`) показывает toast с текстом ошибки по общему правилу обработки
      ошибок API, без специальной обработки этих конкретных бизнес-правил, список корзин не отображается

## 9. QualityGate

- [x] 9.1 `make format`
- [x] 9.2 `make lint`
- [x] 9.3 `make test`
- [x] 9.4 `openspec validate frontend-analytics --strict` и `openspec validate --all --strict`
