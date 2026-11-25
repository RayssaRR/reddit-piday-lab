
import json
import logging
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, HTTPException


app = FastAPI(
    title="Cluster State API",
    version="1.0.0"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("cluster-state")

LEGACY_LABEL = "node-role.kubernetes.io/master"
CURRENT_LABEL = "node-role.kubernetes.io/control-plane"

state_lock = Lock()

control_planes = [
    {
        "name": f"control-plane-0{i}",
        "type": "control-plane",
        "labels": {
            LEGACY_LABEL: ""
            
        }
    }
    for i in range(1, 4)
]

workers = [
    {
        "name": f"worker-0{i}",
        "type": "worker",
        "labels": {}
    }
    for i in range(1, 3)
]

state = {
    "version": "1.23",
    "nodes": control_planes + workers
}


def log_event(event_name: str, **details):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "cluster-state",
        "event": event_name,
        **details
    }

    logger.info(json.dumps(event, ensure_ascii=False))


def get_nodes_unlocked():
    return [
        {
            "name": node["name"],
            "type": node["type"],
            "labels": dict(node["labels"])
        }
        for node in state["nodes"]
    ]


def get_snapshot():
    with state_lock:
        return {
            "version": state["version"],
            "nodes": get_nodes_unlocked()
        }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/nodes")
def list_nodes():
    return get_snapshot()


@app.post("/prepare-mitigation")
def prepare_mitigation():
    with state_lock:
        if state["version"] != "1.23":
            raise HTTPException(
                status_code=409,
                detail="Invalid cluster version"
            )

        changed_nodes = []

        for node in state["nodes"]:
            if node["type"] == "control-plane":
                if CURRENT_LABEL not in node["labels"]:
                    node["labels"][CURRENT_LABEL] = ""
                    changed_nodes.append(node["name"])

        result = {
            "added_to": changed_nodes,
            "nodes": get_nodes_unlocked()
        }

    log_event("current_label_added", **result)

    return result



@app.post("/upgrade")
def upgrade():
    with state_lock:
        if state["version"] != "1.23":
            raise HTTPException(
                status_code=409,
                detail="Cluster already upgraded"
            )

        previous_version = state["version"]
        removed_from = []

        for node in state["nodes"]:
            if LEGACY_LABEL in node["labels"]:
                del node["labels"][LEGACY_LABEL]
                removed_from.append(node["name"])

        state["version"] = "1.24"

        result = {
            "previous_version": previous_version,
            "current_version": state["version"],
            "legacy_label_removed_from": removed_from,
            "nodes": get_nodes_unlocked()
        }

    log_event("version_updated", **result)

    return result


@app.post("/reintroduce-legacy-label")
def reintroduce_legacy_label():
    with state_lock:
        if state["version"] != "1.24":
            raise HTTPException(
                status_code=409,
                detail="Cluster version must be 1.24"
            )

        changed_nodes = []

        for node in state["nodes"]:
            if node["type"] == "control-plane":
                if LEGACY_LABEL not in node["labels"]:
                    node["labels"][LEGACY_LABEL] = ""
                    changed_nodes.append(node["name"])

        result = {
            "reintroduced_on": changed_nodes,
            "nodes": get_nodes_unlocked()
        }

    log_event("legacy_label_reintroduced", **result)

    return result
