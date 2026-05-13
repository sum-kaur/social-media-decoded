"""Tests for the startup config validator."""
from __future__ import annotations

import pytest

from pipeline.config_validator import ConfigurationError, validate_config


class TestValidateConfig:
    def test_valid_config_returns_no_warnings(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key-12345")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        warnings = validate_config()
        assert warnings == []

    def test_missing_api_key_warns(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        warnings = validate_config()
        assert any("ANTHROPIC_API_KEY" in w for w in warnings)

    def test_missing_database_url_warns(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key-12345")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        warnings = validate_config()
        assert any("DATABASE_URL" in w for w in warnings)

    def test_invalid_api_key_format_warns(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-valid-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        warnings = validate_config()
        assert any("ANTHROPIC_API_KEY" in w for w in warnings)

    def test_invalid_database_url_format_warns(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")
        warnings = validate_config()
        assert any("DATABASE_URL" in w for w in warnings)

    def test_strict_mode_raises_on_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(strict=True)
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_strict_mode_does_not_raise_on_valid(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key-12345")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        warnings = validate_config(strict=True)
        assert warnings == []

    def test_asyncpg_url_is_accepted(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key-12345")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        warnings = validate_config()
        assert not any("DATABASE_URL" in w for w in warnings)
