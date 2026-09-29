## Context

Скелет backend готов (`backend-foundation`): `Clock` и `IdGenerator` как протоколы, ошибки `AppError → AuthenticationError|PermissionDeniedError|AlreadyExistsError`, CORS с credentials, обработчик 500 внутри CORS, БД без таблиц (миграция `0001` пуста), тесты без БД плюс `tests/infrastructure/` с БД. Скелет frontend готов (`frontend-init`): `ApiClient`/`FetchApiClient` с точкой расширения `onUnauthorized` и одним повтором, глобальная обработка ошибок через `QueryCache`/`MutationCache` (`shared/errors`), `useToast`, mobile-first layout с `AppLayout`/`MobileShell`/`DesktopShell`, `RouterProvider` из `createBrowserRouter`. Задача: `docs/tasks/005_backend_auth.md`. Референс по токенам — eqSiteCMS: PyJWT HS256, claims `sub`/`exp`/`token_type`, два HttpOnly-cookie, скользящий refresh без хранения; на frontend eqSiteCMS — single-flight refresh с общим `refreshPromise` и редиректом на `/login`, тот же приём переносим.

## Goals / Non-Goals

**Goals:**
- Регистрация, вход, refresh, logout, смена пароля, `/me`; токены не хранятся; отзыв refresh через `token_version`.
- Access проверяется без БД; зависимость `get_current_user` для последующих задач.
- CSRF закрыт проверкой `Origin` и JSON-only телом.
- Слои по AGENTS.md: сервис не знает про HTTP и cookies; криптография за протоколами.
- Frontend: экраны входа/регистрации, защищённые маршруты, автоматическое обновление сессии, выход, смена пароля — полный рабочий цикл авторизации в UI.

**Non-Goals:**
- Подтверждение email, сброс пароля, OAuth, роли, rate limit, отзыв отдельных устройств.
- Менеджер паролей/автозаполнение сверх стандартного поведения браузера, капча.

## Decisions

**Токены: PyJWT, HS256, подпись `JWT_SECRET`, без хранения.** Алгоритм зафиксирован в коде (в eqSiteCMS он настраиваемый — лишняя поверхность для атак подмены алгоритма); при декодировании `algorithms=["HS256"]` и `require: [sub, token_type, exp, iat]`. Claims: `sub` = `user_id` (UUID строкой, не email: email можно менять и переиспользовать), `token_type`, `iat`, `exp`; в refresh ещё `ver`. Срок проверяется вручную по `Clock` (отключаем `verify_exp` у PyJWT), чтобы тесты были детерминированными и не зависели от системного времени; `exp`/`iat` кодируются из `Clock.now()`. Альтернативы: opaque-токены в БД (отвергнуто пользователем), общий секрет для access и refresh — допустим, различие через `token_type`.

**Отзыв без хранения токенов: `users.token_version`.** Хранится число у пользователя, а не токены. `/refresh` загружает пользователя (один SELECT раз в 15 минут) и сверяет `ver`. Logout и смена пароля увеличивают версию условным `UPDATE ... WHERE id=:id AND token_version=:ver` — повтор со старым refresh не увеличивает версию повторно. Цена: logout гасит refresh на всех устройствах; access живёт до истечения TTL (15 минут).

**Refresh скользящий и не инвалидируется обновлением.** Каждый `/refresh` выдаёт новую пару с новым `exp` (30 дней с последней активности) и текущим `ver`. Ротации с отзывом нет, поэтому параллельные обновления (две вкладки) обе успешны, окна терпимости не требуется; single-flight на клиенте убирает лишние запросы (отдельная frontend-задача).

