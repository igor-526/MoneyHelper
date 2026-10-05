# AGENTS.md

Правила для агентов и разработчиков монорепозитория MoneyHelper. Общее описание проекта — в [README.md](README.md).

## Язык

- Все агенты общаются **только на русском языке**.
- Все артефакты OpenSpec (proposal, specs, design, tasks) — только на русском. На английском остаются структурные
  ключевые слова формата (`## ADDED Requirements`, `### Requirement:`, `#### Scenario:`, `WHEN`/`THEN`/`AND`,
  `SHALL`/`MUST`), идентификаторы кода, имена файлов и команды.
- Комментарии и docstring в коде — на русском, только если они действительно нужны (код должен быть самодокументируемым).

## Процесс (OpenSpec)

- Задачи лежат в `docs/tasks/`; файл задачи указывается при вызове `/opsx:propose` или `/opsx:explore`.
- Конфигурация OpenSpec — `openspec/config.yaml`. Изменения — `openspec/changes/`, спецификации — `openspec/specs/`.
- Перед проектированием и реализацией прочитай этот файл.

## QualityGate

Задача завершена, только если подряд проходят (команды покрывают и backend, и frontend):

```bash
make format   # backend: ruff check --fix + ruff format; frontend: eslint --fix + prettier --write
make lint     # backend: ruff, mypy, flake8; frontend: eslint, prettier --check, tsc
make test     # backend: unit + smoke (маркер infrastructure исключён); frontend: vitest
```

- `make test` и голый `pytest` не требуют БД (в CI на GitHub job `quality` идёт без БД); тесты с БД лежат в
  `tests/infrastructure/`, получают маркер `infrastructure` автоматически и запускаются `make test-infra`.
- Frontend-часть тоже не требует внешней инфраструктуры (ни БД, ни backend, ни сети): все обращения к API в тестах идут через фейковый `ApiClient`.
- `make quality` запускает всё сразу; `make test-unit`, `make test-smoke`, `make test-infra` — частные случаи.
- Каждая новая фича сопровождается unit-тестами и, если добавляет эндпоинт или меняет запуск приложения, smoke-тестом.
- Не отключай правила линтера и не правь конфигурацию ради прохождения проверок без явной просьбы.
- Код должен быть чистым и однообразным: следуй существующему стилю, не оставляй мёртвый код и лишние комментарии.

## Структура backend

```text
backend/
├── src/
│   ├── main.py            # создание FastAPI, lifespan, глобальные обработчики ошибок
│   ├── settings.py        # настройки из окружения (pydantic-settings)
│   ├── api/               # HTTP-слой: роутеры и request/response-схемы
│   ├── core/              # ядро (бизнес-логика, не зависит от FastAPI и SQLAlchemy)
│   │   ├── entities/      # доменные сущности (Entity, TimestampMixin)
│   │   ├── schemas/       # pydantic-схемы (Schema с from_attributes)
│   │   ├── protocols/     # интерфейсы репозиториев и внешних зависимостей (typing.Protocol)
│   │   ├── services/      # сценарии использования (бизнес-логика)
│   │   └── exceptions/    # AppError → ClientError → AlreadyExistsError и т. д.
│   ├── depends/           # сборка зависимостей FastAPI (Depends): сессия, репозитории, сервисы
│   ├── models/            # SQLAlchemy Core таблицы
│   ├── repositories/      # реализации protocols на SQLAlchemy Core
│   ├── migration/         # Alembic (versions/ — только схема, без данных)
│   ├── seeds/             # справочные данные в JSON (явные UUID), применяются при старте
│   └── utils/             # инфраструктура: database, basemodel (metadata), configure_sentry, seeding
├── tests/                 # зеркалит src; unit/, api/, smoke/ — без БД; infrastructure/ — с БД; fakes/ — fake-реализации
├── pyproject.toml         # зависимости и конфигурация ruff/pytest/basedpyright
└── Makefile               # format, lint, test, test-unit, test-smoke, test-infra
```

