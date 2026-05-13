"""Startup configuration validator.

Checks that all required environment variables are set and well-formed before
the application begins serving requests. Raises ConfigurationError on failure
so the pod crashes immediately with a clear error rather than failing at
request time.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


class ConfigurationError(Exception):
    pass


@dataclass
class _Check:
    name: str
    required: bool = True
    pattern: str | None = None
    min_length: int = 1


_CHECKS: list[_Check] = [
    _Check("ANTHROPIC_API_KEY", pattern=r"^sk-ant-.+"),
    _Check("DATABASE_URL", pattern=r"^postgresql(\+asyncpg)?://"),
    _Check("APP_ENV", required=False),
    _Check("LOG_LEVEL", required=False),
    _Check("LLM_MODEL", required=False),
    _Check("CACHE_BACKEND", required=False),
]


def validate_config(strict: bool = False) -> list[str]:
    """Validate environment configuration.

    Args:
        strict: If True, raise ConfigurationError on any failure.
                If False, return a list of warning strings.

    Returns:
        List of validation warnings (empty = all OK).
    """
    warnings: list[str] = []

    for check in _CHECKS:
        value = os.environ.get(check.name, "")

        if check.required and len(value) < check.min_length:
            warnings.append(f"Missing required env var: {check.name}")
            continue

        if value and check.pattern and not re.match(check.pattern, value):
            warnings.append(
                f"Env var {check.name} does not match expected pattern "
                f"({check.pattern!r}). Got: {value[:20]!r}..."
            )

    if strict and warnings:
        raise ConfigurationError(
            "Configuration errors:\n" + "\n".join(f"  - {w}" for w in warnings)
        )

    return warnings
