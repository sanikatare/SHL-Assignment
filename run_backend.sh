#!/usr/bin/env bash
# Starts the FastAPI backend on http://localhost:8000
set -e
cd "$(dirname "$0")/backend"

if [ ! -f "catalog.json" ]; then
  if [ -f "sample_catalog.json" ]; then
    echo "No catalog.json found — copying sample_catalog.json so the API has data to serve."
    echo "For the real SHL catalog, run 'python run_scraper.py' instead (requires internet access)."
    cp sample_catalog.json catalog.json
  else
    echo "WARNING: no catalog.json found. Run 'python run_scraper.py' first."
  fi
fi

python3 app.py
