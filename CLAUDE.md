# Social Media Decoded — Claude Code Context

## What this project does

A multi-agent social signal intelligence platform. Given raw social media posts, a 4-agent LangGraph pipeline:

1. **SignalExtractorAgent** — classifies sentiment, topics, trend score, key phrases
2. **TopicClustererAgent** — groups signals into semantic clusters with engagement weighting
3. **InsightGeneratorAgent** — translates clusters into confidence-scored marketing insights
4. **ActionRecommenderAgent** — recommends prioritised next actions with timeframes

Results are stored in PostgreSQL + pgvector and exposed via a FastAPI REST API.

## Tech Stack

| Layer | Tech |
|---|---|
| API | FastAPI (async), Pydantic v2 |
| Database | PostgreSQL 16 + pgvector, asyncpg (no ORM) |
| Agents | LangGraph StateGraph, Anthropic SDK (claude-sonnet-4-6) |
| Embeddings | voyage-3 via Anthropic SDK, batched in groups of 96 |
| Resilience | Exponential backoff + jitter, circuit breaker (pipeline/retry.py) |
| Logging | structlog (JSON in prod, console in dev) |

## Running locally

```bash
# 1. Start Postgres
cp .env.example .env   # set ANTHROPIC_API_KEY
docker-compose up -d postgres

# 2. Install deps
pip install -r requirements.txt

# 3. Load sample data
python scripts/ingest_sample_data.py

# 4. Start API
uvicorn api.main:app --reload
```

Tests: `pytest`

## Key design decisions

**Why LangGraph?**
Gives us a stateful, inspectable graph where the supervisor can retry failed agents or skip them based on `PipelineState`. The `completed_agents` list prevents duplicate work; the circuit breaker prevents cascading failures.

**Why pgvector?**
Enables semantic similarity search over signal embeddings without a separate vector DB. The `ivfflat` index on `signal_embeddings` keeps cosine similarity queries fast at scale. voyage-3 produces 1536-dim embeddings that fit pgvector's default configuration.

**Why no ORM?**
asyncpg with raw SQL gives us full control over query plans, array/JSONB operators, and pgvector's `<=>` cosine distance operator — none of which map cleanly to SQLAlchemy without custom type extensions.

**Why tool_use mode for structured outputs?**
Claude's `tool_use` mode enforces JSON schema conformance at the model level, meaning we never need to parse or validate free text. Every agent output is validated by Pydantic before it enters the pipeline state.

## File map

```
agents/base.py          — shared LLM client, LRU cache, circuit breaker
agents/supervisor.py    — routes to next worker based on completed/failed sets
pipeline/orchestrator.py — LangGraph graph definition + run_pipeline() entrypoint
pipeline/state.py       — PipelineState TypedDict (single source of truth for shape)
pipeline/retry.py       — with_exponential_backoff decorator + CircuitBreaker class
db/connection.py        — asyncpg pool lifecycle (create/close/acquire)
db/queries.py           — all raw SQL (insert_signal, upsert_embedding, insert_insight, etc.)
db/embeddings.py        — voyage-3 batch embedding generation
api/main.py             — FastAPI app with lifespan + router mounts
```
