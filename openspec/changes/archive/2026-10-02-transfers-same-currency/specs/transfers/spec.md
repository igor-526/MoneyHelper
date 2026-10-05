## MODIFIED Requirements

### Requirement: Создание перевода
`POST /api/workspaces/{workspace_id}/transfers` SHALL создавать перевод денежных средств между двумя разными
кошельками указанного воркспейса, принадлежащего текущему аутентифицированному пользователю, без конвертации.
`workspace_id` MUST принадлежать текущему пользователю. `from_wallet_id` и `to_wallet_id` MUST принадлежать
указанному воркспейсу и MUST NOT совпадать. Валюты обоих кошельков MUST совпадать; валюта перевода выводится из
кошельков и в запросе не передаётся: запрос с полем `currency_id` MUST быть отклонён. Сумма MUST быть положительной,
число знаков после запятой MUST NOT превышать `decimal_places` валюты кошельков; округление не выполняется.
`occurred_at` — опциональное поле; при отсутствии SHALL использоваться текущее время сервера. Запрос без
действительной сессии (без access-cookie) SHALL быть отклонён с ошибкой аутентификации.

#### Scenario: Успешное создание перевода
- **WHEN** аутентифицированный пользователь отправляет `POST /api/workspaces/{workspace_id}/transfers` с
  корректными `from_wallet_id` и `to_wallet_id` (оба — кошельки этого воркспейса с одной валютой, разные),
  положительным `amount` с числом знаков не более `decimal_places` этой валюты и явным `occurred_at`
- **THEN** ответ 201 содержит созданный перевод с этим `id`, `from_wallet_id`, `to_wallet_id`, `amount`,
  `occurred_at` (равным переданному), `created_at` и `updated_at`; поле `currency_id` в ответе отсутствует

#### Scenario: Успешное создание перевода без даты — используется текущее время
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен без поля `occurred_at`
- **THEN** ответ 201 содержит перевод с `occurred_at`, равным текущему времени сервера на момент создания

#### Scenario: Отклонение перевода между кошельками разных валют
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `from_wallet_id` и `to_wallet_id`, у которых
  разные валюты
- **THEN** ответ 400 с сообщением, что перевод возможен только между кошельками одной валюты, перевод не создаётся

#### Scenario: Отклонение запроса с currency_id
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с полем `currency_id`
- **THEN** ответ 400 с ошибкой валидации, перевод не создаётся

#### Scenario: Отклонение перевода самому себе
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с одинаковыми `from_wallet_id` и
  `to_wallet_id`
- **THEN** ответ 400 с ошибкой валидации, перевод не создаётся

#### Scenario: Отклонение несуществующего или чужого исходного кошелька
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `from_wallet_id`, которого нет в указанном
  воркспейсе
- **THEN** ответ 404, перевод не создаётся

#### Scenario: Отклонение несуществующего или чужого целевого кошелька
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `to_wallet_id`, которого нет в указанном
  воркспейсе
- **THEN** ответ 404, перевод не создаётся

#### Scenario: Отклонение неположительной суммы
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `amount`, равным нулю или отрицательным
- **THEN** ответ 400 с ошибкой валидации, перевод не создаётся

#### Scenario: Отклонение суммы с превышением числа знаков валюты
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `amount`, число знаков после запятой
  которого превышает `decimal_places` валюты кошельков
- **THEN** ответ 400, перевод не создаётся, сумма не округляется

#### Scenario: Отклонение несуществующего или чужого воркспейса
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `workspace_id`, которого нет ни у одного
  пользователя, либо принадлежащим другому пользователю
- **THEN** ответ 404, перевод не создаётся

#### Scenario: Отказ без аутентификации
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен без действительного access-cookie
- **THEN** ответ 401, перевод не создаётся

### Requirement: Чтение одного перевода
`GET /api/workspaces/{workspace_id}/transfers/{transfer_id}` SHALL возвращать перевод по `id`, только если и
перевод принадлежит указанному воркспейсу, и воркспейс принадлежит текущему аутентифицированному пользователю.

#### Scenario: Успешное чтение своего перевода
- **WHEN** аутентифицированный пользователь запрашивает `GET
  /api/workspaces/{workspace_id}/transfers/{transfer_id}` для перевода своего воркспейса
- **THEN** ответ 200 содержит `id`, `from_wallet_id`, `to_wallet_id`, `amount`, `occurred_at`, `created_at`,
  `updated_at` и не содержит `currency_id`

#### Scenario: Несуществующий перевод
- **WHEN** запрашивается `GET /api/workspaces/{workspace_id}/transfers/{transfer_id}` с `transfer_id`, которого
  нет в указанном воркспейсе
- **THEN** ответ 404

### Requirement: Полное обновление перевода
`PUT /api/workspaces/{workspace_id}/transfers/{transfer_id}` SHALL полностью заменять `from_wallet_id`,
`to_wallet_id`, `amount` и `occurred_at` перевода, принадлежащего указанному воркспейсу текущего аутентифицированного
пользователя, с той же валидацией, что и при создании (включая одинаковую валюту кошельков и отклонение
`currency_id`). Частичное обновление (`PATCH`) не поддерживается.

#### Scenario: Успешная полная замена
- **WHEN** аутентифицированный пользователь отправляет `PUT
  /api/workspaces/{workspace_id}/transfers/{transfer_id}` для перевода своего воркспейса с новыми корректными
  `from_wallet_id`, `to_wallet_id`, `amount` и `occurred_at`
- **THEN** ответ 200 содержит перевод с обновлёнными значениями и обновлённым `updated_at`

#### Scenario: Обновление несуществующего перевода
- **WHEN** `PUT /api/workspaces/{workspace_id}/transfers/{transfer_id}` отправлен с `transfer_id`, которого нет в
  указанном воркспейсе
- **THEN** ответ 404, изменения не применяются

#### Scenario: Обновление с той же валидацией входных данных, что и создание
- **WHEN** `PUT /api/workspaces/{workspace_id}/transfers/{transfer_id}` отправлен с одинаковыми
  `from_wallet_id`/`to_wallet_id`, кошельками разных валют, полем `currency_id`, неположительной суммой, суммой с
  превышением знаков валюты, либо несуществующим/чужим `from_wallet_id` или `to_wallet_id`
- **THEN** ответ 400 или 404 (в зависимости от причины), изменения не применяются

## ADDED Requirements

### Requirement: Перевод не участвует в среднем курсе
Перевод между кошельками одной валюты не меняет валюту средств, поэтому SHALL NOT влиять на средний курс кошелька:
источником курса являются только пополнения.

#### Scenario: Перевод не влияет на курс кошелька
- **WHEN** у кошелька есть переводы (входящие и исходящие)
- **THEN** ответ `GET .../wallets/{wallet_id}/rates` не зависит от наличия этих переводов
