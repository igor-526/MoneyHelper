## 1. Ядро

- [x] 1.1 `core/entities/transaction.py` — поле `comment: str | None = None` на `Transaction`.

## 2. Модель БД и миграция

- [x] 2.1 `models/transaction.py` — колонка `comment` (`String(1000)`, `nullable=True`) на таблице `transactions`.
- [x] 2.2 `make be-makemigrations msg="transaction_comments"` — автогенерация (чистое добавление колонки, без
      ручных правок); `make be-migrate` локально; проверить `alembic downgrade -1` и повторный `upgrade head`.

## 3. Репозиторий

- [x] 3.1 `core/protocols/repositories/transaction_repository.py::update` — новый именованный параметр
      `comment: str | None`.
- [x] 3.2 `repositories/transaction.py` — `_map_row` читает `comment`; `add` пишет `transaction.comment`; `update`
      принимает и записывает `comment` в `.values(...)`.
- [x] 3.3 `tests/fakes/transaction_repository.py` — аналогичные правки fake-реализации.

## 4. Сервис

- [x] 4.1 `core/services/transaction.py` — `create_transaction`, `create_topup`, `update_transaction` принимают
      `comment: str | None` и прокидывают его в `Transaction(...)`/`repositories.update(...)`.
- [x] 4.2 Unit-тесты: создание операции с комментарием и без, обновление меняет и удаляет (заменяет на `None`)
      комментарий, пополнение с комментарием, `get`/`list` возвращают сохранённый комментарий.

## 5. API

- [x] 5.1 `api/schemas/transaction.py` — поле `comment: str | None = Field(default=None, max_length=1000)` в
      `TransactionCreate` и `TopupCreate` с `field_validator`, нормализующим пробельную/пустую строку в `None`
      (по образцу `strip_name` в `api/schemas/workspace.py`); поле `comment: str | None` в `TransactionOut`.
- [x] 5.2 `api/transactions.py` — передача `body.comment` в вызовы `create_transaction`, `create_topup`,
      `update_transaction`.
- [x] 5.3 Smoke-тесты: создание операции/пополнения с комментарием и без, пробельный комментарий → `null` в
      ответе, слишком длинный комментарий → 400, `PUT` меняет и очищает комментарий, `GET` (один/список)
      возвращает сохранённый комментарий.

## 6. QualityGate

- [x] 6.1 `make format`, затем `make lint`, затем `make test` — все проходят подряд; `make test-infra` — прогнать
      для подтверждения, что миграция и существующие сценарии не сломаны.
- [x] 6.2 `docs/tasks/022_transaction_comments.md` — заполнить раздел «Статус» по итогам реализации.
