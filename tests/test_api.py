"""Integration-style tests for FastAPI routes — DB and LLM are mocked."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from api.main import app


@pytest.fixture
def client():
    # Override lifespan for test client
    with patch("api.main.create_pool", new_callable=AsyncMock):
        with patch("api.main.close_pool", new_callable=AsyncMock):
            with TestClient(app, raise_server_exceptions=False) as c:
                yield c


class TestHealthEndpoint:
    def test_health_returns_degraded_without_db(self, client):
        # Pool not initialized in test context
        with patch("api.main.get_pool", side_effect=RuntimeError("no pool")):
            resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["db"] is False

    def test_health_returns_ok_with_db(self, client):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("api.main.get_pool", return_value=mock_pool):
            resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestIngestEndpoints:
    def test_ingest_single_signal(self, client):
        mock_id = uuid.uuid4()
        with patch("api.routes.ingest.queries.insert_signal", new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = mock_id
            resp = client.post("/ingest", json={
                "platform": "twitter",
                "brand": "Nike",
                "category": "sportswear",
                "post_text": "Testing signal ingestion",
                "engagements": 1000,
            })

        assert resp.status_code == 201
        data = resp.json()
        assert data["signal_id"] == str(mock_id)
        assert "ingested_at" in data

    def test_ingest_rejects_empty_post_text(self, client):
        resp = client.post("/ingest", json={
            "platform": "twitter",
            "brand": "Nike",
            "category": "sportswear",
            "post_text": "",
        })
        assert resp.status_code == 422

    def test_bulk_ingest(self, client):
        mock_ids = [uuid.uuid4(), uuid.uuid4()]
        side_effects = iter(mock_ids)

        with patch("api.routes.ingest.queries.insert_signal", new_callable=AsyncMock) as mock_insert:
            mock_insert.side_effect = lambda **kwargs: next(side_effects)
            resp = client.post("/ingest/bulk", json={
                "signals": [
                    {
                        "platform": "twitter",
                        "brand": "Nike",
                        "category": "sportswear",
                        "post_text": "Signal one",
                    },
                    {
                        "platform": "instagram",
                        "brand": "Nike",
                        "category": "sportswear",
                        "post_text": "Signal two",
                    },
                ]
            })

        assert resp.status_code == 201
        data = resp.json()
        assert data["count"] == 2


class TestInsightsEndpoints:
    def _make_insight_row(self) -> dict:
        return {
            "id": uuid.uuid4(),
            "brand": "Nike",
            "platform": "twitter",
            "signal_ids": [],
            "extracted_signals": [],
            "topic_clusters": [],
            "insight_text": "Test insight",
            "recommended_actions": [],
            "pipeline_trace": [],
            "created_at": datetime.now(tz=timezone.utc),
        }

    def test_list_insights(self, client):
        rows = [self._make_insight_row()]
        with patch("api.routes.insights.queries.get_insights", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = rows
            resp = client.get("/insights")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["insights"][0]["brand"] == "Nike"

    def test_get_insight_not_found(self, client):
        with patch("api.routes.insights.queries.get_insight_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            resp = client.get(f"/insights/{uuid.uuid4()}")

        assert resp.status_code == 404

    def test_get_insight_by_id(self, client):
        row = self._make_insight_row()
        with patch("api.routes.insights.queries.get_insight_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = row
            resp = client.get(f"/insights/{row['id']}")

        assert resp.status_code == 200
        assert resp.json()["brand"] == "Nike"
