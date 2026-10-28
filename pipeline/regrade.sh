#!/bin/zsh
# Wait for the Gemini free-tier daily reset (midnight Pacific, ~12:30 IST), then rebuild ledgers with the stronger grader.
# Extraction is cached, so each company costs one or two flash calls; the free tier allows 20 a day.
# Usage: zsh pipeline/regrade.sh [SYMBOL ...]   (default: the companies the last run graded with flash-lite)
cd "$(dirname "$0")/.."
syms=(${@:-CEATLTD MARUTI PIDILITIND POLYCAB SRF SYNGENE TCI ULTRACEMCO})
target=$(python3 -c "import datetime as d; n=d.datetime.now(); t=n.replace(hour=12,minute=40,second=0); t += d.timedelta(days=(t<=n)); print(int((t-n).total_seconds()))")
echo "sleeping ${target}s, then: ${syms[*]}"
sleep "$target"
FINN_PATIENT=1 python3 pipeline/build_ledgers.py ${syms[@]}
