"""Thin Gemini REST client: JSON output, disk cache, retries with fallback, and a usage log."""
import hashlib, json, os, re, time, requests
from . import config

URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
USAGE_LOG = config.CACHE_DIR / "usage.jsonl"

class LLMError(RuntimeError):
    pass

def _key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise LLMError("GEMINI_API_KEY is not set")
    return k

def generate(prompt, *, model, schema=None, task="misc", temperature=0.1, max_tokens=8192, cache=True):
    """Return parsed JSON (if schema) or text. Same prompt + model is served from disk."""
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if schema:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = schema
    key = hashlib.sha256(json.dumps([model, body], sort_keys=True).encode()).hexdigest()
    path = config.CACHE_DIR / "llm" / f"{key}.json"
    if cache and path.exists():
        out = json.loads(path.read_text())
        _log(task, model, out.get("usage", {}), cached=True)
        return out["result"]

    m, last = model, None
    for attempt in range(8 if os.environ.get("FINN_PATIENT") else 4):
        try:
            r = requests.post(URL.format(m=m), params={"key": _key()}, json=body, timeout=120)
        except requests.RequestException as e:
            last = str(e); time.sleep(2); continue
        if r.status_code == 200:
            d = r.json()
            try:
                text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
                result = json.loads(text) if schema else text
            except (KeyError, IndexError, ValueError):
                # Usually the answer was cut off (thinking ate the budget). Give it more room and retry.
                last = f"bad response ({d.get('candidates', [{}])[0].get('finishReason')}): {str(d)[:160]}"
                body["generationConfig"]["maxOutputTokens"] = min(body["generationConfig"]["maxOutputTokens"] * 2, 32768)
                continue
            usage = d.get("usageMetadata", {})
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"result": result, "usage": usage, "model": m}))
            _log(task, m, usage, cached=False)
            return result
        last = f"{r.status_code} {r.text[:200]}"
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
    raise LLMError(f"{model}: {last}")

METER = []  # usage records for the current run; research.py reads and resets it

def _log(task, model, usage, cached):
    rec = {"t": time.time(), "task": task, "model": model, "cached": cached,
           "in": usage.get("promptTokenCount", 0), "out": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)}
    METER.append(rec)
    try:
        with open(USAGE_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass

def cost_usd(model, tin, tout):
    pin, pout = config.PRICES.get(model, (0.3, 2.5))
    return (tin * pin + tout * pout) / 1e6
