<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the relation matrix (25 sites) and its verdicts

Every versioned edge between packages of the coordinated set, with the value it takes and the
verdicts `dpkg --compare-versions` must return. Line numbers were measured 2026-10-15 at each
repository's start commit (research R1). **Re-grep before editing.** This is the planning
document's §4, re-measured, and amended by research R2.

## Targets

| Package | Target | Floor token used by consumers |
|---|---|---|
| `cuems-utils` | `0.1.1` | `>= 0.1.1`, ceiling `<< 0.1.2~` |
| `cuems-common` | `1.3.1-1` | `>= 1.3.1~`; `Breaks: << 1.3.1~` |
| `cuems-nodeconf` | `0.1.1-1` | `Breaks: << 0.1.1~` |
| `cuems-power-bridge` | **`0.4.0-1`** (2026-10-16; was `0.3.2-1`, research R2a) | `Breaks: << 0.4.0~` |
| `cuems-engine` | `0.1.1-1` | `>= 0.1.1` (its own `-mock` package) |
| `cuems-editor` | `0.1.1-1` | — (no package depends on it) |
| `cuems-frontend` | **`0.2.0`** (2026-10-16; was `0.1.0`, research R2b) | — (not packaged) |

Row 25 is not a version move. It is a missing relation declared at the released version, so it
has no "Today" value and no fail-before verdict: it is absent before.

## Sites

| # | Repo | File:line | Today | Becomes |
|---|---|---|---|---|
| 1 | `cuems-utils` | `debian/control:23` | `Breaks: cuems-common (<< 1.3.0-23~)` | `(<< 1.3.1~)` + rewrite the comment at `:15-22` |
| 2 | `cuems-common` | `debian/control:12` | `cuems-utils (>= 0.1.0rc16)` | `(>= 0.1.1)` |
| 3 | `cuems-common` | `debian/control:13` | `cuems-utils (<< 0.1.1~)` | `(<< 0.1.2~)` |
| 4 | `cuems-common` | `debian/control:57` | `Breaks: cuems-nodeconf (<< 0.1.0-8)` | `(<< 0.1.1~)` |
| 5 | `cuems-common` | `debian/control:58` | `cuems-power-bridge (<< 0.3.1-1)` | `(<< 0.4.0~)` — research R2, R2a |
| 6 | `cuems-engine` | `debian/control:26` (`:30` at `e994a5e`) | `cuems-utils (>= 0.1.0rc16)` | `(>= 0.1.1)` |
| 7 | `cuems-engine` | `debian/control:27` (`:31` at `e994a5e`) | `cuems-utils (<< 0.1.1~)` | `(<< 0.1.2~)` |
| 8 | `cuems-engine` | `debian/control:28` (`:32` at `e994a5e`) | `cuems-common (>= 1.3.0-23~)` | `(>= 1.3.1~)` + comment `:20-21` |
| 9 | `cuems-engine` | `debian/control:49` (`:54` at `e994a5e`) | `cuems-engine (>= 0.1.0rc2)` (the `-mock` binary) | `(>= 0.1.1)` |
| 10 | `cuems-engine` | `pyproject.toml:50` | `cuemsutils = ">=0.1.0rc16,<0.1.1"` | `">=0.1.1,<0.1.2"` |
| 11 | `cuems-editor` | `debian/control:18` | `cuems-utils (>= 0.1.0rc16)` | `(>= 0.1.1)` |
| 12 | `cuems-editor` | `debian/control:19` | `cuems-utils (<< 0.1.1~)` | `(<< 0.1.2~)` |
| 13 | `cuems-editor` | `debian/control:20` | `cuems-common (>= 1.0.0)` — stale | `(>= 1.3.1~)` |
| 14 | `cuems-editor` | `pyproject.toml:23` | `"cuemsutils>=0.1.0rc16,<0.1.1"` | `"cuemsutils>=0.1.1,<0.1.2"` |
| 15 | `cuems-nodeconf` | `debian/control:18` | `cuems-utils (>= 0.1.0rc16)` | `(>= 0.1.1)` |
| 16 | `cuems-nodeconf` | `debian/control:19` | `cuems-utils (<< 0.1.1~)` | `(<< 0.1.2~)` |
| 17 | `cuems-nodeconf` | `debian/control:20` | `cuems-common (>= 1.0.0)` — stale | `(>= 1.3.1~)` |
| 18 | `cuems-nodeconf` | `debian/control:28` | `Breaks: cuems-common (<< 1.3.0-23~)` | `(<< 1.3.1~)` |
| 19 | `cuems-nodeconf` | `pyproject.toml:28` | `cuemsutils = ">=0.1.0rc16,<0.1.1"` | `">=0.1.1,<0.1.2"` |
| 20 | `cuems-power-bridge` | `debian/control:18` | `cuems-utils (>= 0.1.0rc16)` | `(>= 0.1.1)` |
| 21 | `cuems-power-bridge` | `debian/control:19` | `cuems-utils (<< 0.1.1~)` | `(<< 0.1.2~)` |
| 22 | `cuems-power-bridge` | `debian/control:20` | `cuems-common (>= 1.3.0-23)` | `(>= 1.3.1~)` |
| 23 | `cuems-power-bridge` | `debian/control:25` | `Breaks: cuems-common (<< 1.3.0-23)` | `(<< 1.3.1~)` |
| 24 | `cuems-power-bridge` | `pyproject.toml:38` | `cuemsutils = ">=0.1.0rc16,<0.1.1"` | `">=0.1.1,<0.1.2"` |
| 25 | `cuems-engine` | `debian/control:35` at `e994a5e` (inserted after `python3-pyossia`) | — (undeclared; `libmtc.py` loads `libmtcmaster.so.0`) | `libmtcmaster (>= 0.0.2-0)` — the published release, no bump (spec FR-023) |

