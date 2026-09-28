## ADDED Requirements

### Requirement: Интерфейс API-клиента
Frontend SHALL общаться с backend только через интерфейс `ApiClient` из `shared/api`. Компоненты и hooks MUST зависеть от этого интерфейса, а не от `fetch` напрямую; реализация подставляется провайдером верхнего уровня.

#### Scenario: Подстановка реализации в тестах
- **WHEN** компонент или hook рендерится в тесте с фейковой реализацией `ApiClient`
- **THEN** он использует фейк и не выполняет сетевых запросов

### Requirement: Cookies и адрес backend
Реализация клиента SHALL отправлять каждый запрос с `credentials: "include"` на адрес из `VITE_API_URL`. Токены MUST NOT читаться и сохраняться в JS, `localStorage` или `sessionStorage`. Тело запросов SHALL передаваться как JSON с заголовком `Content-Type: application/json`.

#### Scenario: Запрос с cookies
- **WHEN** клиент выполняет любой запрос
- **THEN** вызов `fetch` содержит `credentials: "include"` и URL, начинающийся с `VITE_API_URL`

#### Scenario: Адрес не задан
- **WHEN** `VITE_API_URL` не задан при старте приложения
- **THEN** используется значение по умолчанию `http://localhost:8201`

### Requirement: Нормализация ошибок в ApiError
Клиент SHALL превращать любой неуспешный результат в исключение типа `ApiError` с полями `kind`, `status`, `detail` и `fieldErrors`. Возможные `kind`: `validation` (400), `unauthorized` (401), `forbidden` (403), `not_found` (404), `conflict` (409), `server` (5xx), `network` (сбой сети), `timeout`, `unknown` (прочие статусы, ответ не в формате JSON).

#### Scenario: Ошибка с текстовым detail
- **WHEN** backend отвечает 409 и телом `{"detail": "Кошелёк уже существует"}`
- **THEN** клиент бросает `ApiError` с `kind = "conflict"`, `status = 409` и `detail = "Кошелёк уже существует"`

#### Scenario: Ошибка валидации по полям
- **WHEN** backend отвечает 400 и телом `{"detail": [{"loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error"}]}`
- **THEN** клиент бросает `ApiError` с `kind = "validation"` и `fieldErrors = {"email": ["value is not a valid email address"]}`; сегмент `body` в имени поля отбрасывается

#### Scenario: Ответ 500 без JSON
- **WHEN** сервер отвечает 500 с телом, которое не является JSON
- **THEN** клиент бросает `ApiError` с `kind = "server"`, `status = 500` и пустым `detail`

#### Scenario: Сетевой сбой
- **WHEN** `fetch` завершается ошибкой соединения
- **THEN** клиент бросает `ApiError` с `kind = "network"` и `status = null`

#### Scenario: Таймаут
- **WHEN** ответ не получен за время таймаута клиента (по умолчанию 15 секунд)
- **THEN** запрос прерывается и клиент бросает `ApiError` с `kind = "timeout"`

### Requirement: Точка расширения для 401
Клиент SHALL иметь настраиваемый обработчик 401. Если обработчик сообщает об успешном обновлении сессии, клиент MUST один раз повторить исходный запрос; если обработчик не задан или обновление не удалось, клиент SHALL бросить `ApiError` с `kind = "unauthorized"`. Повторный запрос не должен зацикливаться.

#### Scenario: Успешное обновление сессии
- **WHEN** запрос вернул 401, а обработчик вернул успех
- **THEN** запрос повторяется ровно один раз и его результат возвращается вызывающему

#### Scenario: Обработчик не задан
- **WHEN** запрос вернул 401 и обработчик не задан
- **THEN** клиент бросает `ApiError` с `kind = "unauthorized"` без повторных запросов

#### Scenario: Повторный 401
- **WHEN** повторный запрос после успешного обновления снова вернул 401
- **THEN** клиент бросает `ApiError` с `kind = "unauthorized"` и не повторяет запрос ещё раз
