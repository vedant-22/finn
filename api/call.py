"""POST {period, url, urls} -> promises from one earnings call, each quote checked against its page."""
from _common import make_handler
from finn import research

ALLOWED = ("https://nsearchives.nseindia.com/", "https://www.bseindia.com/", "https://archives.nseindia.com/")

def run(body):
    urls = [u for u in (body.get("urls") or [body.get("url")]) if isinstance(u, str) and u.startswith(ALLOWED)]
    if not urls:
        raise ValueError("only exchange-hosted transcripts are read")
    return research.promises_for({"period": body.get("period", ""), "url": urls[0], "urls": urls})

handler = make_handler(run)
