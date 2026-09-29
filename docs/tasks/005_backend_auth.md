# 005. Регистрация и авторизация (этап 0b)

Зависит от: 004. Дорожная карта: [002_roadmap.md](002_roadmap.md). Правила: [AGENTS.md](../../AGENTS.md), раздел «Авторизация».

## Цель
Пользователи могут зарегистрироваться, войти, обновить сессию и выйти; все последующие данные привязываются к `user_id`.

## Контекст и решения
- JWT access и refresh (PyJWT, HS256, подпись `JWT_SECRET`); токены на сервере **не хранятся**; время жизни в `.env`, по умолчанию 15 минут и 30 дней; токены только в cookies, которые ставит и читает backend; в теле ответа токенов нет.
- Claims: `sub` = `user_id` (UUID, не email), `token_type` (`access`/`refresh`), `iat`, `exp`; в refresh ещё `ver` (`token_version`).
- Вход по email (нижний регистр, уникален), подтверждения почты нет.
- Регистрация управляется `REGISTRATION_ENABLED`.
- Refresh скользящий: каждый `/refresh` выдаёт новую пару. Отзыв: у пользователя `token_version`; `/refresh` сверяет `ver` из токена с БД; logout и смена пароля увеличивают `token_version` и гасят все refresh пользователя (на всех устройствах). Окна терпимости нет: старый refresh не инвалидируется при обновлении, гонок нет.
- Пароль: от 8 до 128 символов.
- Пароли — argon2id, хеширование вне event loop; неверные учётные данные дают один и тот же ответ независимо от причины.
- Access проверяется без обращения к БД (до 15 минут после logout он ещё действует — осознанный компромисс).
- Cookies: `HttpOnly`, `Secure` вне development, `SameSite=Lax`; refresh с `Path=/api/auth`.
- CSRF: проверка `Origin` на небезопасных методах по `CORS_ORIGINS`, тело только JSON.

## Объём
- Таблица `users` (в т.ч. `token_version`), миграция Alembic.
- Протоколы `PasswordHasher`, `TokenIssuer`, `TokenVerifier` и реализации; репозиторий пользователей.
- Сценарии register, login, refresh, logout, смена пароля; эндпоинты `/api/auth/register|login|refresh|logout|password` и `/api/auth/me`.
- Установка и удаление cookies в слое `api`; зависимость `get_current_user` в `depends/`.
- Проверка `Origin`.
- Настройки: `JWT_SECRET` (обязателен вне development, валидируется длина), `ACCESS_TOKEN_TTL_MINUTES` (15), `REFRESH_TOKEN_TTL_DAYS` (30), `COOKIE_SECURE`, `COOKIE_DOMAIN`, `COOKIE_SAMESITE`, `REGISTRATION_ENABLED`.
- Замена теста `test_auth_routes_are_not_registered`.
- Unit-тесты на fake-репозиториях и smoke-тесты эндпоинтов.

## Вне рамок
Подтверждение email, сброс пароля, OAuth, роли и права, rate limit на вход.

## Открытые вопросы
Решено: окна терпимости нет (токены не хранятся, refresh скользящий); пароль 8–128 символов; очищать нечего; PyJWT и argon2-cffi. Опыт eqSiteCMS: там refresh-cookie пришлось перенести с `Path=/api/auth` на `/` — проверить, что `Path=/api/auth` работает за нашим прокси.

## Критерии готовности
- Полный цикл register → me → refresh → logout работает через cookies.
- После logout или смены пароля старый refresh отклоняется; чужой `Origin` отклоняется.
- QualityGate проходит.

## Статус
Выполнено (изменение `backend-auth`, архив `2026-09-29-backend-auth`); объём расширен по ходу реализации на
frontend-часть (экраны входа/регистрации, защищённые маршруты, автообновление сессии, выход, смена пароля в UI —
см. capability `frontend-auth`). Проверено вручную в браузере (регистрация → вход → смена пароля → выход → повторный
вход) и полным QualityGate. `Path=/api/auth` у refresh-cookie за прокси в проде не проверялся (нет деплоя) —
на заметку при настройке инфраструктуры.
