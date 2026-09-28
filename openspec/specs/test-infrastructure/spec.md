# test-infrastructure Specification

## Purpose
Разделение тестов на unit/smoke без БД и infrastructure с БД, изолированная тестовая БД, fake-репозитории, CI на GitHub Actions и единое имя переменной БД.
## Requirements
### Requirement: Изолированная тестовая БД
Тесты SHALL использовать отдельную базу данных, имя которой берётся из `TEST_POSTGRES_DB` (по умолчанию `app_test`)
и оканчивается на `_test`. Система MUST NOT обращаться к базе разработки при запуске тестов; при несоответствии имени
фикстура MUST завершиться ошибкой до любых операций с БД.

#### Scenario: Тесты используют тестовую БД
- **WHEN** запускаются тесты
- **THEN** `settings.postgres_db` равен имени тестовой БД, а не БД разработки из `.env`

#### Scenario: Тестовый хост и порт
- **WHEN** заданы `TEST_POSTGRES_HOST` и `TEST_POSTGRES_PORT`
- **THEN** тесты подключаются к этому хосту и порту, а не к значениям `POSTGRES_HOST` и `POSTGRES_PORT` из `.env`

#### Scenario: Недопустимое имя базы
- **WHEN** `TEST_POSTGRES_DB` не оканчивается на `_test`
- **THEN** подготовка тестовой БД завершается ошибкой без создания и изменения базы

### Requirement: Подготовка схемы тестовой БД
Перед infrastructure-тестами система SHALL создать тестовую БД при её отсутствии и применить миграции Alembic до `head`.

#### Scenario: Первый запуск
- **WHEN** тестовой БД не существует
- **THEN** она создаётся, миграции применяются, таблица `alembic_version` существует

#### Scenario: Повторный запуск
- **WHEN** тестовая БД уже существует и миграции применены
- **THEN** подготовка завершается без ошибок и без потери схемы

### Requirement: Изоляция infrastructure-тестов откатом
Каждый infrastructure-тест SHALL выполняться во внешней транзакции, которая откатывается после теста, так что запись
одного теста не видна другому.

#### Scenario: Запись откатывается
- **WHEN** тест создаёт запись через сессию из фикстуры
- **THEN** после завершения теста запись отсутствует в БД

### Requirement: Разделение наборов тестов
`make test` SHALL запускать unit- и smoke-тесты без внешней инфраструктуры и MUST NOT требовать доступа к БД;
`make test-infra` SHALL запускать только тесты с маркером `infrastructure`. Тесты в `tests/infrastructure/` MUST
получать маркер `infrastructure` автоматически, а фикстуры БД SHALL быть доступны только в этом каталоге.

#### Scenario: make test без БД
- **WHEN** PostgreSQL недоступен и выполняется `make test`
- **THEN** все выбранные тесты проходят

#### Scenario: Голый pytest без БД
- **WHEN** PostgreSQL недоступен и выполняется `pytest` без аргументов
- **THEN** infrastructure-тесты не выбираются и запуск завершается успешно

#### Scenario: Маркер выставляется автоматически
- **WHEN** тест лежит в `tests/infrastructure/` без явного маркера
- **THEN** pytest относит его к `infrastructure` и `make test` его не запускает

#### Scenario: make test-infra
- **WHEN** PostgreSQL доступен и выполняется `make test-infra`
- **THEN** выполняются infrastructure-тесты, включая проверку применённых миграций

#### Scenario: make test-infra без БД
- **WHEN** PostgreSQL недоступен и выполняется `make test-infra`
- **THEN** запуск завершается ошибкой с понятным сообщением, а не пропуском тестов

### Requirement: CI на GitHub Actions
Репозиторий SHALL содержать workflow `.github/workflows/ci.yml` с job `quality` (`make lint` и `make test`, без сервисов
и без БД) и job `infrastructure` (сервисный контейнер PostgreSQL и `make test-infra`). Job `quality` MUST NOT зависеть от
доступности БД. Деплой в workflow MUST NOT входить.

#### Scenario: Job quality без БД
- **WHEN** CI запускает job `quality`
- **THEN** `make lint` и `make test` проходят без сервисных контейнеров

#### Scenario: Job infrastructure с БД
- **WHEN** CI запускает job `infrastructure` с контейнером PostgreSQL
- **THEN** `make test-infra` создаёт тестовую БД, применяет миграции и проходит

### Requirement: Единое имя переменной БД
Имя базы данных SHALL задаваться переменной `POSTGRES_DB` во всех конфигурациях (backend и инфраструктура); переменная
`POSTGRES_NAME` MUST NOT использоваться.

#### Scenario: Конфигурация инфраструктуры
- **WHEN** проверяются `.docker-compose/docker-compose.infra.yml` и `.docker-compose/.env`
- **THEN** имя базы задаётся через `POSTGRES_DB`, упоминаний `POSTGRES_NAME` нет

### Requirement: Fake-репозиторий для unit-тестов
Тестовая инфраструктура SHALL содержать базовый `InMemoryRepository`, поведение которого совпадает с контрактом
боевых репозиториев: `get` возвращает `None` для отсутствующей записи, а выбрасывание `NotFoundError` остаётся
ответственностью сервиса.

#### Scenario: Получение отсутствующей записи
- **WHEN** тест вызывает `get` для неизвестного идентификатора
- **THEN** результат — `None`, исключение не бросается

#### Scenario: Список со срезом
- **WHEN** в репозитории три записи и вызывается `list` с `limit=2`, `offset=1`
- **THEN** возвращаются вторая и третья записи в порядке добавления

