## Why

Backend-капабилити кошельков (`wallets`, задача 008) и frontend-фундамент (`frontend-shell`, задача 013:
`CurrencyPicker`, `IconPicker`, `EmptyState`, `Page<T>`) уже готовы и заархивированы, но пользователь до сих пор
не может управлять кошельками через интерфейс — раздел «Кошельки» не существует ни в навигации, ни как экран.
Это первый из пяти оставшихся frontend-экранов (F2b дорожной карты) и зависимость для операций (016), поэтому
он должен появиться сейчас, переиспользуя готовые кирпичи 013 без изобретения новых.

## What Changes

- Новый пункт `navItems` («Кошельки», иконка `"wallet"` — уже существующее имя в `BUSINESS_ICONS`) и маршрут
  `/wallets` в `app/routes.tsx` под `RequireAuth`, третий из пяти пунктов нижней панели.
- `features/wallets/useWallets` — hook на `useQuery`, читающий `GET /api/wallets` одним запросом с максимальным
  `limit` (100), без клиентской постраничной подгрузки (по образцу `useCurrencies`, 013).
- `features/wallets/useCreateWallet`, `useUpdateWallet`, `useDeleteWallet` — мутации на `useMutation`,
  инвалидирующие общий `queryKey` списка кошельков на `onSuccess`.
- `features/wallets/WalletForm` — один компонент формы (название, `IconPicker`, `CurrencyPicker` в режиме
  `multiple`), используемый и для создания, и для редактирования; открывается в `Drawer` на телефоне / `Modal` на
  широком экране поверх экрана списка (по образцу `IconPicker`, 013), без отдельного маршрута.
- `features/wallets/WalletCard` и `features/wallets/WalletsPage` — список карточек кошельков (иконка, название,
  валюты чипами `antd Tag`) в порядке, отданном backend; пустое состояние — `EmptyState` (013) с кнопкой «Создать
  кошелёк».
- Удаление кошелька — `Popconfirm` на карточке; 409 (кошелёк с операциями) обрабатывается общим глобальным
  обработчиком ошибок (`MESSAGE_BUILDERS.conflict` уже показывает `error.detail` от backend), без специального
  кода в этом изменении.
- Тесты hooks и компонентов (`FakeApiClient`, по образцу существующих тестов `features/auth`, `features/settings`,
  `shared/ui/CurrencyPicker`/`IconPicker`).

Backend, база данных и миграции Alembic **не затрагиваются**: используется уже готовый и заархивированный API
`wallets` (008) без изменений контракта.

## Capabilities

### New Capabilities
- `frontend-wallets`: экран управления кошельками пользователя (список, создание, редактирование, удаление) —
  навигация, список карточек с валютами, форма в `Drawer`/`Modal`, обработка ошибок API по общим правилам
  `AGENTS.md`.

### Modified Capabilities
<!-- Требования существующих спецификаций не меняются: используются уже готовые capabilities (frontend-shell,
     wallets backend, error-handling, mobile-layout). Новых требований к ним это изменение не добавляет. -->

## Impact

- Новые файлы только внутри `frontend/src/features/wallets/` (страница, компоненты, hooks, типы, тесты рядом с
  кодом).
- Изменяются существующие файлы `frontend/src/app/navItems.ts` (новый пункт «Кошельки») и
  `frontend/src/app/routes.tsx` (новый маршрут `/wallets` под `RequireAuth`).
- Backend, база данных, миграции Alembic — **не затрагиваются вовсе**. Используется только уже существующий
  эндпоинт `/api/wallets*` (`GET`/`POST`/`PUT`/`DELETE`, `WalletOut`/`WalletCreate`/`WalletUpdate`).
- Новых npm-зависимостей не требуется: используются уже установленные `antd` (`Card`, `Tag`, `Drawer`, `Modal`,
  `Popconfirm`, `Form`, `Input`), `@tanstack/react-query`, уже готовые `CurrencyPicker`/`IconPicker`/`EmptyState`
  из `shared/ui` (013).

## Non-goals

- Баланс кошелька по валютам — появится на экране операций (016), когда будут операции; на этом экране баланс
  нигде не показывается.
- Переводы между кошельками — отдельная задача (017).
- Отдельные маршруты для форм создания/редактирования (`/wallets/new` и т. п.) — форма открывается поверх списка
  в `Drawer`/`Modal`, не как отдельная страница.
- Серверная (клиентская постраничная) пагинация в UI — список кошельков загружается одним запросом с максимальным
  `limit`, персональный объём кошельков пользователя мал.
- Мастер первичной настройки/онбординга — решение дорожной карты: только `EmptyState` с призывом к действию.
