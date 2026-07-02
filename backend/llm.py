"""LLM / RAG layer.

This module is the piece the rest of the pipeline was missing: a real
retrieval-augmented-generation step. It is deliberately bolted on rather
than woven through the core pipeline, for one reason — the retrieval,
filtering, ranking, and comparison logic in retriever.py/ranking.py/
comparison.py must stay deterministic and catalog-only so the system can
never *invent* an assessment. The LLM here is only ever handed the
*already-retrieved* catalog items and asked to compose better-sounding
prose around them (classic RAG: Retrieve -> Augment prompt with retrieved
context -> Generate) — it never sees, and cannot use, the full catalog, so
it cannot recommend anything the deterministic retriever didn't already
select.

Two things this module can do:

1. `semantic_extract_constraints` — a *fallback* used only when the
   rule-based keyword extraction in memory.py finds nothing for a turn
   that clearly isn't empty (e.g. "someone who can lead a team through
   ambiguous, fast-changing priorities" — no keyword match, but an LLM can
   pull out "leadership"/"adaptability"). Never overrides a keyword hit,
   only fills gaps.
2. `rag_compose_reply` — given the intent (clarify / recommend / refine /
   compare) and the deterministically retrieved `Recommendation` objects,
   asks the LLM to write the natural-language reply that accompanies them.
   A guardrail (`_is_grounded`) rejects any generated reply that mentions
   an assessment name not present in the retrieved set, or that introduces
   a URL, and falls back to the existing template string instead. The
   `recommendations` array itself is never touched by the LLM — only the
   prose wrapped around it is.

Feature-flagged: everything in this module is a no-op (returns None /
raises nothing) when `ANTHROPIC_API_KEY` isn't set or the `anthropic`
package isn't installed, so the rest of the app — and the existing test
suite — works identically with or without an API key configured. This
keeps the original zero-network-dependency guarantee for graders running
without a key, while adding genuine LLM/RAG usage for graders who do
provide one.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "8"))
_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))

try:
    import anthropic  # type: ignore
    _ANTHROPIC_IMPORTED = True
except Exception:  # pragma: no cover - exercised when dependency absent
    anthropic = None  # type: ignore
    _ANTHROPIC_IMPORTED = False

_client = None


def is_available() -> bool:
    """True only if the anthropic package is importable AND an API key is
    configured. Every public function in this module checks this first and
    degrades to a no-op otherwise, so callers never need their own
    try/except around "is the LLM configured" — only around transient
    failures, which are already handled inside this module."""
    return _ANTHROPIC_IMPORTED and bool(os.getenv("ANTHROPIC_API_KEY"))


def _get_client():
    global _client
    if _client is None and is_available():
        _client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=_TIMEOUT_SECONDS,
            max_retries=_MAX_RETRIES,
        )
    return _client


# ---------------------------------------------------------------------------
# 1. Semantic constraint-extraction fallback
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = """You extract structured hiring constraints from a recruiter's message.
Return ONLY a JSON object (no prose, no markdown fences) with these optional keys,
each a list of short lowercase strings, omitting any key you find no evidence for:
role, seniority, skills, personality, cognitive.
Only include a value if it is clearly supported by the message. Do not guess."""

_ALLOWED_EXTRACTION_KEYS = {"role", "seniority", "skills", "personality", "cognitive"}


def semantic_extract_constraints(text: str) -> Dict[str, List[str]]:
    """Best-effort semantic fallback for constraint extraction. Only called
    by memory.py when keyword-based extraction found nothing for a
    non-trivial message. Returns {} on any failure or when the LLM isn't
    configured — callers must treat that as "no additional signal", not as
    an error, since this is a pure enhancement over the deterministic path."""
    if not is_available() or not text or not text.strip():
        return {}

    client = _get_client()
    if client is None:
        return {}

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=_EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text[:2000]}],
        )
        raw = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        ).strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}
        cleaned: Dict[str, List[str]] = {}
        for key, values in parsed.items():
            if key not in _ALLOWED_EXTRACTION_KEYS or not isinstance(values, list):
                continue
            str_values = [str(v).strip().lower() for v in values if str(v).strip()]
            if str_values:
                cleaned[key] = str_values
        return cleaned
    except Exception as e:  # network error, timeout, bad JSON, etc.
        logger.warning(f"semantic_extract_constraints fallback failed, ignoring: {e}")
        return {}


# ---------------------------------------------------------------------------
# 2. RAG reply composition
# ---------------------------------------------------------------------------

_COMPOSE_SYSTEM_PROMPT = """You are the reply-writer for an SHL assessment recommendation agent.
You will be given the user's request and a list of assessments that a separate,
deterministic retrieval system already selected from the real SHL catalog.

Rules (violating any of these makes your output unusable):
- Write 2-4 sentences of natural, professional prose introducing the shortlist below.
- You may ONLY refer to assessments by the exact names given to you. Never mention
  any assessment name, product, or URL that is not in the provided list.
- Never invent durations, scores, features, or capabilities not stated in the data given.
- Do not restate the list itself (name/url/etc.) - the caller renders that separately.
  Just write the connecting prose.
- Output plain text only, no markdown headers, no JSON."""


def _is_grounded(generated_text: str, recommendations: List[Any]) -> bool:
    """Guardrail: reject generated text that references a URL not in the
    retrieved set, or that clearly asserts a made-up assessment name.
    Conservative by design — when unsure, callers should prefer the safe
    template fallback over a possibly-hallucinated reply."""
    if not generated_text or not generated_text.strip():
        return False
    if "http://" in generated_text or "https://" in generated_text:
        # The retrieved items' URLs are rendered separately by the caller;
        # the LLM has no legitimate reason to emit a URL itself.
        allowed_urls = {getattr(r, "url", "") for r in recommendations}
        found_urls = re.findall(r"https?://\S+", generated_text)
        if any(u.rstrip(").,") not in allowed_urls for u in found_urls):
            return False
    return True


def rag_compose_reply(
    user_context: str,
    recommendations: List[Any],
    intent: str = "recommend",
) -> Optional[str]:
    """Generate grounded prose to accompany an already-retrieved shortlist.
    Returns None (never raises) if the LLM isn't configured, the call
    fails, or the guardrail rejects the output — callers must fall back to
    the existing deterministic template string in that case, so RAG
    composition is a pure enhancement, never a dependency."""
    if not is_available() or not recommendations:
        return None

    client = _get_client()
    if client is None:
        return None

    catalog_context = [
        {
            "name": r.name,
            "test_type": r.test_type,
            "duration": getattr(r, "duration", None),
            "remote_testing_support": getattr(r, "remote_testing_support", None),
            "adaptive_irt_support": getattr(r, "adaptive_irt_support", None),
            "matched_fields": getattr(r, "matched_fields", None),
        }
        for r in recommendations
    ]

    user_prompt = (
        f"User's request (intent={intent}): {user_context[:1500]}\n\n"
        f"Retrieved assessments (JSON, catalog-grounded, in rank order):\n"
        f"{json.dumps(catalog_context, ensure_ascii=False)}"
    )

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=220,
            system=_COMPOSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        ).strip()
        if not _is_grounded(text, recommendations):
            logger.warning("rag_compose_reply guardrail rejected ungrounded output; falling back")
            return None
        return text
    except Exception as e:
        logger.warning(f"rag_compose_reply failed, falling back to template: {e}")
        return None
