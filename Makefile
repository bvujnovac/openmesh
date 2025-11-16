.PHONY: help dev stop build clean logs shell db-migrate db-upgrade test lint format

# Auto-detect docker-compose command (V2 uses 'docker compose', V1 uses 'docker-compose')
DOCKER_COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

help:
	@echo "OpenMesh Platform - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev        - Start development environment"
	@echo "  make stop       - Stop all containers"
	@echo "  make build      - Build Docker images"
	@echo "  make clean      - Remove containers and volumes"
	@echo "  make logs       - Show container logs"
	@echo "  make shell      - Open shell in backend container"
	@echo "  make db-migrate - Create new database migration"
	@echo "  make db-upgrade - Apply database migrations"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code with black"

dev:
	@echo "Starting development environment..."
	@echo "Using: $(DOCKER_COMPOSE)"
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "Services started:"
	@echo "  - Frontend UI: http://localhost:3000"
	@echo "  - Backend API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - InfluxDB UI: http://localhost:8086"
	@echo "  - Redis: localhost:6379"
	@echo ""
	@echo "Run 'make logs' to see logs"

stop:
	@echo "Stopping all containers..."
	$(DOCKER_COMPOSE) stop

build:
	@echo "Building Docker images..."
	$(DOCKER_COMPOSE) build

clean:
	@echo "Removing containers and volumes..."
	$(DOCKER_COMPOSE) down -v
	@echo "Cleaned up!"

logs:
	$(DOCKER_COMPOSE) logs -f

shell:
	$(DOCKER_COMPOSE) exec backend /bin/bash

db-migrate:
	@read -p "Enter migration message: " message; \
	$(DOCKER_COMPOSE) exec backend alembic revision --autogenerate -m "$$message"

db-upgrade:
	$(DOCKER_COMPOSE) exec backend alembic upgrade head

test:
	$(DOCKER_COMPOSE) exec backend pytest

lint:
	$(DOCKER_COMPOSE) exec backend ruff check backend/
	$(DOCKER_COMPOSE) exec backend mypy backend/

format:
	$(DOCKER_COMPOSE) exec backend black backend/
	$(DOCKER_COMPOSE) exec backend ruff check --fix backend/
