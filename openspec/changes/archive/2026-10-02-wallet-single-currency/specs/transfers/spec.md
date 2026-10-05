## MODIFIED Requirements

### Requirement: Создание перевода
`POST /api/workspaces/{workspace_id}/transfers` SHALL создавать перевод денежных средств между двумя разными
кошельками указанного воркспейса, принадлежащего текущему аутентифицированному пользователю, в одной валюте, без
конвертации. `workspace_id` MUST принадлежать текущему пользователю. `from_wallet_id` и `to_wallet_id` MUST
принадлежать указанному воркспейсу и MUST NOT совпадать. `currency_id` MUST совпадать с валютой одновременно
`from_wallet_id` И `to_wallet_id`. Сумма MUST быть положительной, число знаков после запятой MUST NOT превышать
`decimal_places` валюты; округление не выполняется. `occurred_at` — опциональное поле; при отсутствии SHALL
использоваться текущее время сервера. Запрос без действительной сессии (без access-cookie) SHALL быть отклонён с
ошибкой аутентификации.

#### Scenario: Успешное создание перевода
- **WHEN** аутентифицированный пользователь отправляет `POST /api/workspaces/{workspace_id}/transfers` с
  корректными `from_wallet_id` и `to_wallet_id` (оба — кошельки этого воркспейса, разные), `currency_id`, равным валюте
  обоих кошельков, положительным `amount` с числом знаков не более `decimal_places` валюты и явным
  `occurred_at`
- **THEN** ответ 201 содержит созданный перевод с этим `id`, `from_wallet_id`, `to_wallet_id`, `currency_id`,
  `amount`, `occurred_at` (равным переданному), `created_at` и `updated_at`

#### Scenario: Успешное создание перевода без даты — используется текущее время
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен без поля `occurred_at`
- **THEN** ответ 201 содержит перевод с `occurred_at`, равным текущему времени сервера на момент создания

#### Scenario: Отклонение перевода, если валюта не совпадает с валютой кошельков
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `currency_id`, отличным от валюты
  `from_wallet_id` или от валюты `to_wallet_id` (включая случай, когда у кошельков разные валюты)
- **THEN** ответ 400 с понятным сообщением, перевод не создаётся

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
  которого превышает `decimal_places` валюты `currency_id`
- **THEN** ответ 400, перевод не создаётся, сумма не округляется

#### Scenario: Отклонение несуществующего или чужого воркспейса
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен с `workspace_id`, которого нет ни у одного
  пользователя, либо принадлежащим другому пользователю
- **THEN** ответ 404, перевод не создаётся

#### Scenario: Отказ без аутентификации
- **WHEN** `POST /api/workspaces/{workspace_id}/transfers` отправлен без действительного access-cookie
- **THEN** ответ 401, перевод не создаётся
