
import json
import logging
import os
from datetime import datetime, timezone
from threading import Lock

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse


app = FastAPI(
    title="Network Control API",
    version="1.0.0"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("calico")

K8S_API_URL = os.getenv(
    "K8S_API_URL",
    "http://k8s-sim:8000"
)

APPLICATION_URL = os.getenv(
    "APPLICATION_URL",
    "http://application:8000"
)

LEGACY_LABEL = "node-role.kubernetes.io/master"
CURRENT_LABEL = "node-role.kubernetes.io/control-plane"

selector_lock = Lock()
route_state_lock = Lock()

selectors = {
    "node_selector": LEGACY_LABEL,
    "peer_selector": LEGACY_LABEL
}

last_route_state = None


def log_event(event_name: str, **details):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "calico-sim",
        "event": event_name,
        **details
    }

    logger.info(json.dumps(event, ensure_ascii=False))


def get_nodes():
    try:
        response = httpx.get(
            f"{K8S_API_URL}/nodes",
            timeout=3.0
        )
        response.raise_for_status()

        return response.json()["nodes"]

    except (httpx.HTTPError, KeyError, ValueError) as exc:
        log_event(
            "cluster_state_unavailable",
            error=str(exc)
        )

        raise HTTPException(
            status_code=503,
            detail="Cluster state unavailable"
        )


def select_nodes(nodes, label):
    return [
        node
        for node in nodes
        if label in node.get("labels", {})
    ]


def get_selector_state():
    with selector_lock:
        return dict(selectors)


def evaluate_routes(nodes):
    current_selectors = get_selector_state()

    selected_nodes = select_nodes(
        nodes,
        current_selectors["node_selector"]
    )

    selected_peers = select_nodes(
        nodes,
        current_selectors["peer_selector"]
    )

    routes_available = (
        len(selected_nodes) > 0
        and len(selected_peers) > 0
    )

    return {
        "node_selector": current_selectors["node_selector"],
        "peer_selector": current_selectors["peer_selector"],
        "selected_nodes": [
            node["name"] for node in selected_nodes
        ],
        "selected_peers": [
            node["name"] for node in selected_peers
        ],
        "routes_available": routes_available
    }


def record_route_state(result):
    global last_route_state

    current_state = result["routes_available"]

    with route_state_lock:
        if current_state != last_route_state:
            log_event(
                "route_distribution_changed",
                **result
            )

            last_route_state = current_state


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    nodes = get_nodes()
    result = evaluate_routes(nodes)

    record_route_state(result)

    return result


@app.post("/mitigate")
def mitigate():
    nodes = get_nodes()

    expected_nodes = {
        node["name"]
        for node in nodes
        if node.get("type") == "control-plane"
    }

    selected_node_names = {
        node["name"]
        for node in select_nodes(nodes, CURRENT_LABEL)
    }

    selected_peer_names = {
        node["name"]
        for node in select_nodes(nodes, CURRENT_LABEL)
    }

    if not expected_nodes:
        raise HTTPException(
            status_code=409,
            detail="No control-plane nodes found"
        )

    if (
        selected_node_names != expected_nodes
        or selected_peer_names != expected_nodes
    ):
        raise HTTPException(
            status_code=409,
            detail="New label validation failed"
        )

    with selector_lock:
        previous_selectors = dict(selectors)

        selectors["node_selector"] = CURRENT_LABEL
        selectors["peer_selector"] = CURRENT_LABEL

    result = {
        "previous_selectors": previous_selectors,
        "current_selectors": get_selector_state(),
        "validated_nodes": sorted(expected_nodes),
        "validated_count": len(expected_nodes)
    }

    log_event("selectors_migrated", **result)

    return result


@app.get("/forward")
def forward():
    nodes = get_nodes()
    result = evaluate_routes(nodes)

    record_route_state(result)

    if not result["routes_available"]:
        log_event(
            "request_rejected",
            reason="no_route_reflectors_selected",
            **result
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "reason": "no_route_reflectors_selected",
                **result
            }
        )

    try:
        response = httpx.get(
            f"{APPLICATION_URL}/process",
            timeout=3.0
        )
        response.raise_for_status()

    except httpx.HTTPError as exc:
        log_event(
            "application_unavailable",
            error=str(exc)
        )

        return JSONResponse(
            status_code=503,
            content={"status": "application_unavailable"}
        )

    return {
        "status": "ok",
        "application": response.json(),
        "route_reflectors": result["selected_nodes"]
    }
