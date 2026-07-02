"""Parse and extract information from user messages."""
import logging
from typing import List, Dict
from models import Message
from utils import extract_constraints

logger = logging.getLogger(__name__)


class ConversationParser:
    """Parse conversation history to extract context and intent."""
    
    CLARIFICATION_KEYWORDS = {
        "role": ["role", "position", "job title", "hiring for", "job"],
        "seniority": ["seniority", "experience", "level", "years", "junior", "senior"],
        "skills": ["skills", "competencies", "abilities", "capabilities", "competency"],
        "industry": ["industry", "sector", "vertical", "company type"],
        "team_size": ["team size", "team", "department"],
        "focus": ["focus", "priority", "important", "emphasis"],
    }
    
    # NOTE: keywords here must not overlap with legitimate assessment-shopping
    # vocabulary. "programming", "algorithm", "technical", "coding" etc. are
    # deliberately excluded because they are core catalog terms (e.g. "Java
    # Programming Test") and previously caused false-positive refusals on
    # perfectly in-scope hiring queries.
    OUT_OF_SCOPE_KEYWORDS = [
        "legal advice", "is it legal", "lawsuit", "sue my", "employment law",
        "how much should i pay", "what salary should", "negotiate salary",
        "write my job posting", "write a job description",
        "ignore previous", "ignore all previous", "disregard previous",
        "forget your instructions", "previous instructions", "system prompt",
        "you are now", "jailbreak", "act as if", "reveal your prompt",
        "what is your prompt", "developer mode",
    ]

    # Generic hiring-advice / non-SHL topics that are only out of scope when
    # they are NOT accompanied by any assessment-shopping signal.
    SOFT_OUT_OF_SCOPE_KEYWORDS = [
        "interview questions to ask", "how do i fire", "termination letter",
        "visa sponsorship", "employee onboarding", "performance review template",
    ]
    
    def __init__(self):
        """Initialize parser."""
        self.conversation_history = []
    
    def parse_conversation(self, messages: List[Message]) -> Dict[str, any]:
        """Parse full conversation to extract context."""
        self.conversation_history = messages
        
        all_text = " ".join([msg.content for msg in messages if msg.role == "user"])
        
        return {
            "all_text": all_text,
            "constraints": extract_constraints(all_text),
            "message_count": len(messages),
            "user_message_count": len([m for m in messages if m.role == "user"]),
            "is_out_of_scope": self._check_out_of_scope(all_text),
            "needs_clarification": self._check_needs_clarification(all_text),
            "clarification_topics": self._get_clarification_topics(all_text),
        }
    
    def get_last_user_message(self, messages: List[Message]) -> str:
        """Get the most recent user message."""
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content
        return ""
    
    def _check_out_of_scope(self, text: str) -> bool:
        """Check if query is out of scope.

        Hard keywords (prompt injection, legal/salary advice, etc.) always
        trigger a refusal. Soft keywords only trigger a refusal if there is
        no accompanying hiring/assessment signal in the same message, so a
        message like "what assessment for a role, also draft interview
        questions" still gets a useful assessment answer rather than a
        blanket refusal.
        """
        text_lower = text.lower()

        for keyword in self.OUT_OF_SCOPE_KEYWORDS:
            if keyword in text_lower:
                return True

        constraints = extract_constraints(text)
        has_assessment_signal = bool(constraints)

        if not has_assessment_signal:
            for keyword in self.SOFT_OUT_OF_SCOPE_KEYWORDS:
                if keyword in text_lower:
                    return True

        return False
    
    def _check_needs_clarification(self, text: str) -> bool:
        """Check if more information is needed."""
        constraints = extract_constraints(text)
        required_info = ["role", "experience"]
        
        for info in required_info:
            if not constraints.get(info):
                return True
        
        return False
    
    def _get_clarification_topics(self, text: str) -> List[str]:
        """Identify which topics need clarification."""
        topics = []
        constraints = extract_constraints(text)
        
        if not constraints.get("role"):
            topics.append("role")
        
        if not constraints.get("experience"):
            topics.append("seniority")
        
        if not constraints.get("skills") and \
           not constraints.get("leadership") and \
           not constraints.get("technical") and \
           not constraints.get("personality"):
            topics.append("skills")
        
        return topics
    
    def extract_comparison_items(self, text: str) -> List[str]:
        """Extract candidate assessment names/acronyms from a comparison request.

        Rather than relying on a fixed, easily-stale keyword list, this
        strips known comparison phrasing ("compare", "difference between",
        "vs", "versus", "and") and returns the remaining phrase fragments.
        The retriever is responsible for fuzzy/acronym-matching these
        fragments against the real catalog (see AssessmentRetriever.compare).
        """
        import re

        cleaned = text.strip()
        cleaned = re.sub(
            r"\b(what'?s|what is|what are)\s+the\s+(difference|differences)\s+between\b",
            " ", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r"\bthe\s+(difference|differences)\s+between\b", " ", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r"\b(difference|differences)\s+between\b", " ", cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"\bcompare\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[?.!]", " ", cleaned)

        # Split on connective words that typically separate the two items.
        parts = re.split(r"\s+(?:vs\.?|versus|and|,|&)\s+", cleaned, flags=re.IGNORECASE)

        items = []
        for part in parts:
            candidate = part.strip(" -–—")
            if candidate and len(candidate) > 1:
                items.append(candidate)

        return items
    
    def is_comparison_request(self, text: str) -> bool:
        """Check if message is a comparison request."""
        comparison_keywords = ["compare", "difference", "similar", "vs", "versus"]
        text_lower = text.lower()
        
        return any(kw in text_lower for kw in comparison_keywords)
