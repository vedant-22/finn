"""What the app shows without asking: the notices, a block per filing and a block per company.

`pipeline/build_network.py` writes it to web/public/data/network.json; `/api/network` op `views` rebuilds it from
the investor's answers to "Is it the same person?". One function, so the two cannot drift: with no answers the API
returns the file's content byte for byte (`evals/run_security.py`).
"""
import hashlib
import json


def views(net):
    symbols = list(net.companies)
    out = {
        "asof": net.asof, "synthetic": True, "label": net.label, "me": net.me.name, "contacts": len(net.contacts),
        "notices": net.notices(symbols, limit=40),
        "filings": {f["id"]: b for f in net.filings.values() if (b := net.for_filing(f))},
        "companies": {s: net.company(s) for s in dict.fromkeys(symbols + net.researched) if s in net.reg.by_symbol},
        "themes": [t for t in net.reg.themes if net.expertise(t, limit=1)],
    }
    return out


def dump(out):
    return json.dumps(out, separators=(",", ":"), default=str)


def build_id(out):
    """The build a set of views belongs to: a hash of the views computed with no answers."""
    return hashlib.sha256(dump(out).encode()).hexdigest()[:12]
