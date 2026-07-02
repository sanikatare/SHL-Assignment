"""Assessment retrieval, filtering, and ranking orchestration.

Pipeline stage: Assessment Retrieval -> Filtering -> Ranking (see memory.py
for the stages before this one). Scoring primitives live in ranking.py;
this module is responsible for building the TF-IDF index, calling those
primitives, applying hard filters (remote/duration/adaptive/type/language),
and shaping results into API-facing Recommendation objects.
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

import ranking
from models import Recommendation
from models_catalog import AssessmentItem
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AssessmentRetriever:
    """Retrieve, filter, and rank assessments for a query + constraint set."""

    def __init__(self, assessments: List[Dict[str, Any]]):
        self.assessments = assessments
        self.assessment_items = [AssessmentItem(**item) for item in assessments]
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9,
        )
        self.weights = {
            "tfidf": float(os.getenv("TFIDF_WEIGHT", 0.35)),
            "constraint": float(os.getenv("CONSTRAINT_WEIGHT", 0.2)),
            "fuzzy": float(os.getenv("FUZZY_WEIGHT", 0.15)),
            "skill_overlap": float(os.getenv("SKILL_OVERLAP_WEIGHT", 0.15)),
            "role_similarity": float(os.getenv("ROLE_SIMILARITY_WEIGHT", 0.1)),
            "type_weight": float(os.getenv("TYPE_WEIGHT", 0.05)),
        }
        self._build_index()

    def _build_index(self) -> None:
        if not self.assessment_items:
            logger.warning("No assessments to index")
            self.tfidf_matrix = None
            return
        texts = [item.get_all_text() for item in self.assessment_items]
        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)
            logger.info(f"Built TF-IDF index for {len(self.assessment_items)} assessments")
        except Exception as e:
            logger.error(f"Failed to build TF-IDF index: {e}")
            self.tfidf_matrix = None

    # ------------------------------------------------------------------
    # Retrieval + Ranking
    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        constraints: Dict[str, List[str]] = None,
        top_k: int = 10,
        offset: int = 0,
        remote_required: Optional[bool] = None,
        duration_max_minutes: Optional[int] = None,
        adaptive_required: Optional[bool] = None,
        only_test_types: Optional[List[str]] = None,
        exclude_test_types: Optional[List[str]] = None,
    ) -> List[Recommendation]:
        """Run the full retrieve -> filter -> rank pipeline and return the
        top_k Recommendation objects, skipping the first `offset` (used for
        'show more')."""
        constraints = constraints or {}

        if not self.assessment_items or self.tfidf_matrix is None:
            logger.warning("No assessments or TF-IDF matrix available")
            return []

        # Retrieval: score every candidate on every signal.
        tfidf_scores = self._tfidf_score(query)
        constraint_scores = self._constraint_score(constraints)
        fuzzy_scores = ranking.fuzzy_score(query, self.assessment_items)
        skill_scores = ranking.skill_overlap_score(constraints, self.assessment_items)
        role_scores = ranking.role_similarity_score(constraints, self.assessment_items)
        type_scores = ranking.assessment_type_weight(constraints, self.assessment_items)

        combined_scores = ranking.combine(
            tfidf_scores, constraint_scores, fuzzy_scores, skill_scores, role_scores, type_scores, self.weights
        )

        # Filtering: drop items that violate hard constraints before ranking cuts to top_k.
        candidates = list(zip(self.assessment_items, combined_scores))
        candidates = self._apply_filters(
            candidates,
            remote_required=remote_required,
            duration_max_minutes=duration_max_minutes,
            adaptive_required=adaptive_required,
            only_test_types=only_test_types,
            exclude_test_types=exclude_test_types,
        )

        # Ranking: sort by combined score, paginate.
        ranked = sorted(candidates, key=lambda x: x[1], reverse=True)
        page = ranked[offset: offset + top_k]

        results = []
        for item, score in page:
            results.append(Recommendation(
                name=item.name,
                url=item.url,
                test_type=item.test_type or item.assessment_type,
                score=round(float(min(max(score, 0.0), 1.0)), 4),
                duration=item.duration or None,
                remote_testing_support=item.remote_testing_support,
                adaptive_irt_support=item.adaptive_irt_support,
                explanation=self._build_explanation(item, constraints),
                matched_fields=self._matched_fields(item, constraints),
            ))
        logger.info(f"Retrieved {len(results)} assessments (offset={offset}) for query: {query}")
        return results

    def _apply_filters(
        self,
        candidates,
        remote_required: Optional[bool],
        duration_max_minutes: Optional[int],
        adaptive_required: Optional[bool],
        only_test_types: Optional[List[str]],
        exclude_test_types: Optional[List[str]],
    ):
        def duration_minutes(item: AssessmentItem) -> Optional[int]:
            digits = "".join(ch for ch in (item.duration or "") if ch.isdigit())
            return int(digits) if digits else None

        def matches_type_label(item: AssessmentItem, label: str) -> bool:
            label_lower = label.lower()
            haystack = f"{item.category} {item.assessment_type}".lower()
            return label_lower in haystack

        filtered = []
        for item, score in candidates:
            if remote_required is True and not item.remote_testing_support:
                continue
            if adaptive_required is True and not item.adaptive_irt_support:
                continue
            if duration_max_minutes is not None:
                d = duration_minutes(item)
                # Only exclude items with a *known* duration that exceeds the
                # cap; items with no published duration are kept rather than
                # silently dropped (sparse catalog data shouldn't zero out
                # results).
                if d is not None and d > duration_max_minutes:
                    continue
            if only_test_types:
                if not any(matches_type_label(item, t) for t in only_test_types):
                    continue
            if exclude_test_types:
                if any(matches_type_label(item, t) for t in exclude_test_types):
                    continue
            filtered.append((item, score))
        return filtered

    def _build_explanation(self, item: AssessmentItem, constraints: Dict[str, List[str]]) -> str:
        """Grounded, template-based explanation citing only catalog fields —
        never free-generated, so it can't invent capabilities."""
        matched = self._matched_fields(item, constraints)
        if matched:
            return f"Recommended because it matches {', '.join(matched)} based on the SHL catalog listing for {item.category}."
        return f"Recommended based on relevance to your query within the {item.category} category."

    def _matched_fields(self, item: AssessmentItem, constraints: Dict[str, List[str]]) -> List[str]:
        matched = []
        item_text = item.get_all_text()
        for key in ("role", "experience", "skills", "personality", "cognitive", "language"):
            for value in constraints.get(key, []):
                if value.lower() in item_text and value not in matched:
                    matched.append(value)
        return matched

    def _tfidf_score(self, query: str) -> np.ndarray:
        try:
            query_vec = self.vectorizer.transform([query.lower()])
            return cosine_similarity(query_vec, self.tfidf_matrix)[0]
        except Exception as e:
            logger.warning(f"TF-IDF scoring failed: {e}")
            return np.zeros(len(self.assessment_items))

    def _constraint_score(self, constraints: Dict[str, List[str]]) -> np.ndarray:
        scores = np.zeros(len(self.assessment_items))
        if not constraints:
            return scores
        for idx, item in enumerate(self.assessment_items):
            item_text = item.get_all_text()
            score = 0
            for _, values in constraints.items():
                for value in values:
                    if value.lower() in item_text:
                        score += 1
            scores[idx] = score
        return scores

    # ------------------------------------------------------------------
    # Comparison matching (name/acronym/fuzzy resolution)
    # ------------------------------------------------------------------
    def resolve_items(self, names: List[str]) -> List[AssessmentItem]:
        """Resolve free-text fragments to catalog items, preserving order
        and dropping unmatched fragments."""
        resolved = []
        for name in names:
            match = self._match_single_assessment(name)
            if match and match not in resolved:
                resolved.append(match)
        return resolved

    def compare(self, assessment_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Legacy dict-shaped comparison (kept for backwards compatibility;
        prefer resolve_items() + comparison.build_comparison() for the
        markdown/table-producing path)."""
        comparison = {}
        for name in assessment_names:
            match = self._match_single_assessment(name)
            if match:
                comparison[match.name] = match.to_dict()
        return comparison

    def _match_single_assessment(self, query: str):
        query_norm = query.strip().lower()
        if not query_norm:
            return None

        for item in self.assessment_items:
            item_name_lower = item.name.lower()
            if item_name_lower == query_norm or item_name_lower.startswith(query_norm):
                return item

        if query_norm.isalpha() and len(query_norm) <= 6:
            for item in self.assessment_items:
                words = [w for w in item.name.replace("-", " ").split() if w.isalpha()]
                acronym = "".join(w[0] for w in words).lower()
                if acronym == query_norm or acronym.startswith(query_norm):
                    return item
                first_token = item.name.split()[0].lower() if item.name.split() else ""
                if first_token.startswith(query_norm):
                    return item

        best_item, best_score = None, 0.0
        for item in self.assessment_items:
            score = fuzz.token_set_ratio(query_norm, item.name.lower())
            if score > best_score:
                best_item, best_score = item, score
        if best_score >= 70:
            return best_item

        return None
