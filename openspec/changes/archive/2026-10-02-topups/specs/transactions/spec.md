## MODIFIED Requirements

### Requirement: Создание операции
`POST /api/workspaces/{workspace_id}/transactions` SHALL создавать расход с ровно одной «ногой» (валюта + сумма) в
указанном воркспейсе, принадлежащем текущему аутентифицированному пользователю, с указанием кошелька, категории,
валюты, положительной суммы и опционального комментария (`comment`, не более 1000 символов). `workspace_id` MUST
принадлежать текущему пользователю. Кошелёк и категория MUST принадлежать указанному воркспейсу. Категория MUST
иметь тип `expense`: доход создаётся только пополнением кошелька (`topups`). Валюта операции MUST совпадать с валютой
указанного кошелька (`wallet.currency_id`). Число знаков после запятой суммы MUST NOT превышать `decimal_places`
валюты; округление не выполняется. `comment`, состоящий только из пробелов или не переданный, SHALL сохраняться как
отсутствующий (`null`), а не как пустая строка. `occurred_at` — опциональное поле; при отсутствии SHALL
использоваться текущее время сервера. Запрос без действительной сессии (без access-cookie) SHALL быть отклонён с
ошибкой аутентификации. Ответ представляет операцию в ногозависимой форме: `legs` — список из одного элемента
`{currency_id, amount}`, и включает `comment`.

#### Scenario: Успешное создание расхода с указанной датой
- **WHEN** аутентифицированный пользователь отправляет `POST /api/workspaces/{workspace_id}/transactions` с
  корректными `wallet_id` (кошелька своего воркспейса), `category_id` (категории типа `expense` своего
  воркспейса), `currency_id` валюты кошелька, положительным `amount` с числом знаков не более `decimal_places`
  валюты и явным `occurred_at`
- **THEN** ответ 201 содержит созданную операцию с этим `id`, `wallet_id`, `category_id`, `legs` (список из одного
  элемента с этими `currency_id` и `amount`), `occurred_at` (равным переданному), `created_at` и `updated_at`

#### Scenario: Успешное создание операции без даты — используется текущее время
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен без поля `occurred_at`
- **THEN** ответ 201 содержит операцию с `occurred_at`, равным текущему времени сервера на момент создания

#### Scenario: Отклонение категории дохода
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с категорией типа `income`
- **THEN** ответ 400 с понятным сообщением (доход создаётся пополнением), операция не создаётся

#### Scenario: Отклонение валюты, отличной от валюты кошелька
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `currency_id`, отличным от
  валюты (`currency_id`) указанного кошелька
- **THEN** ответ 400 с понятным сообщением, операция не создаётся

#### Scenario: Отклонение суммы с превышением числа знаков валюты
- **WHEN** `POST /api/workspaces/{workspace_id}/transactions` отправлен с `amount`, число знаков после запятой
  которого превышает `decimal_places` валюты `currency_id`
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

### Requirement: Список операций пользователя с фильтрами и сортировкой
`GET /api/workspaces/{workspace_id}/transactions` SHALL возвращать постраничный список расходов (операций с
категорией типа `expense`), принадлежащих только указанному воркспейсу текущего аутентифицированного пользователя,
отсортированный по `occurred_at` по убыванию, затем по `id` по убыванию как детерминированному tie-breaker (новые
операции первыми). Пополнения в списке MUST NOT присутствовать (они читаются через `topups`). Опциональные
query-параметры `wallet_id`, `category_id`, `date_from` и `date_to` (включительно, диапазон по `occurred_at`) SHALL
сужать список. Если заданы оба `date_from` и `date_to`, и `date_from` позже `date_to`, запрос SHALL быть отклонён.
Параметры пагинации — `limit` (1..100, по умолчанию 20) и `offset` (≥ 0, по умолчанию 0). Каждый элемент списка
представляет операцию в ногозависимой форме (`legs`).

#### Scenario: Список содержит только операции указанного воркспейса
- **WHEN** аутентифицированный пользователь запрашивает `GET /api/workspaces/{workspace_id}/transactions` для
  одного из своих воркспейсов, при этом у него есть операции в других его воркспейсах
- **THEN** ответ 200 содержит только операции указанного воркспейса, `total` равен числу его операций

#### Scenario: Список не содержит пополнений
- **WHEN** в воркспейсе есть и пополнения, и расходы
- **THEN** `GET /api/workspaces/{workspace_id}/transactions` возвращает только расходы, `total` равен их числу

#### Scenario: Порядок списка — новые операции первыми
- **WHEN** в воркспейсе есть несколько операций с разными `occurred_at`
- **THEN** ответ 200 возвращает их отсортированными по `occurred_at` по убыванию, а при равном `occurred_at` — по
  `id` по убыванию

#### Scenario: Фильтр по кошельку
- **WHEN** пользователь запрашивает `GET /api/workspaces/{workspace_id}/transactions?wallet_id=...` для одного из
  кошельков этого воркспейса
- **THEN** ответ 200 содержит только операции этого кошелька

#### Scenario: Фильтр по категории
- **WHEN** пользователь запрашивает `GET /api/workspaces/{workspace_id}/transactions?category_id=...` для одной из
  категорий этого воркспейса
- **THEN** ответ 200 содержит только операции этой категории

#### Scenario: Фильтр по диапазону дат
- **WHEN** пользователь запрашивает `GET
  /api/workspaces/{workspace_id}/transactions?date_from=...&date_to=...`
- **THEN** ответ 200 содержит только операции с `occurred_at` в указанном диапазоне включительно

#### Scenario: Некорректный диапазон дат отклоняется
- **WHEN** `GET /api/workspaces/{workspace_id}/transactions?date_from=...&date_to=...` запрошен с `date_from`,
  позже `date_to`
