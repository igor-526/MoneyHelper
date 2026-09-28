# FastAPI Template

Пустой шаблон FastAPI с Clean Architecture, PostgreSQL и эндпоинтом проверки состояния.

## Стек

- Python 3.14.6
- FastAPI
- SQLAlchemy Core + asyncpg
- PostgreSQL 16
- Alembic
- Sentry (опционально)

## Архитектура

```text
src/
├── api/             # HTTP-контракты
├── core/            # сущности, схемы, протоколы и бизнес-логика
├── depends/         # сборка зависимостей FastAPI
├── models/          # SQLAlchemy Core tables
├── repositories/    # реализации repository protocols
├── migration/       # Alembic
├── utils/           # База данных и инфраструктурные утилиты
├── main.py
└── settings.py
```

## Запуск в Docker

```bash
cp .env.example .env
docker compose up --build
```

Compose дождётся PostgreSQL, применит миграции и запустит API на `http://localhost:8000`.
Swagger доступен на `http://localhost:8000/docs`.
Контейнеры объединяются в Compose-проект `fastapi-template`. Каталог `src` подключён как bind mount,
а Uvicorn автоматически перезапускает приложение при изменении исходного кода.

## Локальная разработка

```bash
cp .env.example .env
uv sync
docker compose up -d db
uv run alembic -c src/alembic.ini upgrade head
uv run uvicorn main:app --app-dir src --reload
```

```bash
make format
make lint
make test
```

## Настройки и тесты

- `CORS_ORIGINS` — разрешённые origin frontend (через запятую, формат `scheme://host[:port]`, `*` запрещён); пусто — CORS выключен.
  Запросы отправляются с credentials, ошибки (в том числе 500) приходят JSON с CORS-заголовками.
- `POSTGRES_DB` — имя БД (одно и то же в backend и `.docker-compose/.env`).
- `TEST_POSTGRES_DB`, `TEST_POSTGRES_HOST`, `TEST_POSTGRES_PORT` — БД для `make test-infra`; имя обязано оканчиваться на `_test`.
- `make test` и `pytest` без аргументов не требуют БД; тесты с БД лежат в `tests/infrastructure/` и запускаются `make test-infra`
  (сначала `make infra` в корне репозитория).

## API

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | Healthcheck |

Пакеты `api`, `core`, `depends`, `models` и `repositories` оставлены как точки расширения для новых бизнес-фич.

Sentry включается через `SENTRY_ENABLED=true` и `SENTRY_DSN`. Prometheus в шаблон не входит.
