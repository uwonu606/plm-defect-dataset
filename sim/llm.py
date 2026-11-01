import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "runs" / "llm_cache"
WORKDIR = Path(tempfile.gettempdir()) / "plm-sim-llm"


def ask(prompt, system, model="haiku", retries=2):
    CACHE.mkdir(parents=True, exist_ok=True)
    WORKDIR.mkdir(exist_ok=True)
    key = hashlib.sha256(json.dumps([model, system, prompt]).encode()).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    cmd = ["claude", "-p", "--model", model, "--tools", "", "--setting-sources", "", "--strict-mcp-config",
           "--system-prompt", system, "--output-format", "json", "--no-session-persistence"]
    for attempt in range(retries + 1):
        started = time.monotonic()
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=WORKDIR, timeout=300)
        elapsed = time.monotonic() - started
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            data = {"is_error": True, "result": proc.stdout[-500:] + proc.stderr[-500:]}
        if not data.get("is_error") and data.get("terminal_reason", "completed") == "completed":
            usage = data.get("usage", {})
            out = {"text": data.get("result", ""), "seconds": round(elapsed, 2),
                   "input_tokens": usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                   + usage.get("cache_creation_input_tokens", 0),
                   "output_tokens": usage.get("output_tokens", 0), "cost_usd": data.get("total_cost_usd", 0)}
            path.write_text(json.dumps(out, ensure_ascii=False))
            return out
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"claude -p failed: {str(data)[:300]}")


def parse_json(text):
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise ValueError(f"no JSON in: {text[:200]}")
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(text[start:])
    return value
