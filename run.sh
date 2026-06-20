#!/usr/bin/env bash
# Media Constellations — start the local engine.
# Runs on your Max plan via the claude CLI; no API key needed.
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "First run: creating virtualenv…"
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

# Local: no OPENAI_API_KEY -> uses claude -p on your Max plan.
# Set OPENAI_API_KEY (and OPENAI_MODEL) to test the hosted OpenAI engine locally.
# CONSTELLATION_MODEL=haiku  -> faster / lighter on Max usage (default: sonnet)
# PORT=5050                  -> change the port if 5050 is taken
exec ./.venv/bin/python server.py
