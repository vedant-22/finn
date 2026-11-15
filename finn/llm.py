"""Thin Gemini REST client: JSON output, disk cache, retries with fallback, and a usage log."""
import contextlib, contextvars, hashlib, json, os, re, time, requests
from . import config

URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
USAGE_LOG = config.CACHE_DIR / "usage.jsonl"

class LLMError(RuntimeError):
    """A fixed code for the client (no_key, quota, unavailable, bad_response); upstream detail is for the log only."""
    def __init__(self, code, detail="", usage=None, model=None):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail
        self.usage, self.model = usage or {"in": 0, "out": 0, "usd": 0.0}, model   # tokens paid for before it failed, and on which model

def has_key():
    return bool(os.environ.get("GEMINI_API_KEY"))

def require_key():
    """Endpoints that spend model quota call this before fetching anything."""
    _key()

def _key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise LLMError("no_key")
    return k

# Which model actually answered, per unit of work. A caller opens a scope around a step and reads it after,
# so a fallback (or a cached fallback) is seen without changing any signature, and threads don't mix.
# fresh=True inside a scope skips cache reads for every call in it (a degraded run re-asked with a key).
_ANSWERED = contextvars.ContextVar("finn_answered", default=None)
_FRESH = contextvars.ContextVar("finn_fresh", default=False)

@contextlib.contextmanager
def scope(fresh=False):
    models = []
    tok, ftok = _ANSWERED.set(models), _FRESH.set(fresh)
    try:
        yield models
    finally:
        _ANSWERED.reset(tok); _FRESH.reset(ftok)

def _answered(m):
    got = _ANSWERED.get()
    if got is not None:
        got.append(m)

def paid_terms():
    return os.environ.get("FINN_MODEL_TERMS") == "paid"

TASKS = ("classify", "people", "explain", "promise_extract", "promise_grade", "answer", "agent")   # the gate's steps (evals/gate.py)

