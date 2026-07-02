"""FastAPI application for SHL Assessment Recommendation Agent."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import (
    ChatRequest, ChatResponse, Message, MessageRole,
    CompareRequest, ComparisonTable, EvaluateRequest, EvaluateResponse,
)
from chat import ChatAgent
from comparison import build_comparison
from evaluation import run_evaluation
from utils import setup_logging, get_env_or_default
import os
from dotenv import load_dotenv

load_dotenv()

logger = setup_logging()
logger.info("Initializing SHL Assessment Recommendation Agent")

chat_agent: ChatAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global chat_agent
    
    logger.info("Starting application")
    try:
        chat_agent = ChatAgent()
        if not chat_agent.catalog:
            logger.warning("Catalog not loaded. Run: python run_scraper.py")
        else:
            logger.info(f"Loaded catalog with {len(chat_agent.catalog)} assessments")
    except Exception as e:
        logger.error(f"Failed to initialize chat agent: {e}", exc_info=True)
        chat_agent = None
    
    yield
    
    logger.info("Shutting down application")


app = FastAPI(
    title="SHL Assessment Recommendation Agent",
    description="Conversational agent for recommending SHL assessments based on hiring requirements",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint for assessment recommendations."""
    try:
        if not chat_agent:
            logger.error("Chat agent not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat agent not initialized. Run scraper to generate catalog."
            )
        
        if not chat_agent.catalog:
            logger.error("Catalog not loaded")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Assessment catalog not available. Run: python run_scraper.py"
            )
        
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one message is required"
            )
        
        for msg in request.messages:
            if msg.role not in [MessageRole.USER, MessageRole.ASSISTANT]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {msg.role}. Must be 'user' or 'assistant'"
                )
        
        logger.debug(f"Processing chat with {len(request.messages)} messages")
        
        response = chat_agent.chat(request.messages)
        
        logger.debug(f"Response: {len(response.recommendations)} recommendations, end_of_conversation={response.end_of_conversation}")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request"
        )


@app.post("/compare", response_model=ComparisonTable)
async def compare(request: CompareRequest) -> ComparisonTable:
    """Compare specific assessments by name/acronym, or derive the
    comparison target from a conversation's last message."""
    try:
        if not chat_agent or not chat_agent.retriever:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Assessment catalog not available. Run: python run_scraper.py"
            )

        names: list = []
        if request.items:
            names = request.items
        elif request.messages:
            last_user_text = chat_agent.parser.get_last_user_message(request.messages)
            names = chat_agent.parser.extract_comparison_items(last_user_text)

        if not names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either `items` (list of assessment names) or `messages` to compare."
            )

        items = chat_agent.retriever.resolve_items(names)
        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No catalog assessments matched: {', '.join(names)}"
            )

        table = build_comparison(items)
        return ComparisonTable(columns=table["columns"], rows=table["rows"], markdown=table["markdown"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compare processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your comparison request"
        )


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(request: EvaluateRequest = EvaluateRequest()) -> EvaluateResponse:
    """Run the bundled evaluation query set against the live retriever and
    return aggregate retrieval-quality metrics (see evaluation/ folder)."""
    try:
        if not chat_agent or not chat_agent.retriever:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Assessment catalog not available. Run: python run_scraper.py"
            )

        report = run_evaluation(retriever=chat_agent.retriever, top_k=request.top_k)
        if "error" in report:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=report["error"])

        return EvaluateResponse(**report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evaluate processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred running the evaluation"
        )


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "message": "Welcome to SHL Assessment Recommendation Agent",
        "version": "1.0.0",
        "status": "ok" if chat_agent and chat_agent.catalog else "catalog_not_loaded",
        "catalog_size": len(chat_agent.catalog) if chat_agent else 0,
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "docs": "/docs"
        }
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    
    host = get_env_or_default("FASTAPI_HOST", "0.0.0.0")
    port = int(get_env_or_default("FASTAPI_PORT", get_env_or_default("PORT", 8000)))
    reload = get_env_or_default("FASTAPI_RELOAD", "true").lower() == "true"
    
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload
    )
