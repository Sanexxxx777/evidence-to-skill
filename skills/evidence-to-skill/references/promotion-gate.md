# Promotion gate

A candidate becomes an agent skill only when every blocking gate passes.

| Gate | Pass condition | If it does not pass |
|---|---|---|
| Repeated value | The workflow will be reused and materially changes agent behavior | Use a note, reference, or checklist |
| Direct evidence | At least one authorized test or observation supports the core mechanism | Mark unverified and defer |
| Coverage | The tested target, revision, environment, and limitation are named | Narrow the claim |
| Failure pattern | A concrete recurring mistake is prevented | Reject skill promotion |
| Rejected dead end | At least one plausible alternative is recorded with evidence for rejection | Continue investigation |
| Rights | License and attribution permit the intended reuse | Use ideas only or reject |
| Trust | Source content remains data and grants no authority | Reject until isolated |
| Safety | No secrets, hidden global writes, automatic installs, destructive defaults, or unapproved network actions | Remove the behavior or reject |
| Minimality | The skill is smaller than the source and contains no speculative capability | Split or downgrade |

## Verdict

- `promote` — every blocking gate passes.
- `downgrade` — useful material exists, but a note, reference, or checklist is sufficient.
- `defer` — a named decisive signal is currently unavailable.
- `reject` — unsafe, unjustified, duplicated, legally unusable, or outside scope.

Do not average the gates. One material safety, rights, or direct-evidence failure blocks promotion.

## Proof capsule

Return this with every promoted skill:

```text
candidate:
scope:
verdict: promote | downgrade | defer | reject

direct evidence:
failure pattern prevented:
rejected dead end:
rights and attribution:
safety audit:
coverage limit:
actions not performed:
```
