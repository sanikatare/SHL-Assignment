"""Tests for the LLM/RAG layer (backend/llm.py) and its wiring into
memory.py / chat.py.

These tests never make a real network call: llm.is_available() is patched
where needed, and the anthropic client is mocked. This means the whole
suite (including these tests) runs identically whether or not
ANTHROPIC_API_KEY is set in the environment, and requires no network
access — consistent with the rest of the project's zero-network-dependency
test guarantee.

Run with: pytest tests/test_llm_rag.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch

import llm
from memory import ConversationMemory, ConversationState
from models import Recommendation


# ---------------------------------------------------------------------------
# No-op behavior when the LLM isn't configured
# ---------------------------------------------------------------------------

def test_is_available_false_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.is_available() is False


def test_semantic_extract_returns_empty_dict_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.semantic_extract_constraints("someone who can lead ambiguous projects") == {}


def test_rag_compose_reply_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rec = Recommendation(name="OPQ32", url="https://www.shl.com/opq32/", test_type="Personality")
    assert llm.rag_compose_reply("hiring a manager", [rec]) is None


def test_memory_build_state_unaffected_when_llm_unavailable(monkeypatch):
    """The full memory pipeline must behave identically to the pre-LLM
    version when no key is configured — this is the byte-for-byte backward
    compatibility guarantee."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from models import Message
    state = ConversationMemory().build_state([
        Message(role="user", content="need someone great at rallying a team through ambiguity")
    ])
    # No keyword hits for this phrasing, and no API key configured, so role
    # stays empty rather than silently calling out to a network service.
    assert state.role_hints == []


# ---------------------------------------------------------------------------
# Semantic extraction fallback (mocked client)
# ---------------------------------------------------------------------------

def _mock_text_response(payload: str):
    block = MagicMock()
    block.type = "text"
    block.text = payload
    resp = MagicMock()
    resp.content = [block]
    return resp


def test_semantic_extract_parses_json_and_filters_unknown_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_text_response(
        '{"role": ["manager"], "seniority": ["senior"], "not_a_real_key": ["x"]}'
    )
    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.semantic_extract_constraints("someone who can rally a team through ambiguity")
    assert result == {"role": ["manager"], "seniority": ["senior"]}


def test_semantic_extract_handles_malformed_json_gracefully(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_text_response("not json at all")
    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.semantic_extract_constraints("some text")
    assert result == {}


def test_semantic_extract_handles_api_exception_gracefully(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("network down")
    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.semantic_extract_constraints("some text")
    assert result == {}


def test_memory_merge_semantic_fallback_never_overrides_keyword_hit():
    state = ConversationState()
    state.role_hints = ["developer"]  # deterministic hit
    ConversationMemory._merge_semantic_fallback(state, {"role": ["manager"]})
    assert state.role_hints == ["developer"], "semantic fallback must not override a keyword hit"


def test_memory_merge_semantic_fallback_fills_empty_field():
    state = ConversationState()
    ConversationMemory._merge_semantic_fallback(state, {"role": ["manager"], "seniority": ["senior"]})
    assert state.role_hints == ["manager"]
    assert state.seniority == ["senior"]


# ---------------------------------------------------------------------------
# RAG reply composition + groundedness guardrail (mocked client)
# ---------------------------------------------------------------------------

def _rec(name="OPQ32", url="https://www.shl.com/opq32/"):
    return Recommendation(name=name, url=url, test_type="Personality")


def test_rag_compose_reply_accepts_grounded_output(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_text_response(
        "Based on your leadership focus, OPQ32 offers strong behavioral insight for this role."
    )
    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.rag_compose_reply("hiring a manager", [_rec()])
    assert result is not None
    assert "OPQ32" in result


def test_rag_compose_reply_rejects_output_with_foreign_url(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_text_response(
        "Check out this great test at https://not-in-catalog.example.com/test"
    )
    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.rag_compose_reply("hiring a manager", [_rec()])
    assert result is None, "guardrail must reject prose containing a URL absent from the retrieved set"


def test_rag_compose_reply_accepts_output_with_matching_url(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    rec = _rec(url="https://www.shl.com/opq32/")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_text_response(
        "See https://www.shl.com/opq32/ for OPQ32, a strong fit here."
    )
    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.rag_compose_reply("hiring a manager", [rec])
    assert result is not None


def test_rag_compose_reply_falls_back_on_exception(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("timeout")
    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.rag_compose_reply("hiring a manager", [_rec()])
    assert result is None


def test_rag_compose_reply_no_recommendations_returns_none(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "is_available", lambda: True)
    assert llm.rag_compose_reply("hiring a manager", []) is None
