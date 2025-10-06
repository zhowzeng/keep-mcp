from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class DuplicateMatch:
    card_id: str
    score: float


class DuplicateDetectionService:
    """Detect potential duplicate cards using TF-IDF cosine similarity."""

    def __init__(self, threshold: float = 0.85) -> None:
        self._threshold = threshold

    def find_duplicate(self, candidate_text: str, corpus: Sequence[tuple[str, str]]) -> DuplicateMatch | None:
        """Return the closest duplicate if it exceeds the configured threshold.

        Spec guidance: Use TF-IDF over "title + summary" and merge when
        cosine similarity ≥ threshold within a 24h window. We intentionally
        avoid extra guards so that integration scenarios with paraphrased
        titles but highly similar summaries still merge as expected.
        """
        if not candidate_text.strip() or not corpus:
            return None

        texts = [candidate_text] + [document for _, document in corpus]
        # Character n-grams (within word boundaries) capture minor wording
        # variations while remaining lightweight for local use.
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 2), lowercase=True)
        matrix = vectorizer.fit_transform(texts)
        sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        if sims.size == 0:
            return None

        best_index = int(sims.argmax())
        best_score = float(sims[best_index])
        if best_score < self._threshold:
            return None

        # Lightweight lexical guard: ensure some word-level overlap exists to
        # avoid merging loosely related notes that only share short phrases.
        word_vec = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), lowercase=True, stop_words="english"
        )
        word_matrix = word_vec.fit_transform([candidate_text] + [doc for _, doc in corpus])
        word_sims = cosine_similarity(word_matrix[0:1], word_matrix[1:]).flatten()
        best_word = float(word_sims[best_index]) if word_sims.size else 0.0
        if best_word < 0.4:
            return None

        best_card_id = corpus[best_index][0]
        return DuplicateMatch(card_id=best_card_id, score=best_score)

    def highest_similarity_scores(self, candidate_text: str, corpus: Iterable[tuple[str, str]]) -> list[DuplicateMatch]:
        entries = list(corpus)
        if not entries:
            return []
        texts = [candidate_text] + [document for _, document in entries]
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 2), lowercase=True)
        matrix = vectorizer.fit_transform(texts)
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        matches = [DuplicateMatch(card_id=entries[i][0], score=float(value)) for i, value in enumerate(similarities)]
        return sorted(matches, key=lambda match: match.score, reverse=True)

    @property
    def threshold(self) -> float:
        return self._threshold
