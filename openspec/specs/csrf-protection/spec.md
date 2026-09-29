# csrf-protection Specification

## Purpose
Защита от CSRF: проверка заголовка Origin на небезопасных методах по CORS_ORIGINS, JSON-only тело, доставка отказа без CORS-заголовков для чужого origin.
## Requirements
### Requirement: Проверка Origin
Для небезопасных методов (`POST`, `PUT`, `PATCH`, `DELETE`) приложение SHALL проверять заголовок `Origin`: если он присутствует и его значение не входит в `CORS_ORIGINS`, запрос MUST быть отклонён ответом 403 с JSON `{"detail": ...}` до выполнения обработчика. Значение `Origin: null` MUST отклоняться. Запрос без заголовка `Origin` (не браузерный клиент) допускается. Безопасные методы (`GET`, `HEAD`, `OPTIONS`) не проверяются.

#### Scenario: Разрешённый origin
- **WHEN** `POST /api/auth/login` приходит с `Origin`, входящим в `CORS_ORIGINS`
- **THEN** запрос обрабатывается

#### Scenario: Чужой origin
- **WHEN** `POST /api/auth/logout` приходит с `Origin: https://evil.example`
- **THEN** ответ 403, состояние не изменилось, cookies не удалены и не установлены

#### Scenario: Origin null
- **WHEN** запрос приходит с `Origin: null`
- **THEN** ответ 403

#### Scenario: Безопасный метод
- **WHEN** `GET /api/auth/me` приходит с чужим `Origin`
- **THEN** проверка Origin не применяется (доступ ограничивает CORS в браузере)

#### Scenario: Preflight
- **WHEN** приходит `OPTIONS` для разрешённого origin
- **THEN** он обрабатывается CORS-middleware без отказа по Origin

### Requirement: Формат отказа
Ответ 403 от проверки Origin SHALL быть JSON `{"detail": "..."}` с текстовым `detail` на русском и MUST NOT содержать заголовок `access-control-allow-origin` для отклонённого origin. Проверка MUST выполняться до обработчика и до чтения тела запроса и не должна раскрывать состояние сессии.

#### Scenario: Отказ без CORS-заголовков
- **WHEN** запрос с чужим `Origin` отклонён
- **THEN** ответ 403 с JSON `detail` и без `access-control-allow-origin`

### Requirement: Только JSON
Эндпоинты, принимающие тело, SHALL принимать его только как JSON (`Content-Type: application/json`); тело в форме `application/x-www-form-urlencoded`, `multipart/form-data` или `text/plain` MUST отклоняться ошибкой валидации (400) и не приводить к изменениям.

#### Scenario: Форма вместо JSON
- **WHEN** на `POST /api/auth/login` приходит `application/x-www-form-urlencoded`
- **THEN** ответ 400, вход не выполнен

