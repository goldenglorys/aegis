from __future__ import annotations

import re

import numpy as np
from sentence_transformers import SentenceTransformer

_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_SIMILARITY_THRESHOLD = 0.72
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_EMBEDDING_MODEL)
    return _model


def _chunk_sentences(text: str) -> list[str]:
    sentences = _SENTENCE_SPLIT.split(text)
    return [s.strip() for s in sentences if len(s.split()) > 3]


def analyze_gaps(
    sub_queries: list[dict],
    content: str,
    threshold: float = _SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    For each sub-query, compute max cosine similarity against sentence chunks
    from content. Returns enriched sub-query dicts with 'covered' and
    'similarity_score' fields.
    """
    model = _get_model()
    sentences = _chunk_sentences(content)

    if not sentences:
        return [
            {**sq, "covered": False, "similarity_score": 0.0}
            for sq in sub_queries
        ]

    content_vecs = model.encode(sentences, normalize_embeddings=True, show_progress_bar=False)
    query_texts = [sq["query"] for sq in sub_queries]
    query_vecs = model.encode(query_texts, normalize_embeddings=True, show_progress_bar=False)

    # Dot product of L2-normalised vectors equals cosine similarity.
    sim_matrix: np.ndarray = np.dot(query_vecs, content_vecs.T)

    enriched = []
    for i, sq in enumerate(sub_queries):
        max_sim = float(sim_matrix[i].max())
        enriched.append({
            **sq,
            "covered": max_sim >= threshold,
            "similarity_score": round(max_sim, 4),
        })

    return enriched


def build_gap_summary(enriched_queries: list[dict]) -> dict:
    """Compute aggregate coverage statistics across sub-query types."""
    covered_types: set[str] = set()
    missing_types: set[str] = set()
    covered_count = 0

    for sq in enriched_queries:
        if sq["covered"]:
            covered_count += 1
            covered_types.add(sq["type"])
        else:
            missing_types.add(sq["type"])

    missing_types -= covered_types
    total = len(enriched_queries)

    return {
        "covered": covered_count,
        "total": total,
        "coverage_percent": round((covered_count / total) * 100, 1) if total else 0.0,
        "covered_types": sorted(covered_types),
        "missing_types": sorted(missing_types),
    }
