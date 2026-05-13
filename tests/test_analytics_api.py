"""Tests for GET /analytics and GET /compare endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    with patch("api.main.create_pool", new_callable=AsyncMock):
        with patch("api.main.close_pool", new_callable=AsyncMock):
            with TestClient(app, raise_server_exceptions=False) as c:
                yield c


class TestAnalyticsEndpoint:
    def _mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool, conn

    def test_analytics_returns_expected_shape(self, client):
        pool, conn = self._mock_pool()
        conn.fetch.return_value = []
        conn.fetchrow.return_value = {
            "total_runs": 5,
            "completed_runs": 4,
            "failed_runs": 1,
            "avg_duration_ms": 1200.5,
        }

        with patch("api.routes.analytics.get_pool", return_value=pool):
            resp = client.get("/analytics")

        assert resp.status_code == 200
        data = resp.json()
        assert "agent_performance_db" in data
        assert "agent_performance_live" in data
        assert "brand_summary" in data
        assert "pipeline_run_summary" in data

    def test_analytics_includes_live_metrics(self, client):
        from pipeline.metrics import get_registry
        get_registry().record("TestAgent", latency_ms=42.0)

        pool, conn = self._mock_pool()
        conn.fetch.return_value = []
        conn.fetchrow.return_value = {
            "total_runs": 0,
            "completed_runs": 0,
            "failed_runs": 0,
            "avg_duration_ms": None,
        }

        with patch("api.routes.analytics.get_pool", return_value=pool):
            resp = client.get("/analytics")

        assert resp.status_code == 200
        live = resp.json()["agent_performance_live"]
        assert "TestAgent" in live

    def test_analytics_brand_summary_rows(self, client):
        pool, conn = self._mock_pool()
        brand_rows = [{"brand": "Nike", "insight_count": 3, "latest_insight_at": datetime.now(tz=timezone.utc)}]
        conn.fetch.side_effect = [[], brand_rows]  # agent perf, then brands
        conn.fetchrow.return_value = {"total_runs": 1, "completed_runs": 1, "failed_runs": 0, "avg_duration_ms": 800.0}

        with patch("api.routes.analytics.get_pool", return_value=pool):
            resp = client.get("/analytics")

        assert resp.status_code == 200


class TestCompareEndpoint:
    def _make_signals(self, brand: str) -> list[dict]:
        return [
            {
                "id": uuid.uuid4(),
                "brand": brand,
                "platform": "twitter",
                "post_text": f"{brand} great product",
                "sentiment": "positive",
                "signal_strength": 0.8,
                "engagements": 50000,
                "category": "sportswear",
                "created_at": datetime.now(tz=timezone.utc),
                "source_url": None,
                "author_handle": None,
                "language": "en",
                "is_verified_author": False,
                "raw_metadata": {},
                "tags": [],
            }
        ]

    def test_compare_returns_report(self, client):
        from agents.competitor_analyzer import CompetitorAnalyzerAgent, CompetitorReport

        nike_signals = self._make_signals("Nike")
        adidas_signals = self._make_signals("Adidas")

        mock_report = CompetitorReport(
            brand_a="Nike",
            brand_b="Adidas",
            comparisons=[],
            overall_winner="Nike",
            strategic_recommendation="Focus on UGC",
        )

        with patch("api.routes.compare.queries.get_signals_by_brand", new_callable=AsyncMock) as mock_signals:
            mock_signals.side_effect = [nike_signals, adidas_signals]
            with patch.object(CompetitorAnalyzerAgent, "compare", new_callable=AsyncMock) as mock_compare:
                mock_compare.return_value = mock_report
                resp = client.post("/compare", json={"brand_a": "Nike", "brand_b": "Adidas"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_winner"] == "Nike"
        assert data["brand_a"] == "Nike"

    def test_compare_rejects_same_brand(self, client):
        resp = client.post("/compare", json={"brand_a": "Nike", "brand_b": "Nike"})
        assert resp.status_code == 422

    def test_compare_missing_brand_returns_422(self, client):
        resp = client.post("/compare", json={"brand_a": "Nike"})
        assert resp.status_code == 422


class TestBrandsEndpoint:
    def test_brands_returns_list(self, client):
        mock_rows = [
            {"brand": "Nike", "signal_count": 10, "platforms": ["twitter", "instagram"]},
            {"brand": "Adidas", "signal_count": 5, "platforms": ["twitter"]},
        ]
        with patch("api.routes.brands.queries.get_brands", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rows
            resp = client.get("/brands")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["brands"]) == 2
        assert data["brands"][0]["brand"] == "Nike"

    def test_brands_empty_db(self, client):
        with patch("api.routes.brands.queries.get_brands", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            resp = client.get("/brands")

        assert resp.status_code == 200
        assert resp.json()["brands"] == []


class TestSignalsEndpoint:
    def _make_signal_row(self, brand: str = "Nike") -> dict:
        return {
            "id": uuid.uuid4(),
            "brand": brand,
            "platform": "twitter",
            "post_text": "Great shoes",
            "sentiment": "positive",
            "signal_strength": 0.75,
            "engagements": 1000,
            "category": "sportswear",
            "created_at": datetime.now(tz=timezone.utc),
            "source_url": None,
            "author_handle": "@user",
            "language": "en",
            "is_verified_author": False,
            "raw_metadata": {},
            "tags": [],
        }

    def test_signals_list(self, client):
        rows = [self._make_signal_row(), self._make_signal_row()]
        with patch("api.routes.signals.queries.get_signals_by_brand", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = rows
            resp = client.get("/signals?brand=Nike&limit=2")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["signals"]) == 2

    def test_signals_has_more_flag(self, client):
        # Return limit+1 rows so has_more=True
        rows = [self._make_signal_row() for _ in range(3)]
        with patch("api.routes.signals.queries.get_signals_by_brand", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = rows
            resp = client.get("/signals?brand=Nike&limit=2")

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_more"] is True
        assert len(data["signals"]) == 2
