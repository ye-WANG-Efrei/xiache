COMPOSE ?= docker compose
SERVICE_POSTGRES ?= postgres
DB_USER ?= xiache
DB_NAME ?= xiache

.PHONY: bootstrap boootstrap up down restart logs psql shell-backend shell-frontend init-db

# Real one-command setup:
# 1) Create .env from .env.example when missing
# 2) Build and start all services
# 3) Re-apply init SQL from inside postgres (idempotent)
bootstrap:
	@if [ ! -f .env ]; then \
		echo "[bootstrap] .env not found, copying from .env.example"; \
		cp .env.example .env; \
	else \
		echo "[bootstrap] using existing .env"; \
	fi
	$(COMPOSE) up -d --build
	$(MAKE) init-db
	@FE=$$($(COMPOSE) port frontend 3000 2>/dev/null | sed 's/.*://'); \
	BE=$$($(COMPOSE) port backend 8000 2>/dev/null | sed 's/.*://'); \
	echo "[bootstrap] done. frontend=http://localhost:$$FE backend=http://localhost:$$BE"

# Backward-compatible alias for common typo.
boootstrap: bootstrap

up:
	$(COMPOSE) up -d --build
	@LOCAL_IP=$$(hostname -I 2>/dev/null | awk '{print $$1}' || ipconfig 2>/dev/null | grep -m1 "IPv4" | awk '{print $$NF}'); \
	FE=$$($(COMPOSE) port frontend 3000 2>/dev/null | sed 's/.*://'); \
	BE=$$($(COMPOSE) port backend 8000 2>/dev/null | sed 's/.*://'); \
	PG=$$($(COMPOSE) port postgres 5432 2>/dev/null | sed 's/.*://'); \
	echo ""; \
	echo "  Services running:"; \
	echo "  Frontend   http://localhost:$$FE   http://$$LOCAL_IP:$$FE"; \
	echo "  Backend    http://localhost:$$BE    http://$$LOCAL_IP:$$BE"; \
	echo "  Postgres   localhost:$$PG           $$LOCAL_IP:$$PG"; \
	echo ""

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) down
	$(COMPOSE) up -d --build

logs:
	$(COMPOSE) logs -f --tail=200

psql:
	$(COMPOSE) exec $(SERVICE_POSTGRES) psql -U $(DB_USER) -d $(DB_NAME)

# Re-run schema init SQL from inside the postgres container (no local password prompt).
init-db:
	$(COMPOSE) exec -T $(SERVICE_POSTGRES) psql -U $(DB_USER) -d $(DB_NAME) -f /docker-entrypoint-initdb.d/01_init.sql

shell-backend:
	$(COMPOSE) exec backend sh

shell-frontend:
	$(COMPOSE) exec frontend sh
