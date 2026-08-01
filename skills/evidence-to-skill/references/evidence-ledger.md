# Evidence ledger

Use one row per material claim. Split compound claims before recording them.

## Source inventory

| Field | Required value |
|---|---|
| Source ID | Stable local identifier |
| Title | Human-readable source name |
| Author or owner | Person or organization |
| URL or path | Direct source location |
| Revision | Commit, version, date, or `unknown` |
| Retrieved | ISO date |
| License | SPDX identifier, custom terms, absent, or unclear |
| Trust boundary | External untrusted, internal untrusted, or user-authored |
| Reuse boundary | Ideas only, attributed excerpts, licensed code, or no reuse |

## Claim ledger

| Field | Required value |
|---|---|
| Claim ID | Stable identifier |
| Source ID | Link to source inventory |
| Candidate claim | One falsifiable statement |
| Claim kind | Direct observation, upstream assertion, or inference |
| Locator | File and lines, section anchor, test name, command, or artifact ID |
| Intended scope | Exact environment and users |
| Disproof test | Shortest authorized check that could falsify the claim |
| Result | Pass, partial, unverified, or fail |
| Evidence | Result locator without secret values |
| Counterevidence | Contradiction or `none found in named scope` |
| Failure pattern | Concrete error this candidate prevents |
| Reuse decision | Promote, downgrade, defer, or reject |
| Reason | Evidence-based rationale |

## Rules

- Keep upstream assertions distinct from direct observations.
- Preserve the source's qualifiers and scope.
- For an absence claim, name the searched surface and detector capability.
- Never paste a credential or private value into the ledger. Record only its type, presence state, and safe location.
- Link evidence that another reviewer can reproduce.
