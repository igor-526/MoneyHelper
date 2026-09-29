## Why

Backend-капабилити доходов и расходов (`transactions`, задача 010) и три frontend-фундамента, от которых зависит
эта задача, — `frontend-shell` (013), `frontend-wallets` (014), `frontend-categories` (015) — уже реализованы и
заархивированы, но пользователь до сих пор не может вести список своих операций через интерфейс: раздел «Операции»
не существует ни как экран, ни как точка входа. Это третий из пяти оставшихся frontend-экранов (F2d дорожной
карты), самая крупная из оставшихся frontend-задач, и прямая зависимость для пополнений/переводов (017: экран
017 расширяет именно этот раздел), поэтому она должна появиться сейчас, комбинируя уже проверенные в проде паттерны
кошельков и категорий с новой для frontend механикой — реальной серверной пагинацией.

## What Changes

- Новый пункт `navItems` («Операции», маршрут `/transactions`, иконка по аналогии с существующими пунктами) МЕЖДУ
  «Кошельки» и «Настройки» (итоговый порядок: Главная, Кошельки, Операции, Настройки); маршрут `/transactions` в
  `app/routes.tsx` под `RequireAuth`.
- `features/transactions/Transaction.ts` — тип `Transaction` (ногозависимый, зеркалит `TransactionOut` без
  camelCase-маппинга: `id`, `wallet_id`, `category_id`, `legs: { currency_id, amount }[]`, `occurred_at`,
  `created_at`, `updated_at`) и `TransactionFormValues` (тело `TransactionCreate`/`TransactionUpdate`).
- `features/transactions/useTransactions` — hook списка с РЕАЛЬНОЙ серверной пагинацией (antd `Pagination`, размер
  страницы 20) и фильтрами (кошелёк, категория, тип, диапазон дат `occurred_at`), в отличие от кошельков/категорий/
  валют (один запрос без пагинации) — список операций растёт без ограничения. `queryKey` включает все фильтры и
  `offset`/`limit`.
- `features/transactions/useCreateTransaction`/`useUpdateTransaction`/`useDeleteTransaction` — мутации,
  инвалидирующие по префиксу `["transactions"]` и, дополнительно, `["wallet-balances"]` (любое изменение операции
  меняет баланс кошелька).
- `features/transactions/useWalletBalances` — новый hook `GET /api/wallets/{id}/balances`, показывается карточкой
  над списком, когда фильтр «кошелёк» установлен в конкретный кошелёк.
- `features/transactions/TransactionForm` — один компонент формы создания/редактирования: кошелёк (`Select`) →
  тип-переключатель (`Segmented`, только сужает список категорий, не отправляется в тело запроса) → категория
  (`Select` из `useCategories(type)`) → валюта (`CurrencyPicker`, ограничена набором валют выбранного кошелька) →
  сумма (`MoneyInput`, число знаков — из валюты) → дата (`DatePicker` с `showTime`, необязательна). Открывается в
  `Drawer`/`Modal` по `useIsMobile()`, обработка ошибок — существующий паттерн `kind === "validation"` →
  `applyFieldErrors` + `form.setFields` + toast, без специальных веток для бизнес-правил backend.
- `features/transactions/TransactionCard` и `features/transactions/TransactionsPage` — лента карточек операций
  (кошелёк, иконка+название+`Tag` типа категории, сумма+код валюты, дата) с фильтрами и пагинацией, удаление через
  `Popconfirm` (без спецобработки 409, по образцу `useDeleteWallet`/`useDeleteCategory`).
- **РАСШИРЕНИЕ `shared/ui/CurrencyPicker/CurrencyPicker.tsx`** новым опциональным пропом `allowedIds?: string[]`:
  фильтрует список опций до переданных id; при отсутствии пропа поведение не меняется (список полный, как сейчас).
  Единственное затрагиваемое изменение уже архивированного изменения `frontend-shell` (013) — обратно совместимое
  расширение существующего компонента, не поломка контракта: существующий потребитель (`WalletForm`) проп не
  передаёт и продолжает работать как раньше.
