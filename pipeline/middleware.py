"""Request-scoped context vars for pipeline tracing."""
from __future__ import annotations

import contextvars
import uuid

# Bound to each pipeline run so log lines carry the run_id
_run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "run_id", default=""
)


def set_run_id(run_id: str | None = None) -> str:
    rid = run_id or str(uuid.uuid4())
    _run_id_var.set(rid)
    return rid


def get_run_id() -> str:
    return _run_id_var.get()