Импорты идут от корня `src` (`from core.exceptions import AppError`), а не относительные между слоями.
Пакеты первого уровня перечислены в `tool.ruff.lint.isort.known-first-party`; при добавлении нового — допиши его туда.

### Направление зависимостей

`api → depends → core ← repositories`. `core` ничего не знает об `api`, `models`, `repositories` и FastAPI.
`repositories` реализуют `core.protocols`; `models` используются только в `repositories` и `migration`.

## Архитектура: SOLID (обязательна)

Агент **всегда** проектирует и пишет код по SOLID. Скелет проекта строится по этим правилам; отступления
допустимы только с обоснованием в `design.md` изменения OpenSpec.

**S — единственная ответственность.** У класса или модуля одна причина для изменения.
- Роутер только транслирует HTTP; сервис — один сценарий или связная группа сценариев одной сущности;
  репозиторий — только доступ к данным одной сущности; схема — только форма данных.
- Сервис не знает про HTTP-коды, cookies, `Request`/`Response`; репозиторий не содержит бизнес-правил.
- Файл на сущность в каждом слое: `core/entities/wallet.py`, `core/protocols/wallet.py`, `core/services/wallet.py`,
  `repositories/wallet.py`, `models/wallet.py`, `api/wallets.py`, `depends/wallet.py`. Не сваливай разные сущности в один файл.

**O — открытость/закрытость.** Расширяем новым кодом, а не правкой работающего.
- Новое поведение — новая реализация протокола или новый сервис, а не ещё один `if` в существующем.
- Варианты поведения (виды операций, срезы аналитики, способы расчёта курса) оформляются стратегиями за протоколом
  и регистрируются в одном месте, а не разветвляются по коду через `if type == ...`.

**L — подстановка Барбары Лисков.** Любая реализация протокола заменима без изменения поведения вызывающего кода.
- Репозиторий в тестах (in-memory/fake) и в проде (SQLAlchemy) ведут себя одинаково: те же исключения,
  те же возвращаемые типы, те же правила для «не найдено».
- Реализация не ужесточает предусловия и не бросает исключений, не описанных в протоколе.

**I — разделение интерфейсов.** Протоколы узкие и ориентированы на потребителя.
- Не делай «god-протокол» `Repository` со всеми методами; выделяй по потребностям
  (`WalletReader`, `WalletWriter`), если потребители используют разные подмножества.
- Сервис зависит только от тех протоколов и только от тех методов, которые ему нужны.

**D — инверсия зависимостей.**
- `core` зависит от абстракций (`core/protocols`), а не от SQLAlchemy, FastAPI, `settings` или `utils`.
- Конкретные реализации создаются и связываются только в `depends/` (composition root). Внутри `core` и `api`
  нет `SomeRepository()` и обращений к глобальным синглтонам (`settings`, `engine`) — зависимости приходят через конструктор.
- Время, генерация UUID, хеширование паролей и подпись JWT — тоже зависимости за протоколами
  (`Clock`, `PasswordHasher`, `TokenSigner`), чтобы код был детерминированно тестируемым.

**Как добавлять фичу (порядок работы):**
1. `core/entities` — сущность и инварианты.
2. `core/protocols` — узкие протоколы репозиториев и внешних зависимостей.
3. `core/services` — сценарий; тест на fake-репозиториях.
4. `models` + миграция Alembic; `repositories` — реализация протокола.
5. `core/schemas` и `api` — контракт и роутер; `depends` — сборка зависимостей.
6. unit-тесты, smoke-тест эндпоинта, QualityGate.

**Что считается нарушением (ревью останавливает):** SQL или `select()` вне `repositories`; импорт `fastapi`,
`sqlalchemy`, `settings` внутри `core`; бизнес-логика в роутере; сервис, сам создающий свой репозиторий;
`isinstance`/`if type ==` для ветвления по видам вместо полиморфизма; протокол с методами, которые потребитель не использует.