- Тесты hooks и компонентов (`FakeApiClient`, по образцу существующих тестов `features/wallets`/`features/categories`).

Backend, база данных и миграции Alembic **не затрагиваются**: используется уже готовый и заархивированный API
`transactions`/`balances` (010, 011) без изменений контракта.

## Capabilities

### New Capabilities
- `frontend-transactions`: экран учёта доходов и расходов пользователя по кошелькам и категориям — лента операций
  с фильтрами (кошелёк, категория, тип, диапазон дат) и серверной пагинацией, создание и редактирование через
  единую форму с ограничением валюты набором кошелька, удаление с подтверждением, карточка баланса выбранного
  кошелька по валютам, точка входа через пункт нижней/верхней навигации и маршрут `/transactions`.

### Modified Capabilities
- `frontend-shell`: требование «Выбор валюты — `CurrencyPicker`» получает новый опциональный проп `allowedIds`,
  ограничивающий список опций переданным набором id валют; поведение без пропа не меняется.

## Impact

- Новые файлы только внутри `frontend/src/features/transactions/` (страница, компоненты, hooks, типы, тесты рядом
  с кодом).
- Изменяются существующие файлы: `frontend/src/app/navItems.ts` (новый пункт «Операции» между «Кошельки» и
  «Настройки»), `frontend/src/app/routes.tsx` (новый маршрут `/transactions` под `RequireAuth`),
  `frontend/src/shared/ui/CurrencyPicker/CurrencyPicker.tsx` (новый опциональный проп `allowedIds`, обратно
  совместимо) и его тест `CurrencyPicker.test.tsx` (новые сценарии на `allowedIds`, существующие не меняются).
- Backend, база данных, миграции Alembic — **не затрагиваются вовсе**. Используются уже существующие эндпоинты
  `/api/transactions*` (`GET`/`POST`/`GET/{id}`/`PUT/{id}`/`DELETE/{id}`, `TransactionCreate`/`TransactionUpdate`/
  `TransactionOut`/`TransactionListParams`) и `GET /api/wallets/{id}/balances` (`WalletBalanceOut`).
- Новых npm-зависимостей не требуется: используются уже установленные `antd` (`Select`, `Segmented`, `DatePicker`,
  `Pagination`, `Card`, `Tag`, `Drawer`, `Modal`, `Popconfirm`, `Form`), `dayjs` (уже используется antd 6 внутри),
  `@tanstack/react-query`, уже готовые `CurrencyPicker`/`MoneyInput`/`EmptyState` из `shared/ui` (013).

## Non-goals

- Пополнения многовалютных кошельков (`POST /api/transactions/topups`) и переводы между кошельками — задача 017;
  форма этой задачи создаёт только обычную операцию с одной валютой, как и `POST /api/transactions`.
- Отображение нескольких ног в карточке операции — задел на 017; здесь единственный случай, который создаёт эта
  форма, — ровно одна нога (`transaction.legs[0]`).
- Баланс по всем кошелькам сразу — backend не даёт единого баланса по всем кошелькам одним запросом; при фильтре
  «Все кошельки» карточка баланса не показывается.
- Отдельные маршруты для форм создания/редактирования (`/transactions/new` и т. п.) — форма открывается поверх
  списка в `Drawer`/`Modal`, не как отдельная страница.
- Переиспользуемый общий компонент выбора кошелька в `shared/ui` — этой задаче нужен только один потребитель
  (`TransactionForm`), заводить общий компонент преждевременно (YAGNI); 017 сама решит, переиспользовать этот код
  или обобщить, если ей тоже понадобится выбор кошелька.
- Специальная обработка бизнес-правил backend (валюта операции не из набора валют кошелька, превышение знаков
  суммы, неположительная сумма) — все они приходят как `kind === "validation"` с текстовым `detail` и уже покрыты
  существующим общим механизмом `applyFieldErrors`/toast, применённым в `WalletForm`/`CategoryForm`.
