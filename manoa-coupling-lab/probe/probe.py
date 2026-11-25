
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

TARGET_URL = os.getenv(
    "TARGET_URL",
    "http://localhost:4000/recommendations"
)
SCENARIO = os.getenv("SCENARIO", "baseline")
TOTAL_REQUESTS = 10

LOG_DIR = Path("/logs") / SCENARIO
LOG_DIR.mkdir(parents=True, exist_ok=True)

results = []

for number in range(1, TOTAL_REQUESTS + 1):
    payload = json.dumps({
        "products": [{"id": 1}, {"id": 2}, {"id": 3}],
        "limit": 2
    }).encode("utf-8")

    request = urllib.request.Request(
        TARGET_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    started = time.perf_counter()
    status = None
    error = None

    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            status = response.status
            response.read()
    except Exception as exc:
        error = str(exc)

    elapsed = time.perf_counter() - started

    record = {
        "request": number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "success": status == 200,
        "elapsed_seconds": round(elapsed, 4),
        "error": error
    }

    results.append(record)
    print(json.dumps(record), flush=True)
    time.sleep(0.2)

successes = sum(item["success"] for item in results)
failures = TOTAL_REQUESTS - successes

summary = {
    "scenario": SCENARIO,
    "target_url": TARGET_URL,
    "requests_total": TOTAL_REQUESTS,
    "successes": successes,
    "failures": failures,
    "error_percentage": round(failures / TOTAL_REQUESTS * 100, 2)
}

(LOG_DIR / "probe.jsonl").write_text(
    "".join(json.dumps(item) + "\n" for item in results),
    encoding="utf-8"
)

(LOG_DIR / "summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\nRESUMO:")
print(json.dumps(summary, indent=2), flush=True)
