"""POST {symbol} -> financial tables, snapshot and the list of transcripts. No model calls."""
import re
from _common import make_handler
from finn import research

def run(body):
    sym = re.sub(r"[^A-Z0-9&-]", "", str(body.get("symbol", "")).upper())[:20]
    if not sym:
        raise ValueError("symbol required")
    return research.sources(sym)

handler = make_handler(run)
