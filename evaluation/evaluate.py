#!/usr/bin/env python3
"""Standalone evaluation CLI.

Runs test_queries.json against the live retriever/catalog and prints a
detailed evaluation report. Reuses backend/evaluation.py (the same engine
behind `POST /evaluate`) so there is exactly one implementation of the
evaluation logic — this script is just an entry point.

Usage:
    cd evaluation
    python evaluate.py
    python evaluate.py --top-k 5
    python evaluate.py --json report.json
"""
import argparse
import json
import sys
from pathlib import Path

# backend/ is a sibling directory; add it to sys.path so we can import the
# retriever, catalog loader, and the shared evaluation engine without
# duplicating any of that logic here.
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND_DIR))

from evaluation import run_evaluation, format_report, load_test_queries  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the SHL assessment retrieval pipeline.")
    parser.add_argument("--top-k", type=int, default=10, help="Results to retrieve per query (default: 10)")
    parser.add_argument("--queries", type=str, default=None, help="Path to a custom test_queries.json")
    parser.add_argument("--json", type=str, default=None, help="Optional path to also write the full JSON report")
    args = parser.parse_args()

    test_queries = load_test_queries(args.queries)
    if not test_queries:
        print("No test queries found — check evaluation/test_queries.json", file=sys.stderr)
        sys.exit(1)

    report = run_evaluation(test_queries=test_queries, top_k=args.top_k)
    print(format_report(report))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nFull JSON report written to {args.json}")


if __name__ == "__main__":
    main()
