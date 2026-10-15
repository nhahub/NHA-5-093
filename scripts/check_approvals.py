"""Trusted-base PR approval policy. Never import or execute PR-head code."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.github_api import REPO, GitHub, GitHubError

ROOT = Path(__file__).resolve().parents[1]


def owner(path):
    for prefix, role in (
        ("services/engine/", "M2"),
        ("services/api/", "M3"),
        ("target/", "M3"),
        ("packages/security/", "M4"),
        ("packages/evaluation/", "M5"),
        ("data/", "M5"),
        ("apps/dashboard/", "M6"),
    ):
        if path.startswith(prefix):
            return role
    if path.startswith("agents/M") and len(path) > 8:
        return path[7:9]
    return "M1"


def review_errors(files, author, head_sha, reviews, team, writers):
    latest = {}
    for review in sorted(reviews, key=lambda item: item["id"]):
        login = review["user"]["login"].lower()
        if review["state"] != "COMMENTED":
            latest[login] = review
    approved = {
        login
        for login, review in latest.items()
        if review["state"] == "APPROVED"
        and review["commit_id"] == head_sha
        and login in writers
        and login != author.lower()
        and review["user"].get("type") != "Bot"
    }
    errors = []
    if not approved:
        errors.append("An independent write-authorized reviewer must approve the current head")
    if any(r["state"] == "CHANGES_REQUESTED" for login, r in latest.items() if login in writers):
        errors.append("Outstanding changes requested by a write-authorized reviewer")
    roles = {owner(path) for path in files}
    # Shared transport/tool/interface changes affect all producers and consumers.
    if any(path.startswith("contracts/") for path in files):
        roles.update(team)
    for role in roles:
        login = (team.get(role, {}).get("github") or "").lower()
        if not login:
            errors.append(f"{role} GitHub assignment is pending")
        elif login != author.lower() and login not in approved:
            errors.append(f"{role} owner approval is required on the current head")
    if any(
        owner(path)
        != next((r for r, v in team.items() if (v["github"] or "").lower() == author.lower()), None)
        for path in files
    ):
        lead = (team["M1"]["github"] or "").lower()
        if lead != author.lower() and lead not in approved:
            errors.append("Cross-owner edits require M1 approval")
    return sorted(set(errors))


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    api = GitHub()
    number = event.get("pull_request", event.get("issue", {})).get("number")
    if not isinstance(number, int):
        raise GitHubError("Pull request number missing")
    if "comment" in event:
        sender = event["sender"]["login"]
        permission = api.request("GET", f"/repos/{REPO}/collaborators/{sender}/permission")
        if event["comment"]["body"] != "/check-ownership" or permission["permission"] not in {
            "admin",
            "write",
            "maintain",
        }:
            raise GitHubError("Only write-authorized members may refresh ownership")
    base = f"/repos/{REPO}/pulls/{number}"
    pr = api.request("GET", base)
    if pr["base"]["ref"] != "main":
        raise GitHubError("Ownership status is defined only for pull requests into main")
    status_path = f"/repos/{REPO}/statuses/{pr['head']['sha']}"
    api.request(
        "POST",
        status_path,
        {
            "state": "pending",
            "context": "ownership",
            "description": "Checking current-head owner and independent approvals",
        },
    )
    team = json.loads((ROOT / "infra/team.json").read_text(encoding="utf-8"))
    changes = api.pages(base + "/files")
    if len(changes) != pr["changed_files"]:
        raise GitHubError("Incomplete file list; approval cannot be established")
    files = {item["filename"] for item in changes}
    files.update(item["previous_filename"] for item in changes if "previous_filename" in item)
    reviews = api.pages(base + "/reviews")
    writers = set()
    for login in {item["user"]["login"].lower() for item in reviews}:
        permission = api.request("GET", f"/repos/{REPO}/collaborators/{login}/permission")
        if permission["permission"] in {"admin", "write", "maintain"}:
            writers.add(login)
    errors = review_errors(files, pr["user"]["login"], pr["head"]["sha"], reviews, team, writers)
    if api.request("GET", base)["head"]["sha"] != pr["head"]["sha"]:
        raise GitHubError("Head changed while checking approvals; rerun on the current head")
    api.request(
        "POST",
        status_path,
        {
            "state": "failure" if errors else "success",
            "context": "ownership",
            "description": "Required approvals pending"
            if errors
            else "Independent and affected-owner approvals verified",
        },
    )
    for error in errors:
        print(f"PENDING: {error}")
    if not errors:
        print("PASS: current-head independent and affected-owner approvals")
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GitHubError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
