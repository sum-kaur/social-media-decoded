"""Tests for the signal deduplicator."""
from __future__ import annotations

import pytest

from pipeline.deduplicator import (
    deduplicate_batch,
    exact_hash,
    is_near_duplicate,
)


class TestExactHash:
    def test_same_text_same_hash(self):
        assert exact_hash("Hello world") == exact_hash("Hello world")

    def test_different_text_different_hash(self):
        assert exact_hash("Hello world") != exact_hash("Goodbye world")

    def test_normalised_whitespace(self):
        assert exact_hash("Hello   world") == exact_hash("hello world")

    def test_case_insensitive(self):
        assert exact_hash("NIKE IS GREAT") == exact_hash("nike is great")


class TestIsNearDuplicate:
    def test_identical_text_is_duplicate(self):
        text = "Nike just launched a new shoe collection"
        assert is_near_duplicate(text, [text]) is True

    def test_completely_different_text_is_not_duplicate(self):
        assert is_near_duplicate(
            "Nike launched a running shoe",
            ["Adidas made a collaboration with a famous designer"],
        ) is False

    def test_empty_candidate_is_not_duplicate(self):
        assert is_near_duplicate("", ["some existing text"]) is False

    def test_no_existing_texts_is_not_duplicate(self):
        assert is_near_duplicate("Some new text about sneakers", []) is False

    def test_high_similarity_above_threshold(self):
        a = "Nike just dropped their best running shoe collection this year"
        b = "Nike just released their best running shoe collection this year"
        assert is_near_duplicate(a, [b], threshold=0.7) is True

    def test_low_similarity_below_threshold(self):
        a = "Nike running shoes are great for marathons in summer"
        b = "Adidas soccer boots dominate the european football league"
        assert is_near_duplicate(a, [b], threshold=0.85) is False


class TestDeduplicateBatch:
    def test_exact_duplicates_removed(self):
        texts = ["Nike great", "Nike great", "Adidas cool"]
        unique, dropped = deduplicate_batch(texts)
        assert len(unique) == 2
        assert 1 in dropped

    def test_near_duplicates_removed(self):
        texts = [
            "Nike just dropped their best running shoe collection this year",
            "Nike just released their best running shoe collection this year",
            "Adidas made a very different collaboration with Pharrell Williams",
        ]
        unique, dropped = deduplicate_batch(texts, threshold=0.7)
        assert len(unique) == 2
        assert 1 in dropped

    def test_all_unique_batch_preserved(self):
        texts = [
            "Nike launches new Air Max 2025 with improved cushioning",
            "Adidas collaborates with Bad Bunny on streetwear collection",
            "Puma releases Velocity Nitro 3 running shoe for competitive athletes",
        ]
        unique, dropped = deduplicate_batch(texts)
        assert len(unique) == 3
        assert dropped == []

    def test_empty_batch(self):
        unique, dropped = deduplicate_batch([])
        assert unique == []
        assert dropped == []

    def test_first_occurrence_kept(self):
        texts = ["original text about sneakers", "original text about sneakers"]
        unique, dropped = deduplicate_batch(texts)
        assert unique[0] == texts[0]
        assert dropped == [1]
