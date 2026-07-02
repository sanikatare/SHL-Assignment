# SHL - Assessment Recommendation Agent 

A conversational agent that recommends SHL assessments based on hiring
requirements. This repo contains three pieces:

```
SHL-Full-Project/
├── backend/        FastAPI service
│   ├── app.py            API routes: /health, /chat, /compare, /evaluate
│   ├── chat.py            Thin orchestrator: wires memory → retriever → comparison
│   ├── memory.py          Conversation state: constraint extraction + refinement intents
│   ├── parser.py          Scope / injection detection, comparison-item text extraction
│   ├── retriever.py        Retrieval + filtering + ranking orchestration (TF-IDF index owner)
│   ├── ranking.py          Scoring primitives: keyword/TF-IDF, fuzzy, skill overlap, role sim, type weight
│   ├── comparison.py       Markdown + structured comparison table builder (catalog-only, no hallucination)
│   ├── evaluation.py       Evaluation engine shared by POST /evaluate and evaluation/evaluate.py
│   ├── models.py / models_catalog.py   Pydantic API contracts + catalog dataclass
│   ├── utils.py            Catalog I/O, logging, base constraint extraction
│   └── tests/               pytest behavior suite
├── evaluation/      Standalone evaluation harness (no FastAPI dependency)
│   ├── evaluate.py         CLI entry point
│   ├── metrics.py           Canonical, dependency-free metric functions
│   └── test_queries.json    Ground-truth query set derived from catalog.json
├── frontend/        React + Vite + Tailwind chat UI
├── run_backend.sh
└── run_frontend.sh
```

The backend has been reviewed and fixed against `SHL_AI_Intern_Assignment.pdf`
— see [`docs/APPROACH.md`](docs/APPROACH.md) for the original writeup, and
`backend/tests/` for the behavior test suite (`pytest`). **`catalog.json`
currently ships with 57 verified real SHL entries as a demo seed — run
`python run_scraper.py` with real internet access before submitting to pull
the full catalog.**

## What's new in this upgrade

All of the below is **additive**: `GET /health` and `POST /chat` keep their
original request/response shape (new fields are optional), and every
pre-existing test in `test_chat_behaviors.py` still passes unmodified.

1. **Conversational clarifying questions** — `memory.ConversationState.missing_fields()`
   checks role / seniority / skills (personality or cognitive-ability phrasing
   also satisfies the skills slot) before any retrieval happens, and `chat.py`
   asks one concise question at a time. A turn-cap safety valve
   (`MAX_TURNS_BEFORE_FORCED_RECOMMENDATION`) guarantees a best-effort
   shortlist is produced well before the assignment's 8-turn cap.
2. **Conversation memory** — the API is intentionally stateless (the client
   re-sends full history each turn), so "memory" means deterministically
   re-deriving state from that history in `memory.py` rather than a session
   store. Because retrieval is a pure function of accumulated constraints,
   replaying the same history always reproduces the same base shortlist —
   which is what makes index-based refinements ("compare the first two")
   possible without server-side session state.
3. **Refinement pipeline** — `chat.py` now follows: *Query → Intent Detection
   → Context Update → Constraint Extraction → Assessment Retrieval →
   Filtering → Ranking → Response*, matching the assignment diagram.
   Supported refinements: `"only remote assessments"`, `"shorter than 30
   minutes"`, `"only personality tests"`, `"exclude numerical reasoning"`,
   `"show more"`, `"only adaptive tests"`.
4. **Assessment comparison** — `"compare the first two"`, `"Java 8 vs Core
   Java"`, `"which is better?"` all resolve to a markdown + structured
   comparison table (`comparison.py`) with columns: Assessment Name, Type,
   Skills Measured, Duration, Remote Testing, Adaptive, Use Case, Strengths,
   Limitations, Recommendation — every cell derived from catalog fields only,
   never free-generated.
