#!/bin/sh
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
if [ ! -f .env ]; then cp .env.example .env; echo 'Created .env. Add your private OpenAI API key when ready.'; fi
python3 -m pip install -r requirements.txt
printf '\nOpen http://localhost:3000 in your browser. Press Ctrl+C to stop.\n\n'
PORT=3000 python3 server.py
