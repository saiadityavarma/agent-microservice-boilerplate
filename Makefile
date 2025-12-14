# Makefile
.PHONY: help start stop logs shell test lint format migrate reset

COMPOSE = docker compose -f docker/docker-compose.yml

help:
	@echo "Commands:"
	@echo "  start   - Start dev environment"
	@echo "  stop    - Stop dev environment"
	@echo "  logs    - View API logs"
	@echo "  shell   - Open shell in API container"
	@echo "  test    - Run tests"
	@echo "  lint    - Run linter"
	@echo "  format  - Format code"
	@echo "  migrate - Run DB migrations"
	@echo "  reset   - Reset environment"

start:
	$(COMPOSE) up -d --build
	@echo "API: http://localhost:8000"

stop:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api

shell:
	$(COMPOSE) exec api bash

test:
	$(COMPOSE) exec api pytest tests/ -v

lint:
	$(COMPOSE) exec api ruff check src/

format:
	$(COMPOSE) exec api ruff format src/

migrate:
	$(COMPOSE) exec api alembic upgrade head

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build