**Unchanged on purpose** (recorded, not edited), each with an owner:

| Site | Value | Why / owner |
|---|---|---|
| `cuems-common/debian/control:49` | `Suggests: cuems-power-bridge` (unversioned) | 010 T077's decision |
| `cuems-engine/debian/control:30` | `python3-pyossia (>= 2.0.0-rc6+124+cuems3)` | libossia is an independent input (FR-023); moves with libossia's next release |
| `cuems-engine/pyproject.toml:84` | dev-group `pyossia` wheel URL (`cuems3`) | moves **together with** `:30`; libossia |
| `cuems-engine/poetry.lock` | still resolves `cuemsutils 0.1.0rc16` | FR-022: relock at publication; strict-xfail test guards it |
| `libmtcmaster` `debian/control` | `Depends: … cuems-utils` (unversioned) | libmtcmaster maintainers (engine doc §4.4) |
| `iproute2`, `procps` | undeclared, `Priority: important` | engine (engine doc §4.6) |
| `rtpmidid` fork | tag `v26.06-1stagelab1` vs package `26.01~1~g7f552` | rtpmidid fork (engine doc §4.4) |

**Ordering inside a commit**: the relations are the last edit in each repository's bump (planning
document §11 step 6), so the version and its relations land in one commit.

## Verdicts (each one is evidence, written to `evidence/relation-verdicts.txt`)

`A` = must be admitted, `R` = must be refused, by the conjunction of the relations on that edge.

| Edge | `R` | `A` |
|---|---|---|
| consumers → `cuems-utils` (sites 2–3, 6–7, 10–12, 14–16, 19–21, 24) | `0.1.0rc16`, `0.1.0rc16+1`, `0.1.0rc17`, `0.1.0`, `0.1.1~rc1`, `0.1.2~rc1`, `0.1.2`, `0.2.0` | `0.1.1`, `0.1.1-1`, `0.1.1+b1` |
| `cuems-utils` `Breaks:` `cuems-common` (site 1) | breaks `1.3.0-22`, `1.3.0-23`, `1.3.0-24`, `1.3.0-25` | does not break `1.3.1~rc1`, `1.3.1-1` |
| consumers → `cuems-common` (8, 13, 17, 22) | `1.0.0`, `1.3.0-23`, `1.3.0-25` | `1.3.1-1` |
| `Breaks:` `cuems-common` (18, 23) | breaks `1.3.0-25` | does not break `1.3.1-1` |
| `cuems-common` `Breaks:` `cuems-nodeconf` (4) | breaks `0.1.0-8`, `0.1.0-9` | does not break `0.1.1~rc1`, `0.1.1-1` |
| `cuems-common` `Breaks:` `cuems-power-bridge` (5) | breaks `0.3.0-11`, `0.3.1-1`, `0.3.1-2`, `0.3.2-1`, `0.3.2-2` | does not break `0.4.0-1` |
| `cuems-engine-mock` → `cuems-engine` (9) | `0.1.0rc6-5` | `0.1.1-1` |
| `cuems-engine` → `libmtcmaster` (25) | `0.0.1-1`, `0.0.2~rc1` | `0.0.2-0`, `0.0.2-1` |

Python bounds (sites 10, 14, 19, 24) are judged with `packaging.specifiers.SpecifierSet` on the
same upstream versions: `0.1.0rc17` refused, `0.1.1` admitted, `0.1.2rc1` refused. Under PEP 440,
`<0.1.2` excludes pre-releases of `0.1.2` by default.
