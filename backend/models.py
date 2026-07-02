"""Pydantic models for API contracts."""
from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional
from enum import Enum


class MessageRole(str, Enum):
    """Enum for message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    """Message model for conversation history."""
    role: MessageRole
    content: str = Field(..., min_length=1, description="Message content")

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "I need an assessment for a sales role"
            }
        }


class Recommendation(BaseModel):
    """Individual assessment recommendation."""
    name: str = Field(..., description="Name of the assessment")
    url: str = Field(..., description="URL to the assessment")
    test_type: str = Field(..., description="Type of assessment")
    score: Optional[float] = Field(None, ge=0, le=1, description="Relevance score (0-1)")
    duration: Optional[str] = Field(None, description="Assessment duration, if known")
    remote_testing_support: Optional[bool] = Field(None, description="Whether remote/unproctored testing is supported")
    adaptive_irt_support: Optional[bool] = Field(None, description="Whether the assessment uses adaptive/IRT scoring")
    explanation: Optional[str] = Field(None, description="Grounded, catalog-only explanation of why this was recommended")
    matched_fields: Optional[List[str]] = Field(None, description="Catalog fields/terms that matched the request")

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Verify Ability - Numerical",
                "url": "https://www.shl.com/en/solutions/verify-ability-numerical/",
                "test_type": "Cognitive Ability Test",
                "score": 0.92,
                "duration": "18 minutes",
                "remote_testing_support": True,
                "adaptive_irt_support": False,
                "explanation": "Recommended because it matches numerical, cognitive based on the SHL catalog listing for Ability & Aptitude.",
                "matched_fields": ["numerical", "cognitive"]
            }
        }


class ChatRequest(BaseModel):
    """Chat API request model."""
    messages: List[Message] = Field(..., min_items=1, description="Conversation history")

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "What assessment do you recommend for a manager?"
                    }
                ]
            }
        }


class ComparisonRow(BaseModel):
    """One row of a comparison table, keyed by column name."""
    data: Dict[str, Any] = Field(..., description="Column name -> value for this assessment")


class ComparisonTable(BaseModel):
    """Structured + markdown comparison output. Additive/optional so it
    never breaks clients that only read `reply`/`recommendations`."""
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    markdown: str = Field(default="", description="Ready-to-render markdown table")


class ChatResponse(BaseModel):
    """Chat API response model - matches the original specification, with
    additive optional fields for comparison support."""
    reply: str = Field(..., description="Assistant's response")
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="List of recommended assessments (empty during clarification)"
    )
    end_of_conversation: bool = Field(
        default=False,
        description="Whether conversation should end"
    )
    comparison: Optional[ComparisonTable] = Field(
        default=None,
        description="Present only when this turn was a comparison request"
    )
    needs_clarification: bool = Field(
        default=False,
        description="True when `reply` is a clarifying question rather than a shortlist"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "reply": "Based on your requirements, here are my recommendations:",
                "recommendations": [
                    {
                        "name": "OPQ32",
                        "url": "https://www.shl.com/en/solutions/opq32/",
                        "test_type": "Personality"
                    }
                ],
                "end_of_conversation": False
            }
        }


class CompareRequest(BaseModel):
    """POST /compare request. Either `items` (explicit names/acronyms) or
    `messages` (derive comparison targets from conversation) must be given."""
    items: Optional[List[str]] = Field(
        default=None, description="Assessment names/acronyms to compare, e.g. ['OPQ', 'GSA']"
    )
    messages: Optional[List[Message]] = Field(
        default=None, description="Conversation history to extract a comparison request from"
    )

    class Config:
        json_schema_extra = {
            "example": {"items": ["Java 8", "Core Java"]}
        }


class EvaluateRequest(BaseModel):
    """POST /evaluate request. Empty body runs the full bundled test set."""
    top_k: int = Field(default=10, ge=1, le=20, description="How many results to retrieve per query")


class EvaluateResponse(BaseModel):
    """POST /evaluate response — aggregate retrieval-quality report."""
    num_queries: int
    top_1_accuracy: float
    top_3_accuracy: float
    precision_at_3: float
    recall_at_3: float
    mrr: float
    average_retrieval_score: float
    average_response_time_ms: float
    groundedness: float
    recommendation_relevance: float
    per_query: List[Dict[str, Any]] = Field(default_factory=list)