**Слои и протоколы (SOLID).**
- `core/protocols/password_hasher.py`: `PasswordHasher` (`async hash(str) -> str`, `async verify(str, hash) -> bool`, `needs_rehash(hash) -> bool`); реализация `utils/password_hasher.py` — `argon2-cffi`, вызовы через `asyncio.to_thread`.
- `core/protocols/tokens.py`: `TokenIssuer` (`issue_access(user_id)`, `issue_refresh(user_id, version)`) и `TokenVerifier` (`verify_access(token) -> AccessClaims`, `verify_refresh(token) -> RefreshClaims`) — раздельно (ISP): `get_current_user` нужен только верификатор access. Реализация `utils/jwt_tokens.py`: `JwtTokenService` (реализует оба протокола), получает `secret`, TTL и `Clock` конструктором. Ошибки проверки — `AuthenticationError`.
- `core/protocols/user_repository.py`: `get_by_id`, `get_by_email`, `add`, `update_password(user_id, hash, now) -> None` (с увеличением версии), `bump_token_version(user_id, expected_version, now) -> bool`.
- `core/services/auth.py`: `AuthService(users, hasher, issuer, verifier, clock, ids, registration_enabled)`. Методы: `register`, `login -> (User, TokenPair)`, `refresh -> TokenPair`, `logout(refresh_token | None)`, `change_password(user_id, current, new) -> TokenPair`, `get_user(user_id)`. Возвращает `TokenPair(access, refresh)`; о cookies не знает.
- `api/auth.py` (роутер), `api/cookies.py` (`set_session_cookies`/`clear_session_cookies`, единственное место, знающее атрибуты cookies), `api/schemas` для тел запросов; `depends/auth.py` (`get_auth_service`, `get_current_user`), `depends/user.py` (репозиторий).
- `core/entities/user.py`: `User(Entity, TimestampMixin)` c `email`, `password_hash`, `token_version`. Ответ API — отдельная схема `UserOut` (`id`, `email`, `created_at`).
- Один файл на сущность и слой, как требует AGENTS.md.

**Вход и тайминг.** Для неизвестного email `login` всё равно вызывает `verify` против заранее вычисленного «пустого» хеша (создаётся один раз при старте), чтобы время ответа не выдавало наличие email; ответ 401 в обоих случаях одинаков («Неверный email или пароль»). При успехе, если `needs_rehash`, хеш обновляется (задел на смену параметров argon2).

**Регистрация.** Флаг `registration_enabled` передаётся в сервис из настроек через `depends` (сервис не читает `settings`); при `false` бросает `PermissionDeniedError` до любых проверок. Email нормализуется схемой запроса (`EmailStr` + strip/lower, длина ≤ 254). Дубликат — `AlreadyExistsError` (409), а также перехват нарушения уникальности при гонке двух регистраций (репозиторий переводит `IntegrityError` в `AlreadyExistsError`). Утечка факта существования email при регистрации принимается: регистрация по умолчанию выключена.

**Пароль.** 8–128 символов в схеме запроса; верхний предел защищает от дорогих запросов к argon2. Смена пароля: проверка текущего, новый хеш, `token_version + 1` одной операцией репозитория, затем выдача новой пары с новым `ver` — текущая сессия продолжает работать.

**Cookies.** `HttpOnly`; `Secure` по `COOKIE_SECURE` (по умолчанию `environment != development`); `SameSite` из настроек (по умолчанию lax; `none` только при `Secure`); `Domain` из `COOKIE_DOMAIN`. `access_token`: `Path=/`. `refresh_token`: `Path=/api/auth` — так refresh не отправляется на прочие эндпоинты и `logout` его получает. Риск: в eqSiteCMS refresh-cookie пришлось перенести с `/api/auth/refresh` на `/` (остался код очистки «legacy»-cookie), вероятно, из-за префиксов прокси. Здесь префикс `/api/auth` фиксирован константой роутера; при деплое проверить, что прокси не меняет путь, иначе — вынести путь в настройку. Ответы `login`/`refresh`/`logout`/`password` не содержат токенов.

**CSRF.** Чистый ASGI-middleware `OriginCheckMiddleware` (`utils/origin_check_middleware.py`), подключается рядом с CORS: для `POST|PUT|PATCH|DELETE` при наличии `Origin` сверяет с `CORS_ORIGINS`, иначе отвечает 403 JSON до обработчика. Заголовок `Origin` браузер всегда добавляет к небезопасным кросс-origin запросам, поэтому запросы без него допускаются (не браузерные клиенты; CSRF без браузера невозможен). Порядок middleware: проверка Origin выполняется после CORS (внутри), чтобы preflight `OPTIONS` обрабатывался CORS-слоем. JSON-only обеспечивается моделями FastAPI: тело не в JSON не парсится в модель и даёт 400 через существующий обработчик валидации; тест закрепляет поведение для `x-www-form-urlencoded` и `text/plain`. Пустой список `CORS_ORIGINS` = все небезопасные запросы с `Origin` отклоняются (закрыто по умолчанию).

