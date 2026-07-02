#!/usr/bin/env bash
# Starts the React/Vite frontend on http://localhost:5173
set -e
cd "$(dirname "$0")/frontend"

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

npm run dev
