# 005. Регистрация и авторизация (этап 0b)

Зависит от: 004. Дорожная карта: [002_roadmap.md](002_roadmap.md). Правила: [AGENTS.md](../../AGENTS.md), раздел «Авторизация».

## Цель
Пользователи могут зарегистрироваться, войти, обновить сессию и выйти; все последующие данные привязываются к `user_id`.

## Контекст и решения
- JWT access и refresh; время жизни в `.env`; токены только в cookies, которые ставит и читает backend; в теле ответа токенов нет.
- Вход по email (нижний регистр, уникален), подтверждения почты нет.
- Регистрация управляется `REGISTRATION_ENABLED`.
- Refresh хранится хешем в `refresh_sessions` с `family_id`; ротация при каждом обновлении, повторное использование отзывает семью.
- Пароли — argon2id, хеширование вне event loop; неверные учётные данные дают один и тот же ответ независимо от причины.
- Access проверяется без обращения к БД.
- Cookies: `HttpOnly`, `Secure` вне development, `SameSite=Lax`; refresh с `Path=/api/auth`.
- CSRF: проверка `Origin` на небезопасных методах по `CORS_ORIGINS`, тело только JSON.

## Объём
- Таблицы `users` и `refresh_sessions`, миграция Alembic.
- Протоколы `PasswordHasher`, `TokenIssuer`, `TokenVerifier` и реализации; репозитории пользователей и сессий.
- Сценарии register, login, refresh, logout; эндпоинты `/api/auth/register|login|refresh|logout` и `/api/auth/me`.
- Установка и удаление cookies в слое `api`; зависимость `get_current_user` в `depends/`.
- Проверка `Origin`.
- Настройки: `JWT_SECRET` (обязателен вне development, валидируется длина), `ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS`, `COOKIE_SECURE`, `COOKIE_DOMAIN`, `COOKIE_SAMESITE`, `REGISTRATION_ENABLED`.
- Замена теста `test_auth_routes_are_not_registered`.
- Unit-тесты на fake-репозиториях и smoke-тесты эндпоинтов.

## Вне рамок
Подтверждение email, сброс пароля, OAuth, роли и права, rate limit на вход.

## Открытые вопросы
Окно терпимости при параллельном refresh; требования к паролю (длина); срок жизни и очистка просроченных сессий; выбор библиотек (PyJWT, argon2).

## Критерии готовности
- Полный цикл register → me → refresh → logout работает через cookies.
- Повторное использование refresh отзывает семью; чужой `Origin` отклоняется.
- QualityGate проходит.
