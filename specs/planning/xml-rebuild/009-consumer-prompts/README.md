# Feature 009 — consumer migration: the per-repository prompt set

**Status:** ready to run
**Date:** 2026-09-03
**Parent:** [Part 4 §8](../xml-rebuild-07-speckit-prompts.md) is the cross-repo
prompt; [Part 6](../xml-rebuild-09-consumer-audit.md) (`C1`–`C11`) is its
call-site evidence. This directory is those two, **cut per repository**, so each
consumer can run its own spec-kit flow from its own checkout without reading the
other six.

## Why one file per repository

Part 4 §8 is a single cross-repo prompt. That worked as a *plan* and does not
work as an *instruction*: seven repositories are involved, five of them have no
spec-kit installed at all, three sit on different base branches, four have
different test runners, and one is Angular. A single `/speckit.specify` run
cannot be pasted into any of them unmodified — the CONTEXT paths do not resolve
outside `cuems-utils`, and the constitution it checks does not exist in five of
the seven.

Each file here is **self-contained and runnable as-is** from its repository's
current state: branch and bootstrap first, then a constitution step, then the
full `specify → clarify → plan → tasks → checklist → analyze → implement` chain,
then that repository's own exit criteria.

## Every repository branches to the same name

**`feat/xml-refactor`**, in all seven — matching `cuems-utils`'s own branch for
this work. Each file's §1 carries the exact base for its repository, because
they differ: three are on a release branch, one on a feature branch, two on
`main`, and one already has `feat/xml-refactor` checked out with feature 007's
work on it.

## Run order

The dependency chain, and the reason for it. Everything not chained runs in
parallel.

| # | File | Repository | Gated on | Why |
|---|---|---|---|---|
| 00 | [00-cuems-utils.md](00-cuems-utils.md) | `cuems-utils` | — | D34's public descriptor path through `ConfigManager`. **Precondition** of 02 and 05; nothing consumer-side can be written against an internal module. |
| 01 | [01-cuems-engine.md](01-cuems-engine.md) | `cuems-engine` | — | Node-role readers, the show-load path, the dead fade handlers. Independent of 00. |
| 02 | [02-cuems-editor.md](02-cuems-editor.md) | `cuems-editor` | 00 | Starts by fixing an import that stops the process today (C2), then the five parser sites, then serves the descriptor 00 published. |
| 03 | [03-cuems-common.md](03-cuems-common.md) | `cuems-common` | pairs with 04 | Postinst ordering, packaging gate edges, and **half** of the Avahi cutover. |
| 04 | [04-cuems-nodeconf.md](04-cuems-nodeconf.md) | `cuems-nodeconf` | pairs with 03 | The network-map object swap, and the **other half** of the Avahi cutover. |
| 05 | [05-cuems-frontend.md](05-cuems-frontend.md) | `cuems-frontend` | 00, 02 | Characterization tests first (D35), then the template and config-domain ports. The largest single port. |
| 06 | [06-cuems-wsclient.md](06-cuems-wsclient.md) | `cuems-wsclient` | — | The sixth consumer nobody had listed (C1). Fully independent — **last by dependency, first by severity**; see below. |

**03 and 04 are one cutover, not two features that happen to be adjacent.** The
Avahi TXT record is the wire between a publisher in `cuems-nodeconf` and a
listener in the same repo, against templates shipped by both — D33 forbids a
half-renamed intermediate state. Their specs are separate because the
repositories are; their *merges* are simultaneous.

**Nothing releases until all seven are done** (D27, extending 007's
FR-030c/FR-030d). These are seven spec-kit flows, one release.

**Run 06 first anyway.** It is last in the dependency order because nothing waits
on it, but tracing `slave_avahi_names` into its only caller turned C1 from "a
silently wrong filter" into something sharper: `cuems-wsclient`'s power bridge
resolves its shutdown targets through that filter, so post-007 it resolves
**zero** nodes, skips the reachability poll entirely (`if resolved:`), and then
arms the Shelly relay that cuts mains power — to a cluster of machines nothing
ever told to shut down. It logs `"0 nodes to power off: (none)"` at INFO. No test
could have caught it: that repository has no `tests/` directory at all, while its
`pyproject.toml` configures one. It is the cheapest flow here and the one whose
current state is worst.

## Bootstrap: five of seven have no spec-kit

Measured 2026-09-03:

