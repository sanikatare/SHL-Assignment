# SHL Assessment Recommendation Agent

A conversational AI application that recommends the most relevant SHL assessments based on hiring requirements. The system supports multi-turn conversations, clarification questions, assessment comparison, hybrid retrieval, and grounded recommendations while ensuring responses remain based on the SHL assessment catalog.

---

## Overview

This project was built as part of the SHL AI Internship Assignment.

The application enables recruiters and hiring managers to describe hiring requirements in natural language and receive the most appropriate SHL assessments with explanations. The system maintains conversational context, asks clarification questions when necessary, supports follow-up refinements, and compares assessments using only verified catalog data.

---

## Features

### Conversational Recommendation Engine

- Natural language hiring requirement understanding
- Multi-turn conversation support
- Context-aware follow-up questions
- Conversation memory without server-side sessions
- Constraint extraction from previous messages

### Intelligent Retrieval

- Hybrid ranking pipeline
- TF-IDF similarity
- Keyword matching
- RapidFuzz fuzzy matching
- Skill overlap scoring
- Role similarity scoring
- Assessment type weighting

### Assessment Comparison

Compare assessments using catalog-backed information including:

- Assessment Type
- Skills Measured
- Duration
- Remote Testing Support
- Adaptive Testing
- Use Cases
- Strengths
- Limitations

No comparison content is hallucinated—all information is derived from the SHL catalog.

### Grounded Recommendations

Each recommendation includes:

- Explanation
- Matching criteria
- Assessment metadata
- Official SHL URL

### Optional LLM + RAG Support

When an Anthropic API key is configured, the system uses Retrieval-Augmented Generation to produce more natural responses while enforcing groundedness checks to prevent hallucinations.

Without an API key, the application continues to operate using deterministic retrieval only.

### Evaluation Framework

Built-in evaluation metrics include:

- Top-1 Accuracy
- Top-3 Accuracy
- Precision@3
- Recall@3
- Mean Reciprocal Rank (MRR)
- Average Retrieval Score
- Average Response Time
- Groundedness
- Recommendation Relevance

---

# Project Structure

```
SHL-Full-Project/
│
├── backend/
│   ├── app.py
│   ├── chat.py
│   ├── memory.py
│   ├── retriever.py
│   ├── ranking.py
│   ├── comparison.py
│   ├── evaluation.py
│   ├── parser.py
│   ├── models.py
│   ├── utils.py
│   └── tests/
│
├── evaluation/
│   ├── evaluate.py
│   ├── metrics.py
│   └── test_queries.json
│
├── frontend/
│
├── run_backend.sh
├── run_frontend.sh
└── README.md
```

---

# Technology Stack

## Backend

- FastAPI
- Python
- Pydantic
- TF-IDF (Scikit-learn)
- RapidFuzz
- Anthropic Claude (Optional)
- Pytest

## Frontend

- React
- Vite
- Tailwind CSS

---

# Installation

## Clone the Repository

```bash
git clone https://github.com/yourusername/shl-assessment-agent.git

cd shl-assessment-agent
```

---

# Backend Setup

```bash
cd backend

pip install -r requirements.txt
```

Generate the SHL catalog:

```bash
python run_scraper.py
```

Or use the bundled sample catalog:

```bash
cp sample_catalog.json catalog.json
```

Start the backend:

```bash
python app.py
```

Backend runs at:

```
http://localhost:8000
```

---

# Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---


# Key Capabilities

- Conversational recommendation engine
- Multi-turn context awareness
- Clarification question generation
- Hybrid retrieval pipeline
- Assessment comparison
- Grounded recommendations
- Optional Retrieval-Augmented Generation (RAG)
- Evaluation framework
- Production-ready FastAPI backend
- Modern React frontend


