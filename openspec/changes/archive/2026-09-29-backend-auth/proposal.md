## Why

Все данные приложения (кошельки, категории, операции) принадлежат пользователю, поэтому до них нужны регистрация и
авторизация — и backend, и frontend. Скелет backend готов (`backend-foundation`), скелет frontend с обработкой ошибок
и точкой расширения для 401 готов (`frontend-init`). Делаем полный цикл сразу: без него приложением нельзя пользоваться.

## What Changes

- Таблица `users` (email, хеш пароля argon2id, `token_version`) и миграция Alembic.
- Регистрация по email и паролю (8–128 символов), управляемая флагом `REGISTRATION_ENABLED`.
- Вход, обновление сессии, выход, текущий пользователь, смена пароля: `/api/auth/register|login|refresh|logout|password|me`.
- JWT access и refresh (HS256, подпись `JWT_SECRET`), **без хранения токенов на сервере**; время жизни из `.env` (по умолчанию 15 минут и 30 дней); токены только в HttpOnly-cookies, которые ставит и читает backend.
- Скользящий refresh; отзыв через `token_version` пользователя: logout и смена пароля гасят все refresh пользователя.
- Зависимость `get_current_user` (access проверяется без БД) для последующих эндпоинтов.
- Защита от CSRF: проверка заголовка `Origin` на небезопасных методах по `CORS_ORIGINS`, тело только JSON.
- Настройки `JWT_SECRET`, `ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS`, `COOKIE_SECURE`, `COOKIE_DOMAIN`, `COOKIE_SAMESITE`, `REGISTRATION_ENABLED`.
- Зависимости: `pyjwt`, `argon2-cffi`, `email-validator`.
- Замена теста `test_auth_routes_are_not_registered`.

**Frontend:**
- Страницы входа и регистрации (`/login`, `/register`), доступные без сессии; авторизованный пользователь на них не попадает.
- Защита остальных маршрутов: без сессии — редирект на `/login` с возвратом на исходный путь после входа.
- Проверка сессии (`GET /api/auth/me`) при старте приложения; single-flight обновление сессии (`/api/auth/refresh`) при 401 у любого запроса, с повтором исходного запроса.
- Истёкшая сессия (обновление не удалось): toast «Сессия истекла, войдите снова» и переход на `/login`.
- Выход и смена пароля на странице настроек.

Затрагивается API: новые эндпоинты `/api/auth/*`. Затрагивается БД: новая таблица `users`, **нужна миграция Alembic**.
**BREAKING**-изменений нет.

## Capabilities

### New Capabilities
- `frontend-auth`: экраны входа и регистрации, защищённые и публичные маршруты, проверка и обновление сессии, выход, смена пароля в UI.
- `user-accounts`: пользователи, регистрация по email, правила пароля, смена пароля, изоляция идентичности (`user_id`).
- `session-auth`: JWT-токены без хранения, cookies, вход, скользящий refresh, отзыв через `token_version`, выход, текущий пользователь, настройки.
- `csrf-protection`: проверка `Origin` на небезопасных методах и JSON-only тело.

### Modified Capabilities
<!-- Требования существующих спецификаций не меняются. -->

## Impact

- `backend/src`: `core/entities/user.py`, `core/protocols/{user_repository,password_hasher,tokens}.py`, `core/services/auth.py`, `core/schemas/auth.py`, `core/exceptions`, `models/user.py`, `repositories/user.py`, `api/auth.py` и `api/cookies.py`, `depends/{auth,user}.py`, `utils/{password_hasher,jwt_tokens,origin_check_middleware}.py`, `settings.py`, `main.py`, миграция.
- `backend/.env`, `backend/.env.example`: новые переменные.
- Тесты backend: unit (сервис на fake-репозитории, токены, хешер), API (полный цикл через cookies, Origin), smoke, infrastructure (репозиторий на БД).
- `frontend/src`: `shared/api/refreshSession.ts` (single-flight, используется в `onUnauthorized`), `shared/errors` — обработчик ошибок дополняется опциональным колбэком на `kind === "unauthorized"`; `features/auth/` (сессия, `RequireAuth`, `GuestOnly`, страницы входа/регистрации); `features/settings/` — выход и смена пароля; `app/routes.tsx`, `app/App.tsx`, `main.tsx` — подключение. Тесты Vitest на все сценарии.

## Non-goals

- Подтверждение email, сброс пароля, OAuth, роли и права, rate limit на вход.
- Хранение токенов и списки отозванных токенов; отзыв одного устройства (logout гасит все refresh пользователя).
- Запоминание пароля менеджером паролей и автозаполнение сверх стандартного поведения браузера; капча.