5. **Grounded responses** — each `Recommendation` now carries an
   `explanation` (template-built from catalog fields) and `matched_fields`
   (the literal request terms found in that assessment's catalog text), so
   nothing is asserted that isn't backed by the catalog.
6. **Retrieval improvements** — `ranking.py` combines keyword/TF-IDF
   similarity, RapidFuzz fuzzy matching, skill-overlap scoring, role
   similarity, and assessment-type weighting into one weighted score
   (weights configurable via `.env`, see `.env.example`).
7. **Evaluation module** — `evaluation/` (Top-1/Top-3 accuracy, Precision@3,
   Recall@3, MRR, average retrieval score, average response time,
   groundedness, recommendation relevance) — see "Evaluation" below.
8. **New endpoints** — `POST /compare`, `POST /evaluate` (existing endpoints
   unchanged).
9. **Frontend** — comparison tables now render as real tables (not raw
   markdown), a "Clarifying question" badge appears on clarification turns,
   loading/error states are unchanged from before.
10. **LLM / RAG layer** (`backend/llm.py`, optional, off by default) —
    retrieval stays deterministic and catalog-only; when `ANTHROPIC_API_KEY`
    is set, the already-retrieved shortlist is handed to an LLM to compose
    natural prose around it (classic RAG: retrieve -> augment prompt with
    retrieved context -> generate), with a groundedness guardrail that
    rejects any output referencing a name/URL outside the retrieved set,
    plus a semantic fallback for constraint extraction when keyword
    matching finds nothing. With no key configured, every code path that
    touches this module short-circuits and behavior is identical to before
    it existed — see `docs/APPROACH.md` §2 for the full design rationale
    and `backend/tests/test_llm_rag.py` for the (mocked, no-network) tests.

## Evaluator's checklist

| Requirement | Status | Where |
|---|---|---|
| LLM and/or RAG usage | Present (optional, off by default) | `backend/llm.py`, wired into `chat.py`/`memory.py` |
| Clarifying questions | Present | `memory.ConversationState.missing_fields()`, `chat._generate_clarification_response` |
| Context-aware follow-up refinement | Present | `memory.py` (stateless re-derivation from full history), `chat.py` refinement branch |
| Assessment comparison using catalog evidence | Present | `comparison.py`, `retriever.resolve_items` (name/acronym/fuzzy match) |
| Grounded recommendations | Present | `Recommendation.explanation`/`matched_fields`, RAG guardrail in `llm._is_grounded` |
| Retrieval quality | Present, bounded by seed catalog size | `ranking.py` hybrid TF-IDF/fuzzy/skill/role/type scoring |
| Evaluation methodology | Present | `evaluation/` (CLI) + `backend/evaluation.py` + `POST /evaluate`; Top-1/3, P@3, R@3, MRR, groundedness, relevance |
| API quality | Present | FastAPI + Pydantic schemas, typed responses, `/docs` |
| Error handling | Present | try/except + `HTTPException` per route, global exception handler, graceful catalog-missing states |
| Documentation | Present | this file, `docs/APPROACH.md`, `frontend/README.md`, module docstrings |

**Open item:** `catalog.json` ships with a 57-item verified seed, not the full
~377-item SHL catalog — run `python run_scraper.py` with real internet access
before submitting (see "Quick start" below and `docs/APPROACH.md` §6).

## Quick start (two terminals)

### Terminal 1 — backend

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
```

The recommender needs `catalog.json` (a list of SHL assessments) to serve
recommendations. You have two options:

**Option A — real SHL data (requires internet access to shl.com):**
```bash
python run_scraper.py
python app.py
```

**Option B — quick smoke test with a small bundled sample catalog:**
```bash
cp sample_catalog.json catalog.json
python app.py
```

Either way, the API comes up at `http://localhost:8000`. Verify with:
```bash
curl http://localhost:8000/health
```

Or, from the project root, `./run_backend.sh` does the "copy sample catalog
if none exists, then start" dance automatically.

### Terminal 2 — frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. It talks to `http://localhost:8000` by
default (override via `frontend/.env`, see `frontend/.env.example`).

Or, from the project root: `./run_frontend.sh`.

## What's in the frontend

- Chat interface (user/assistant bubbles, auto-scroll, typewriter-style
  reply animation)
- Recommendation cards rendered from the `recommendations` array in the
  `/chat` response — test-type badge, relevance meter when `score` is
  present, link out to the SHL assessment page, responsive grid → stacked
  on mobile
- **Comparison tables** — rendered from the new `comparison` field as an
  actual HTML table (`ComparisonTable.jsx`), not raw markdown text
- **Clarifying-question badge** — shown on assistant turns where
  `needs_clarification` is true
- Fixed input bar (Enter to send, Shift+Enter for newline, disabled while
  loading)
- Loading / empty / error states, with retry on failure
- Suggested prompts, clear-conversation button, dark mode toggle, chat
  history persisted to localStorage, copy-message button, toast
  notifications, live backend connection indicator

Full details, design rationale, and project structure are in
[`frontend/README.md`](frontend/README.md).

## API contract

`GET /health` and `POST /chat`'s original fields are unchanged; `comparison`
and `needs_clarification` are new, optional, additive fields.

```
GET  /health
  → { "status": "ok" }

POST /chat
  Request:  { "messages": [{ "role": "user" | "assistant", "content": string }] }
  Response: {
    "reply": string,
    "recommendations": [{
      "name": string, "url": string, "test_type": string,
      "score"?: number, "duration"?: string,
      "remote_testing_support"?: boolean, "adaptive_irt_support"?: boolean,
      "explanation"?: string, "matched_fields"?: string[]
    }],
    "end_of_conversation": boolean,
    "comparison"?: { "columns": string[], "rows": object[], "markdown": string },
    "needs_clarification": boolean
  }

POST /compare
  Request:  { "items"?: string[], "messages"?: Message[] }   // provide one of the two
  Response: { "columns": string[], "rows": object[], "markdown": string }

POST /evaluate
  Request:  { "top_k"?: number }   // defaults to 10
  Response: {
    "num_queries": number, "top_1_accuracy": number, "top_3_accuracy": number,
    "precision_at_3": number, "recall_at_3": number, "mrr": number,
    "average_retrieval_score": number, "average_response_time_ms": number,
    "groundedness": number, "recommendation_relevance": number,
    "per_query": object[]
  }
```

## Evaluation

Two ways to run it:

**Standalone CLI (no server needed):**
```bash
cd evaluation
python evaluate.py                 # prints a report, uses backend/catalog.json
python evaluate.py --top-k 5 --json report.json
```

**Via the running API:**
```bash
curl -X POST http://localhost:8000/evaluate -H "Content-Type: application/json" -d '{"top_k": 10}'
```

`evaluation/test_queries.json` contains 17 hand-authored queries with
`relevant_names` grounded directly in the bundled `catalog.json` contents
(e.g. a "Java developer" query's relevant set is the catalog's actual Java
assessments) — replace/extend this file once the full ~377-item catalog is
scraped for a more representative evaluation.

## Tests

```bash
cd backend
pip install pytest httpx --break-system-packages
pytest tests/ -v
```

`tests/test_chat_behaviors.py` is the original hard-eval suite (schema
compliance, catalog-only URLs, scope refusal, prompt-injection resistance,
turn-cap safety, clarify/recommend/refine/compare). `tests/test_new_features.py`
covers the memory/refinement/comparison/evaluation modules. `tests/test_llm_rag.py`
covers the LLM/RAG layer — entirely mocked (no network, no API key needed) —
including the no-key no-op path, the semantic-extraction merge rules, and the
groundedness guardrail that rejects ungrounded generated replies.

## Deployment

`backend/Dockerfile`, `backend/Procfile`, and `backend/render.yaml` are
included for Render/Fly/Railway/Heroku-style hosts. All read `$PORT` from
the environment. Health check path is `/health` (allow up to 2 minutes for
cold starts, per the assignment).

## Verified working end-to-end

Both pieces were installed and run together during development of this
frontend: `pip install -r backend/requirements.txt`, a smoke-test catalog,
`python app.py`, then `curl -X POST /chat` returned real recommendation
payloads that the new frontend renders directly — confirming the contract
match. `npm install && npm run build` in `frontend/` also completes cleanly.
