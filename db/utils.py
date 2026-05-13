"""Database utility functions."""
from __future__ import annotations


def normalize_signal_strength(
    engagements: int | None,
    max_engagements: int = 1_000_000,
) -> float | None:
    """
    Derive a 0–1 signal_strength from raw engagement count when not provided.

    Uses log scaling so viral outliers don't dominate.
    """
    if engagements is None or engagements <= 0:
        return None
    import math
    log_eng = math.log1p(engagements)
    log_max = math.log1p(max_engagements)
    return min(round(log_eng / log_max, 4), 1.0)


def safe_uuid_list(values: list | None) -> list:
    """Ensure a list from a JSONB/array column is always a plain list."""
    if not values:
        return []
    return [str(v) for v in values]