## Паттерны

**Слои и ответственность**
- `api/` — только HTTP: разбор запроса, вызов сервиса, формирование ответа. Никакой бизнес-логики и SQL.
- `core/services/` — бизнес-логика; работает с репозиториями через протоколы из `core/protocols/`.
- `repositories/` — единственное место с SQL (SQLAlchemy Core, без ORM-сущностей). Возвращают доменные сущности.
- `depends/` — единственное место, где сервисы связываются с конкретными репозиториями и сессией.

**Сущности и схемы**
- Доменные сущности наследуют `Entity` (UUID `id`) и при необходимости `TimestampMixin`.
- Схемы API наследуют `core.schemas.base.Schema`. Схемы запроса и ответа разделены; сущности наружу не отдаются напрямую.

**Ошибки**
- Бизнес-ошибки — исключения от `AppError` (`core/exceptions`), у каждого свой `status_code`: 400 `ClientError`,
  401 `AuthenticationError`, 403 `PermissionDeniedError`, 404 `NotFoundError`, 409 `AlreadyExistsError`. Новые ошибки
  добавляются в `core/exceptions/` и экспортируются в `__init__.py`.
- Все ошибки отдаются как JSON `{"detail": ...}`; обработчики зарегистрированы в `api/errors.py`, в роутерах ошибки не
  перехватываются. Ошибки валидации запроса возвращаются с кодом 400 (`detail` — список, всегда сериализуемый).
- Необработанное исключение превращает `UnhandledErrorMiddleware` в `500 {"detail": "Internal server error"}` (с логом и
  Sentry). Он стоит **внутри** CORS, поэтому ответ 500 получает CORS-заголовки, и frontend видит статус и показывает toast.
  Не заменяй его на `@app.exception_handler(Exception)`: такой ответ остаётся без CORS-заголовков.
- Приложение собирается в `main.create_app()`; порядок middleware важен (последний добавленный — самый внешний).

**Время и идентификаторы**
- `core` получает время и UUID только через протоколы `Clock` и `IdGenerator` (`core/protocols`); прямые вызовы
  `datetime.now()` и `uuid4()` в `core` запрещены. `Entity.id` и `TimestampMixin.created_at` без значений по умолчанию
  — их задаёт сервис. Реализации — `utils/clock.py`, `utils/id_generator.py`, зависимости — `depends/providers.py`.

**Пагинация**
- Запрос: `Annotated[PageParams, Query()]` (`limit` 1..100, по умолчанию 20; `offset` ≥ 0). Ответ: `Page[T]`
  (`items`, `total`, `limit`, `offset`) из `core/schemas`.

**CORS**
- Разрешённые origin — `CORS_ORIGINS` (через запятую, формат `scheme://host[:port]`, `*` запрещён); пустое значение
  выключает CORS. Подключается `utils/configure_cors.py` с `allow_credentials=True`.

**База данных**
- Таблицы определяются в `models/` на общем `utils.basemodel.metadata`; новые модели импортируются в
  `models/__init__.py`, иначе Alembic их не увидит.
- Транзакция управляется зависимостью `utils.database.get_session`: commit в конце запроса, rollback при исключении.
  Репозитории и сервисы сами не коммитят.
- Любое изменение схемы БД — миграция Alembic (`make be-makemigrations msg="..."`, `make be-migrate`).
  Миграции ревьюятся вручную.
- Данные пользователей изолированы: каждый запрос к пользовательским данным фильтруется по владельцу.

**Настройки**
- Все параметры окружения — поля `Settings` в `settings.py` с `alias`. Пример значений — `backend/.env.example`.
  Секреты не коммитятся (`.env` в `.gitignore`).

