"""Paths, model routing and prices in one place."""
import os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# On Vercel the project dir is read-only; /tmp is the only writable place.
CACHE_DIR = pathlib.Path(os.environ.get("FINN_CACHE", "/tmp/finn-cache" if os.environ.get("VERCEL") else ROOT / "data" / "cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

# Model routing. Cheap model for bulk reading, the stronger flash only where it has to reason.
FAST = os.environ.get("FINN_FAST_MODEL", "gemini-3.5-flash-lite")   # classify, one-liners, people, promise extraction
SMART = os.environ.get("FINN_SMART_MODEL", "gemini-3.5-flash")      # grading promises against delivery, bull/bear
FALLBACK = {SMART: FAST, FAST: "gemini-3.1-flash-lite"}

# USD per 1M tokens (input, output), paid-tier list prices as of Aug 2026
# (anotherwrapper.com/llm-pricing). We run on the free tier; these show what the same work would cost if billed.
PRICES = {
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.30, 2.50),  # fallback only; priced like 3.5 flash-lite to stay conservative
    "gemini-3.5-flash": (1.50, 9.00),
}
