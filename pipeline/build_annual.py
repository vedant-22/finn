"""Fetch, cut and read the FY26 annual reports of the built-in companies.

    python3 pipeline/build_annual.py --cut SYNGENE MARUTI ...   fetch each report, cut it, add it to the fixture
    python3 pipeline/build_annual.py --serve                     read the fixture, write web/public/data/annual/<SYM>.json

The fixture (evals/fixtures/annual_pages.json.gz) holds the cut pages keyed by the PDF's page number, with
the PDF's sha256 and page count, and the call pages the search reads, so the readers and their evals run
offline and in CI. Only this script fetches an annual report; the API never does (55 MB is not a
request-time job). Every connection goes through finn/netguard.py to a public address, and only to the
hosts below.
"""
import datetime as dt, gzip, hashlib, json, pathlib, sys
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finn import netguard
netguard.install()
from finn import annual
from finn.sources import nse, pdf, screener

FIXTURE = ROOT / "evals" / "fixtures" / "annual_pages.json.gz"
SERVED = ROOT / "web" / "public" / "data" / "annual"
COMPANIES = ROOT / "web" / "public" / "data" / "companies"
SNAPSHOT = dt.date(2026, 10, 28)          # the demo's day: a report filed after it is not used
MAX_MB, DEADLINE_S = 80, 180              # the API keeps 40 MB and 45 s
ALLOW = {"nsearchives.nseindia.com", "www.nseindia.com", "www.bseindia.com", "www.screener.in"}


def allowed(url, extra=()):
    host = urlsplit(url).hostname or ""
    if host not in ALLOW and host not in extra:
        raise SystemExit(f"refused host {host} for {url}")
    return url


def load_fixture():
    if FIXTURE.exists():
        return json.loads(gzip.decompress(FIXTURE.read_bytes()))
    return {"reports": {}, "unread": {}, "calls": {}}


def save_fixture(fx):
    FIXTURE.write_bytes(gzip.compress(json.dumps(fx, ensure_ascii=False, sort_keys=True).encode(), mtime=0))


def listing(sym):
    """The FY26 annual report NSE lists for the company, the latest filed on or before the snapshot."""
    d = nse.get_json(f"https://www.nseindia.com/api/annual-reports?index=equities&symbol={sym}", ttl_hours=24 * 365)
    rows = []
    for r in d.get("data", []):
        if r["fromYr"] != "2025" or r["toYr"] != "2026":
            continue
        try:
            when = dt.datetime.strptime(r["broadcast_dttm"], "%d-%b-%Y %H:%M:%S")
        except ValueError:          # an undated row can't be shown to predate the snapshot
            continue
        if when.date() <= SNAPSHOT:
            rows.append((when, r))
    if not rows:
        return None
    when, r = max(rows, key=lambda x: x[0])
    return {"url": r["fileName"], "filed": when.strftime("%Y-%m-%d"), "filed_text": f"{when.day} {when:%b %Y}",
            "kind": r.get("submission_type")}


def read_pdf(url):
    import pymupdf
    data = pdf.fetch(allowed(url), max_mb=MAX_MB, deadline_s=DEADLINE_S)
    doc = pymupdf.open(stream=data, filetype="pdf")
    return hashlib.sha256(data).hexdigest(), {i + 1: doc[i].get_text() for i in range(doc.page_count)}


def cut_one(sym, fx):
    meta = listing(sym)
    if not meta:
        fx["unread"][sym] = {"why": "no FY26 annual report on NSE by 28 Oct 2026"}
        return
    sha, pages = read_pdf(meta["url"])
    meta["source"] = "nse"
    if len(pages) < 5:
        # The exchange copy is a cover letter. Screener links the BSE copy; try it once.
        alt = next((a["url"] for a in screener.company(sym).get("annual_reports", []) if a["label"].endswith("2026")), None)
        tried = {"nse": meta["url"], "bse": alt}
        if alt:
            sha2, pages2 = read_pdf(alt)
            if len(pages2) >= 5:
                sha, pages, meta["source"], meta["url"] = sha2, pages2, "bse", alt
        if len(pages) < 5:
            fx["unread"][sym] = {"why": "The copy filed on NSE, and the one on BSE, is a one-page cover letter.",
                                 "url": meta["url"], "filed": meta["filed"], "filed_text": meta["filed_text"], "tried": tried}
            fx["reports"].pop(sym, None)
            return
    c = annual.cut(pages)
    if not c["reports"]:
        fx["unread"][sym] = {"why": "FINN’s rules found no auditor’s report on the financial statements in this PDF.",
                             "url": meta["url"], "filed": meta["filed"], "filed_text": meta["filed_text"]}
        fx["reports"].pop(sym, None)
        print(f"{sym}: no audit report found", flush=True)
        return
    fx["unread"].pop(sym, None)
    fx["reports"][sym] = {**meta, "sha256": sha, "pages_total": c["pages_total"],
                          "pages": {str(p): t for p, t in c["pages"].items()},
                          "reports": c["reports"], "notes": c["notes"], "related": c["related"], "sweep": c["sweep"]}
    # The calls the search reads: only where the auditor drew attention to a matter with a defined term
    company = json.loads((COMPANIES / f"{sym}.json").read_text())
    kind = "consolidated" if any(r["set"] == "consolidated" for r in c["reports"]) else "standalone"
    rep = next(r for r in c["reports"] if r["set"] == kind)
    if any(e["term"] for e in annual.read_report(c["pages"], rep)["emphasis"]):
        hosts = {urlsplit(x["url"]).hostname for x in company["calls"]}
        for call in company["calls"]:
            if call.get("error"):
                continue
            allowed(call["url"], hosts)
            fx["calls"][call["url"]] = {str(i): t for i, t in enumerate(pdf.pages(call["url"]), start=1)}
    print(f"{sym}: {len(c['pages'])} of {c['pages_total']} pages kept, {len(c['sweep'])} sweep hits", flush=True)


def serve(fx):
    SERVED.mkdir(parents=True, exist_ok=True)
    for f in sorted(COMPANIES.glob("*.json")):
        sym = f.stem
        company = json.loads(f.read_text())
        if sym in fx["reports"]:
            r = fx["reports"][sym]
            pages = {int(p): t for p, t in r["pages"].items()}
            notes = r["notes"]
            out = annual.compose(sym, r, {"reports": r["reports"], "notes": notes, "pages_total": r["pages_total"]},
                                 pages, company, fx["calls"])
        elif sym in fx["unread"]:
            u = fx["unread"][sym]
            out = annual.not_read(sym, {"url": u.get("url"), "filed": u.get("filed_text")}, u["why"])
        else:
            continue
        (SERVED / f"{sym}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print(f"{sym}: {out['verdict']}; {len(out['questions'])} questions")


if __name__ == "__main__":
    args = sys.argv[1:]
    fx = load_fixture()
    if args and args[0] == "--cut":
        for s in args[1:]:
            cut_one(s.upper(), fx)
            save_fixture(fx)
    elif args == ["--serve"]:
        serve(fx)
    else:
        raise SystemExit(__doc__)
