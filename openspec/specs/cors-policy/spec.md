# cors-policy Specification

## Purpose
Политика CORS для frontend на другом origin: список разрешённых origin, credentials и доставка CORS-заголовков в том числе на ответах с ошибками.
## Requirements
### Requirement: Конфигурация списка origin
Система SHALL читать разрешённые origin из переменной `CORS_ORIGINS` как значения, разделённые запятыми, в поле
`Settings.cors_origins`. Пустое значение MUST означать, что CORS не включён.

#### Scenario: Несколько origin
- **WHEN** `CORS_ORIGINS=http://localhost:5173,https://app.example.com`
- **THEN** `cors_origins` содержит оба значения

#### Scenario: Переменная не задана
- **WHEN** `CORS_ORIGINS` пуста или отсутствует
- **THEN** `cors_origins` — пустой список и CORS-заголовки в ответах не добавляются

### Requirement: Валидация значений origin
Система MUST отклонять запуск с некорректным `CORS_ORIGINS`: значение `*`, значение без схемы и значение с путём.
Допустимый формат — `scheme://host[:port]`.

#### Scenario: Wildcard
- **WHEN** `CORS_ORIGINS=*`
- **THEN** создание `Settings` завершается ошибкой валидации

#### Scenario: Origin с путём
- **WHEN** `CORS_ORIGINS=https://app.example.com/path`
- **THEN** создание `Settings` завершается ошибкой валидации

### Requirement: Разрешённый origin получает CORS-заголовки с credentials
Для запроса с заголовком `Origin` из списка система SHALL возвращать `Access-Control-Allow-Origin`, равный этому
origin, и `Access-Control-Allow-Credentials: true`; preflight-запрос SHALL получать разрешённые методы
`GET, POST, PUT, PATCH, DELETE, OPTIONS` и заголовок `Content-Type`.

#### Scenario: Простой запрос с разрешённого origin
- **WHEN** `GET /health` приходит с `Origin`, присутствующим в `CORS_ORIGINS`
- **THEN** ответ содержит `access-control-allow-origin` с этим origin и `access-control-allow-credentials: true`

#### Scenario: Preflight с разрешённого origin
- **WHEN** приходит `OPTIONS` с `Origin` из списка и `Access-Control-Request-Method: POST`
- **THEN** ответ имеет успешный код и содержит разрешённые методы и заголовки

### Requirement: CORS-заголовки на ответах с ошибками
Ответы с ошибками (400, 401, 403, 404, 409 и 500) на запросы с разрешённого origin SHALL содержать те же CORS-заголовки,
что и успешные ответы, чтобы браузер передал frontend код и тело ошибки.

#### Scenario: Ответ 404 с разрешённого origin
- **WHEN** запрос несуществующего пути приходит с `Origin` из списка
- **THEN** ответ имеет код 404 и содержит `access-control-allow-origin` и `access-control-allow-credentials: true`

#### Scenario: Ответ 400 с разрешённого origin
- **WHEN** запрос с ошибкой валидации приходит с `Origin` из списка
- **THEN** ответ имеет код 400 и содержит CORS-заголовки

#### Scenario: Ответ 500 с разрешённого origin
- **WHEN** обработчик бросает необработанное исключение при запросе с `Origin` из списка
- **THEN** ответ имеет код 500, тело `{"detail": "Internal server error"}` и CORS-заголовки

### Requirement: Чужой origin не получает разрешения
Для запроса с `Origin`, которого нет в списке, система MUST NOT добавлять `Access-Control-Allow-Origin`, поэтому
браузер не передаёт ответ страницам чужого origin. (`CORSMiddleware` Starlette может добавить
`Access-Control-Allow-Credentials` на любой запрос с `Origin`; без `Access-Control-Allow-Origin` этот заголовок
не даёт доступа и допустим.)

#### Scenario: Запрос с чужого origin
- **WHEN** `GET /health` приходит с `Origin: https://evil.example`
- **THEN** в ответе нет `access-control-allow-origin`

