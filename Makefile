.PHONY: help dev stop build clean logs logs-backend logs-celery logs-beat logs-frontend shell db-migrate db-upgrade test lint format

# Auto-detect container compose command (supports Podman and Docker)
# Priority: podman compose > podman-compose > docker compose > docker-compose
DOCKER_COMPOSE := $(shell \
	if command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then \
		echo "podman compose"; \
	elif command -v podman-compose >/dev/null 2>&1; then \
		echo "podman-compose"; \
	elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then \
		echo "docker compose"; \
	elif command -v docker-compose >/dev/null 2>&1; then \
		echo "docker-compose"; \
	else \
		echo "docker-compose"; \
	fi)

help:
	@echo "OpenMesh Platform - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev        - Start development environment"
	@echo "  make stop       - Stop all containers"
	@echo "  make build      - Build Docker images"
	@echo "  make clean      - Remove containers and volumes"
	@echo "  make logs       - Show all container logs (with timestamps)"
	@echo "  make logs-backend  - Show backend logs only"
	@echo "  make logs-celery   - Show celery worker logs only"
	@echo "  make logs-beat     - Show celery beat logs only"
	@echo "  make logs-frontend - Show frontend logs only"
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
	@echo "Showing logs from all containers (Ctrl+C to stop)..."
	$(DOCKER_COMPOSE) logs -f --tail=100 --timestamps

logs-backend:
	@echo "Showing backend logs only (Ctrl+C to stop)..."
	$(DOCKER_COMPOSE) logs -f --tail=200 --timestamps backend

logs-celery:
	@echo "Showing Celery worker logs only (Ctrl+C to stop)..."
	$(DOCKER_COMPOSE) logs -f --tail=200 --timestamps celery-worker

logs-beat:
	@echo "Showing Celery beat logs only (Ctrl+C to stop)..."
	$(DOCKER_COMPOSE) logs -f --tail=200 --timestamps celery-beat

logs-frontend:
	@echo "Showing frontend logs only (Ctrl+C to stop)..."
	$(DOCKER_COMPOSE) logs -f --tail=200 --timestamps frontend

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
