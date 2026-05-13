# ADR 001: LangGraph Supervisor/Worker Pattern

**Status:** Accepted  
**Date:** 2025-05-14

## Context

The pipeline must coordinate four sequential agents (signal extraction → topic clustering → insight generation → action recommendation) with clear state handoff, retry logic, and observable control flow. The naive approach — calling agents in a linear `await agent1(); await agent2(); ...` chain — lacks routing flexibility and makes it difficult to add conditional steps (e.g. skip clustering if signals are sparse) or parallel branches (e.g. run trend analysis and action recommendation concurrently).

## Decision

Use **LangGraph's `StateGraph`** with a supervisor/worker pattern:

- A `supervisor` node reads `completed_agents` from `PipelineState` and routes to the next worker, or to `persist` when all agents are done.
- Each of the four worker nodes (signal_extractor, topic_clusterer, insight_generator, action_recommender) writes its output directly into `PipelineState` and returns to the supervisor.
- A terminal `persist` node commits results to PostgreSQL.

All state flows through a single `PipelineState` TypedDict — there are no direct agent-to-agent calls. The supervisor is the only node with routing logic.

## Rationale

| Concern | Alternative | Chosen approach |
|---|---|---|
| Control flow | Linear chain | Supervisor routing with conditional edges |
| State management | Pass dicts between agents | Single `PipelineState` TypedDict |
| Observability | Inline print statements | `pipeline_trace` list appended by each agent |
| Retry | Per-agent custom retry | `with_exponential_backoff` decorator on `BaseAgent._call_llm` |
| Future branching | Rewrite the chain | Add conditional edges in LangGraph without touching agents |

## Consequences

- **Positive:** Adding a new agent (e.g. a `sentiment_comparator`) requires only a new node + edge in `build_graph()`, not changes to existing agents.
- **Positive:** `pipeline_trace` gives per-run visibility into which agents ran, their latency, and token usage, without additional instrumentation.
- **Negative:** LangGraph adds a dependency and a non-trivial learning curve. The supervisor indirection adds ~1ms overhead per route step.
- **Negative:** All state must be JSON-serialisable (no Python objects), which requires converting `datetime`/`UUID` values on the boundaries.

## Alternatives Considered

- **Direct chain (no framework):** Simpler but rigid. Adding conditional steps requires invasive refactoring.
- **Prefect/Airflow:** Better for DAG-based batch workflows but heavy for real-time API calls. No native LLM tool-use support.
- **LangChain LCEL:** Better for single-chain pipelines but lacks the graph model needed for supervisor routing and future parallel branches.
