.PHONY: up down db-shell ingest-samples seed-benchmark run health test test-cov lint fmt typecheck refresh-views

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

# Seed 50 synthetic benchmark signals across 5 brands
seed-benchmark:
	python scripts/seed_benchmark_data.py

# Check API health (one-shot)
health:
	python scripts/check_health.py

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

# Refresh analytics materialized views (requires DB to be running)
refresh-views:
	python -c "import asyncio; from dotenv import load_dotenv; load_dotenv(); from db.connection import create_pool, close_pool; from db.queries import refresh_analytics_views; asyncio.run(create_pool()); asyncio.run(refresh_analytics_views()); asyncio.run(close_pool()); print('Views refreshed.')"
