# Held-out freeze checklist

Current status: **PROPOSED_NOT_FROZEN — do not run final evaluation.**

- [ ] ADR-08 and the experiment accounting are approved by M1, M4, M5, and mentor.
- [ ] All 20 scenario records validate and are approved for execution.
- [ ] No scenario/paraphrase group overlaps DEVELOPMENT or DEMO.
- [ ] Two reviewers approve every MSA/EGY semantic-equivalence pair.
- [ ] Ten repeatability transcripts and canonical hashes are reviewed.
- [ ] Role, policy, checker, target, agent model, tokenizer, and seeds are frozen.
- [ ] Matched ADAPTIVE/FIXED budgets and accessible information are verified.
- [ ] M3 persistence provides immutable run/event/score IDs and pricing evidence.
- [ ] Human review protocol and reviewer identities are approved.
- [ ] Manifests receive canonical content hashes and `FROZEN_APPROVED` only after
      the approvals above are recorded.
- [ ] Any post-freeze change creates a new version and is labeled non-comparable.
