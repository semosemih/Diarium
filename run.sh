#!/usr/bin/env bash
# Ayna Launcher Script
cd "$(dirname "$0")"

# Activate Python virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the app launcher
python3 app.py