| Repository | `.specify/` | `.claude/skills/speckit-*` | Constitution | On first run |
|---|---|---|---|---|
| `cuems-utils` | yes | 9 skills | yes (1.0.0) | check, do not amend |
| `cuems-engine` | yes | 14 skills (incl. `speckit-git-*`) | yes | check, do not amend |
| `cuems-editor` | **no** | **no** | **no** | `specify init` + `/speckit.constitution` |
| `cuems-common` | **no** | **no** | **no** | `specify init` + `/speckit.constitution` |
| `cuems-nodeconf` | **no** | **no** | **no** | `specify init` + `/speckit.constitution` |
| `cuems-frontend` | **no** | **no** | **no** | `specify init` + `/speckit.constitution` |
| `cuems-wsclient` | **no** | **no** | **no** | `specify init` + `/speckit.constitution` |

Where spec-kit is absent it is **added on the first run**, and that file
therefore carries a `/speckit.constitution` prompt grounded in what that
repository actually is — not a copy of `cuems-utils`'s. The two repositories
that already have one keep it: Part 4 §1's rule ("check, do not amend") applies
unchanged, and neither constitution needs a carve-out for this work.

`cuems-utils` was initialized with spec-kit `0.5.1.dev0` as
`specify init --here --integration claude --script sh` with sequential branch
numbering (`.specify/init-options.json`). The bootstrap blocks below use the
same options so the seven repositories stay comparable.

## Feature numbering inside each repository

Spec-kit numbers features per repository, so this one work item gets a
**different number in each**:

| Repository | Existing `specs/NNN-*` | This feature becomes |
|---|---|---|
| `cuems-utils` | 001–008 | `009-consumer-migration` |
| `cuems-engine` | 004–007 | `008-cuems-utils-migration` |
| `cuems-editor` | none | `001-cuems-utils-migration` |
| `cuems-common` | none | `001-node-role-and-conversion-ordering` |
| `cuems-nodeconf` | none | `001-network-map-object-adoption` |
| `cuems-frontend` | none | `001-schema-descriptor-migration` |
| `cuems-wsclient` | none | `001-node-role-reader` |

The **branch** is `feat/xml-refactor` everywhere regardless; only the `specs/`
directory name follows the local numbering. Where spec-kit's sequential branch
numbering wants to create its own branch, stay on `feat/xml-refactor` and let it
name the directory only — each file says so in its §1.

## The context block, and where it is authoritative

Every file carries its own CONTEXT block, with **sibling-absolute paths**
(`/disk/Projects/StageLab/cuems-utils/specs/...`) because the planning documents
live in `cuems-utils` and a relative path does not resolve from a consumer
checkout. Each block carries the subset of the settled decisions (`D1`–`D35`)
that binds that repository, plus a pointer to the full list.

**[Part 4 §2](../xml-rebuild-07-speckit-prompts.md) is authoritative for the
decision list.** These blocks are derived from it. If a decision changes, change
it there first, then propagate — and if a question arises that the local subset
does not answer, read Part 4 §2 rather than inventing an answer locally.

## Standing rules

[Part 4 §10](../xml-rebuild-07-speckit-prompts.md)'s eight standing rules bind
every one of these flows. Three matter enough in a consumer repository to be
restated in each file: never `/speckit.implement` on a red suite; commits are
GPG-signed (retry on "gpg failed to sign", never `--no-gpg-sign`); planning
artifacts stay in `specs/planning/`, feature artifacts in `specs/NNN-*/`.

Two more apply *because* this is the consumer side, and both come from 007:

- **Callers that keep resolving but become semantically wrong** (FR-030a-ii) are
  a distinct and more dangerous class than callers that stop resolving. Nothing
  fails, the suite stays green, and the answer is silently wrong. They are
  **searched for**, and each one gets a test that fails against the old value.
  `cuems-wsclient` (C1) is what this class looks like when nobody searches.
- **The node model lives in `cuemsutils` exclusively** (FR-030a-i). No consumer
  re-implements or re-tests it. A node-model test appearing in a consumer
  repository during this migration is a regression, not coverage.

## The quality loop

[Part 4 §9](../xml-rebuild-07-speckit-prompts.md), unchanged, in every
repository: `/speckit.check-integration` and `/speckit.optimize` after
`/speckit.tasks` and before `/speckit.implement`; `/speckit.verify` after.
`check-integration` earns its place here more than anywhere in the rebuild —
these are migrations, and the failure mode is writing the new call alongside the
old one instead of replacing it.