def generate(prompt, *, model, schema=None, task=None, temperature=0.1, max_tokens=8192, cache=True,
             public=False, meta=False, fresh=False, budget=None):
    """Return parsed JSON (if schema) or text; with meta=True, {result, model, cached, usage}.

    Text is private unless the caller says public=True (public filings). Private text needs a key on terms
    that forbid training (FINN_MODEL_TERMS=paid) and is never cached. That flag guards against accidents;
    in production the control is Vertex in its own project (docs/adr/0001-three-kinds-of-data.md).
    Public text with the same prompt + model is served from disk, unless fresh (or FINN_FRESH=1): then the
    cache is written but not read.
    Usage is every try's, summed: a cut-off reply is retried with more room, and each try is paid for. With a budget
    (tokens, in and out), a try that could pass it isn't sent: LLMError("budget"). The input is estimated at
    3 characters a token, on the high side, since the API reports the real count only after.
    A task the gate doesn't fingerprint is refused, so no prompt reaches a model unseen."""
    if task not in TASKS:
        raise LLMError("unknown_task", f"{task!r} is not a model step the gate fingerprints")
    if not public:
        if not paid_terms():
            raise LLMError("terms", "private text needs a key on paid terms")
        cache = False
    fresh = fresh or os.environ.get("FINN_FRESH") == "1" or _FRESH.get()
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if schema:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = schema
    key = hashlib.sha256(json.dumps([model, body], sort_keys=True).encode()).hexdigest()
    path = config.CACHE_DIR / "llm" / f"{key}.json"
    if cache and not fresh and path.exists():
        out = json.loads(path.read_text())
        answered = out.get("model", model)   # the entry keeps the model that answered, which a fallback changes
        _log(task, answered, out.get("usage", {}), cached=True)
        _answered(answered)
        return {"result": out["result"], "model": answered, "cached": True, "usage": _tokens(out.get("usage", {}))} if meta else out["result"]

    m, last, code, paid, est_in = model, None, "unavailable", {"in": 0, "out": 0, "usd": 0.0}, len(prompt) // 3 + 1
    for attempt in range(8 if os.environ.get("FINN_PATIENT") else 4):
        if budget is not None and paid["in"] + paid["out"] + est_in + body["generationConfig"]["maxOutputTokens"] > budget:
            raise LLMError("budget", f"{model}: {paid['in'] + paid['out']} tokens spent, {budget} allowed", usage=paid, model=m)
        try:
            # The key goes in a header, so it never appears in a URL, a log line or an exception.
            r = requests.post(URL.format(m=m), headers={"x-goog-api-key": _key()}, json=body, timeout=120)
        except requests.RequestException as e:
            last, code = type(e).__name__, "unavailable"; time.sleep(2); continue
        if r.status_code == 200:
            try:
                d = r.json()
            except ValueError:
                d = None
            if not isinstance(d, dict):   # a 200 that isn't the API's JSON (a proxy's page): an error with a code, not a crash
                last, code = f"bad response (not JSON): {r.text[:160]}", "bad_response"
                continue
            got = _tokens(d.get("usageMetadata") or {})
            paid = {"in": paid["in"] + got["in"], "out": paid["out"] + got["out"], "usd": paid["usd"] + usd(m, got["in"], got["out"])}
            _log(task, m, d.get("usageMetadata") or {}, cached=False)
            try:
                text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
                result = json.loads(text) if schema else text
            except (KeyError, IndexError, ValueError, TypeError, AttributeError):
                # Usually the answer was cut off (thinking ate the budget). Give it more room and retry.
                # No candidates at all (a blocked prompt) lands here too, and what it cost is kept.
                first = (d.get("candidates") or [{}])[0]
                last, code = f"bad response ({first.get('finishReason') if isinstance(first, dict) else None}): {str(d)[:160]}", "bad_response"
                body["generationConfig"]["maxOutputTokens"] = min(body["generationConfig"]["maxOutputTokens"] * 2, 32768)
                continue
            usage = d.get("usageMetadata", {})
            if cache:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"result": result, "usage": usage, "model": m}))
            _answered(m)
            return {"result": result, "model": m, "cached": False, "usage": paid} if meta else result
        last = f"{r.status_code} {r.text[:200]}"
        code = "quota" if r.status_code == 429 else "unavailable"
        if r.status_code == 429 and "free_tier" in r.text and "PerDay" not in r.text and os.environ.get("FINN_PATIENT"):
            # Batch jobs only: a per-minute limit clears in under a minute, so wait rather than drop a tier.
            wait = re.search(r'"retryDelay":\s*"(\d+)', r.text)
            time.sleep(min(65, int(wait.group(1)) + 2 if wait else 30))
            continue
        if r.status_code == 429 and "free_tier" in r.text and m in config.FALLBACK:
            # Free quota for this model is gone (or, live, we can't afford to wait). Drop a tier now.
            m = config.FALLBACK[m]
            continue
        if r.status_code in (429, 500, 503):
            # Overloaded or out of quota: wait a little, then drop to the fallback model.
            time.sleep(min(20, 3 * (attempt + 1)))
            if attempt >= 1 and m in config.FALLBACK:
                m = config.FALLBACK[m]
            continue
        break
    raise LLMError(code, f"{model}: {last}", usage=paid, model=m)

METER = []  # usage records for the current run; research.py reads and resets it

def usd(model, tokens_in, tokens_out):
    """List price of one call (config.PRICES), so a cost compares across models. Every model FINN can call has a price
    (config.py checks it at import), so an unknown one is an error, never $0."""
    pin, pout = config.PRICES[model]
    return (tokens_in * pin + tokens_out * pout) / 1e6

def _tokens(usage):
    """Tokens the API reported for one answer: in, and out with thinking, which is billed as output."""
    return {"in": usage.get("promptTokenCount", 0), "out": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)}

def _log(task, model, usage, cached):
    rec = {"t": time.time(), "task": task, "model": model, "cached": cached,
           "in": usage.get("promptTokenCount", 0), "out": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)}
    METER.append(rec)
    try:
        with open(USAGE_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass

