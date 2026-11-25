
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


SCENARIO = os.getenv("SCENARIO", "baseline").lower()

K8S_API_URL = os.getenv(
    "K8S_API_URL",
    "http://k8s-sim:8000"
)

CALICO_API_URL = os.getenv(
    "CALICO_API_URL",
    "http://calico-sim:8000"
)

LOG_DIR = Path(
    os.getenv("LOG_DIR", f"/logs/{SCENARIO}")
)

REQUEST_INTERVAL = 0.25
WARMUP_SECONDS = 4
OUTAGE_SECONDS = 8
POST_UPGRADE_WINDOW_SECONDS = 12

LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "probe.jsonl"
SUMMARY_FILE = LOG_DIR / "summary.json"

samples = []
experiment_start = None


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def log_event(event, **details):
    record = {
        "timestamp": timestamp(),
        "service": "probe",
        "event": event,
        **details
    }

    line = json.dumps(record, ensure_ascii=False)

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")

    print(line, flush=True)


def wait_for_services(client, timeout=60):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            k8s = client.get(f"{K8S_API_URL}/health")
            calico = client.get(f"{CALICO_API_URL}/health")

            if k8s.status_code == 200 and calico.status_code == 200:
                return

        except httpx.HTTPError:
            pass

        time.sleep(0.5)

    raise RuntimeError("Services did not become ready")


def sample_request(client, phase):
    started = time.monotonic()

    status_code = None
    error = None

    try:
        response = client.get(
            f"{CALICO_API_URL}/forward"
        )

        status_code = response.status_code

    except httpx.HTTPError as exc:
        error = str(exc)

    finished = time.monotonic()

    elapsed_seconds = round(
        finished - experiment_start, 6
    )

    latency_ms = (finished - started) * 1000

    outcome = "success" if status_code == 200 else "error"

    sample = {
        "elapsed_seconds": elapsed_seconds,
        "phase": phase,
        "status_code": status_code,
        "outcome": outcome
    }

    samples.append(sample)

    log_event(
        "request",
        phase=phase,
        status_code=status_code,
        outcome=outcome,
        latency_ms=round(latency_ms, 3),
        elapsed_seconds=elapsed_seconds,
        error=error
    )

    return sample


def run_until(client, deadline, phase):
    while time.monotonic() < deadline:
        loop_started = time.monotonic()

        sample_request(client, phase)

        elapsed = time.monotonic() - loop_started
        remaining = REQUEST_INTERVAL - elapsed

        if remaining > 0:
            time.sleep(remaining)


def post_action(client, url, event):
    started = round(
        time.monotonic() - experiment_start, 6
    )

    response = client.post(url)
    response.raise_for_status()

    completed = round(
        time.monotonic() - experiment_start, 6
    )

    result = response.json()

    log_event(
        event,
        status_code=response.status_code,
        action_started_elapsed_seconds=started,
        action_completed_elapsed_seconds=completed,
        response=result
    )

    return result, completed


def calculate_metrics(upgrade_time, restore_time):
    first_failure = next(
        (
            item for item in samples
            if item["elapsed_seconds"] >= upgrade_time
            and item["outcome"] == "error"
        ),
        None
    )

    first_recovery = None

    if restore_time is not None and first_failure is not None:
        first_recovery = next(
            (
                item for item in samples
                if item["elapsed_seconds"] >= restore_time
                and item["elapsed_seconds"] > first_failure["elapsed_seconds"]
                and item["status_code"] == 200
            ),
            None
        )

    total = len(samples)

    errors = sum(
        item["outcome"] == "error"
        for item in samples
    )

    outage_requests = [
        item for item in samples
        if item["phase"] == "baseline_outage"
    ]

    outage_errors = sum(
        item["outcome"] == "error"
        for item in outage_requests
    )

    post_upgrade_requests = [
        item for item in samples
        if item["elapsed_seconds"] >= upgrade_time
    ]

    post_upgrade_errors = sum(
        item["outcome"] == "error"
        for item in post_upgrade_requests
    )

    return {
        "requests_total": total,
        "requests_error": errors,
        "error_percentage": round(
            errors / total * 100, 2
        ) if total else 0,

        "outage_requests_total": len(outage_requests),
        "outage_requests_error": outage_errors,
        "outage_error_percentage": round(
            outage_errors / len(outage_requests) * 100, 2
        ) if outage_requests else None,

        "post_upgrade_requests_total": len(post_upgrade_requests),
        "post_upgrade_requests_error": post_upgrade_errors,
        "post_upgrade_error_percentage": round(
            post_upgrade_errors / len(post_upgrade_requests) * 100, 2
        ) if post_upgrade_requests else None,

        "time_to_failure_seconds": round(
            first_failure["elapsed_seconds"] - upgrade_time, 3
        ) if first_failure else None,

        "time_to_recovery_seconds": round(
            first_recovery["elapsed_seconds"]
            - first_failure["elapsed_seconds"], 3
        ) if first_failure and first_recovery else None,

        "recovery_propagation_seconds": round(
            first_recovery["elapsed_seconds"] - restore_time, 3
        ) if restore_time is not None and first_recovery else None
    }


