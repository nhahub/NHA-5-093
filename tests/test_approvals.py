from scripts.check_approvals import branch_errors, owner, review_errors

TEAM = {f"M{i}": {"github": f"member{i}"} for i in range(1, 7)}


def test_branches_follow_assigned_member_and_cannot_impersonate_another_role():
    assert not branch_errors("feat/m2-fixed-runner", "member2", TEAM)
    assert branch_errors("feat/m3-fixed-runner", "member2", TEAM)
    assert branch_errors("main", "member1", TEAM)
    assert branch_errors("feat/m2-fixed-runner", "unassigned", TEAM)


def review(login, state="APPROVED", sha="head", identifier=1):
    return {
        "id": identifier,
        "user": {"login": login, "type": "User"},
        "state": state,
        "commit_id": sha,
    }


def errors(files, author, reviews, team=TEAM):
    return review_errors(files, author, "head", reviews, team, {f"member{i}" for i in range(1, 7)})


def test_m1_cannot_self_approve():
    assert errors(["infra/compose.yaml"], "member1", [review("member1")])


def test_m1_needs_independent_reviewer():
    assert not errors(["scripts/dev.py"], "member1", [review("member2")])


def test_cross_owner_needs_both_m1_and_affected_owner():
    assert errors(["services/api/target/a.py"], "member2", [review("member1")])
    assert errors(["services/api/target/a.py"], "member2", [review("member3")])
    assert not errors(
        ["services/api/target/a.py"],
        "member2",
        [review("member1"), review("member3", identifier=2)],
    )


def test_old_approval_and_dismissed_approval_do_not_count():
    assert errors(["scripts/dev.py"], "member1", [review("member2", sha="old")])
    assert errors(
        ["scripts/dev.py"],
        "member1",
        [review("member2"), review("member2", state="DISMISSED", identifier=2)],
    )


def test_comment_does_not_erase_approval():
    assert not errors(
        ["scripts/dev.py"],
        "member1",
        [review("member2"), review("member2", state="COMMENTED", identifier=2)],
    )


def test_unassigned_owner_blocks_merge():
    team = {**TEAM, "M3": {"github": None}}
    assert any(
        "assignment" in error
        for error in errors(["services/api/a.py"], "member1", [review("member2")], team)
    )


def test_shared_contract_needs_every_consumer():
    assert errors(["contracts/openapi.yaml"], "member1", [review("member2")])
    assert not errors(
        ["contracts/openapi.yaml"],
        "member1",
        [review(f"member{i}", identifier=i) for i in range(2, 7)],
    )


def test_unprivileged_review_does_not_count():
    assert review_errors(["infra/a"], "member1", "head", [review("outsider")], TEAM, set())


def test_ownership_matches_nested_paths():
    assert owner("services/api/target/model.py") == "M3"
    assert owner("agents/M2-agent.md") == "M2"
    assert owner("apps/dashboard/src/app.tsx") == "M6"
    assert owner("data/heldout/manifest.json") == "M5"
