# MoneyHelper

Личное приложение для ведения финансов в Китае. Монорепозиторий: backend (FastAPI) и frontend (React, PWA).
Приложение в основном используется на телефоне.

## Суть

Живя в Китае, я держу деньги в нескольких кошельках и валютах и веду таблицу доходов и расходов. MoneyHelper
заменяет эту таблицу: кошельки, категории, операции и аналитика.

### Возможности

**Авторизация**
- Регистрация по email (управляется флагом `REGISTRATION_ENABLED`) и вход.
- Сессия — JWT access и refresh в HTTP-only cookies; backend их не хранит, только проверяет подпись и срок.
- Смена пароля и выход завершают сессию на всех устройствах.

**Воркспейсы, кошельки и валюты**
- Воркспейс — изолированное рабочее пространство пользователя со своей основной валютой; кошельки, категории,
  операции и аналитика принадлежат воркспейсу.
- Кошельки администрируются отдельно для каждого воркспейса.
- Примеры кошельков: UPay (USDT), Alipay CNY (2 шт.), WeChatPay CNY (2 шт.), NihaoChina CNY, наличные RUB и др.
- У кошелька ровно одна валюта; она может совпадать с основной валютой воркспейса.
- Пополнение кошелька указывается в двух валютах (валюта воркспейса и валюта кошелька; одна сумма, если они
  совпадают) — по нему считается курс.

**Категории**
- Отдельные категории для доходов и для расходов.
- Иконки есть у категорий и у кошельков. Iconpack — Lucide; в БД хранится имя иконки, общее для backend и frontend.

**Доходы и расходы**
- Каждая операция привязана к конкретному кошельку: пополнение (доход) — в двух валютах, расход — в валюте кошелька.
- Дата операции хранится как локальная календарная дата и время без часового пояса.

**Аналитика**
- Просмотр доходов и расходов в разных разрезах (кошелёк, категория, валюта, период и т. д.); суммы по умолчанию в
  валюте воркспейса, курс — средний по всем пополнениям воркспейса независимо от периода аналитики.
- Режим «Курс» показывает по датам фактическую цену выбранной валюты в RUB и минимум, максимум и среднее по
  отображаемым дневным значениям.

## Структура репозитория

```text
.
├── backend/           # FastAPI API (Clean Architecture), см. AGENTS.md
├── frontend/          # React + Ant Design, CSR, PWA (mobile-first, светлая и тёмная темы)
├── docs/tasks/        # файлы задач, которые передаются в OpenSpec (propose / explore)
├── openspec/          # OpenSpec: конфигурация, спецификации, изменения
├── .claude/           # навыки и команды OpenSpec для Claude Code
├── .docker-compose/   # docker compose: инфраструктура (БД) и backend
├── AGENTS.md          # правила и паттерны для агентов и разработчиков
├── CLAUDE.md          # ссылка на AGENTS.md
└── Makefile           # единая точка входа: сборка, запуск, QualityGate
```

## Технологии (backend)

- Python 3.14, FastAPI, Uvicorn
- SQLAlchemy Core + asyncpg, PostgreSQL, Alembic
- Pydantic / pydantic-settings
- JWT (access + refresh) в cookies, без хранения токенов на сервере; argon2id
- Sentry (опционально)
- uv, pytest, ruff, flake8, mypy

## Технологии (frontend)

- React 19, TypeScript (strict), Vite, полностью CSR
- Ant Design 6, mobile-first, светлая и тёмная темы (режим «как в системе» по умолчанию)
- PWA: установка на домашний экран, оболочка открывается офлайн; данные API не кэшируются
- TanStack Query, react-router, Lucide (иконки)
- ESLint, Prettier, Vitest + Testing Library, npm

## Быстрый старт

```bash
# сеть для docker compose (один раз)
docker network create moneyhelper_network

cp backend/.env.example backend/.env
# переменные инфраструктуры (порты, доступы к БД) лежат в .docker-compose/.env

make infra      # PostgreSQL
make be-build   # сборка образа backend
make be         # backend + миграции
make be-migrate # применить миграции вручную
```

Swagger: `http://localhost:${EXPOSE_APP_PORT}/docs`.

