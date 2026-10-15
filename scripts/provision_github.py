"""Idempotently create the authorized M1 backlog and verify repository protection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.github_api import REPO, GitHub, GitHubError

ROOT = Path(__file__).resolve().parents[1]


def verify_protection(actual, contexts):
    reviews = actual.get("required_pull_request_reviews", {})
    checks = actual.get("required_status_checks", {})
    if not all(
        (
            actual.get("enforce_admins", {}).get("enabled"),
            reviews.get("required_approving_review_count", 0) >= 1,
            reviews.get("dismiss_stale_reviews"),
            reviews.get("require_last_push_approval"),
            checks.get("strict"),
            set(contexts).issubset(checks.get("contexts", [])),
            actual.get("required_conversation_resolution", {}).get("enabled"),
            not actual.get("allow_force_pushes", {}).get("enabled", True),
            not actual.get("allow_deletions", {}).get("enabled", True),
        )
    ):
        raise GitHubError("Protection readback does not enforce the complete requested policy")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backlog", action="store_true")
    parser.add_argument("--protect", action="store_true")
    args = parser.parse_args()
    api = GitHub()
    base = f"/repos/{REPO}"
    repo = api.request("GET", base)
    print(
        f"Repository: {REPO}; private={repo['private']}; admin={repo.get('permissions', {}).get('admin', False)}"
    )
    if args.backlog:
        milestones = {item["title"]: item for item in api.pages(base + "/milestones?state=all")}
        issues = {
            item["title"]: item
            for item in api.pages(base + "/issues?state=all")
            if "pull_request" not in item
        }
        tasks = json.loads((ROOT / "infra/backlog.json").read_text(encoding="utf-8"))
        for task in tasks:
            title = f"{task['id']}: {task['title']}"
            milestone = milestones.get(title)
            if not milestone:
                milestone = api.request(
                    "POST",
                    base + "/milestones",
                    {"title": title, "description": task["acceptance"]},
                )
            body = "\n\n".join(
                f"**{label}:** {task[key]}"
                for label, key in (
                    ("Owners", "owners"),
                    ("Allowed paths", "paths"),
                    ("Dependencies", "dependencies"),
                    ("Contracts / FR-AC mapping", "contracts"),
                    ("Acceptance", "acceptance"),
                    ("Evidence", "evidence"),
                )
            )
            body += "\n\nBranch: `feat/m1-task-name`. M2-M6 implement their own modules. Original FR/AC mapping is pending source recovery. No approvals or completion are implied by this issue."
            if title not in issues:
                issue = api.request(
                    "POST",
                    base + "/issues",
                    {
                        "title": title,
                        "body": body,
                        "milestone": milestone["number"],
                        "assignees": ["WalidAbdelmeguid"],
                    },
                )
            else:
                issue = issues[title]
            print(f"BACKLOG: {issue['html_url']}")
    if args.protect:
        contexts = ["quality-gate"]
        try:
            api.request("GET", base + "/contents/scripts/check_approvals.py?ref=main")
            contexts.append("ownership")
        except GitHubError as exc:
            if "HTTP 404" not in str(exc):
                raise
            print(
                "PENDING: trusted ownership check cannot be required until foundation is merged to main"
            )
        protection = {
            "required_status_checks": {"strict": True, "contexts": contexts},
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
                "required_approving_review_count": 1,
                "require_last_push_approval": True,
            },
            "restrictions": None,
            "required_conversation_resolution": True,
            "allow_force_pushes": False,
            "allow_deletions": False,
        }
        try:
            api.request("PUT", base + "/branches/main/protection", protection)
            actual = api.request("GET", base + "/branches/main/protection")
        except GitHubError as exc:
            print(f"PENDING: protection not established: {exc}")
            return 2
        verify_protection(actual, contexts)
        print(
            "VERIFIED: main protection; required checks: "
            + ", ".join(actual["required_status_checks"]["contexts"])
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GitHubError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
