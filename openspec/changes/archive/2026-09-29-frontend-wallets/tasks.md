## 1. Тип `Wallet` и hooks данных

- [x] 1.1 Создать `frontend/src/features/wallets/Wallet.ts` с типом `Wallet` (форма `WalletOut`: `id`, `name`,
      `icon`, `currency_ids`, `created_at`, `updated_at`) и типом `WalletFormValues` (`name`, `icon`,
      `currency_ids`), без camelCase-маппинга (design.md, раздел «`Wallet` — без camelCase-маппинга»)
- [x] 1.2 Реализовать `useWallets` в `frontend/src/features/wallets/useWallets.ts` (`useQuery`,
      `WALLETS_QUERY_KEY = ["wallets"]`, `GET /api/wallets` через `useApiClient`, `query: { limit: 100, offset: 0
      }`, возвращает `page.items` без маппинга) и `useWallets.test.ts` (`FakeApiClient`: успешная загрузка,
      состояние ошибки)
- [x] 1.3 Реализовать `useCreateWallet` в `frontend/src/features/wallets/useCreateWallet.ts` (`useMutation`,
      `POST /api/wallets`, `meta: { silent: true }`, `onSuccess` → `invalidateQueries({ queryKey:
      WALLETS_QUERY_KEY })`) и `useCreateWallet.test.ts` (успех вызывает инвалидацию кэша, ошибка не вызывает
      глобальный toast сама по себе — `silent`)
- [x] 1.4 Реализовать `useUpdateWallet` в `frontend/src/features/wallets/useUpdateWallet.ts` (`useMutation`,
      вход `{ id, values }`, `PUT /api/wallets/{id}`, `meta: { silent: true }`, `onSuccess` → инвалидация того же
      `queryKey`) и `useUpdateWallet.test.ts`
- [x] 1.5 Реализовать `useDeleteWallet` в `frontend/src/features/wallets/useDeleteWallet.ts` (`useMutation`,
      вход `id`, `DELETE /api/wallets/{id}`, **без** `meta: { silent: true }` и без `onError` — 409 показывает
      `error.detail` через `MESSAGE_BUILDERS.conflict` глобального обработчика, design.md), `onSuccess` →
      инвалидация того же `queryKey`, и `useDeleteWallet.test.ts` (успех инвалидирует кэш; ошибка не обрабатывается
      локально)

## 2. `WalletForm`

- [x] 2.1 Реализовать `frontend/src/features/wallets/WalletForm.tsx`: пропы `{ open, onClose, wallet? }`
      (design.md), поля `name` (`Input`, обязательное), `icon` (`IconPicker`, обязательное), `currency_ids`
      (`CurrencyPicker multiple`, обязательное, минимум одна валюта); контейнер — `Drawer` на телефоне / `Modal`
      на широком экране по `useIsMobile()`
- [x] 2.2 Реализовать безусловный вызов `useCreateWallet()`/`useUpdateWallet()` и выбор мутации по наличию
      `wallet` в `handleSubmit`; `useEffect` на `open`/`wallet` — `form.setFieldsValue(...)` при редактировании
      (без запроса `GET /api/wallets/{id}`), `form.resetFields()` при создании
- [x] 2.3 Реализовать обработку ошибок отправки: `meta: { silent: true }` уже задан в hook'ах, `onError` формы —
      `kind === "validation"` → `applyFieldErrors(apiError, ["name", "icon", "currency_ids"])` + `form.setFields`
      + `toast.error(toastMessage)`, иначе → `toast.error(resolveErrorMessage(apiError))`; `onSuccess` —
      `toast.success(...)`, `onClose()`
- [x] 2.4 Написать `WalletForm.test.tsx`: создание (успех добавляет кошелёк, форма закрывается), редактирование
      (поля предзаполнены значениями переданного `wallet`, успех обновляет данные), ошибка валидации по полю
      (`name`/`icon`/`currency_ids`) остаётся в форме и не закрывает её, `Drawer` на телефоне / `Modal` на широком
      экране (мок `matchMedia`, по образцу `IconPicker.test.tsx`)

## 3. `WalletCard` и список

- [x] 3.1 Реализовать `frontend/src/features/wallets/WalletCard.tsx`: пропы `{ wallet, currencyCodes, onEdit }`
      (design.md); `Card` с `Icon`, названием, `Tag` на каждый код валюты (в порядке `currencyCodes`), кнопки
      «Редактировать» (`onClick={() => onEdit(wallet)}`) и «Удалить» (`Popconfirm` + собственный вызов
      `useDeleteWallet()`)
- [x] 3.2 Написать `WalletCard.test.tsx`: рендер иконки/названия/чипов валют в переданном порядке, нажатие
      «Редактировать» вызывает `onEdit` с этим кошельком, подтверждение в `Popconfirm` вызывает `DELETE
      /api/wallets/{id}`, отмена подтверждения не вызывает запрос

## 4. `WalletsPage`

- [x] 4.1 Реализовать `frontend/src/features/wallets/WalletsPage.tsx`: `useWallets()` + `useCurrencies()`,
      построение `Map<string, Currency>` для разрешения `currencyCodes` каждой карточки по `wallet.currency_ids`,
      состояние `formState` (`{ open, wallet? }`) для кнопки «Создать кошелёк» и кнопок «Редактировать» карточек,
      единственный `<WalletForm>` на странице
- [x] 4.2 Реализовать состояния экрана: индикатор загрузки на `walletsQuery.isPending`, `EmptyState` (`icon:
      "wallet"`, заголовок, действие «Создать кошелёк») при пустом списке, иначе — заголовок + кнопка «Создать
      кошелёк» + список `WalletCard` в порядке ответа backend (без клиентской пересортировки)
- [x] 4.3 Написать `WalletsPage.test.tsx`: загрузка и рендер списка карточек с чипами валют, пустой список
      показывает `EmptyState` и кнопка действия открывает форму создания, кнопка «Создать кошелёк» и
      «Редактировать» карточки открывают форму с ожидаемыми пропами, ошибка загрузки показывает toast (общий
      обработчик)

## 5. Навигация и маршрут

- [x] 5.1 Добавить пункт `{ key: "wallets", path: "/wallets", label: "Кошельки", icon: "wallet" }` в
      `frontend/src/app/navItems.ts` вторым пунктом — после «Главная», перед «Настройки» (итоговый порядок к концу
      014/016/018: Главная, Кошельки, Операции, Аналитика, Настройки — «Настройки» остаётся последним пунктом,
      обычная практика мобильной навигации; 016/018 при добавлении своих пунктов тоже вставляют их перед
      «Настройки», не после)
- [x] 5.2 Добавить маршрут `{ path: "wallets", element: <WalletsPage /> }` в защищённое поддерево
      `frontend/src/app/routes.tsx` (внутри существующего `RequireAuth`)

## 6. Интеграционные и сквозные тесты

- [x] 6.1 Обновить/дополнить интеграционный тест навигации (по образцу существующих тестов `app`/`renderApp`):
      пункт «Кошельки» виден авторизованному пользователю и ведёт на `/wallets`
- [x] 6.2 Проверить тестом, что прямой переход на `/wallets` без сессии перенаправляет на `/login` (по образцу
      существующих тестов `RequireAuth`)

## 7. QualityGate

- [x] 7.1 `make format`
- [x] 7.2 `make lint`
- [x] 7.3 `make test`
- [x] 7.4 `openspec validate frontend-wallets --strict` и `openspec validate --all --strict`
