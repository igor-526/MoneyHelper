## MODIFIED Requirements

### Requirement: Создание операции
`POST /api/workspaces/{workspace_id}/transactions` SHALL создавать расход с ровно одной «ногой» (валюта + сумма) в
указанном воркспейсе, принадлежащем текущему аутентифицированному пользователю, с указанием кошелька, категории,
положительной суммы и опционального комментария (`comment`, не более 1000 символов). `workspace_id` MUST
принадлежать текущему пользователю. Кошелёк и категория MUST принадлежать указанному воркспейсу. Категория MUST
иметь тип `expense`: доход создаётся только пополнением кошелька (`topups`). Валюта в запросе MUST NOT передаваться:
валюта ноги — всегда валюта кошелька (`wallet.currency_id`); тело запроса с лишними полями (в т.ч. `currency_id`)
отклоняется. Число знаков после запятой суммы MUST NOT превышать `decimal_places`
валюты кошелька; округление не выполняется. `comment`, состоящий только из пробелов или не переданный, SHALL сохраняться как
отсутствующий (`null`), а не как пустая строка. `occurred_at` — опциональное поле; при отсутствии SHALL
использоваться текущее время сервера. Запрос без действительной сессии (без access-cookie) SHALL быть отклонён с
ошибкой аутентификации. Ответ представляет операцию в ногозависимой форме: `legs` — список из одного элемента
`{currency_id, amount}`, и включает `comment`.

#### Scenario: Успешное создание расхода с указанной датой
- **WHEN** аутентифицированный пользователь отправляет `POST /api/workspaces/{workspace_id}/transactions` с
  корректными `wallet_id` (кошелька своего воркспейса), `category_id` (категории типа `expense` своего
  воркспейса), положительным `amount` с числом знаков не более `decimal_places` валюты кошелька и явным
  `occurred_at`, без валюты
- **THEN** ответ 201 содержит созданную операцию с этим `id`, `wallet_id`, `category_id`, `legs` (список из одного
  элемента с `currency_id` кошелька и этим `amount`), `occurred_at` (равным переданному), `created_at` и `updated_at`

#### Scenario: Успешное создание операции без даты — используется текущее время
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен без поля `occurred_at`
- **THEN** ответ 201 содержит операцию с `occurred_at`, равным текущему времени сервера на момент создания

#### Scenario: Отклонение категории дохода
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с категорией типа `income`
- **THEN** ответ 400 с понятным сообщением (доход создаётся пополнением), операция не создаётся

#### Scenario: Отклонение валюты в запросе
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с полем `currency_id`
- **THEN** ответ 400 с ошибкой валидации, операция не создаётся

#### Scenario: Отклонение суммы с превышением числа знаков валюты
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `amount`, число знаков после запятой
  которого превышает `decimal_places` валюты кошелька
- **THEN** ответ 400, операция не создаётся, сумма не округляется

#### Scenario: Отклонение неположительной суммы
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `amount`, равным нулю или отрицательным
- **THEN** ответ 400 с ошибкой валидации, операция не создаётся

#### Scenario: Отклонение несуществующего или чужого кошелька
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `wallet_id`, которого нет в указанном
  воркспейсе
- **THEN** ответ 404, операция не создаётся

#### Scenario: Отклонение несуществующей или чужой категории
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `category_id`, которой нет в указанном
  воркспейсе
- **THEN** ответ 404, операция не создаётся

#### Scenario: Отклонение несуществующего или чужого воркспейса
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `workspace_id`, которого нет ни у одного
  пользователя, либо принадлежащим другому пользователю
- **THEN** ответ 404, операция не создаётся

#### Scenario: Отказ без аутентификации
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен без действительного access-cookie
- **THEN** ответ 401, операция не создаётся

#### Scenario: Успешное создание операции с комментарием
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с непустым `comment` (не более 1000
  символов)
- **THEN** ответ 201 содержит операцию с этим `comment`

#### Scenario: Пробельный комментарий сохраняется как отсутствующий
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `comment`, состоящим только из пробелов
- **THEN** ответ 201 содержит операцию с `comment = null`

#### Scenario: Операция без комментария
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен без поля `comment`
- **THEN** ответ 201 содержит операцию с `comment = null`

#### Scenario: Отклонение слишком длинного комментария
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `comment` длиннее 1000 символов
- **THEN** ответ 400 с ошибкой валидации, операция не создаётся

### Requirement: Полное обновление операции
`PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` SHALL полностью заменять `wallet_id`,
`category_id`, `amount`, `occurred_at` и `comment` расхода, принадлежащего указанному воркспейсу
текущего аутентифицированного пользователя, с той же валидацией, что и при создании (валюта не передаётся и берётся из кошелька; включая категорию типа
`expense`, нормализацию пробельного `comment` в `null` и ограничение длины). Результат содержит ровно одну ногу.
Пополнение через этот ресурс обновить нельзя (404). Частичное обновление (`PATCH`) не поддерживается — отсутствие
`comment` в теле `PUT` заменяет существующий комментарий на `null` (все поля `PUT` обязательны, кроме `comment`).

#### Scenario: Успешная полная замена
- **WHEN** аутентифицированный пользователь отправляет `PUT
  /api/workspaces/{workspace_id}/transactions/{transaction_id}` для расхода своего воркспейса с новыми
  корректными `wallet_id`, `category_id`, `amount` и `occurred_at`
- **THEN** ответ 200 содержит операцию с `legs` — списком из одного элемента с валютой кошелька и обновлённым
  `amount`, и обновлённым `updated_at`

#### Scenario: Обновление несуществующей операции
- **WHEN** `PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен с `transaction_id`,
  которого нет в указанном воркспейсе
- **THEN** ответ 404, изменения не применяются

#### Scenario: Обновление пополнения через ресурс операций
- **WHEN** `PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен для пополнения
- **THEN** ответ 404, изменения не применяются

#### Scenario: Обновление с той же валидацией входных данных, что и создание
- **WHEN** `PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен с полем `currency_id`,
  категорией типа `income`, неположительной суммой, суммой с превышением знаков валюты, либо
  несуществующим/чужим `wallet_id` или `category_id`
- **THEN** ответ 400 или 404 (в зависимости от причины), изменения не применяются

#### Scenario: Изменение комментария существующей операции
- **WHEN** аутентифицированный пользователь отправляет `PUT
  /api/workspaces/{workspace_id}/transactions/{transaction_id}` для своего расхода с новым `comment`
- **THEN** ответ 200 содержит операцию с обновлённым `comment`

#### Scenario: Удаление комментария полной заменой
- **WHEN** операция ранее имела непустой `comment`, и `PUT
  /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен без поля `comment`
- **THEN** ответ 200 содержит операцию с `comment = null`
