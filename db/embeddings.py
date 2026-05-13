"""Embedding generation with voyage-3 via Anthropic SDK, batched in groups of 96."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import anthropic

from db import queries
from pipeline.retry import with_exponential_backoff

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "voyage-3")
BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "96"))

_client = anthropic.AsyncAnthropic()


@with_exponential_backoff(
    max_retries=3,
    base_delay=1.0,
    retryable_exceptions=(anthropic.RateLimitError, anthropic.APIStatusError),
)
async def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Call Anthropic's voyage-3 embedding endpoint for a single batch."""
    response = await _client.post(
        "/v1/embeddings",
        body={"model": EMBEDDING_MODEL, "input": texts},
    )
    return [item["embedding"] for item in response["data"]]


async def embed_signals(signal_ids: list[uuid.UUID], texts: list[str]) -> None:
    """
    Generate and store embeddings for a list of signals.

    Batches texts in groups of BATCH_SIZE (default 96) to respect API limits.
    """
    if len(signal_ids) != len(texts):
        raise ValueError("signal_ids and texts must have the same length")

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i : i + BATCH_SIZE]
        logger.info(
            "Embedding batch %d/%d (%d texts)",
            i // BATCH_SIZE + 1,
            (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE,
            len(batch_texts),
        )
        batch_embeddings = await _embed_batch(batch_texts)
        all_embeddings.extend(batch_embeddings)

    for signal_id, embedding in zip(signal_ids, all_embeddings):
        await queries.upsert_embedding(
            signal_id=signal_id,
            embedding=embedding,
            model=EMBEDDING_MODEL,
        )

    logger.info("Stored %d embeddings for model=%s", len(all_embeddings), EMBEDDING_MODEL)
