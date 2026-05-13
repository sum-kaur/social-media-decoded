"""Pytest fixtures and configuration."""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def set_required_env_vars(monkeypatch):
    """Ensure tests have minimal required env vars without hitting real services."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