**Настройки и валидация (`settings.py`).** `JWT_SECRET` (в development есть значение по умолчанию только для разработки; вне development — обязателен, ≥ 32 символов, не равен дефолту), `ACCESS_TOKEN_TTL_MINUTES=15`, `REFRESH_TOKEN_TTL_DAYS=30` (`gt=0`), `COOKIE_SECURE: bool | None` (None → по окружению), `COOKIE_DOMAIN: str | None`, `COOKIE_SAMESITE: Literal["lax","strict","none"]`, `REGISTRATION_ENABLED=false`. Проверки в `model_validator`, как существующая проверка Sentry. В `.env`/`.env.example` добавляются переменные, для development `REGISTRATION_ENABLED=true`.

**БД.** Таблица `users`: `id UUID PK`, `email VARCHAR(254) NOT NULL UNIQUE` + `CHECK (email = lower(email))`, `password_hash TEXT NOT NULL`, `token_version INTEGER NOT NULL DEFAULT 0 CHECK (token_version >= 0)`, `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NULL`. Миграция `20260929_0002_users.py` (только схема; откат удаляет таблицу). Значения `id` и времени задаёт приложение (`IdGenerator`, `Clock`), а не БД.

**Тесты.**
- unit: `JwtTokenService` (выдача, истечение по `FixedClock`, подмена типа, подпись, `alg=none`), `Argon2PasswordHasher` (реальный, быстрые параметры не нужны: один тест), `AuthService` на `InMemoryUserRepository` и фейковых `PasswordHasher`/токенах (регистрация, флаг, дубликат, вход, тайминговый путь, refresh с `ver`, logout условный, смена пароля), настройки (`JWT_SECRET`, TTL, SameSite/Secure);
- api: полный цикл через cookies с `TestClient` (register → login → me → refresh → logout → refresh даёт 401), атрибуты `Set-Cookie`, `Path` refresh, параллельный refresh, Origin (разрешённый, чужой, `null`, безопасный метод, preflight), форма вместо JSON, 401 без cookie;
- smoke: `/api/auth/*` зарегистрированы; замена `test_auth_routes_are_not_registered`;
- infrastructure (`make test-infra`): `UserRepository` на БД — добавление, уникальность email (в т.ч. в другом регистре), условное увеличение версии, `update_password`.

**Frontend: сессия — обычный запрос, не глобальный контекст.** `useSession()` (`features/auth/session.ts`) — тонкая
обёртка над `useQuery({ queryKey: SESSION_QUERY_KEY, queryFn: () => api.get<User>("/auth/me"), retry: false, meta: { silent: true } })`.
`meta.silent: true` — осознанное решение: 401 для анонимного посетителя при первом визите это нормальное состояние, а
не «ошибка», глобальный toast «Сессия истекла...» тут неуместен (отдельный сценарий в спеке). `SESSION_QUERY_KEY =
["auth", "session"]` экспортируется, чтобы `useLogin`/`useLogout` могли обновлять кэш напрямую без рефетча.
`isAuthenticated = query.isSuccess`, `isChecking = query.isPending`.

**`RequireAuth` и `GuestOnly` (`features/auth/`) — обёртки маршрутов, не HOC над каждой страницей.** Подключаются в
`app/routes.tsx` на уровне групп маршрутов (принцип D: страницы не знают про авторизацию):
```
routes = [
  { element: <GuestOnly />, children: [login, register] },
  { element: <RequireAuth><AppLayout /></RequireAuth>, errorElement: ..., children: [health, settings, notFound] },
]
```
`RequireAuth`: пока `isChecking` — общий спиннер (без мигания формы входа); если не аутентифицирован —
`<Navigate to="/login" replace state={{ from: location }} />`. `GuestOnly` — зеркально, при `isAuthenticated`
редиректит на `from` из `state` или на `/`. Все прочие маршруты (включая `*`) защищены: это личное приложение, публичных
данных, кроме входа и регистрации, нет.

