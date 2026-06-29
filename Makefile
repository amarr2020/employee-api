.PHONY: help install test lint format run mock fetch seed docker-build docker-run docker-stop clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter"
	@echo "  make format       - Format code"
	@echo "  make run          - Start the API server"
	@echo "  make mock         - Start mock server"
	@echo "  make fetch        - Fetch employees from API"
	@echo "  make seed         - Seed database with sample data"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make docker-stop  - Stop Docker container"
	@echo "  make clean        - Remove cache files"

install:
	pip install -r requirements.txt

test:
	pytest

lint:
	ruff check src tests

format:
	ruff format src tests

run:
	python -m src.main serve

mock:
	python -m src.main mock

fetch:
	python -m src.main fetch

seed:
	python scripts/seed_database.py

docker-build:
	docker build -t employee-api .

docker-run:
	docker run -d --name employee-api -p 8000:8000 employee-api

docker-stop:
	docker stop employee-api && docker rm employee-api

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
