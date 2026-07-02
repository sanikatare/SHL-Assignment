"""Core chat logic and conversation orchestration.

Refinement pipeline (per assignment spec):

    User Query -> Intent Detection -> Context Update -> Constraint
    Extraction -> Assessment Retrieval -> Filtering -> Ranking -> Response

Intent detection + context update + constraint extraction live in
memory.py (ConversationMemory). Retrieval + filtering + ranking live in
retriever.py/ranking.py. Comparison-table formatting lives in comparison.py.
This module is the thin orchestrator that wires those stages together.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from models import Message, ChatResponse, Recommendation, MessageRole, ComparisonTable
from parser import ConversationParser
from retriever import AssessmentRetriever
from memory import ConversationMemory, ConversationState
from comparison import build_comparison
from utils import load_catalog
import llm

logger = logging.getLogger(__name__)


CLARIFICATION_QUESTIONS = {
    "role": "What role are you hiring for?",
    "seniority": "Is this an entry-level, mid-level, or senior role?",
    "skills": "What type of skills are most important for this role? (e.g., leadership, technical, analytical, personality, or cognitive ability)",
    "industry": "What industry is this role in?",
    "team_size": "What is the size of the team?",
    "focus": "What is the primary focus area for assessment?",
}

OUT_OF_SCOPE_RESPONSE = (
    "I appreciate the question, but I'm specifically designed to help recommend "
    "SHL assessments. I can't provide general hiring advice, legal guidance, or "
    "answer questions unrelated to SHL assessments. "
    "How can I help you find the right SHL assessment for your needs?"
)

INSUFFICIENT_INFO_PREFIX = (
    "I'd like to help you find the best assessment. Let me ask a clarifying question:"
)

RECOMMENDATION_PREFIX = (
    "Based on your requirements, here are my recommendations:"
)

REFINED_RECOMMENDATION_PREFIX = (
    "Got it — here's the updated shortlist based on your latest input:"
)

MORE_RESULTS_PREFIX = (
    "Here are more options from the catalog:"
)

CLOSING_RESPONSE = (
    "Glad I could help you find the right SHL assessments. Good luck with your hiring!"
)

CLOSING_KEYWORDS = [
    "thanks", "thank you", "that's all", "that is all", "sounds good",
    "that works", "perfect", "no more questions", "that's everything",
    "goodbye", "bye", "great, thanks", "all set", "that's it",
]

# Once the conversation has used this many total turns (user + assistant),
# stop asking clarifying questions and commit to a best-effort shortlist so
# the harness's 8-turn cap is never exhausted without a recommendation.
MAX_TURNS_BEFORE_FORCED_RECOMMENDATION = 5

DEFAULT_TOP_K = 5


class ChatAgent:
    """Main chat agent for assessment recommendations (Stateless)."""

    def __init__(self):
        """Initialize chat agent."""
        self.parser = ConversationParser()
        self.memory = ConversationMemory()
        self.catalog = load_catalog()
        self.retriever = AssessmentRetriever(self.catalog) if self.catalog else None
        logger.info(f"Chat agent initialized with {len(self.catalog)} assessments")

    def chat(self, messages: List[Message]) -> ChatResponse:
        """Process chat message and generate response (Stateless)."""
        if not messages:
            return ChatResponse(
                reply="Hello! I'm here to help you find the right SHL assessment. What role or position are you looking to assess?",
                recommendations=[],
                end_of_conversation=False,
            )

        # Stage 1-3: Intent detection, context update, constraint extraction.
        parsed = self.parser.parse_conversation(messages)
        state = self.memory.build_state(messages)
        last_user_msg = self.parser.get_last_user_message(messages)

        logger.debug(f"Constraints: {parsed['constraints']} | Memory state: {state}")

        if parsed["is_out_of_scope"]:
            logger.info("Out of scope query detected")
            return ChatResponse(reply=OUT_OF_SCOPE_RESPONSE, recommendations=[], end_of_conversation=False)

        already_recommended, prior_shortlist_pages = self._recommendation_history(messages)

        if already_recommended and self._is_closing_message(last_user_msg):
            logger.info("Closing message detected after prior recommendation")
            return ChatResponse(reply=CLOSING_RESPONSE, recommendations=[], end_of_conversation=True)

        # Comparison intent: either named items ("compare Java 8 vs Core
        # Java") or an index-based reference into the current shortlist
        # ("compare the first two").
        comparison_response = self._maybe_handle_comparison(last_user_msg, state, already_recommended)
        if comparison_response is not None:
            return comparison_response

        # Stage: clarification. Skip once we're close to the harness's turn
        # cap so we always commit to a best-effort shortlist in time.
        turns_used = len(messages)
        missing = state.missing_fields()
        if missing and turns_used < MAX_TURNS_BEFORE_FORCED_RECOMMENDATION:
            logger.info(f"Clarification needed for: {missing}")
            return self._generate_clarification_response(missing)

        # Stage: retrieval + filtering + ranking.
        logger.info("Generating recommendations")
        offset = prior_shortlist_pages * DEFAULT_TOP_K if state.wants_show_more else 0
        prefix = MORE_RESULTS_PREFIX if state.wants_show_more else (
            REFINED_RECOMMENDATION_PREFIX if already_recommended else RECOMMENDATION_PREFIX
        )
        return self._generate_recommendations(state, offset=offset, reply_prefix=prefix)

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _recommendation_history(messages: List[Message]) -> Tuple[bool, int]:
        """Return (already_recommended, number_of_prior_shortlist_turns)."""
        count = 0
        for msg in messages:
            if msg.role == MessageRole.ASSISTANT and (
                RECOMMENDATION_PREFIX in msg.content
                or REFINED_RECOMMENDATION_PREFIX in msg.content
                or MORE_RESULTS_PREFIX in msg.content
            ):
                count += 1
        return count > 0, count

    @staticmethod
    def _is_closing_message(text: str) -> bool:
        """Detect a short closing/gratitude message from the user."""
        text_lower = text.strip().lower()
        if len(text_lower) > 60:
            return False
        return any(kw in text_lower for kw in CLOSING_KEYWORDS)

    # ------------------------------------------------------------------
    # Clarification
    # ------------------------------------------------------------------
    def _generate_clarification_response(self, missing_topics: List[str]) -> ChatResponse:
        """Generate clarification question."""
        topic = missing_topics[0] if missing_topics else "role"
        question = CLARIFICATION_QUESTIONS.get(topic, "Could you tell me more about your hiring needs?")
        reply = f"{INSUFFICIENT_INFO_PREFIX} {question}"
        return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False, needs_clarification=True)

    # ------------------------------------------------------------------
    # Recommendation generation
    # ------------------------------------------------------------------
    def _generate_recommendations(
        self,
        state: ConversationState,
        offset: int = 0,
        reply_prefix: str = RECOMMENDATION_PREFIX,
        top_k: int = DEFAULT_TOP_K,
    ) -> ChatResponse:
        """Generate assessment recommendations for the accumulated state."""
        if not self.retriever:
            logger.error("Retriever not initialized - catalog not loaded")
            return ChatResponse(
                reply="I don't have access to the assessment catalog. Please ensure catalog.json is generated by running the scraper.",
                recommendations=[],
                end_of_conversation=False,
            )

        constraints = state.to_constraint_dict()
        recommendations = self.retriever.retrieve(
            query=state.accumulated_text,
            constraints=constraints,
            top_k=top_k,
            offset=offset,
            remote_required=state.remote_required,
            duration_max_minutes=state.duration_max_minutes,
            adaptive_required=state.adaptive_required,
            only_test_types=state.only_test_types or None,
            exclude_test_types=state.exclude_test_types or None,
        )

        if not recommendations:
            logger.warning(f"No recommendations found for state: {state}")
            return ChatResponse(
                reply="I couldn't find matching assessments for your criteria. Could you relax a constraint (e.g. remote/duration) or provide more details?",
                recommendations=[],
                end_of_conversation=False,
            )

        logger.info(f"Returning {len(recommendations)} recommendations")
        reply = self._compose_reply(state, recommendations, reply_prefix)
        return ChatResponse(reply=reply, recommendations=recommendations, end_of_conversation=False)

    @staticmethod
    def _compose_reply(state: ConversationState, recommendations: List[Recommendation], fallback_prefix: str) -> str:
        """RAG step: ask the LLM to write grounded prose around the
        deterministically retrieved shortlist (retrieve -> augment prompt
        with retrieved context -> generate). Falls back to the fixed
        template string used throughout development/testing whenever the
        LLM isn't configured, fails, or the groundedness guardrail in
        llm.py rejects the output - so behavior with no API key configured
        is byte-for-byte identical to before this feature existed."""
        if not llm.is_available():
            return fallback_prefix
        composed = llm.rag_compose_reply(
            user_context=state.accumulated_text,
            recommendations=recommendations,
            intent="recommend",
        )
        return composed if composed else fallback_prefix

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------
    def _maybe_handle_comparison(
        self, last_user_msg: str, state: ConversationState, already_recommended: bool
    ) -> Optional[ChatResponse]:
        is_named_comparison = self.parser.is_comparison_request(last_user_msg)
        is_index_comparison = state.compare_indices is not None and already_recommended

        if not is_named_comparison and not is_index_comparison:
            return None

        if not self.retriever:
            return ChatResponse(reply="I don't have access to the assessment catalog.", recommendations=[], end_of_conversation=False)

        items = []
        if is_named_comparison:
            candidate_names = self.parser.extract_comparison_items(last_user_msg)
            items = self.retriever.resolve_items(candidate_names) if candidate_names else []

        if not items and is_index_comparison:
            # Re-derive the current shortlist deterministically from the
            # accumulated constraints (retrieval is a pure function of
            # state), then pick out the requested positions.
            base_query_state = state
            base_recs = self.retriever.retrieve(
                query=base_query_state.accumulated_text,
                constraints=base_query_state.to_constraint_dict(),
                top_k=max(DEFAULT_TOP_K, (max(state.compare_indices) + 1) if state.compare_indices else DEFAULT_TOP_K),
            )
            for idx in state.compare_indices or []:
                if 0 <= idx < len(base_recs):
                    match = self.retriever._match_single_assessment(base_recs[idx].name)
                    if match:
                        items.append(match)

        if not items:
            if is_named_comparison:
                return ChatResponse(
                    reply="I couldn't find assessments matching that comparison request in the SHL catalog. Please check the names and try again.",
                    recommendations=[],
                    end_of_conversation=False,
                )
            return None  # fall through to normal flow

        table = build_comparison(items)
        reply = "Here's a comparison of the requested assessments based on our catalog:\n\n" + table["markdown"]
        recs = [
            Recommendation(name=i.name, url=i.url, test_type=i.test_type or i.assessment_type)
            for i in items
        ]
        logger.info(f"Comparison complete for {len(items)} assessments")
        return ChatResponse(
            reply=reply,
            recommendations=recs,
            end_of_conversation=False,
            comparison=ComparisonTable(columns=table["columns"], rows=table["rows"], markdown=table["markdown"]),
        )
