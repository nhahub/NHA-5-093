"""Exercise a running, local MOCK API; never synthesize responses or start a target."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.contracts import ROOT, ContractError, Contracts, local_url


class Smoke:
    def __init__(self, client, *, timeout=150):
        self.client = client
        self.contracts = Contracts()
        self.api = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text(encoding="utf-8"))
        self.timeout = timeout

    def request(self, method, path, template, expected=200, payload=None):
        operation = self.api["paths"][template][method.lower()]
        if payload is not None:
            schema = operation["requestBody"]["content"]["application/json"]["schema"]
            self.contracts.validate_schema(schema, payload, "request")
        response = self.client.request(method, path, json=payload)
        if response.status_code != expected:
            raise ContractError(
                f"{method} {template}: expected {expected}, got {response.status_code}"
            )
        content_type = response.headers.get("content-type", "").split(";")[0]
        if content_type != "application/json":
            raise ContractError(f"Unexpected media type for {template}")
        value = response.json()
        schema = operation["responses"][str(expected)]["content"]["application/json"]["schema"]
        self.contracts.validate_schema(schema, value, template)
        return value

    def collection(self, run_id, kind):
        template = f"/api/v1/runs/{{run_id}}/{kind}"
        result, cursor, seen = [], None, set()
        for _ in range(100):
            path = f"/api/v1/runs/{run_id}/{kind}?limit=100"
            if cursor is not None:
                path += "&cursor=" + str(cursor)
            page = self.request("GET", path, template)
            result.extend(page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                return result
            if cursor in seen:
                raise ContractError("Pagination cursor repeated")
            seen.add(cursor)
        raise ContractError("Pagination exceeded smoke limit")

    def wait(self, run_id):
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            detail = self.request("GET", f"/api/v1/runs/{run_id}", "/api/v1/runs/{run_id}")
            if detail["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
                if detail["status"] != "COMPLETED":
                    raise ContractError("Mock run did not complete successfully")
                return detail
            time.sleep(0.2)
        raise ContractError("Mock run exceeded polling deadline; no automatic retry")

    def workflow(self):
        if os.environ.get("HG_ALLOW_TEST_REVIEWS") != "1":
            raise ContractError("Full workflow requires an explicitly isolated mock review fixture")
        batch_config = self.contracts.fixture("BatchCreate")
        batch_config["method"] = "FIXED"
        batch = self.request("POST", "/api/v1/batches", "/api/v1/batches", 202, batch_config)
        if batch["status"] != "QUEUED":
            raise ContractError("Batch creation must return QUEUED")
        run_id = batch["run_ids"][0]
        detail = self.wait(run_id)
        if not detail["config"]["model_settings"]["model_id"].startswith("mock-") or not detail[
            "resolved_versions"
        ]["target_model_id"].startswith("mock-"):
            raise ContractError("Golden fixture workflow requires explicit MOCK models")
        if detail["outcome"] != "PROPOSED_FINDING":
            raise ContractError("Golden mock must propose the canary finding")
        limits = detail["config"]["limits"]
        if (
            detail["used_candidate_turns"] > limits["max_candidate_turns"]
            or detail["used_total_tokens"] > limits["max_total_tokens"]
        ):
            raise ContractError("Recorded budget exceeded")
        events = self.collection(run_id, "events")
        seqs = [event["seq"] for event in events]
        if seqs != list(range(1, len(events) + 1)):
            raise ContractError("Events must begin at 1 and be sequential")
        if len({event["event_id"] for event in events}) != len(events):
            raise ContractError("Duplicate event IDs")
        turns = [e for e in events if e["event_type"] == "TURN"]
        checks = [e for e in events if e["event_type"] == "CHECK"]
        if not turns or any(
            not any(
                c["turn_index"] == turn["turn_index"] and c["seq"] > turn["seq"] for c in checks
            )
            for turn in turns
        ):
            raise ContractError("Every returned turn requires a persisted check")
        for event in events:
            if event["event_type"] in {"TURN", "DECISION"}:
                usage = event["data"]["usage"]
                if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
                    raise ContractError("Token accounting mismatch")
        # Stable terminal snapshots make read-only monitoring observable without racing the worker.
        if events != self.collection(run_id, "events"):
            raise ContractError("Terminal GET monitoring mutated the event stream")
        findings = self.collection(run_id, "findings")
        if not findings or any(f["reviewer_status"] != "PENDING" for f in findings):
            raise ContractError("Golden findings must await human review")
        finding = findings[0]
        if not finding["proposal"]["evidence_spans"]:
            raise ContractError("Golden canary finding requires a nonempty target span")
        by_id = {e["event_id"]: e for e in events}
        for event_id in finding["proposal"]["evidence_event_ids"]:
            if event_id not in by_id or by_id[event_id]["event_type"] != "TURN":
                raise ContractError("Finding must reference target TURN evidence")
        replies = [
            by_id[key]["data"]["target_response"]
            for key in finding["proposal"]["evidence_event_ids"]
        ]
        canary = self.contracts.fixture("PolicyRule")["forbidden_value"]
        for span in finding["proposal"]["evidence_spans"]:
            match = re.fullmatch(r"target_response\[(\d+):(\d+)\]", span)
            if not match or not any(
                reply[int(match[1]) : int(match[2])] == canary for reply in replies
            ):
                raise ContractError("Golden canary span does not match target output")
        retest_config = self.contracts.fixture("RetestCreate")
        retest_config["original_run_id"] = run_id
        self.request("POST", "/api/v1/retests", "/api/v1/retests", 409, retest_config)
        if os.environ.get("HG_ALLOW_TEST_REVIEWS") != "1":
            raise ContractError(
                "Full review fixture requires HG_ALLOW_TEST_REVIEWS=1 on an isolated mock instance"
            )
        # Simulates a human test fixture; never an agent tool or live evaluation review.
        review = self.contracts.fixture("ReviewCreate")
        review["idempotency_key"] = f"review-{finding['finding_id']}-1"
        review_path = f"/api/v1/findings/{finding['finding_id']}/reviews"
        receipt = self.request(
            "POST", review_path, "/api/v1/findings/{finding_id}/reviews", 201, review
        )
        duplicate = self.request(
            "POST", review_path, "/api/v1/findings/{finding_id}/reviews", 201, review
        )
        if receipt != duplicate:
            raise ContractError("Review idempotency did not preserve the receipt")
        updated = self.collection(run_id, "findings")
        current = next(f for f in updated if f["finding_id"] == finding["finding_id"])
        if current["proposal"] != finding["proposal"] or current["reviewer_status"] != "CONFIRMED":
            raise ContractError("Review must preserve proposal and update its projection")
        retest = self.request("POST", "/api/v1/retests", "/api/v1/retests", 202, retest_config)
        if retest["status"] != "QUEUED":
            raise ContractError("Retest must queue")
        retest_detail = self.wait(retest["retest_run_id"])
        expected = copy.deepcopy(detail["config"])
        expected["target_version"] = "hardened-v1"
        if retest_detail["config"] != expected:
            raise ContractError("Retest changed settings beyond target version")
        view = self.request(
            "GET", f"/api/v1/retests/{retest['retest_id']}", "/api/v1/retests/{retest_id}"
        )
        if view["status"] != "COMPLETED" or view["result"] is None:
            raise ContractError("Retest did not expose completed result")
        result = view["result"]
        verdicts = {
            "PASS": "MITIGATION_VERIFIED",
            "FAIL": "VULNERABILITY_PERSISTS",
            "INCONCLUSIVE": "RETEST_INCONCLUSIVE",
        }
        if result["verdict"] != verdicts[result["status_after"]]:
            raise ContractError("Retest verdict mismatch")
        report = self.request(
            "GET", f"/api/v1/reports/{batch['batch_id']}", "/api/v1/reports/{batch_id}"
        )
        for metric, numerator, denominator in (
            (
                "finding_precision",
                report["confirmed_findings"],
                report["metric_denominators"]["all_reviewed_flags"],
            ),
            (
                "false_positive_rate",
                report["rejected_flags"],
                report["metric_denominators"]["all_reviewed_flags"],
            ),
            (
                "completion_rate",
                report["completed_runs"],
                report["metric_denominators"]["all_scheduled_runs"],
            ),
        ):
            expected_ratio = numerator / denominator if denominator else None
            if report[metric] != expected_ratio:
                raise ContractError(f"Report calculation mismatch: {metric}")
        for fmt, media in (("csv", "text/csv"), ("md", "text/markdown")):
            response = self.client.get(f"/api/v1/reports/{batch['batch_id']}?format={fmt}")
            if (
                response.status_code != 200
                or not response.content
                or response.headers.get("content-type", "").split(";")[0] != media
            ):
                raise ContractError(f"Invalid {fmt} export")
        return {
            "batch_id": batch["batch_id"],
            "run_id": run_id,
            "retest_run_id": retest["retest_run_id"],
            "mode": "MOCK",
            "scope": "API smoke; browser, restart, live model and full evaluation remain separate gates",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--workflow", action="store_true")
    args = parser.parse_args()
    with httpx.Client(
        base_url=local_url(args.base_url), timeout=10, trust_env=False, follow_redirects=False
    ) as client:
        smoke = Smoke(client)
        smoke.request("GET", "/health", "/health")
        smoke.request("GET", "/api/v1/config", "/api/v1/config")
        if not args.workflow:
            print("PASS: health/config only; full runtime workflow NOT VERIFIED")
            return
        result = smoke.workflow()
    result["commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    result["working_tree_dirty"] = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    result["recorded_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    digest = hashlib.sha256()
    for path in sorted((ROOT / "contracts").rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    result["contract_digest"] = digest.hexdigest()
    result["contract_descriptor"] = smoke.api["info"]
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "mock-smoke.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: local mock API workflow; evidence in artifacts/mock-smoke.json")


if __name__ == "__main__":
    try:
        main()
    except (ContractError, httpx.HTTPError, KeyError, ValueError) as exc:
        print(
            f"FAILED: {type(exc).__name__}; inspect the local service and contract checks",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
