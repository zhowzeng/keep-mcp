from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from keep_mcp.storage.models.memory_card import MemoryCard
from keep_mcp.utils.time import parse_utc, utc_now_str


@dataclass(frozen=True)
class RankedCard:
    card: MemoryCard
    score: float


class RankingService:
    """Score cards for recall responses."""

    def rank(self, cards: Iterable[MemoryCard], query: str | None) -> List[RankedCard]:
        cards_list = list(cards)
        if not cards_list:
            return []

        semantic_scores = self._semantic_scores(cards_list, query)
        now = parse_utc(utc_now_str())

        ranked: list[RankedCard] = []
        for card in cards_list:
            semantic = semantic_scores.get(card.card_id, 0.0)
            recency = self._recency_score(card.updated_at, now)
            penalty = self._recall_penalty(card.recall_count)
            score = 0.6 * semantic + 0.3 * recency + 0.1 * penalty
            ranked.append(RankedCard(card=card, score=score))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked

    def _semantic_scores(self, cards: list[MemoryCard], query: str | None) -> dict[str, float]:
        if query is None or not query.strip():
            base_score = 0.5
            return {card.card_id: base_score for card in cards}

        documents = [query] + [f"{card.title}\n{card.summary}\n{card.body or ''}" for card in cards]
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(documents)
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        return {card.card_id: float(similarities[index]) for index, card in enumerate(cards)}

    def _recency_score(self, updated_at: str, now: datetime) -> float:
        try:
            updated_dt = parse_utc(updated_at)
        except ValueError:
            return 0.5
        delta_days = (now - updated_dt).total_seconds() / 86400.0
        return math.exp(-delta_days / 14.0)

    def _recall_penalty(self, recall_count: int) -> float:
        if recall_count <= 5:
            return 1.0
        return 1.0 / (1.0 + (recall_count - 5) / 5.0)
