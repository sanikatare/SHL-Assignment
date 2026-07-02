"""Conversation memory and refinement pipeline.

The API is stateless (the client re-sends the full message history on every
request), so "memory" here means: deterministically re-deriving conversation
state from that history rather than storing it server-side. Because the
retrieval pipeline is a pure function of accumulated constraints, replaying
the same accumulated text always reproduces the same base shortlist, which
lets refinement commands ("only remote", "show more", "compare the first
two") operate against a stable, reproducible "current shortlist" without
needing a session store.

Pipeline (see chat.py for orchestration):

    User Query -> Intent Detection -> Context Update -> Constraint
    Extraction -> Assessment Retrieval -> Filtering -> Ranking -> Response
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models import Message, MessageRole
import llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constraint extraction (broadened beyond utils.extract_constraints to cover
# every field called out in the assignment: role, seniority, skills, test
# type, duration, remote, adaptive, language, personality, cognitive).
# ---------------------------------------------------------------------------

SENIORITY_KEYWORDS = {
    "entry": ["entry level", "entry-level", "junior", "graduate", "intern", "0-2 years"],
    "mid": ["mid level", "mid-level", "intermediate", "3-5 years"],
    "senior": ["senior", "expert", "lead", "principal", "5+ years", "10+ years"],
}

COGNITIVE_KEYWORDS = [
    "cognitive", "numerical reasoning", "verbal reasoning", "inductive reasoning",
    "deductive reasoning", "aptitude", "problem solving ability", "g+", "logical reasoning",
]

PERSONALITY_KEYWORDS = [
    "personality", "behavioral", "behaviour", "opq", "traits", "temperament",
]

REMOTE_POSITIVE = ["remote", "online", "virtual", "unproctored", "work from home"]
REMOTE_NEGATIVE = ["in-person", "on-site", "proctored only", "not remote"]

ADAPTIVE_POSITIVE = ["adaptive", "irt", "computer adaptive"]

LANGUAGE_KEYWORDS = [
    "english", "spanish", "french", "german", "mandarin", "chinese", "japanese",
    "portuguese", "italian", "dutch", "arabic", "hindi",
]

TEST_TYPE_KEYWORDS = {
    "personality": ["personality", "behavioral", "behaviour"],
    "cognitive": ["cognitive", "numerical", "verbal", "inductive", "deductive", "aptitude"],
    "technical": ["technical", "coding", "programming", "knowledge & skills", "knowledge and skills"],
    "simulation": ["simulation", "simulations"],
    "assessment exercise": ["assessment exercise", "assessment center", "assessment centre"],
    "development & 360": ["360", "development report", "multi-rater"],
    "biodata & situational judgement": ["situational judgement", "biodata"],
    "competencies": ["competency", "competencies"],
}

DURATION_PATTERN = re.compile(
    r"(?:under|less than|shorter than|no more than|within|max(?:imum)?)\s*(\d{1,3})\s*(?:min|mins|minutes)",
    re.IGNORECASE,
)

SHOW_MORE_PATTERN = re.compile(r"\b(show more|more options|see more|additional options)\b", re.IGNORECASE)

EXCLUDE_PATTERN = re.compile(
    r"\bexclude\s+([a-z0-9 ,&/+-]+?)(?:\.|$| and | but )", re.IGNORECASE
)

ONLY_PATTERN = re.compile(
    r"\bonly\s+([a-z0-9 ,&/+-]+?)(?:\.|$| and | but )", re.IGNORECASE
)

COMPARE_INDEX_WORDS = {
    "first two": (0, 1), "first 2": (0, 1), "top two": (0, 1), "top 2": (0, 1),
    "first three": (0, 2), "first 3": (0, 2), "top three": (0, 2), "top 3": (0, 2),
    "1 and 2": (0, 1), "1 and 3": (0, 2), "2 and 3": (1, 2),
}


@dataclass
class ConversationState:
    """Structured, reproducible view of the conversation so far."""

    accumulated_text: str = ""
    latest_user_text: str = ""
    turn_count: int = 0
    user_turn_count: int = 0

    role_hints: List[str] = field(default_factory=list)
    seniority: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    wants_personality: bool = False
    wants_cognitive: bool = False
    remote_required: Optional[bool] = None
    duration_max_minutes: Optional[int] = None
    adaptive_required: Optional[bool] = None
    languages: List[str] = field(default_factory=list)
    only_test_types: List[str] = field(default_factory=list)
    exclude_test_types: List[str] = field(default_factory=list)

    # Latest-turn-only refinement signals (not accumulated across turns).
    wants_show_more: bool = False
    compare_indices: Optional[List[int]] = None

    def missing_fields(self) -> List[str]:
        """Return the subset of the assignment's required-info checklist that
        is still unknown, in priority order."""
        missing = []
        if not self.role_hints:
            missing.append("role")
        if not self.seniority:
            missing.append("seniority")
        if not self.skills and not self.wants_personality and not self.wants_cognitive:
            missing.append("skills")
        return missing

    def to_constraint_dict(self) -> Dict[str, List[str]]:
        """Flatten into the {constraint_type: [values]} shape the retriever
        already expects for keyword/constraint scoring."""
        out: Dict[str, List[str]] = {}
        if self.role_hints:
            out["role"] = self.role_hints
        if self.seniority:
            out["experience"] = self.seniority
        if self.skills:
            out["skills"] = self.skills
        if self.wants_personality:
            out["personality"] = ["personality"]
        if self.wants_cognitive:
            out["cognitive"] = ["cognitive"]
        if self.languages:
            out["language"] = self.languages
        return out


class ConversationMemory:
    """Derives a ConversationState from the raw message history."""

    def build_state(self, messages: List[Message]) -> ConversationState:
        user_msgs = [m.content for m in messages if m.role == MessageRole.USER]
        accumulated_text = " ".join(user_msgs)
        latest_user_text = user_msgs[-1] if user_msgs else ""

        state = ConversationState(
            accumulated_text=accumulated_text,
            latest_user_text=latest_user_text,
            turn_count=len(messages),
            user_turn_count=len(user_msgs),
        )

        self._extract_accumulated(state, accumulated_text)
        self._extract_latest_only(state, latest_user_text)

        # LLM semantic fallback: only invoked when the deterministic
        # keyword pass above still leaves required fields missing for a
        # non-trivial message (e.g. "someone who can rally a team through
        # ambiguity" has no keyword hit but clearly signals leadership).
        # This never overrides a keyword-derived value, only fills gaps,
        # and is a complete no-op when no API key is configured.
        if state.missing_fields() and len(accumulated_text.strip()) > 15 and llm.is_available():
            semantic = llm.semantic_extract_constraints(accumulated_text)
            self._merge_semantic_fallback(state, semantic)

        return state

    @staticmethod
    def _merge_semantic_fallback(state: ConversationState, semantic: Dict[str, List[str]]) -> None:
        """Fill only the fields the keyword pass left empty; never
        overwrite a deterministic hit with an LLM-derived one."""
        if not semantic:
            return
        if not state.role_hints and semantic.get("role"):
            state.role_hints.extend(semantic["role"])
        if not state.seniority and semantic.get("seniority"):
            state.seniority.extend(semantic["seniority"])
        if not state.skills and not state.wants_personality and not state.wants_cognitive:
            if semantic.get("skills"):
                state.skills.extend(semantic["skills"])
            if semantic.get("personality"):
                state.wants_personality = True
            if semantic.get("cognitive"):
                state.wants_cognitive = True

    # -- accumulated (sticky across the whole conversation) -----------------
    def _extract_accumulated(self, state: ConversationState, text: str) -> None:
        text_lower = text.lower()

        role_keywords = {
            "manager": ["manager", "team lead", "supervisor", "director"],
            "developer": ["developer", "engineer", "programmer", "coder"],
            "sales": ["sales", "account executive", "business development"],
            "support": ["support", "customer service", "helpdesk"],
            "analyst": ["analyst", "data analyst", "business analyst"],
            "hr": ["hr", "human resources", "recruiter"],
        }
        for role, kws in role_keywords.items():
            if any(kw in text_lower for kw in kws) and role not in state.role_hints:
                state.role_hints.append(role)

        for level, kws in SENIORITY_KEYWORDS.items():
            if any(kw in text_lower for kw in kws) and level not in state.seniority:
                state.seniority.append(level)

        skill_keywords = {
            "leadership": ["leadership", "leading", "team management"],
            "communication": ["communication", "interpersonal", "stakeholder"],
            "analytical": ["analytical", "problem solving", "critical thinking"],
            "technical": ["technical", "programming", "coding", "java", "python", "sql"],
        }
        for skill, kws in skill_keywords.items():
            if any(kw in text_lower for kw in kws) and skill not in state.skills:
                state.skills.append(skill)

        if any(kw in text_lower for kw in PERSONALITY_KEYWORDS):
            state.wants_personality = True
        if any(kw in text_lower for kw in COGNITIVE_KEYWORDS):
            state.wants_cognitive = True

        if any(kw in text_lower for kw in REMOTE_POSITIVE):
            state.remote_required = True
        if any(kw in text_lower for kw in REMOTE_NEGATIVE):
            state.remote_required = False

        if any(kw in text_lower for kw in ADAPTIVE_POSITIVE):
            state.adaptive_required = True

        for lang in LANGUAGE_KEYWORDS:
            if lang in text_lower and lang not in state.languages:
                state.languages.append(lang)

        m = DURATION_PATTERN.search(text_lower)
        if m:
            state.duration_max_minutes = int(m.group(1))

        for label, kws in TEST_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in kws):
                if "exclude " + label in text_lower or f"not {label}" in text_lower:
                    if label not in state.exclude_test_types:
                        state.exclude_test_types.append(label)

        for m in EXCLUDE_PATTERN.finditer(text_lower):
            fragment = m.group(1).strip()
            for label, kws in TEST_TYPE_KEYWORDS.items():
                if any(kw in fragment for kw in kws) and label not in state.exclude_test_types:
                    state.exclude_test_types.append(label)

    # -- latest turn only (refinement commands, not sticky) ------------------
    def _extract_latest_only(self, state: ConversationState, text: str) -> None:
        text_lower = text.lower()

        for m in ONLY_PATTERN.finditer(text_lower):
            fragment = m.group(1).strip()
            for label, kws in TEST_TYPE_KEYWORDS.items():
                if any(kw in fragment for kw in kws) and label not in state.only_test_types:
                    state.only_test_types.append(label)
            if "remote" in fragment:
                state.remote_required = True
            if "adaptive" in fragment:
                state.adaptive_required = True

        if SHOW_MORE_PATTERN.search(text_lower):
            state.wants_show_more = True

        for phrase, idx_pair in COMPARE_INDEX_WORDS.items():
            if phrase in text_lower:
                state.compare_indices = list(idx_pair)
                break
