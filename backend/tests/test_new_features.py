"""Tests for the new refinement pipeline: memory (context/refinement
extraction), comparison tables, and the evaluation engine.

Run with: pytest tests/test_new_features.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chat import ChatAgent
from models import Message
from memory import ConversationMemory


@pytest.fixture(scope="module")
def agent():
    a = ChatAgent()
    assert a.catalog, "catalog.json must be present and non-empty to run these tests"
    return a


def _ask(agent, turns):
    return agent.chat([Message(role=r, content=c) for r, c in turns])


# ---------------------------------------------------------------------------
# Memory / constraint extraction
# ---------------------------------------------------------------------------

def test_memory_extracts_role_and_seniority():
    state = ConversationMemory().build_state([
        Message(role="user", content="Hiring a senior Java developer with strong technical skills")
    ])
    assert "developer" in state.role_hints
    assert "senior" in state.seniority
    assert not state.missing_fields()


def test_memory_detects_remote_and_duration_refinement():
    state = ConversationMemory().build_state([
        Message(role="user", content="Hiring a Java developer"),
        Message(role="assistant", content="Based on your requirements, here are my recommendations:"),
        Message(role="user", content="Only remote assessments, shorter than 30 minutes"),
    ])
    assert state.remote_required is True
    assert state.duration_max_minutes == 30


def test_memory_detects_show_more_and_compare_indices():
    state = ConversationMemory().build_state([Message(role="user", content="show more")])
    assert state.wants_show_more is True

    state2 = ConversationMemory().build_state([Message(role="user", content="compare the first two")])
    assert state2.compare_indices == [0, 1]


# ---------------------------------------------------------------------------
# Refinement pipeline via ChatAgent
# ---------------------------------------------------------------------------

def test_refinement_filters_to_remote_only(agent):
    turns = [("user", "Hiring a mid-level Java developer, technical skills")]
    first = _ask(agent, turns)
    assert first.recommendations

    refine_turns = turns + [("assistant", first.reply), ("user", "Only remote assessments")]
    refined = _ask(agent, refine_turns)
    assert all(r.remote_testing_support in (True, None) for r in refined.recommendations)


def test_show_more_returns_a_different_page(agent):
    turns = [("user", "Hiring a mid-level Java developer, technical skills")]
    first = _ask(agent, turns)
    assert first.recommendations

    more_turns = turns + [("assistant", first.reply), ("user", "show more")]
    more = _ask(agent, more_turns)
    first_urls = {r.url for r in first.recommendations}
    more_urls = {r.url for r in more.recommendations}
    assert more_urls, "show more should return additional results"
    assert first_urls != more_urls


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def test_named_comparison_returns_structured_table(agent):
    r = _ask(agent, [("user", "Compare Java 8 vs Core Java")])
    assert r.comparison is not None
    assert "Assessment Name" in r.comparison.columns
    assert len(r.comparison.rows) >= 1


def test_index_based_comparison_after_shortlist(agent):
    turns = [("user", "Hiring a mid-level Java developer, technical skills")]
    first = _ask(agent, turns)
    assert first.recommendations

    compare_turns = turns + [("assistant", first.reply), ("user", "compare the first two")]
    compared = _ask(agent, compare_turns)
    assert compared.comparison is not None
    assert len(compared.comparison.rows) == 2


def test_comparison_never_invents_urls(agent):
    catalog_urls = {item["url"] for item in agent.catalog}
    r = _ask(agent, [("user", "What is the difference between OPQ and GSA?")])
    assert r.comparison is not None
    for row in r.comparison.rows:
        assert row["url"] in catalog_urls


# ---------------------------------------------------------------------------
# Evaluation engine
# ---------------------------------------------------------------------------

def test_evaluation_report_has_expected_shape():
    from evaluation import run_evaluation

    report = run_evaluation(top_k=5)
    assert report["num_queries"] > 0
    for key in (
        "top_1_accuracy", "top_3_accuracy", "precision_at_3", "recall_at_3",
        "mrr", "average_retrieval_score", "average_response_time_ms",
        "groundedness", "recommendation_relevance",
    ):
        assert key in report
        assert 0.0 <= report[key] or report[key] >= 0.0

    assert report["groundedness"] == 1.0, "retrieval must never return non-catalog URLs"
