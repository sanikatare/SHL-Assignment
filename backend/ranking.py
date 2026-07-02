"""Scoring and ranking primitives for assessment retrieval.

Separated out of retriever.py so each scoring signal (keyword/TF-IDF, fuzzy,
skill overlap, role similarity, assessment-type weighting) is independently
testable and the retriever is left to orchestrate + combine them.
"""
import logging
from typing import Dict, List

import numpy as np
from rapidfuzz import fuzz

from models_catalog import AssessmentItem

logger = logging.getLogger(__name__)


def normalize(scores: np.ndarray) -> np.ndarray:
    """Min-free normalization to [0, 1] by dividing by the max (keeps 0s at 0)."""
    max_score = np.max(scores) if scores.size and np.max(scores) > 0 else 1
    return scores / max_score


def fuzzy_score(query: str, items: List[AssessmentItem]) -> np.ndarray:
    """RapidFuzz token-set similarity across name, keywords, and category."""
    scores = np.zeros(len(items))
    query_lower = query.lower()
    for idx, item in enumerate(items):
        name_score = fuzz.token_set_ratio(query_lower, item.name.lower())
        keywords_score = fuzz.token_set_ratio(query_lower, " ".join(item.keywords).lower())
        category_score = fuzz.token_set_ratio(query_lower, item.category.lower())
        scores[idx] = (name_score + keywords_score + category_score) / 300.0
    return scores


def skill_overlap_score(constraints: Dict[str, List[str]], items: List[AssessmentItem]) -> np.ndarray:
    """Fraction of requested skill/role terms that literally appear in an
    item's skills_measured + keywords."""
    scores = np.zeros(len(items))
    requested_terms: List[str] = []
    for key in ("skills", "role", "cognitive", "personality"):
        requested_terms.extend(constraints.get(key, []))
    if not requested_terms:
        return scores

    for idx, item in enumerate(items):
        item_terms = set(t.lower() for t in (item.skills_measured + item.keywords))
        item_terms.add(item.category.lower())
        hits = 0
        for term in requested_terms:
            term_lower = term.lower()
            if any(term_lower in t or t in term_lower for t in item_terms):
                hits += 1
        scores[idx] = hits / len(requested_terms)
    return scores


def role_similarity_score(constraints: Dict[str, List[str]], items: List[AssessmentItem]) -> np.ndarray:
    """How well an item's name/description aligns with the requested role(s)."""
    roles = constraints.get("role", [])
    scores = np.zeros(len(items))
    if not roles:
        return scores

    role_synonyms = {
        "developer": ["developer", "programming", "coding", "java", "python", ".net", "software"],
        "manager": ["manager", "leadership", "management", "supervisor"],
        "sales": ["sales", "account", "business development"],
        "support": ["support", "customer service", "helpdesk"],
        "analyst": ["analyst", "data", "business analysis"],
        "hr": ["hr", "human resources", "recruit"],
    }
    for idx, item in enumerate(items):
        item_text = item.get_all_text()
        hits = 0
        for role in roles:
            for term in role_synonyms.get(role, [role]):
                if term in item_text:
                    hits += 1
                    break
        scores[idx] = hits / len(roles)
    return scores


def assessment_type_weight(constraints: Dict[str, List[str]], items: List[AssessmentItem]) -> np.ndarray:
    """Small bonus for items whose test-type matches an explicitly requested
    category (e.g. the user asked for a 'personality' or 'cognitive' test)."""
    scores = np.zeros(len(items))
    wants_personality = bool(constraints.get("personality"))
    wants_cognitive = bool(constraints.get("cognitive"))
    if not (wants_personality or wants_cognitive):
        return scores

    for idx, item in enumerate(items):
        code = (item.test_type or "").upper()
        if wants_personality and "P" in code:
            scores[idx] += 1
        if wants_cognitive and "A" in code:
            scores[idx] += 1
    return scores


def combine(
    tfidf_scores: np.ndarray,
    constraint_scores: np.ndarray,
    fuzzy_scores: np.ndarray,
    skill_scores: np.ndarray,
    role_scores: np.ndarray,
    type_scores: np.ndarray,
    weights: Dict[str, float],
) -> np.ndarray:
    """Weighted sum of every normalized signal."""
    return (
        weights.get("tfidf", 0.35) * normalize(tfidf_scores)
        + weights.get("constraint", 0.2) * normalize(constraint_scores)
        + weights.get("fuzzy", 0.15) * normalize(fuzzy_scores)
        + weights.get("skill_overlap", 0.15) * normalize(skill_scores)
        + weights.get("role_similarity", 0.1) * normalize(role_scores)
        + weights.get("type_weight", 0.05) * normalize(type_scores)
    )
