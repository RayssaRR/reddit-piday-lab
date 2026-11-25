
import json
import sys
from pathlib import Path


log_file = Path(sys.argv[1])

summary_file = log_file.with_name("summary.json")

with log_file.open(encoding="utf-8") as file:
    records = [
        json.loads(line)
        for line in file
        if line.strip()
    ]

requests = [
    record for record in records
    if record.get("event") == "request"
]

upgrade = next(
    record for record in records
    if record.get("event") == "upgrade_completed"
)

recovery = next(
    (
        record for record in records
        if record.get("event") == "recovery_intervention"
    ),
    None
)

upgrade_time = upgrade["action_completed_elapsed_seconds"]

recovery_time = (
    recovery["action_completed_elapsed_seconds"]
    if recovery else None
)

first_failure = next(
    (
        request for request in requests
        if request["elapsed_seconds"] >= upgrade_time
        and request["outcome"] == "error"
    ),
    None
)

first_success_after_recovery = None

if recovery_time is not None:
    first_success_after_recovery = next(
        (
            request for request in requests
            if request["elapsed_seconds"] >= recovery_time
            and request["status_code"] == 200
        ),
        None
    )

errors = [
    request for request in requests
    if request["outcome"] == "error"
]

outage_requests = [
    request for request in requests
    if request["phase"] == "baseline_outage"
]

summary = {
    "scenario": "baseline",
    "requests_total": len(requests),
    "requests_error": len(errors),
    "error_percentage": round(
        len(errors) / len(requests) * 100, 2
    ),
    "outage_error_percentage": round(
        sum(r["outcome"] == "error" for r in outage_requests)
        / len(outage_requests) * 100, 2
    ) if outage_requests else None,
    "upgrade_elapsed_seconds": upgrade_time,
    "recovery_intervention_elapsed_seconds": recovery_time,
    "first_failure_elapsed_seconds": (
        first_failure["elapsed_seconds"]
        if first_failure else None
    ),
    "first_recovery_elapsed_seconds": (
        first_success_after_recovery["elapsed_seconds"]
        if first_success_after_recovery else None
    ),
    "time_to_failure_seconds": (
        round(
            first_failure["elapsed_seconds"] - upgrade_time, 3
        ) if first_failure else None
    ),
    "time_to_recovery_seconds": (
        round(
            first_success_after_recovery["elapsed_seconds"]
            - first_failure["elapsed_seconds"], 3
        ) if first_failure and first_success_after_recovery else None
    ),
    "recovery_propagation_seconds": (
        round(
            first_success_after_recovery["elapsed_seconds"]
            - recovery_time, 3
        ) if recovery_time is not None
        and first_success_after_recovery else None
    )
}

with summary_file.open("w", encoding="utf-8") as file:
    json.dump(summary, file, indent=2, ensure_ascii=False)

print(json.dumps(summary, indent=2, ensure_ascii=False))
