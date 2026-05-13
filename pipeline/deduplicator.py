"""Signal deduplication utilities.

Provides two levels of deduplication:
1. Exact dedup — MD5 hash of post_text, enforced at DB level via unique index.
2. Near-dedup — Jaccard similarity on word trigrams to catch rephrased duplicates.

These are checked before insertion to give early feedback rather than relying
solely on DB constraint violations.
"""
from __future__ import annotations

import hashlib
import re
from typing import Sequence


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _trigrams(text: str) -> set[str]:
    words = _normalize(text).split()
    return {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def exact_hash(post_text: str) -> str:
    """MD5 hex digest of normalised post_text — matches the DB unique index."""
    return hashlib.md5(_normalize(post_text).encode()).hexdigest()


def is_near_duplicate(
    candidate: str,
    existing_texts: Sequence[str],
    threshold: float = 0.85,
) -> bool:
    """Return True if `candidate` is too similar to any text in `existing_texts`.

    Uses word-trigram Jaccard similarity. O(n) in existing_texts — suitable for
    batch dedup of a few hundred signals; use embedding similarity for larger sets.
    """
    candidate_grams = _trigrams(candidate)
    if not candidate_grams:
        return False
    for existing in existing_texts:
        existing_grams = _trigrams(existing)
        if _jaccard(candidate_grams, existing_grams) >= threshold:
            return True
    return False


def deduplicate_batch(
    texts: list[str],
    threshold: float = 0.85,
) -> tuple[list[str], list[int]]:
    """Remove near-duplicates from a batch, keeping the first occurrence.

    Returns (unique_texts, dropped_indices).
    """
    unique: list[str] = []
    dropped: list[int] = []
    seen_hashes: set[str] = set()

    for i, text in enumerate(texts):
        h = exact_hash(text)
        if h in seen_hashes:
            dropped.append(i)
            continue
        if is_near_duplicate(text, unique, threshold=threshold):
            dropped.append(i)
            continue
        unique.append(text)
        seen_hashes.add(h)

    return unique, dropped
