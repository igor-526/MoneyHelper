## ADDED Requirements

### Requirement: Токены без хранения на сервере
Система SHALL выдавать JWT access и refresh, подписанные HS256 ключом `JWT_SECRET`, и MUST NOT сохранять токены (ни в открытом виде, ни хешем) на сервере. Алгоритм подписи MUST быть зафиксирован в коде и не настраиваться. Claims: `sub` (UUID пользователя строкой), `token_type` (`access` или `refresh`), `iat`, `exp`; в refresh дополнительно `ver` (`token_version` пользователя). Проверка MUST требовать `sub`, `token_type`, `exp`, сверять `exp` с `Clock` и отклонять токен неверного типа.

#### Scenario: Выдача и проверка access
- **WHEN** выпускается access для пользователя и затем проверяется до истечения
- **THEN** проверка возвращает `user_id` из `sub`

#### Scenario: Истёкший токен
- **WHEN** проверяется токен, время `exp` которого по `Clock` уже прошло
- **THEN** проверка отклоняет токен как недействительный

#### Scenario: Подмена типа
- **WHEN** refresh-токен предъявляется как access (или наоборот)
- **THEN** проверка отклоняет токен

#### Scenario: Подделка подписи
- **WHEN** токен подписан другим ключом или изменён
- **THEN** проверка отклоняет токен

#### Scenario: Алгоритм none
- **WHEN** предъявляется токен с алгоритмом `none`
- **THEN** проверка отклоняет токен

### Requirement: Время жизни токенов
Время жизни access и refresh SHALL задаваться настройками `ACCESS_TOKEN_TTL_MINUTES` (по умолчанию 15) и `REFRESH_TOKEN_TTL_DAYS` (по умолчанию 30) и MUST NOT быть захардкожено. Значения должны быть положительными целыми.

#### Scenario: Значения по умолчанию
- **WHEN** переменные не заданы
- **THEN** access действует 15 минут, refresh — 30 дней

#### Scenario: Некорректное значение
- **WHEN** `ACCESS_TOKEN_TTL_MINUTES=0`
- **THEN** приложение не запускается с понятной ошибкой конфигурации

### Requirement: Настройки безопасности
Настройка `JWT_SECRET` SHALL быть обязательной вне окружения `development` и иметь длину не менее 32 символов; в `development` допускается значение по умолчанию для разработки, которое MUST быть отвергнуто в любом другом окружении. Также SHALL поддерживаться `COOKIE_SECURE` (по умолчанию: включено вне `development`), `COOKIE_DOMAIN` (по умолчанию не задан) и `COOKIE_SAMESITE` (`lax` по умолчанию; `none` допускается только вместе с `COOKIE_SECURE=true`).

#### Scenario: Слабый секрет вне development
- **WHEN** `ENVIRONMENT=production`, а `JWT_SECRET` короче 32 символов или равен значению по умолчанию
- **THEN** приложение не запускается с понятной ошибкой конфигурации

#### Scenario: SameSite=None без Secure
- **WHEN** `COOKIE_SAMESITE=none` и `COOKIE_SECURE=false`
- **THEN** приложение не запускается с понятной ошибкой конфигурации

### Requirement: Вход
`POST /api/auth/login` с JSON `{"email": ..., "password": ...}` SHALL проверять учётные данные и при успехе отвечать 200 с данными пользователя, устанавливая cookies `access_token` и `refresh_token`. Токены MUST NOT попадать в тело ответа. Неизвестный email и неверный пароль MUST давать идентичный ответ 401 (одинаковый текст) и сопоставимое время обработки (проверка выполняется и для неизвестного email).

#### Scenario: Успешный вход
- **WHEN** отправляются верные email (в любом регистре) и пароль
- **THEN** ответ 200 с данными пользователя, заголовки `Set-Cookie` содержат `access_token` и `refresh_token`, в теле токенов нет

#### Scenario: Неверные данные неотличимы
- **WHEN** отправляется несуществующий email, а затем существующий email с неверным паролем
- **THEN** оба ответа имеют статус 401 и одинаковое тело