Ключевые переменные `backend/.env` (пример — `backend/.env.example`): `POSTGRES_*` (в том числе `POSTGRES_DB` — то же имя
используется в `.docker-compose/.env`), `CORS_ORIGINS` (origin frontend через запятую, например `http://localhost:5173`),
`TEST_POSTGRES_DB`.

Frontend (нужен Node.js 22+; backend должен быть запущен, а `CORS_ORIGINS` в `backend/.env` содержать
`http://localhost:5173`):

```bash
cp frontend/.env.example frontend/.env   # VITE_API_URL, по умолчанию http://localhost:8201
make fe-dev                              # http://localhost:5173
make fe-preview                          # сборка + предпросмотр: так проверяется PWA (service worker выключен в dev)
```

Для проверки на телефоне откройте dev-сервер по адресу компьютера в локальной сети (`npm --prefix frontend run dev -- --host`)
и добавьте этот origin в `CORS_ORIGINS`. Установка PWA и service worker работают только по HTTPS или на `localhost`.

Локальная разработка без Docker для backend:

```bash
cd backend
uv sync
uv run alembic -c src/alembic.ini upgrade head
uv run uvicorn main:app --app-dir src --reload
```

## QualityGate

Любая задача считается выполненной только после прохождения трёх команд, запускаемых строго в таком порядке
(каждая покрывает и backend, и frontend):

```bash
make format   # backend: ruff; frontend: eslint --fix + prettier --write
make lint     # backend: ruff, mypy, flake8; frontend: eslint, prettier --check, tsc
make test     # backend: unit + smoke (без БД); frontend: vitest (без backend и сети)
```

Дополнительно:

| Команда | Что делает |
|---|---|
| `make quality` | `format` → `lint` → `test` одной командой |
| `make test-unit` | только unit-тесты |
| `make test-smoke` | только smoke-тесты (приложение поднимается, критичные эндпоинты отвечают) |
| `make test-infra` | тесты с маркером `infrastructure` (лежат в `backend/tests/infrastructure/`, нужна БД) |
| `make fe-test` / `make fe-lint` / `make fe-format` | то же только для frontend |
| `make fe-build` | сборка frontend (`tsc` + `vite build`) |

`make test` и просто `pytest` не требуют БД, поэтому проходят в CI на GitHub без сервисов. Тесты с БД используют
отдельную базу `TEST_POSTGRES_DB` (по умолчанию `app_test`, имя обязано оканчиваться на `_test`); при запуске с хоста
задайте `TEST_POSTGRES_HOST`/`TEST_POSTGRES_PORT`. Перед `make test-infra` поднимите БД: `make infra`.

CI (`.github/workflows/ci.yml`): job `frontend` (`npm ci`, lint, тесты, сборка) — без БД и без backend.
Деплой в workflow не входит.

Цель — чистый и однообразный код: форматирование и линтинг не обсуждаются, а автоматизируются.

## Процесс разработки: OpenSpec

Разработка ведётся по spec-driven подходу с [OpenSpec](https://github.com/Fission-AI/OpenSpec).

1. Задача описывается в файле `docs/tasks/NNN_name.md`.
2. Файл передаётся навыку `/opsx:explore` (обсуждение и детализация) или `/opsx:propose` (создание изменения).
3. OpenSpec создаёт артефакты в `openspec/changes/<change>/`: proposal, specs, design, tasks.
4. `/opsx:apply` реализует задачи, `/opsx:archive` архивирует завершённое изменение.
5. Перед завершением обязателен QualityGate.

Все артефакты OpenSpec и всё общение агентов — **только на русском языке**. Правила заданы в
`openspec/config.yaml`, `AGENTS.md` и `.claude/settings.json`.

Основная задача (постановка проекта): [`docs/tasks/001_main_task.md`](docs/tasks/001_main_task.md).
Дорожная карта и принятые решения: [`docs/tasks/002_roadmap.md`](docs/tasks/002_roadmap.md); отдельные задачи — `docs/tasks/003_*.md` … `012_*.md`.
Пошаговый план реализации создаётся через `/opsx:explore`; каждый этап затем детализируется отдельным `explore`.

## Ссылки

- [AGENTS.md](AGENTS.md) — структура backend и паттерны работы
- [backend/README.md](backend/README.md) — описание шаблона backend