**Single-flight обновление сессии: `shared/api/refreshSession.ts`, не метод `ApiClient`.** Обновление сессии —
отдельный «сырой» HTTP-вызов (как в eqSiteCMS), а не через `ApiClient.post`, чтобы не создавать рекурсию в
`FetchApiClient.send`. `createSingleFlightRefresh(baseUrl, fetchImpl?)` возвращает `() => Promise<boolean>`: пока
предыдущий вызов не завершился, все обращения получают один и тот же promise (это и есть точка single-flight, а не
свойство `FetchApiClient` — он и так делает один повтор на запрос, но без дедупликации между параллельными запросами
дал бы N обращений к `/refresh`). Сетевые сбои и любой не-2xx ответ превращаются в `false`, без исключений и без
собственного toast — вызывающая сторона (`FetchApiClient`) уже решает, что делать с результатом. Функция создаётся
один раз в `main.tsx` и передаётся в `FetchApiClient({ onUnauthorized })`.

**Истёкшая сессия — через очистку кэша сессии, не через императивный `router.navigate`.** Первая версия дёргала
`router.navigate("/login")` прямо из `shared/errors/createErrorHandler`. Это не работает: `GuestOnly` тоже следит за
`SESSION_QUERY_KEY`, и раз сама сессия (`/api/auth/me`) не инвалидирована, он видит «пользователь всё ещё
авторизован» и немедленно отправляет обратно на `/` — навигация на `/login` откатывается тем же рендером. Источник
истины один — кэш `SESSION_QUERY_KEY`, поэтому колбэк ничего не знает о роутере и просто очищает его:
```ts
createErrorHandler(toast, { onUnauthorized: () => queryClient.setQueryData(SESSION_QUERY_KEY, null) })
```
Колбэк вызывается только когда `!meta?.silent` (то есть не для самой проверки `/me`, у неё `meta.silent`) и
`error.kind === "unauthorized"` — после того как `FetchApiClient` уже попытался обновить сессию и не смог. Дальше
`RequireAuth`, уже подписанный на ту же сессию, реагирует на её исчезновение сам и уводит на `/login` — тем же кодом
и с тем же сохранением текущего пути (`state.from`), что и при обычном заходе без сессии; отдельный `router.navigate`
для этого сценария не нужен. `QueryProvider` создаёт `QueryClient` и передаёт в `onUnauthorized` ссылку на себя
(через `let`, замыкание) — колбэку нужен только `queryClient`, `router` в композицию `App`/`QueryProvider` возвращать
не потребовалось.

**Формы (Login/Register/ChangePassword) — единый паттерн, уже описанный в AGENTS.md.** Мутация всегда с
`meta: { silent: true }`; `onError` в компоненте: `kind === "validation"` → `applyFieldErrors` + `form.setFields` +
toast с `toastMessage`; `kind === "unauthorized"` → инлайн-сообщение конкретно под контекст (неверные учётные данные /
неверный текущий пароль), не переиспользуя дефолтный «Сессия истекла...»; остальные виды → `toast.error(resolveErrorMessage(error))`
(переиспользуем чистую функцию из `shared/errors` вместо ветвления по кодам). Это единственное место, где вызывающий
код обращается к `resolveErrorMessage` напрямую, а не только к дефолтному обработчику — сознательное расширение уже
описанного в `frontend-init` правила «`silent` + `applyFieldErrors`» на произвольный текст по виду ошибки.

**Login не рефетчит `/me`.** По спеке `session-auth` тело успешного `/login` уже содержит данные пользователя
(`UserOut`), поэтому `useLogin` мутация напрямую делает `queryClient.setQueryData(SESSION_QUERY_KEY, user)` — на один
запрос меньше и нет промежуточного состояния «вошёл, но сессия ещё не подтверждена». `useLogout` делает
`queryClient.setQueryData(SESSION_QUERY_KEY, null)` независимо от результата запроса (cookies на backend уже
недействительны после ответа, а если запрос не дошёл — они всё равно истекут по TTL).

**Редирект после входа — только в `GuestOnly`, не в `LoginPage`.** Первая версия делала оба: `useLogin`
обновлял кэш сессии, а `LoginPage.onSuccess` сам вызывал `navigate(from)`. Это гонка: обновление кэша сразу
перерисовывает `GuestOnly` (он тоже подписан на `SESSION_QUERY_KEY`), и его собственный `<Navigate to="/" replace/>`
мог выполниться позже explicit-вызова из `LoginPage` и затереть переход на `from` переходом на `/`. Порядок между
реакцией на изменение кэша React Query и явным вызовом `navigate` в одном обработчике не гарантирован. Исправление:
`GuestOnly` — единственное место, решающее «куда редиректить авторизованного пользователя», и само читает
`location.state.from`; `LoginPage.onSuccess` только обрабатывает ошибки, а успешный вход не делает ничего, кроме
обновления кэша — переход выполняет `GuestOnly` тем же рендером, что и при прямом заходе на `/login` под сессией.

