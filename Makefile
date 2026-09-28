# =====VARIABLES=====
COMPOSE_DIR = .docker-compose
NETWORK = moneyhelper_network

# Всё приложение — один Compose-проект `moneyhelper` (имя задано `name:` в compose-файлах, флаг -p не нужен).
# Infra и backend лежат в разных файлах, поэтому контейнеры соседнего файла не считаем «осиротевшими».
export COMPOSE_IGNORE_ORPHANS = true

# Docker compose files
COMPOSE_BE = $(COMPOSE_DIR)/docker-compose.be.yml
COMPOSE_INFRA = $(COMPOSE_DIR)/docker-compose.infra.yml

# Docker compose commands
DC_BE = docker compose -f $(COMPOSE_BE)
DC_INFRA = docker compose -f $(COMPOSE_INFRA)

.PHONY: network down be-down infra-down ps be-build be-build-nc infra be be-attach test test-unit test-smoke test-infra lint format quality be-makemigrations be-migrate fe-install fe-dev fe-build fe-preview fe-test fe-lint fe-format fe-pwa-assets

# =====NETWORK=====

# Общая сеть infra и backend; создаётся один раз
network:
	@docker network inspect $(NETWORK) >/dev/null 2>&1 || docker network create $(NETWORK)

# =====BUILD COMMANDS=====

be-build:
	@echo "Building backend image..."
	$(DC_BE) build

be-build-nc:
	@echo "Building backend image without build cache..."
	$(DC_BE) build --no-cache

# =====RUN COMMANDS=====

# Infrastructure
infra: network
	$(DC_INFRA) --env-file $(COMPOSE_DIR)/.env up -d

# Backend
be: network
	$(DC_BE) --env-file backend/.env up -d

be-attach: network
	$(DC_BE) --env-file backend/.env up

# =====STOP / STATUS=====

# Остановка не удаляет тома: данные БД сохраняются
be-down:
	$(DC_BE) --env-file backend/.env down

infra-down:
	$(DC_INFRA) --env-file $(COMPOSE_DIR)/.env down

down: be-down infra-down

ps:
	docker ps -a --filter label=com.docker.compose.project=moneyhelper

# =====QUALITY GATE=====
# Порядок: format -> lint -> test (см. AGENTS.md)

test:
	$(MAKE) -C backend test
	$(MAKE) fe-test

test-unit:
	$(MAKE) -C backend test-unit

test-smoke:
	$(MAKE) -C backend test-smoke

test-infra: network
	$(MAKE) -C backend test-infra

lint:
	$(MAKE) -C backend lint
	$(MAKE) fe-lint

format:
	$(MAKE) -C backend format
	$(MAKE) fe-format

quality: format lint test

# =====FRONTEND=====
# Зависимости ставятся по lock-файлу автоматически при первом запуске и при изменении package-lock.json

frontend/node_modules: frontend/package-lock.json
	npm --prefix frontend ci
	@touch frontend/node_modules

fe-install:
	npm --prefix frontend ci
	@touch frontend/node_modules

# Dev-сервер на http://localhost:5173 (порт совпадает с CORS_ORIGINS backend)
fe-dev: frontend/node_modules
	npm --prefix frontend run dev

fe-build: frontend/node_modules
	npm --prefix frontend run build

# Сборка + preview: так проверяется PWA (service worker выключен в dev-сервере)
fe-preview: fe-build
	npm --prefix frontend run preview

fe-test: frontend/node_modules
	npm --prefix frontend run test

fe-lint: frontend/node_modules
	npm --prefix frontend run lint

fe-format: frontend/node_modules
	npm --prefix frontend run format

# Перегенерировать PWA-иконки из frontend/public/icon.svg
fe-pwa-assets: frontend/node_modules
	npm --prefix frontend run pwa-assets

# =====BACKEND MANAGEMENT=====

be-makemigrations:
	cd backend && docker exec moneyhelper-backend sh -c "cd src && uv run --no-sync alembic revision --autogenerate -m '$(msg)'"

be-migrate:
	cd backend && docker exec moneyhelper-backend sh -c "cd src && uv run --no-sync alembic upgrade head"
