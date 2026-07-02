"""Pure, dependency-free retrieval-quality metrics.

Every function takes plain lists/sets so it can be unit tested (and reused
by backend/evaluation.py) without needing a live catalog or retriever.
"""
from typing import Iterable, List, Sequence, Set


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def top_k_accuracy(predicted: Sequence[str], relevant: Set[str], k: int) -> float:
    """1.0 if any of the first k predictions is relevant, else 0.0."""
    top = {_norm(p) for p in predicted[:k]}
    rel = {_norm(r) for r in relevant}
    return 1.0 if top & rel else 0.0


def precision_at_k(predicted: Sequence[str], relevant: Set[str], k: int) -> float:
    if k == 0:
        return 0.0
    top = [_norm(p) for p in predicted[:k]]
    rel = {_norm(r) for r in relevant}
    hits = sum(1 for p in top if p in rel)
    return hits / k


def recall_at_k(predicted: Sequence[str], relevant: Set[str], k: int) -> float:
    rel = {_norm(r) for r in relevant}
    if not rel:
        return 0.0
    top = [_norm(p) for p in predicted[:k]]
    hits = sum(1 for r in rel if r in top)
    return hits / len(rel)


def mean_reciprocal_rank(predicted: Sequence[str], relevant: Set[str]) -> float:
    rel = {_norm(r) for r in relevant}
    for idx, p in enumerate(predicted, start=1):
        if _norm(p) in rel:
            return 1.0 / idx
    return 0.0


def groundedness(predicted_urls: Sequence[str], catalog_urls: Set[str]) -> float:
    """Fraction of returned URLs that actually exist in the catalog. A
    perfectly grounded (non-hallucinating) system scores 1.0."""
    if not predicted_urls:
        return 1.0
    hits = sum(1 for u in predicted_urls if u in catalog_urls)
    return hits / len(predicted_urls)


def recommendation_relevance(predicted: Sequence[str], relevant: Set[str], k: int = 5) -> float:
    """Fraction of the returned shortlist (up to k) that is relevant."""
    top = predicted[:k]
    if not top:
        return 0.0
    rel = {_norm(r) for r in relevant}
    hits = sum(1 for p in top if _norm(p) in rel)
    return hits / len(top)


def average(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