**Выход — по той же причине, только в `RequireAuth`, не в `LogoutButton`.** Тот же паттерн гонки нашёлся и здесь:
`useLogout` очищает `SESSION_QUERY_KEY`, а `LogoutButton` сам вызывал `navigate("/login")` в `onSettled`. Очистка
кэша сразу перерисовывает `RequireAuth` (он подписан на сессию и рендерится на `/settings`, откуда обычно выходят) —
его `<Navigate to="/login" replace state={{from: location}}/>` мог выполниться позже явного вызова из
`LogoutButton` и записать в `state.from` путь, с которого вышли (например, `/settings`), из-за чего следующий вход
возвращал туда же, а не на `/`. Исправление то же: `LogoutButton` только вызывает мутацию, `RequireAuth` — уже
существующий и единственный источник истины для «куда вести неавторизованного» — сам уводит на `/login`, когда
сессия пропадает. Побочный эффект принят как есть: выход со страницы настроек и повторный вход возвращают на
страницу настроек — это не противоречит требованиям и не хуже прежнего поведения.

**Пароль на frontend: только минимальная длина как подсказка, не дублирование backend-валидации.** Поле показывает
`minLength=8` и текст-подсказку «не менее 8 символов»; финальная проверка (в т.ч. верхняя граница 128) — на backend
через `validation`/`applyFieldErrors`, чтобы правило не расходилось в двух местах.

**Структура:**
```
frontend/src/
├── shared/api/refreshSession.ts        # createSingleFlightRefresh
├── shared/errors/createQueryClient.ts  # + необязательный onUnauthorized
├── features/auth/
│   ├── session.ts                      # useSession, SESSION_QUERY_KEY, User
│   ├── RequireAuth.tsx
│   ├── GuestOnly.tsx
│   ├── useLogin.ts / useRegister.ts / useLogout.ts
│   ├── LoginPage.tsx / RegisterPage.tsx
├── features/settings/
│   ├── useChangePassword.ts
│   ├── ChangePasswordForm.tsx
│   └── LogoutButton.tsx
```

## Risks / Trade-offs

- [Редирект на `/login` после истёкшей сессии теряет несохранённый ввод пользователя] → toast предупреждает заранее (короткий access — до 15 минут простоя); за пределами рамок — черновики форм.
- [`meta.silent` на сессии скрывает toast и при реальном обрыве сети на старте] → приемлемо: `RequireAuth` всё равно покажет `/login`, пользователь может повторить.
- [Разные компоненты сами формируют текст ошибки через `resolveErrorMessage`] → небольшое расширение существующего паттерна, не новый механизм; тесты закрепляют тексты.
- [Украденный access действует до 15 минут после logout] → короткий TTL; осознанный компромисс stateless access.
- [Logout гасит все устройства] → принято; отзыв отдельных устройств потребовал бы хранения сессий (вне рамок).
- [Утечка `JWT_SECRET` позволяет подделывать токены] → секрет только в окружении, ≥ 32 символов, запрет дефолта вне development; ротация секрета инвалидирует все сессии (обновление вручную).
- [Один SELECT на `/refresh`] → раз в 15 минут на пользователя, приемлемо.
- [Путь refresh-cookie `/api/auth` и прокси (опыт eqSiteCMS)] → проверить при деплое, при проблемах вынести в настройку.
- [Argon2 нагружает CPU] → выполнение в потоке, верхний предел длины пароля, rate limit вне рамок (риск перебора остаётся до отдельной задачи).
- [Перечисление email через регистрацию] → регистрация по умолчанию выключена.

## Migration Plan

1. Добавить зависимости (`pyjwt`, `argon2-cffi`, `email-validator`) — уже выполнено.
2. Применить миграцию `0002` (`make be-migrate`), задать `JWT_SECRET` (≥ 32 символов) в окружении развёртывания.
3. Откат: `alembic downgrade -1` удаляет `users`; токены не хранятся, откат безопасен.

## Open Questions

- Нужна ли отдельная frontend-задача для экранов входа/регистрации и single-flight refresh (в дорожной карте её нет).