def main():
    global experiment_start

    if SCENARIO not in ("baseline", "mitigated"):
        raise ValueError(
            "SCENARIO must be baseline or mitigated"
        )

    with LOG_FILE.open("w", encoding="utf-8"):
        pass

    samples.clear()

    with httpx.Client(timeout=3.0) as client:
        wait_for_services(client)

        initial_status = client.get(
            f"{CALICO_API_URL}/status"
        )
        initial_status.raise_for_status()

        initial_state = initial_status.json()

        if not initial_state["routes_available"]:
            raise RuntimeError(
                "Initial network state is unavailable"
            )

        if (
            len(initial_state["selected_nodes"]) != 3
            or len(initial_state["selected_peers"]) != 3
        ):
            raise RuntimeError(
                "Expected three initial Route Reflectors"
            )

        experiment_start = time.monotonic()

        log_event(
            "experiment_started",
            scenario=SCENARIO,
            initial_state=initial_state
        )

        run_until(
            client,
            time.monotonic() + WARMUP_SECONDS,
            "warmup"
        )

        if SCENARIO == "mitigated":
            post_action(
                client,
                f"{K8S_API_URL}/prepare-mitigation",
                "current_label_added"
            )

            mitigation, _ = post_action(
                client,
                f"{CALICO_API_URL}/mitigate",
                "mitigation_applied"
            )

            if mitigation["validated_count"] != 3:
                raise RuntimeError(
                    "Expected three validated control-plane nodes"
                )

        _, upgrade_time = post_action(
            client,
            f"{K8S_API_URL}/upgrade",
            "upgrade_completed"
        )

        restore_time = None

        upgrade_deadline = experiment_start + upgrade_time

        experiment_deadline = (
            upgrade_deadline + POST_UPGRADE_WINDOW_SECONDS
        )

        if SCENARIO == "baseline":
            outage_deadline = (
                upgrade_deadline + OUTAGE_SECONDS
            )

            run_until(
                client,
                outage_deadline,
                "baseline_outage"
            )

            _, restore_time = post_action(
                client,
                f"{K8S_API_URL}/reintroduce-legacy-label",
                "recovery_intervention"
            )

            run_until(
                client,
                experiment_deadline,
                "baseline_recovery"
            )

        else:
            run_until(
                client,
                experiment_deadline,
                "mitigated_after_upgrade"
            )

        metrics = calculate_metrics(
            upgrade_time,
            restore_time
        )

        summary = {
            "scenario": SCENARIO,
            "finished_at": timestamp(),
            "upgrade_elapsed_seconds": upgrade_time,
            "recovery_intervention_elapsed_seconds": restore_time,
            **metrics
        }

        with SUMMARY_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                summary,
                file,
                indent=2,
                ensure_ascii=False
            )

        log_event(
            "experiment_finished",
            summary=summary
        )

        print(
            json.dumps(
                summary,
                indent=2,
                ensure_ascii=False
            ),
            flush=True
        )


if __name__ == "__main__":
    main()
