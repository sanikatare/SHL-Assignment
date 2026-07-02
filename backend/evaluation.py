"""Evaluation engine for the retrieval pipeline.

Metrics themselves live in evaluation/metrics.py (kept dependency-free and
outside backend/ so they're reusable from a plain CLI). This module wires
those metric functions up to the real retriever + catalog and produces a
report consumable by both `POST /evaluate` and `evaluation/evaluate.py`.
"""
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from retriever import AssessmentRetriever
from utils import load_catalog

logger = logging.getLogger(__name__)

# evaluation/metrics.py is a sibling of backend/, not a package inside it,
# so it's reached via an explicit path insertion rather than a relative
# import. This keeps metric functions in exactly one place (no duplicated
# scoring code between the API-facing engine and the standalone CLI).
_EVAL_DIR = Path(__file__).resolve().parent / "evaluation"
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

from metrics import * (  # noqa: E402
    top_k_accuracy,
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
    groundedness,
    recommendation_relevance,
    average,
)

DEFAULT_TEST_QUERIES_PATH = _EVAL_DIR / "test_queries.json"


def load_test_queries(path: Optional[str] = None) -> List[Dict[str, Any]]:
    query_path = Path(path) if path else DEFAULT_TEST_QUERIES_PATH
    if not query_path.exists():
        logger.warning(f"Test query file not found at {query_path}")
        return []
    with open(query_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_evaluation(
    retriever: Optional[AssessmentRetriever] = None,
    test_queries: Optional[List[Dict[str, Any]]] = None,
    top_k: int = 10,
) -> Dict[str, Any]:
    """Run every test query through the retriever and compute aggregate
    retrieval-quality metrics. Returns a JSON-serializable report dict."""
    if retriever is None:
        catalog_path = str(Path(__file__).resolve().parent / "catalog.json")
        catalog = load_catalog(catalog_path)
        retriever = AssessmentRetriever(catalog) if catalog else None

    if retriever is None:
        return {"error": "Catalog/retriever not available. Run the scraper first.", "queries": []}

    queries = test_queries if test_queries is not None else load_test_queries()
    catalog_urls = {item.url for item in retriever.assessment_items}

    per_query_results = []
    top1_scores, top3_scores, precisions, recalls, mrrs = [], [], [], [], []
    retrieval_scores, response_times, groundedness_scores, relevance_scores = [], [], [], []

    for tq in queries:
        query_text = tq["query"]
        relevant = set(tq.get("relevant_names", []))

        start = time.perf_counter()
        recs = retriever.retrieve(query=query_text, top_k=top_k)
        elapsed = time.perf_counter() - start

        predicted_names = [r.name for r in recs]
        predicted_urls = [r.url for r in recs]

        top1 = top_k_accuracy(predicted_names, relevant, k=1)
        top3 = top_k_accuracy(predicted_names, relevant, k=3)
        p3 = precision_at_k(predicted_names, relevant, k=3)
        r3 = recall_at_k(predicted_names, relevant, k=3)
        mrr = mean_reciprocal_rank(predicted_names, relevant)
        grounded = groundedness(predicted_urls, catalog_urls)
        relevance = recommendation_relevance(predicted_names, relevant, k=5)
        top_score = float(recs[0].score) if recs and recs[0].score is not None else 0.0

        top1_scores.append(top1)
        top3_scores.append(top3)
        precisions.append(p3)
        recalls.append(r3)
        mrrs.append(mrr)
        retrieval_scores.append(top_score)
        response_times.append(elapsed)
        groundedness_scores.append(grounded)
        relevance_scores.append(relevance)

        per_query_results.append({
            "id": tq.get("id"),
            "query": query_text,
            "relevant_names": list(relevant),
            "predicted_top5": predicted_names[:5],
            "top1_hit": bool(top1),
            "top3_hit": bool(top3),
            "precision_at_3": round(p3, 3),
            "recall_at_3": round(r3, 3),
            "mrr": round(mrr, 3),
            "groundedness": round(grounded, 3),
            "response_time_ms": round(elapsed * 1000, 2),
        })

    report = {
        "num_queries": len(queries),
        "top_1_accuracy": round(average(top1_scores), 4),
        "top_3_accuracy": round(average(top3_scores), 4),
        "precision_at_3": round(average(precisions), 4),
        "recall_at_3": round(average(recalls), 4),
        "mrr": round(average(mrrs), 4),
        "average_retrieval_score": round(average(retrieval_scores), 4),
        "average_response_time_ms": round(average(response_times) * 1000, 3),
        "groundedness": round(average(groundedness_scores), 4),
        "recommendation_relevance": round(average(relevance_scores), 4),
        "per_query": per_query_results,
    }
    return report


def format_report(report: Dict[str, Any]) -> str:
    """Render the report dict as a human-readable text block (used by both
    the CLI and, optionally, logged by the API)."""
    if "error" in report:
        return f"Evaluation error: {report['error']}"

    lines = [
        "=" * 60,
        "SHL Assessment Retrieval — Evaluation Report",
        "=" * 60,
        f"Queries evaluated:         {report['num_queries']}",
        f"Top-1 Accuracy:            {report['top_1_accuracy']:.2%}",
        f"Top-3 Accuracy:            {report['top_3_accuracy']:.2%}",
        f"Precision@3:               {report['precision_at_3']:.2%}",
        f"Recall@3:                  {report['recall_at_3']:.2%}",
        f"MRR:                       {report['mrr']:.4f}",
        f"Average Retrieval Score:   {report['average_retrieval_score']:.4f}",
        f"Average Response Time:     {report['average_response_time_ms']:.2f} ms",
        f"Groundedness:              {report['groundedness']:.2%}",
        f"Recommendation Relevance:  {report['recommendation_relevance']:.2%}",
        "=" * 60,
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    result = run_evaluation()
    print(format_report(result))