- **THEN** ответ 400 с ошибкой валидации

#### Scenario: Пагинация по умолчанию
- **WHEN** `GET /api/workspaces/{workspace_id}/transactions` запрошен без параметров `limit`/`offset`
- **THEN** ответ 200 использует `limit = 20`, `offset = 0`

#### Scenario: Недопустимые параметры пагинации отклоняются
- **WHEN** `GET /api/workspaces/{workspace_id}/transactions` запрошен с `limit` вне диапазона 1..100 или с
  отрицательным `offset`
- **THEN** ответ 400 с ошибкой валидации

#### Scenario: Отклонение несуществующего или чужого воркспейса
- **WHEN** `GET /api/workspaces/{workspace_id}/transactions` отправлен с `workspace_id`, которого нет ни у одного
  пользователя, либо принадлежащим другому пользователю
- **THEN** ответ 404

### Requirement: Чтение одной операции
`GET /api/workspaces/{workspace_id}/transactions/{transaction_id}` SHALL возвращать расход по `id`, только если и
операция принадлежит указанному воркспейсу, и воркспейс принадлежит текущему аутентифицированному пользователю.
Пополнение с таким `id` MUST считаться несуществующим. Ответ представляет операцию в ногозависимой форме: `legs` —
список из одного элемента `{currency_id, amount}`, и включает `comment` (`null`, если комментарий не задан).

#### Scenario: Успешное чтение своей операции
- **WHEN** аутентифицированный пользователь запрашивает `GET
  /api/workspaces/{workspace_id}/transactions/{transaction_id}` для расхода своего воркспейса
- **THEN** ответ 200 содержит `id`, `wallet_id`, `category_id`, `legs`, `comment`, `occurred_at`, `created_at`,
  `updated_at`

#### Scenario: Несуществующая операция
- **WHEN** запрашивается `GET /api/workspaces/{workspace_id}/transactions/{transaction_id}` с `transaction_id`,
  которого нет в указанном воркспейсе
- **THEN** ответ 404

#### Scenario: Пополнение недоступно через ресурс операций
- **WHEN** запрашивается `GET /api/workspaces/{workspace_id}/transactions/{transaction_id}`, где `transaction_id`
  — пополнение
- **THEN** ответ 404

### Requirement: Полное обновление операции
`PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` SHALL полностью заменять `wallet_id`,
`category_id`, `currency_id`, `amount`, `occurred_at` и `comment` расхода, принадлежащего указанному воркспейсу
текущего аутентифицированного пользователя, с той же валидацией, что и при создании (включая категорию типа
`expense`, нормализацию пробельного `comment` в `null` и ограничение длины). Результат содержит ровно одну ногу.
Пополнение через этот ресурс обновить нельзя (404). Частичное обновление (`PATCH`) не поддерживается — отсутствие
`comment` в теле `PUT` заменяет существующий комментарий на `null` (все поля `PUT` обязательны, кроме `comment`).

#### Scenario: Успешная полная замена
- **WHEN** аутентифицированный пользователь отправляет `PUT
  /api/workspaces/{workspace_id}/transactions/{transaction_id}` для расхода своего воркспейса с новыми
  корректными `wallet_id`, `category_id`, `currency_id`, `amount` и `occurred_at`
- **THEN** ответ 200 содержит операцию с `legs` — списком из одного элемента с обновлёнными `currency_id`/
  `amount`, и обновлённым `updated_at`

#### Scenario: Обновление несуществующей операции
- **WHEN** `PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен с `transaction_id`,
  которого нет в указанном воркспейсе
- **THEN** ответ 404, изменения не применяются

#### Scenario: Обновление пополнения через ресурс операций
- **WHEN** `PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен для пополнения
- **THEN** ответ 404, изменения не применяются

#### Scenario: Обновление с той же валидацией входных данных, что и создание
- **WHEN** `PUT /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен с валютой, не совпадающей с
  валютой кошелька, категорией типа `income`, неположительной суммой, суммой с превышением знаков валюты, либо
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

### Requirement: Удаление операции
`DELETE /api/workspaces/{workspace_id}/transactions/{transaction_id}` SHALL физически удалять расход,
принадлежащий указанному воркспейсу текущего аутентифицированного пользователя, вместе со связанной строкой
`transaction_legs` (каскадно). Пополнение через этот ресурс удалить нельзя (404).

#### Scenario: Успешное удаление
- **WHEN** аутентифицированный пользователь отправляет `DELETE
  /api/workspaces/{workspace_id}/transactions/{transaction_id}` для расхода своего воркспейса
- **THEN** ответ 204, операция и её нога удалены; последующий `GET
  /api/workspaces/{workspace_id}/transactions/{transaction_id}` для того же `id` возвращает 404

#### Scenario: Удаление несуществующей операции
- **WHEN** `DELETE /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен с `transaction_id`,
  которого нет в указанном воркспейсе
- **THEN** ответ 404

#### Scenario: Удаление пополнения через ресурс операций
- **WHEN** `DELETE /api/workspaces/{workspace_id}/transactions/{transaction_id}` отправлен для пополнения
- **THEN** ответ 404, пополнение не удаляется

## REMOVED Requirements

### Requirement: Пополнение многовалютного кошелька
**Reason**: Пополнение стало самостоятельным видом операции с собственным ресурсом
`/api/workspaces/{workspace_id}/topups` и правилом ног «валюта воркспейса + валюта кошелька» (capability `topups`).
**Migration**: Вместо `POST /api/workspaces/{workspace_id}/transactions/topups` использовать
`POST /api/workspaces/{workspace_id}/topups`; чтение, обновление и удаление — через `/topups/{topup_id}`.
