#!/bin/zsh
# Wait for the Gemini free-tier daily reset (midnight Pacific), then rebuild ledgers with the stronger grader.
# Extraction is cached, so each company costs one flash call.
cd "$(dirname "$0")/.."
target=$(python3 -c "import datetime as d; n=d.datetime.now(); t=n.replace(hour=12,minute=40,second=0); print(int((t-n).total_seconds()))")
[ "$target" -gt 0 ] && sleep "$target"
python3 pipeline/build_ledgers.py HAVELLS DIXON CYIENT SYNGENE HOMEFIRST DCMSHRIRAM KFINTECH SUNPHARMA ULTRACEMCO CROMPTON HDFCBANK LT MARUTI CGPOWER CEATLTD TCI SRF POLYCAB PIDILITIND
