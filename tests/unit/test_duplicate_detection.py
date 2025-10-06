from __future__ import annotations

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from keep_mcp.services.duplicate import DuplicateDetectionService

pytestmark = pytest.mark.unit


def _similarity(candidate: str, document: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([candidate, document])
    return float(cosine_similarity(matrix[0:1], matrix[1:]).flatten()[0])


def test_find_duplicate_returns_match_when_score_exceeds_threshold() -> None:
    candidate = "Async gather tasks for concurrency"
    document = "Async gather tasks for concurrency"
    service = DuplicateDetectionService(threshold=0.95)

    match = service.find_duplicate(candidate, [("card-1", document)])

    assert match is not None
    assert match.card_id == "card-1"
    assert match.score == pytest.approx(1.0)


def test_find_duplicate_returns_none_when_score_below_threshold() -> None:
    candidate = "Async gather tasks for concurrency"
    document = "Async concurrency best practices"
    similarity = _similarity(candidate, document)
    assert 0.0 < similarity < 0.99
    service = DuplicateDetectionService(threshold=min(similarity + 0.05, 0.999))

    match = service.find_duplicate(candidate, [("card-1", document)])

    assert match is None


def test_find_duplicate_returns_none_for_empty_inputs() -> None:
    service = DuplicateDetectionService()

    assert service.find_duplicate("   ", [("card-1", "Async gather tasks")]) is None
    assert service.find_duplicate("Async gather tasks", []) is None
