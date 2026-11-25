
import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI


app = FastAPI(
    title="Application API",
    version="1.0.0"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("application")


def log_event(event_name: str):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "application",
        "event": event_name
    }

    logger.info(json.dumps(event, ensure_ascii=False))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/process")
def process_request():
    log_event("request_served")

    return {
        "status": "ok",
        "service": "application"
    }
