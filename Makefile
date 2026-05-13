.PHONY: up down db-shell ingest-samples run test lint fmt typecheck

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Open a psql shell
db-shell:
	docker-compose exec postgres psql -U postgres -d social_media_decoded

# Load sample data into the running DB
ingest-samples:
	python scripts/ingest_sample_data.py

# Start the API server in development mode
run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
test:
	pytest

# Run tests with coverage report
test-cov:
	pytest --cov=. --cov-report=term-missing --cov-omit="tests/*,scripts/*"

# Lint with ruff
lint:
	ruff check . --select E,F,W --ignore E501

# Auto-fix lint issues
fmt:
	ruff check . --fix
	ruff format .

# Type check with mypy
typecheck:
	mypy . --ignore-missing-imports --exclude tests/
