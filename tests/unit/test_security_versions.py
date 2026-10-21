from packages.security import CHECKER_VERSION, POLICY_VERSION


def test_checker_version_frozen():
    assert CHECKER_VERSION == "m4-checks-1.0.0"


def test_policy_version_frozen():
    assert POLICY_VERSION == "m4-policy-1.0.0"
