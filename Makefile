.PHONY: help dev stop build clean logs shell db-migrate db-upgrade test lint format

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
	docker-compose up -d
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
	docker-compose stop

build:
	@echo "Building Docker images..."
	docker-compose build

clean:
	@echo "Removing containers and volumes..."
	docker-compose down -v
	@echo "Cleaned up!"

logs:
	docker-compose logs -f

shell:
	docker-compose exec backend /bin/bash

db-migrate:
	@read -p "Enter migration message: " message; \
	docker-compose exec backend alembic revision --autogenerate -m "$$message"

db-upgrade:
	docker-compose exec backend alembic upgrade head

test:
	docker-compose exec backend pytest

lint:
	docker-compose exec backend ruff check backend/
	docker-compose exec backend mypy backend/

format:
	docker-compose exec backend black backend/
	docker-compose exec backend ruff check --fix backend/
