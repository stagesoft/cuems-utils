# Migration guide — feature 010, consumer migration

**Status**: accumulating. This document is written **as the work lands**, not retrofitted at the
end (FR-002, FR-005). Sections are stubs until their wave closes.
**Audience**: the six consumer repositories' spec-kit flows, and whoever runs the next
ecosystem-wide sweep.
**Constitution III**: this guide is feature 010's user-experience deliverable.

Its inputs are `specs/007-node-model-migration/migration-guide.md` and
`specs/008-rebuild-extension/migration-guide.md` — both are input inventories, not background
reading.

---

## 1. What changed, entry point by entry point

*(FR-UX-001 — every removed or changed entry point mapped to its replacement, with before/after
examples, at call-site granularity, so a consumer flow can be written against this without reading
library source.)*

| Removed / changed | Replacement | Landed in |
|---|---|---|
| _(accumulates)_ | | |

## 2. The public descriptor path *(wave 0)*

*(FR-020–FR-028a. Filled by T017.)*

## 3. Per-repository obligations

*(FR-UX-004 — which obligation landed in which repository. Seven flows produce seven task lists and
no single view of the whole; this is that view.)*

| Repository | Obligation | State |
|---|---|---|
| `cuems-utils` | descriptor path · deprecated-surface removal · this guide | in progress |
| `cuems-engine` | | not started |
| `cuems-editor` | | not started |
| `cuems-common` | | not started |
| `cuems-nodeconf` | | not started |
| `cuems-frontend` | | not started |
| **`cuems-wsclient`** | | not started |

**`cuems-wsclient` is listed deliberately** (FR-UX-002). It was absent from 007's guide, 008's
guide and the cross-repo plan's repository list, and that absence is why a silently broken shutdown
path survived two features. The next sweep must reach it by construction, not by memory.

## 4. Behaviour that changes for everyone

*(FR-043d, FR-049c — widenings and new user-visible outcomes, recorded so an operator meeting one
has it documented rather than diagnosed.)*

## 5. The ecosystem-wide count

*(FR-070–FR-073a, FR-UX-003. Filled by T062. Carries the counting **method** alongside the count,
and the exempt set enumerated as `<path>:<start_line>[-<end_line>]` with its two distinct
reasons — "exists to detect or convert the retired spelling" (permanent) and "not shipped"
(removable at any time) — never merged.)*

## 6. Rollout, rollback and the release gate

*(FR-091–FR-104. Filled by T038a, T040, T041, T043–T045.)*
