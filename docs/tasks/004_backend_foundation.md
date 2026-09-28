# 004. Скелет backend (этап 0a)

Зависит от: — (можно параллельно с 003). Дорожная карта: [002_roadmap.md](002_roadmap.md). Правила: [AGENTS.md](../../AGENTS.md).

## Цель
Подготовить скелет и соглашения backend по SOLID, на которых строятся все следующие этапы, а также CORS и тестовую БД.

## Контекст и решения
- Шаблон содержит только `/health`, `AppError`-иерархию (`ClientError`, `AlreadyExistsError`) и пустые пакеты слоёв.
- Frontend и backend на разных origin (same-site): CORS с `allow_credentials` и точным списком `CORS_ORIGINS` в `.env`, `*` запрещён.
- Деньги — `Decimal`/`NUMERIC`, никогда `float`.
- Тест `test_template_runtime_has_no_cors_configuration_or_headers` больше не отражает требования и заменяется.
- Ошибки (400, 404, 500 и др.) обязаны доходить до frontend как JSON с CORS-заголовками: по каждой frontend показывает toast (задача 003).
- Тесты делятся на unit/smoke без БД (`make test`, CI на GitHub) и infrastructure с БД (`make test-infra`).
- Имя БД везде `POSTGRES_DB`.

## Объём
- Протоколы и реализации `Clock` и `IdGenerator`; fake-реализации для тестов.
- Базовые протоколы и заготовки слоёв по правилам SOLID (порядок добавления фичи из AGENTS.md).
- Соглашения: тип денег, пагинация (запрос и ответ), формат ошибок, исключения для 401 и 403.
- CORS-настройка: `CORS_ORIGINS`, `allow_credentials`, проверка в `Settings`; тесты для разрешённого и чужого origin.
- Тестовая БД для `make test-infra` (отдельная база, применение миграций) и пример infrastructure-теста; каталог `tests/infrastructure/` с автоматическим маркером.
- Middleware необработанных ошибок (500 в JSON с CORS-заголовками, лог и Sentry).
- Workflow GitHub Actions: job без БД (`make lint`, `make test`) и job с PostgreSQL (`make test-infra`).
- Унификация `POSTGRES_NAME` → `POSTGRES_DB` (уже выполнена в конфигурации).
- Расширение smoke-тестов, если меняется запуск приложения.
- Обновление `backend/.env.example`, AGENTS.md и README.md.

## Вне рамок
Пользователи, JWT, cookies и проверка `Origin` (задача 005); сидирование (006).

## Открытые вопросы
Формат пагинации; версии Python и кэширование зависимостей в CI.

## Критерии готовности
- CORS работает по конфигурации, тесты заменены.
- Есть fake-репозитории и `Clock`/`IdGenerator` за протоколами, покрытые unit-тестами.
- `make test-infra` поднимается на тестовой БД.
- QualityGate (`make format`, `make lint`, `make test`) проходит.