### Requirement: Cookies сессии
Cookies SHALL ставиться и удаляться только backend. Оба cookie MUST быть `HttpOnly`; `Secure` — по настройке (включён вне `development`); `SameSite` — по настройке (по умолчанию `Lax`); `Domain` — по настройке. `access_token` SHALL иметь `Path=/` и `Max-Age` равный TTL access; `refresh_token` — `Path=/api/auth` и `Max-Age` равный TTL refresh. Frontend не читает токены из JS.

#### Scenario: Атрибуты cookies
- **WHEN** выполняется успешный вход вне development
- **THEN** `access_token` имеет `HttpOnly; Secure; SameSite=Lax; Path=/`, `refresh_token` — `HttpOnly; Secure; SameSite=Lax; Path=/api/auth`

#### Scenario: Refresh не уходит на прочие эндпоинты
- **WHEN** браузер отправляет запрос к `/api/wallets`
- **THEN** cookie `refresh_token` в запрос не включается (его путь `/api/auth`)

### Requirement: Защищённые эндпоинты
Зависимость `get_current_user` SHALL читать `access_token` из cookie, проверять подпись, тип и срок без обращения к БД и возвращать `user_id`. Отсутствующий, просроченный или некорректный токен MUST давать 401 (`AuthenticationError`) с текстовым `detail`.

#### Scenario: Нет cookie
- **WHEN** запрос к защищённому эндпоинту не содержит `access_token`
- **THEN** ответ 401

#### Scenario: Просроченный access
- **WHEN** запрос содержит access, срок которого истёк
- **THEN** ответ 401, по которому клиент может выполнить refresh

### Requirement: Скользящий refresh
`POST /api/auth/refresh` SHALL читать `refresh_token` из cookie, проверять подпись, тип и срок, загружать пользователя и сверять `ver` из токена с `token_version` в БД; при успехе отвечать 204 и устанавливать новую пару токенов (новый `exp` для обоих, актуальный `ver`). Отсутствие cookie, просроченный или некорректный токен, отсутствующий пользователь или несовпадение `ver` MUST давать 401 без установки cookies. Refresh MUST NOT инвалидироваться самим обновлением, поэтому параллельные обновления с одним refresh обе завершаются успехом.

#### Scenario: Успешное обновление
- **WHEN** отправляется валидный refresh существующего пользователя
- **THEN** ответ 204, `Set-Cookie` содержит новые `access_token` и `refresh_token`

#### Scenario: Параллельные обновления
- **WHEN** два запроса `/refresh` приходят одновременно с одним и тем же refresh
- **THEN** оба возвращают 204

#### Scenario: Устаревшая версия
- **WHEN** refresh выдан при `ver = 0`, а `token_version` пользователя уже 1
- **THEN** ответ 401, cookies не устанавливаются

#### Scenario: Access вместо refresh
- **WHEN** в cookie `refresh_token` лежит access-токен
- **THEN** ответ 401

### Requirement: Выход
`POST /api/auth/logout` SHALL всегда удалять оба cookie и отвечать 204. Если в запросе есть валидный refresh, backend MUST увеличить `token_version` пользователя на 1 (условным обновлением по совпадающей версии, без двойного увеличения), гася все refresh этого пользователя на всех устройствах. Отсутствие или недействительность refresh MUST NOT приводить к ошибке.

#### Scenario: Выход с валидным refresh
- **WHEN** отправляется logout с валидным refresh
- **THEN** ответ 204, cookies удалены, `token_version` увеличен на 1, прежний refresh больше не работает

#### Scenario: Выход без сессии
- **WHEN** отправляется logout без cookies
- **THEN** ответ 204, ничего не изменилось

#### Scenario: Повторный logout
- **WHEN** logout повторяется со старым refresh
- **THEN** ответ 204, `token_version` не увеличивается повторно

#### Scenario: Access после выхода
- **WHEN** access, выданный до logout, предъявляется до истечения TTL
- **THEN** он принимается (осознанный компромисс stateless access, не более TTL)
