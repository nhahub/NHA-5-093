import copy

import pytest

from scripts.github_api import GitHubError
from scripts.provision_github import verify_protection


def policy():
    return {
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_last_push_approval": True,
        },
        "required_status_checks": {"strict": True, "contexts": ["quality-gate"]},
        "required_conversation_resolution": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }


def test_protection_verifies_server_state_not_only_success_status():
    verify_protection(policy(), ["quality-gate"])
    for key in policy():
        incomplete = copy.deepcopy(policy())
        del incomplete[key]
        with pytest.raises(GitHubError):
            verify_protection(incomplete, ["quality-gate"])
    with pytest.raises(GitHubError):
        verify_protection(policy(), ["quality-gate", "ownership"])
