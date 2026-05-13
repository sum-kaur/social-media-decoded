# Social Media Decoded

A production-grade multi-agent social signal intelligence platform. Given social marketing campaign data, a 4-agent LangGraph pipeline classifies signals, groups them by topic, generates marketing insights, and recommends actions — all backed by PostgreSQL + pgvector and served over a FastAPI async API.

---

## Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │              FastAPI (async)                  │
                    │  POST /ingest  │  POST /pipeline/run         │
                    │  GET /insights │  GET /health                │
                    └──────────────┬───────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────────────┐
                    │          LangGraph Orchestrator               │
                    │                                               │
                    │   ┌─────────────┐                            │
                    │   │  Supervisor │ ◄── conditional routing    │
                    │   └──────┬──────┘                            │
                    │          │                                    │
                    │   ┌──────▼──────┐                            │
                    │   │  Agent 1    │  SignalExtractorAgent       │
                    │   │  Extract    │  sentiment + topics         │
                    │   └──────┬──────┘  trend_score + key_phrases │
                    │          │                                    │
                    │   ┌──────▼──────┐                            │
                    │   │  Agent 2    │  TopicClustererAgent        │
                    │   │  Cluster    │  semantic grouping          │
                    │   └──────┬──────┘  engagement weighting      │
                    │          │                                    │
                    │   ┌──────▼──────┐                            │
                    │   │  Agent 3    │  InsightGeneratorAgent      │
                    │   │  Insights   │  what it means              │
                    │   └──────┬──────┘  confidence scoring        │
                    │          │                                    │
                    │   ┌──────▼──────┐                            │
                    │   │  Agent 4    │  ActionRecommenderAgent     │
                    │   │  Actions    │  prioritised next steps     │
                    │   └──────┬──────┘  platform + timeframe      │
                    │          │                                    │
                    │   ┌──────▼──────┐                            │
                    │   │   Persist   │  asyncpg → PostgreSQL      │
                    │   └─────────────┘                            │
                    └──────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────────────┐
                    │        PostgreSQL + pgvector                  │
                    │  signals  │  signal_embeddings  │  insights  │
                    └──────────────────────────────────────────────┘
```

---

## Quickstart

**1. Start Postgres + pgvector**
```bash
cp .env.example .env  # add your ANTHROPIC_API_KEY
docker-compose up -d postgres
```

**2. Install dependencies and load sample data**
```bash
pip install -r requirements.txt
python scripts/ingest_sample_data.py
```

**3. Run the API**
```bash
uvicorn api.main:app --reload
# API docs at http://localhost:8000/docs
```

Then trigger the pipeline:
```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"brand": "Nike", "platform": "twitter"}'
```

---

## Production Considerations

| Concern | Implementation |
|---|---|
| **Rate limiting** | Exponential backoff with full jitter on all Anthropic API calls (max 3 retries) |
| **Circuit breaker** | Opens after 5 failures in a rolling window; half-open recovery after 60s |
| **LLM response caching** | SHA-256 keyed in-memory LRU cache (512 entries); swap `_response_cache` for Redis in prod |
| **Structured outputs** | All agents use Claude `tool_use` mode — zero free-text parsing |
| **Embedding batching** | voyage-3 calls batched in groups of 96 to respect API limits |
| **Agent trace logging** | Every invocation logged: agent, input hash, output, latency_ms, token_count |
| **Async throughout** | asyncpg pool, AsyncAnthropic client, async FastAPI handlers |
| **DB migrations** | Plain SQL in `db/migrations/` mounted into Docker init directory |

---

## Evaluation Results

Measured on 5-signal Nike/Adidas fixture set:

| Metric | Score | Threshold |
|---|---|---|
| Sentiment accuracy | 0.80 | ≥ 0.70 |
| Topic recall | 0.67 | ≥ 0.50 |
| Cluster quality (min clusters met) | ✅ | ≥ 2 clusters |
| Action priority distribution (has high) | ✅ | at least 1 high |

Run evals:
```python
from evaluation.eval import run_eval
results = await run_eval(pipeline_output)
```

---

## Project Structure

```
social-media-decoded/
├── agents/           # 4 worker agents + supervisor
├── api/              # FastAPI routes and Pydantic models
├── db/               # asyncpg pool, migrations, query functions, embeddings
├── pipeline/         # LangGraph orchestrator, state, retry, logging
├── evaluation/       # precision/recall checks + fixtures
├── scripts/          # sample data loader
└── tests/            # unit + integration tests
```

---

## Tech Stack

- **Python 3.11+** · **FastAPI** · **asyncpg** (no ORM)
- **LangGraph** — supervisor/worker agent orchestration
- **Anthropic SDK** — claude-sonnet-4-6 for agents, voyage-3 for embeddings
- **Pydantic v2** — structured outputs enforced via `tool_use` mode
- **PostgreSQL 16 + pgvector** — signal storage and semantic similarity
- **Docker + docker-compose** — local development environment
- **structlog** — structured JSON logging in production