**Иконки**
- Iconpack — [Lucide](https://lucide.dev). Иконка категории и кошелька хранится в БД как строка — имя иконки
  Lucide в kebab-case (например `wallet`, `banknote`). Список допустимых имён задаётся в одном месте
  (`core`) и валидируется на входе API; frontend отрисовывает иконку по этому имени.

**Авторизация**
- JWT (PyJWT, HS256, подпись `JWT_SECRET`): пара access + refresh; **токены на сервере не хранятся**. Время жизни задаётся в
  `.env` (по умолчанию 15 минут и 30 дней), в коде не хардкодится. `sub` — `user_id`; `token_type` различает access и refresh.
- Токены передаются только через cookies: backend сам ставит и удаляет их (`HttpOnly`, `Secure` вне development,
  `SameSite`), читает из запроса; frontend лишь отправляет запросы с `credentials`. В теле ответа токены не возвращаются.
- Refresh скользящий: каждый `/refresh` выдаёт новую пару токенов. Отзыв без хранения токенов — `token_version`
  пользователя: он лежит в claim `ver` refresh, `/refresh` сверяет его с БД; logout и смена пароля увеличивают его и
  гасят все refresh пользователя. Access проверяется без обращения к БД (после logout действует до истечения TTL).
- Вход по email (нижний регистр, уникален). Пароли — argon2id (8–128 символов), хеширование выполняется вне event loop.
  Ответ на неверные учётные данные одинаков для неизвестного email и неверного пароля.
- Регистрация включается настройкой `REGISTRATION_ENABLED`.
- Frontend и backend работают на разных origin, но обязаны быть same-site (общий registrable domain, в dev —
  `localhost` с разными портами) при `SameSite=Lax`. CORS: `allow_credentials=true` и точный список origin
  `CORS_ORIGINS` из `.env`; `*` запрещён.
- CSRF: на небезопасных методах (POST/PUT/PATCH/DELETE) проверяется заголовок `Origin` по `CORS_ORIGINS`,
  тело принимается только как JSON. Refresh-cookie ставится с `Path=/api/auth`.
- Текущий пользователь получается зависимостью из `depends/`; сервисы получают `user_id` явным аргументом.

**Сидирование**
- Справочные данные (например глобальные валюты) сидируются **не миграциями**, а при старте приложения в `lifespan`.
- Механизм — `utils/seeding.py`; данные — JSON в `src/seeds/`. Сидирование идемпотентно (upsert по явному UUID)
  и безопасно при нескольких репликах (advisory lock).
- В сидах **всегда явные UUID**, сгенерированные функцией (`uuid.uuid4()`), например
  `uv run python -c "import uuid; print(uuid.uuid4())"`. Выдуманные идентификаторы вроде `1111-…` запрещены.
  Выданный UUID не меняется никогда.
- В тестах сидирование отключается настройкой или подменой, чтобы `make test` не требовал БД.

**Деньги и валюты**
- Суммы — `Decimal`/`NUMERIC`, никогда `float`: в схемах тип `Money` (`core/schemas/money.py`, до 24 цифр, 8 знаков,
  в JSON — строка), в таблицах столбец `MONEY` (`models/types.py`, `NUMERIC(24, 8)`). Валюта суммы указывается всегда.
- У воркспейса основная валюта (`workspaces.currency_id`); у кошелька ровно одна валюта (`wallets.currency_id`),
  которая может совпадать с валютой воркспейса. Валюту кошелька с операциями или переводами менять нельзя (409).
- Пополнение (`/topups`) — доход (категория `income`): ноги в валюте воркспейса и в валюте кошелька (одна нога, если
  валюты совпадают). Курс не хранится отдельным полем и выводится из сумм ног.
- Расход (`/transactions`) — категория `expense`, одна нога в валюте кошелька; валюта в запросе не передаётся.
- Перевод между кошельками допустим только при одинаковой валюте кошельков, без конвертации; валюта перевода выводится
  из кошельков. Конвертация между валютами происходит только через пополнение. Перевод не участвует в курсе и аналитике.
- Баланс кошелька — одно число в валюте кошелька: пополнения и переводы внутрь минус расходы и переводы наружу.
- Аналитика: суммы по умолчанию в валюте воркспейса; `display_currency` (GET-параметр, необязательный) — валюта
  воркспейса или валюта кошелька воркспейса. Курс — простое среднее по пополнениям воркспейса за диапазон анализа;
  средний курс кошелька считается только по его пополнениям.
- Удаление физическое; связанные данные защищаются внешними ключами (запрет или каскад — решается в OpenSpec-изменении).
- Категории — плоский список (без вложенности).

**Тесты**
- `tests/` зеркалит `src/`. Unit-тесты не требуют БД и внешних сервисов (зависимости подменяются fake-реализациями
  из `tests/fakes/`: `FixedClock`, `SequentialIdGenerator`, базовый `InMemoryRepository`).
- `tests/smoke/` — smoke-тесты с `pytestmark = pytest.mark.smoke`: приложение поднимается, критичные эндпоинты отвечают.
- Тесты с БД лежат **только** в `tests/infrastructure/`: каталог получает маркер `infrastructure` автоматически,
  фикстуры БД (`engine`, `db_session` с откатом транзакции) определены только там. `make test` и голый `pytest`
  (`addopts = -m "not infrastructure"`) их не запускают; они идут через `make test-infra`. Внешние сервисы и секреты — то же правило.
- Тесты работают с отдельной БД `TEST_POSTGRES_DB` (по умолчанию `app_test`, имя обязано оканчиваться на `_test`;
  `TEST_POSTGRES_HOST`/`TEST_POSTGRES_PORT` при запуске с хоста). `conftest.py` подменяет `POSTGRES_*` до импорта
  `settings`, так что БД разработки тесты не затрагивают. Схема создаётся `alembic upgrade head`.
- CI (`.github/workflows/ci.yml`): job `quality` (`make lint`, `make test`) идёт **без БД** — не добавляй в unit/smoke
  скрытых зависимостей от БД; job `infrastructure` поднимает PostgreSQL и запускает `make test-infra`.
- `asyncio_mode = "auto"`: асинхронные тесты не требуют декоратора.

## Frontend

- React 19 + TypeScript (strict), Vite, полностью CSR (без серверного рендеринга). Каталог `frontend/`, менеджер пакетов — npm
  (зависимости по `package-lock.json`). UI — **Ant Design 6** (`antd`); иконки — только Lucide (`shared/ui/Icon`), пакет
  `@ant-design/icons` не используется. Серверное состояние — TanStack Query, роутинг — react-router.
- Общение с backend — только по HTTP API; токены в cookies выставляет и читает backend, frontend шлёт запросы
  с `credentials: "include"` и не хранит токены в JS/`localStorage`/`sessionStorage`. Единственное исключение по
  `localStorage` — предпочтение интерфейса (режим темы, ключ `moneyhelper.theme`); ничего связанного с авторизацией
  и данными пользователя там не хранится.
- Адрес backend — `VITE_API_URL` (`frontend/.env.example`); dev-сервер на порту 5173 (совпадает с `CORS_ORIGINS` backend).
- Те же принципы SOLID:
  - **S**: компонент либо отображает (presentational), либо управляет данными (container/hook). Логика — в hooks и чистых функциях (`parseApiError`, `resolveTheme`, `resolveErrorMessage`), не в JSX.
  - **O**: варианты (виды операций, срезы аналитики, пункты навигации, сообщения об ошибках) — через конфигурацию и таблицы (`navItems`, `MESSAGE_BUILDERS`), без цепочек `if`.
  - **L/I**: пропсы компонентов минимальны; компонент получает только то, что использует.
  - **D**: компоненты и hooks зависят от интерфейсов `ApiClient` (`shared/api`) и `ToastApi` (`useToast`), а не от `fetch`/antd `message` напрямую; реализация подставляется на верхнем уровне (`app/App.tsx`, `main.tsx`).
- Структура:

  ```text
  frontend/src/
  ├── app/                # App (композиция провайдеров), routes, layout (MobileShell/DesktopShell), navItems
  ├── features/<feature>/ # страницы, компоненты, hooks и api фичи (например analytics, settings, workspaces)
  ├── shared/
  │   ├── api/            # ApiClient (интерфейс), FetchApiClient, ApiError, parseApiError, ApiClientProvider, refreshSession
  │   ├── errors/         # ErrorBoundary, resolveErrorMessage, createQueryClient, applyFieldErrors
  │   ├── ui/             # theme (ThemeProvider, токены), useIsMobile, toast (ToastProvider), Icon
  │   ├── pwa/            # manifest, PwaBanners, useOnlineStatus, usePwaUpdate, installPrompt
  │   └── config/         # чтение переменных окружения
  └── test/               # setup, FakeApiClient, toastSpy, matchMedia, renderApp, session (withSession)
  ```

  `features/auth/` — не обычная фича, а инфраструктура маршрутов: `session.ts` (`useSession`, `SESSION_QUERY_KEY`),
  `RequireAuth`/`GuestOnly` (обёртки маршрутов в `app/routes.tsx`), `LoginPage`/`RegisterPage`, `useLogin`/`useRegister`.
  Выход и смена пароля живут в `features/settings/` (`LogoutButton`, `ChangePasswordForm`), где ими и пользуются.

  Тесты лежат рядом с кодом (`*.test.ts(x)`). Импорты между слоями: `app` → `features` → `shared`; `shared` не зависит от `features`.
- **Обработка ошибок обязательна для каждого действия.** Любой запрос к API обрабатывает все ошибки: 400 (включая
  валидацию по полям), 401, 403, 404, 409, 500, сетевые сбои и таймаут. Пользователь всегда получает уведомление (toast);
  молчаливых сбоев быть не должно. Ошибки нормализуются в API-клиенте (`ApiError`), toast по умолчанию показывает
  глобальный обработчик `QueryCache`/`MutationCache` (`shared/errors`), а конкретное действие может переопределить
  сообщение (`meta: { errorMessages }`). Backend отдаёт все ошибки, включая 500 и 404, как JSON `{"detail": ...}`
  с CORS-заголовками.
  - Обращения к API — только через hooks TanStack Query (`useQuery`/`useMutation`); прямой вызов `ApiClient`
    допустим только внутри `queryFn`/`mutationFn`, иначе ошибка минует глобальный обработчик.
  - `meta: { silent: true }` отключает глобальный toast; тогда действие **обязано** обработать ошибку само. Для форм с
    ошибками 400 по полям: `silent` + `applyFieldErrors(error, [поля формы])` → сообщения у полей и
    `toast.error(toastMessage)` (в нём остаются сообщения неизвестных форме полей).
  - Ошибки не из API (баги) тоже показываются toast «Что-то пошло не так»; ошибки рендеринга ловит `ErrorBoundary`.
- **Авторизация.** Сессия — обычный запрос (`useSession`, `GET /api/auth/me`), а не React-контекст; у него
  `meta.silent: true`, потому что 401 при первом визите анонима — нормальное состояние, не ошибка. `RequireAuth`
  оборачивает защищённые маршруты (все, кроме `/login` и `/register`), `GuestOnly` — публичные; оба реагируют на
  один и тот же кэш `SESSION_QUERY_KEY`, поэтому редирект всегда один на событие: например, `GuestOnly` сам решает
  «куда» (сохранённый `from` или `/`), а не `LoginPage` — два места, редиректящих по одному и тому же изменению
  кэша, гоняются друг с другом за `router.navigate`.
  - Обновление токена при 401 — `createSingleFlightRefresh` (`shared/api`), передаётся в `FetchApiClient` как
    `onUnauthorized`; несколько запросов, упавших в 401 одновременно, ждут одно обновление, не по одному на каждый.
  - Если обновление не помогло, глобальный обработчик ошибок не зовёт роутер напрямую — он очищает
    `SESSION_QUERY_KEY` (`onUnauthorized` в `createQueryClient`), а `RequireAuth` сам уводит на `/login` тем же кодом,
    что и при обычном заходе без сессии (включая сохранение пути для возврата).
  - Формы входа/регистрации/смены пароля — тот же паттерн `silent` + `applyFieldErrors`, но `kind === "unauthorized"`
    каждая форма показывает своим текстом под свой контекст (неверные учётные данные / неверный текущий пароль),
    а не переиспользует дефолтное «Сессия истекла…».
- **Mobile-first (обязательно).** Приложение в основном используется на телефоне: вёрстка проектируется сначала под
  узкий экран (от 320 px, без горизонтальной прокрутки), затем расширяется.
  - Режим выбирается только хуком `useIsMobile` (порог 768 px, `md` antd), не собственными `matchMedia`.
    Телефон — нижняя панель навигации (не более 5 пунктов), широкий экран — верхняя навигация.
  - Тема antd (`shared/ui/theme/tokens.ts`): высота элементов ≥ 44 px, шрифт ≥ 16 px (без автозума iOS). Не используй
    `size="small"` для интерактивных элементов; расстояние между ними ≥ 8 px.
  - Высота экрана — `100dvh` (не `100vh`); фиксированные элементы у краёв учитывают `env(safe-area-inset-*)`.
  - Формы — в одну колонку, подписи над полями, правильные `type`/`inputMode` (`decimal` для сумм, `email` для email),
    основное действие — кнопка на всю ширину. Модальные окна на телефоне — нижний `Drawer`, а не `Modal`. Вместо
    таблиц на телефоне — списки/карточки. Горизонтальная прокрутка допустима только внутри отдельного компонента
    (например, ряд чипов). Hover не должен быть единственным способом доступа к действию.
- **Тёмная и светлая темы.** Режимы `light` / `dark` / `system` (по умолчанию `system`), выбор сохраняется на устройстве.
  Цвета берутся только из токенов antd (`theme.useToken()`) и CSS-переменных (`--app-bg`, `--app-fg`, ...); жёстко
  заданные цвета запрещены. Контраст не ниже WCAG AA в обеих темах. Скрипт в `index.html` применяет тему до загрузки
  бандла и должен совпадать с `resolveTheme` (это проверяет тест).
- **PWA.** `vite-plugin-pwa`: manifest (`shared/pwa/manifest.ts`), иконки из `frontend/public/icon.svg`
  (`make fe-pwa-assets`, результат коммитится), service worker кэширует **только оболочку приложения**. Запросы к API
  никогда не кэшируются (нет `runtimeCaching`): деньги не должны быть устаревшими, а данные пользователя не хранятся в
  кэше; изменение этого правила — отдельная задача. Новая версия применяется только по кнопке «Обновить»
  (`registerType: "prompt"`). В dev-сервере service worker выключен: PWA проверяется через `make fe-preview`. Для
  продакшена нужен HTTPS.
- Не отключай правила линтера и не правь конфигурацию ради прохождения проверок без явной просьбы.

## Команды

| Команда | Назначение |
|---|---|
| `make infra` | поднять PostgreSQL |
| `make be-build` / `make be` | собрать и запустить backend |
| `make be-makemigrations msg="..."` | создать миграцию |
| `make be-migrate` | применить миграции |
| `make format` / `make lint` / `make test` | QualityGate |
| `make quality` | весь QualityGate |
| `make fe-install` | установить зависимости frontend (`npm ci`; остальные `fe-*` делают это сами при необходимости) |
| `make fe-dev` | dev-сервер frontend на `http://localhost:5173` |
| `make fe-build` / `make fe-preview` | сборка frontend / сборка и предпросмотр (так проверяется PWA) |
| `make fe-test` / `make fe-lint` / `make fe-format` | QualityGate только для frontend |
| `make fe-pwa-assets` | перегенерировать PWA-иконки из `frontend/public/icon.svg` |
