# ADR 002: asyncpg Over ORM (SQLAlchemy / Tortoise)

**Status:** Accepted  
**Date:** 2025-05-14

## Context

The application is I/O-bound and makes heavy use of PostgreSQL-specific features: `pgvector` for cosine similarity search, `tsvector` for full-text search, JSONB operators for pipeline trace queries, and materialized views with concurrent refresh. An ORM must abstract these away or provide escape hatches that reintroduce raw SQL anyway.

## Decision

Use **asyncpg directly** with raw SQL in `db/queries.py`. No ORM layer.

- `db/connection.py` manages the asyncpg pool lifecycle.
- `db/queries.py` contains all SQL as string literals.
- Migrations are plain `.sql` files in `db/migrations/`, applied in order.

## Rationale

| Concern | ORM | asyncpg |
|---|---|---|
| pgvector queries | Requires extension or escape hatch | Native SQL: `<=>` operator just works |
| Full-text search | tsvector generated columns need raw DDL anyway | Straightforward |
| JSONB unnesting | Expression API is verbose and opaque | `jsonb_to_recordset(...)` in plain SQL |
| Performance | N+1 query risk, serialization overhead | Direct row access, zero abstraction overhead |
| Migrations | Alembic adds its own model-diffing complexity | Plain SQL files, readable and reviewable |
| Async | SQLAlchemy async is mature but heavy | asyncpg is the reference async PG driver |

## Consequences

- **Positive:** SQL is readable and reviewable in PRs. No "what query did the ORM generate?" debugging.
- **Positive:** PostgreSQL-specific features work without workarounds.
- **Negative:** No automatic schema migration diffing — changes to DB schema require manually writing migration SQL.
- **Negative:** No model-level validation — input validation must happen at the Pydantic API layer before SQL execution.
- **Negative:** Parameter binding syntax (`$1`, `$2`) is PostgreSQL-specific and not portable, but portability is not a goal here.

## Alternatives Considered

- **SQLAlchemy 2.0 async core:** Reasonable choice; rejected because the project uses too many pg-specific features that would require dropping to `text()` expressions throughout.
- **Tortoise ORM:** Async-first Django-style ORM; lacks mature pgvector support.
- **Piccolo:** Lightweight async ORM with pgvector support; newer ecosystem, less community knowledge.
