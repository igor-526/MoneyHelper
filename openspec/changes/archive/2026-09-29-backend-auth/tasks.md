## 1. Настройки и зависимости

- [x] 1.1 Добавить в `Settings` поля `JWT_SECRET`, `ACCESS_TOKEN_TTL_MINUTES` (15), `REFRESH_TOKEN_TTL_DAYS` (30), `COOKIE_SECURE`, `COOKIE_DOMAIN`, `COOKIE_SAMESITE`, `REGISTRATION_ENABLED` и проверки (секрет ≥ 32 вне development, TTL > 0, `none` только с Secure)
- [x] 1.2 Обновить `backend/.env` и `backend/.env.example`, `backend/README.md`; unit-тесты настроек (без `.env`)

## 2. Ядро (core)

- [x] 2.1 Сущность `User`, схемы ядра `TokenPair`, `AccessClaims`, `RefreshClaims` и правила пароля (8–128) как константы
- [x] 2.2 Протоколы `PasswordHasher`, `TokenIssuer`, `TokenVerifier`, `UserRepository`
- [x] 2.3 `AuthService`: register (флаг, дубликат), login (единый отказ, тайминговый путь), refresh (сверка `ver`), logout (условное увеличение), change_password, get_user
- [x] 2.4 Fake-реализации в `tests/fakes` (`InMemoryUserRepository`, `FakePasswordHasher`) и unit-тесты `AuthService`

## 3. Инфраструктура

- [x] 3.1 `utils/password_hasher.py` (argon2id через `asyncio.to_thread`, `needs_rehash`) и тест
- [x] 3.2 `utils/jwt_tokens.py` (`JwtTokenService`: HS256 зафиксирован, срок по `Clock`, тип токена, `require` claims) и тесты (истечение, подмена типа, подпись, `alg=none`)
- [x] 3.3 Таблица `models/user.py`, `repositories/user.py` (перевод `IntegrityError` в `AlreadyExistsError`), миграция `20260929_0002_users.py`
- [x] 3.4 Тесты репозитория в `tests/infrastructure/` (уникальность email в любом регистре, условная версия, смена пароля)

## 4. API

- [x] 4.1 `api/cookies.py`: установка и удаление cookies по настройкам (HttpOnly, Secure, SameSite, Domain, Path, Max-Age)
- [x] 4.2 `depends/`: `get_auth_service`, `get_current_user` (access без БД) и зависимости репозитория/хешера/токенов
- [x] 4.3 Схемы запросов/ответов в `api` (`RegisterRequest`, `LoginRequest`, `ChangePasswordRequest` с нормализацией и валидацией email/пароля, `UserOut`) и `api/auth.py`: `/register`, `/login`, `/refresh`, `/logout`, `/password`, `/me`; подключение роутера в `main.py`
- [x] 4.4 `utils/origin_check_middleware.py` и подключение в `create_app()` (внутри CORS); тесты Origin, формы вместо JSON, отсутствия CORS-заголовков при отказе
- [x] 4.5 API-тесты: полный цикл через cookies, атрибуты `Set-Cookie`, Path refresh, параллельный refresh, устаревший `ver`, регистрация выключена, дубликат, неверные данные неотличимы, 401 без cookie
- [x] 4.6 Заменить `test_auth_routes_are_not_registered` и добавить smoke-тест регистрации маршрутов

## 5. Frontend: обновление сессии

- [x] 5.1 `shared/api/refreshSession.ts`: `createSingleFlightRefresh(baseUrl, fetchImpl?)`; тесты (дедупликация параллельных вызовов, `false` при сетевом сбое и при не-2xx)
- [x] 5.2 `shared/errors/createQueryClient.ts`: необязательный `onUnauthorized`-колбэк в `createErrorHandler`, вызывается при `kind === "unauthorized"` и `!meta?.silent`; тесты
- [x] 5.3 `main.tsx`: `FetchApiClient` с `onUnauthorized` (single-flight refresh). Изменение по ходу реализации: `createQueryClient`'s `onUnauthorized` не дёргает `router.navigate` напрямую (гонка с `GuestOnly`, см. design.md), а очищает кэш сессии — редирект делает `RequireAuth` реактивно; `router` в `QueryProvider` не понадобился

## 6. Frontend: экраны и защита маршрутов

- [x] 6.1 `features/auth/session.ts`: `User`, `SESSION_QUERY_KEY`, `useSession` (`retry: false`, `meta.silent: true`)
- [x] 6.2 `features/auth/RequireAuth.tsx` и `GuestOnly.tsx` (спиннер во время проверки, редирект с сохранением `from`); тесты
- [x] 6.3 `features/auth/useLogin.ts`, `LoginPage.tsx`: форма email/пароль, `setQueryData` при успехе, переход на `from`/`/`, инлайн-ошибка `unauthorized`; тесты (успех, неверные данные, сеть/сервер — toast)
- [x] 6.4 `features/auth/useRegister.ts`, `RegisterPage.tsx`: форма email/пароль с подсказкой длины, привязка ошибок валидации к полям, сообщение при `forbidden` (регистрация отключена) и `conflict` (email занят), переход на `/login` с уведомлением после успеха; тесты
- [x] 6.5 Обновить `app/routes.tsx` (группы `GuestOnly`/`RequireAuth`, все существующие маршруты под защитой) и `app/App.tsx`/`main.tsx`; обновить/добавить тесты `app/App.test.tsx`

## 7. Frontend: выход и смена пароля

- [x] 7.1 `features/settings/useLogout.ts` и `LogoutButton.tsx` на странице настроек: `setQueryData(null)`, переход на `/login`; тесты
- [x] 7.2 `features/settings/useChangePassword.ts` и `ChangePasswordForm.tsx` на странице настроек: поля текущего/нового пароля, привязка ошибок валидации, инлайн `unauthorized`, toast «Пароль изменён» и очистка полей при успехе; тесты
- [x] 7.3 Реакция на истёкшую сессию во время работы: тест — запрос завершается `unauthorized` после неудачного refresh → toast «Сессия истекла, войдите снова» и переход на `/login`

## 8. Документация и проверка

- [x] 8.1 Уточнить AGENTS.md (раздел «Авторизация» backend и frontend, структура `features/auth`, single-flight refresh, `meta.silent` для сессии) и `openspec/config.yaml`; README.md
- [x] 8.2 Проверить вручную с реальной БД и frontend: `make be-migrate`, полный цикл в браузере (регистрация → вход → защищённая страница → смена пароля → выход → повторный вход), `Set-Cookie`, отказ по чужому `Origin`, редирект `/login` ↔ `/register`, mobile-viewport форм. Обновление access по истечении TTL (15 минут) не выжидалось живьём — проверено юнит- и API-тестами (истечение по `FixedClock`, параллельный refresh, реакция на `unauthorized` во время работы)
- [x] 8.3 QualityGate: `make format`, `make lint`, `make test`, `make test-infra`
