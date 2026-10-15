# Repository governance verification — 2026-10-15

Repository: WalidAbdelmeguid/HireGuard (private). M1 has administrator permission.

The GitHub REST protection endpoint accepted the configuration and a subsequent
GET verified independent PR approval and administrator enforcement. Required
bootstrap check: `quality-gate`. The configured policy also requires an up-to-date
branch and resolved conversations, dismisses stale reviews, and disallows branch
force pushes/deletion.

The custom `ownership` status must be added after this foundation is merged to
main, because its trusted implementation is not on main yet. Run:

```
python scripts/provision_github.py --protect
```

Do not self-merge the foundation. Another write-authorized human must review it.
Only M1 is currently mapped; M2-M6 handles/backups and actual acknowledgments are
still pending. CODEOWNERS and code policy files are not proof that a review took
place. Milestones and issues have been created idempotently by the provisioning
script; see repository issues M1-01 through M1-08.

## Review refresh

Approval evaluation always uses main/base code and mapping. After reviews change,
a write-authorized team member comments `/check-ownership` on the PR to refresh
the status. Opening/updating/reopening the PR also evaluates it. The status is
attached to the exact head commit; an older head approval cannot satisfy it.

M1 plus affected owner must agree on cross-owner edits. Shared contract changes
require acknowledgments from all producer/consumer owners. Missing mapping fails
closed. Never use PR labels, body checkboxes or a model's assertions as approval.
