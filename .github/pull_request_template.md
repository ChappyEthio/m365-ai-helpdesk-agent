## What changed and why
<!-- Link the task / user story and its acceptance criteria -->

## Checklist (author)
- [ ] Acceptance criteria met and demonstrated in DEV
- [ ] No hard-coded URLs, IDs, connections or secrets (environment variables / connection references / Key Vault)
- [ ] Flows: Try/Catch scopes, retry policy on external calls, user always gets a response
- [ ] Risky actions go through the approval step
- [ ] `pytest` and `python -m evaluation.run_eval` pass locally
- [ ] Docs/runbook updated if behaviour changed

## Reviewer
- [ ] Diff of unpacked solution reviewed (flows, topics, connection references)
- [ ] Security: least-privilege permissions, no new admin consent without approval
- [ ] Cost: no new premium connectors or licences without sign-off
