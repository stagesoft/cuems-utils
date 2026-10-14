<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Baseline — the consumer-gate closure

**Feature**: `015-consumer-gate-closure` | **Branch point**: `75a958e` | **Created**: 2026-10-13

## Measurement method

Best of three medians of five warm runs, one warm call first (schema parse and registry build
are once per process), fresh process, per `quickstart.md` §3. **Check `/proc/loadavg` first**
and wait if the 1-minute figure is above ~1.5 — skipping this produced a phantom 2× regression
during this feature's own Phase 0 (research.md R10). **Sample in more than one window** — a
single quiet window produced a wrong tolerance twice (R10).

**Interpreter build** (FR-PERF-005): `uvx hatch run test.py3.11:python -VV` resolves
`3.11.9 [Clang 18.1.8]` (python-build-standalone, via `uv`), at
`/home/adria/.local/share/hatch/env/virtual/cuemsutils/KPtCKENL/test.py3.11/bin/python`.
`sysconfig.get_config_var('CONFIG_ARGS')` reports both `optimizations` and `lto`. This is the
interpreter every figure below is measured on, unless stated otherwise.

**Tolerance**: **115%** (FR-PERF-002), settled in research.md R10 after two wrong readings from
single-window sampling (a 110% reading from one 2.9%-spread window, and an earlier phantom 2×
regression from contended samples). Pooled spread over 16 samples in three windows is 7.8%,
corroborating 014's recorded ±4–8%.

## Branch-point reference table (re-measured 2026-10-13, post-migration)

| Path | Branch point (worst observed) | Budget (115%) |
|---|---|---|
| show-document **save** | 14.297 ms | ≤ 16.4 ms |
| descriptor derivation, `script` | 1.060 ms | ≤ 1.22 ms |
| suite | 8.93 ms/test | ≤ 10.3 ms/test |
| show-document **load** | band **16.465–17.750 ms**, median 16.864, n=16 across three windows | compared against the band (FR-079a), not the straddled 16.5 ms line — 14 of 16 samples exceed it |

Two pre-migration figures (save 28.6 ms, derive 2.08 ms) are **withdrawn**, not restated as a
"before" — weaker method, contended window, an interpreter that no longer exists to re-measure
on (research.md R10).

## Branch-point suite (T002, confirmed 2026-10-13)

```
5 failed, 3565 passed, 113 skipped, 2 xfailed in 36.42s
```

The five failures, all attributed to this feature (SC-TEST-002):

| Test | Cause | Disposed by |
|---|---|---|
| `test_read_path_regression.py::test_the_show_document_load_is_within_its_recorded_budget` | budget straddled | FR-079 (T094/T095) |
| `test_migration_guide.py::test_the_coupled_engine_version_resolves` | 012's guide names a dead engine version | FR-080 (T100) |
| `test_migration_guide.py::test_the_engine_really_broadcasts_the_status_the_guide_tells_you_to_watch` | the named signal is gone from the engine source | FR-080 (T100) |
| `test_migration_guide_names_sites.py::…[cuems-editor]` | 013's guide pins a dead commit | FR-080 (T101) |
| `test_migration_guide_names_sites.py::…[cuems-frontend]` | same | FR-080 (T101) |

⚠ **The first run of the full suite this session reported 7 failures**, not 5: two
perf-sensitive tests in `test_descriptor_laziness.py` failed under contention (box load average
2.1–2.5 at the time). Re-running them in isolation passed cleanly, and a second full-suite run
(load average had dropped) reproduced exactly the expected five. Recorded here as the
confirming instance of R10's own lesson, not a sixth attributed failure.

## T003/T004 snapshots (captured 2026-10-13)

- `snapshots/repairability-before.txt` — 327 rows (schema, type, field, repairability, default)
  across all six schemas, for SC-005a's zero-change comparison.
- `snapshots/union-enums-before.txt` — exactly the five sites research.md and data-model.md §4
  name: `network_map.NodeType.uuid`, `settings.NodeConfType.uuid`,
  `settings.AudioPlayerType.output_latency_ms`, `settings.VideoPlayerType.output_latency_ms`,
  `project_mappings.NodeMappingType.uuid` — each reporting a one-value choice set today.

## T005 — G5's dead end (reproduced 2026-10-13)

```
/tmp/pref3.xml: skipped (would not validate: ... Unexpected child with tag 'audio_cards' at
position 3 ...)
nothing to do (1 skipped)
exit 1
```

Matches `quickstart.md` §4 exactly. This is the red state US3 inverts.

## G5 (US3) — SC-003/SC-004, measured against the restored population

11 documents restored by ref (none exist in any working tree — 014's gate pass hand-rewrote
them):
`../cuems-power-bridge@dd1256f^:tests/fixtures/network_map/map-{controller-only,incomplete,mixed,no-self,none-adopted,partial-resolve,pre007,two-adopted,unresolvable}/settings.xml`
(9) and `../cuems-nodeconf@61c5705^:tests/fixtures/etc_cuems/settings{,_sentinel}.xml` (2).

| | Control (branch point) | After the fix |
|---|---|---|
| `cuems-reshape-devices` over all 11 | 0 of 11 (each: `skipped (would not validate: ... Unexpected child with tag 'audio_cards'/'universes' ...)`) | **11 of 11 `reshaped`, one invocation** |
| Then load through `load_config_document` | n/a — never reshaped | **11 of 11 load cleanly** |

Matches SC-003 (11 of 11, against the control of 0 of 11) and SC-004 (one invocation, no
hand-rewrite). The one surviving **live** dead-end document — `../cuems-engine/dev/test_xml_files/settings.xml` —
is closed separately by T039a, in that checkout, per FR-105.

## G4 (US5) — T049, verified rather than changed

`NodeIndex.signature()` already includes `alias` (`src/cuemsutils/tools/NodeList.py:288`):
`n.get("alias")` is one of the nine tuple entries sorted by key. `set_alias` therefore needed no
change to the write-if-changed path (FR-041) — confirmed by
`test_set_alias_to_the_current_value_does_not_move_the_signature`.

---

*Sections below are filled in as each phase lands.*

## Static-quality ratchet — registered after the sweep (T136)

| Instrument | Tool (bound, T127) | Before | After | Gate from here |
|---|---|---|---|---|
| lint | ruff 0.17.0 (`>=0.17.0,<0.18`) | **606** (316 `src/` + 290 `tests/`) | **0** | **0** |
| types | mypy 2.4.0 (`>=2.4.0,<3`) | **80** | **72** | **72** |

Snapshots: `snapshots/lint-after.txt`, `snapshots/types-after.txt`; residue and reasons are in the
latter. **Re-baseline trigger**: a minor bump of either tool inside its bound may legitimately move
the count — record the new figure and attribute the delta to the tool. Behaviour-preservation
(T135): the 8 re-cut XML goldens, the 24 wire-dict goldens and `outcomes.json` are byte-identical
across the sweep (sha256 compared); the whitespace part (`W293`/`W291`) has an empty `diff -w`; the
non-whitespace edits are the 7 `F541` and import sorts, done file by file with the suite after each
(three files initially failed only on remint **timing** tests and passed on retry). Three judgement
fixes worth naming: `E721` became `type(x) is Y` and **not** `isinstance` (exact-type assertions
kept); `E712` became `is True`/`is False` and the suite stayed green, so those comparisons were
genuine booleans; three bare `except:` became `except Exception:`.

## Budgets after the code landed — measured 2026-10-14 (T116–T120, T123)

**Interpreter**: the `hatch` build, CPython 3.11.9 python-build-standalone (Clang 18.1.8, PGO+LTO).
**Box state — read this first.** An unrelated Chrome renderer was holding one core at ~80% for the
whole session and `/proc/loadavg` read **2.0–3.1** throughout (the quickstart's quiet band is
0.6–1.1; `nproc` = 12). The box then ran in two states: a slow one where *every* path reads ~2×
(load 33 ms, save 28 ms — **discarded, not a result**) and a fast one that reproduces the branch
point. Both arms were therefore run **interleaved in one session**, A = a throwaway `git worktree` at
`75a958e`, B = this branch, and only the fast-state pairs are used. The raw pairs are in
`snapshots/perf-paired-2026-10-14.txt`. By the sampling lesson (R10): consistency within a window is
not evidence, so the verdicts below lean on the **A/B ratio**, not on the absolute figure.

| Path | A: branch point | B: this branch | Δ | Budget | Verdict |
|---|---|---|---|---|---|
| show-document **load** | 17.217 / 17.219 ms | 17.317 / 17.294 ms | +0.5% | band 16.465–17.750 (bound 20.41) | **inside the band** |
| show-document **save** | 14.186 / 14.800 | 14.870 / 14.971 | +1–5% | ≤ 16.4 ms | **met** |
| `network_map` load | 1.117 / 1.159 | 1.044 / 1.086 | −5% | reported (SC-PERF-004) | not moved |
| `settings` load | 2.470 / 2.519 | 2.427 / 2.620 | ±4% | reported | not moved |
| `project_mappings` load | 4.844 / 5.065 | 5.062 / 5.367 | +4–6% | reported | within the ±4–8% spread |
| **descriptor derivation**, `script` | **1.023 / 1.062 ms** | **2.791 / 2.873 ms** | **+170%** | **≤ 1.22 ms** | ⚠ **EXCEEDED** |
| suite, per test | 36.03 s / 3553 = **10.14 ms** | 39.19 s / 3706 = **10.57 ms** | +4.3% | ≤ 10.3 ms/test | ⚠ absolute exceeded in this contended session; **relative +4.3%** |

**The writer did not move the reader** (T118): all four load paths are inside their spread, and the
show-document load equals its control to 0.5% — the proof an edit to the writer owed.

### Exceeded, recorded as exceeded (T120, FR-PERF-001)

1. **Descriptor derivation: 1.04 → 2.83 ms, +170%, against ≤ 1.22 ms.** The mechanism is identified
   by profile, not guessed: of a 34-type `types('script')` call, **~80% of the cumulative time is
   `descriptor._instance_for`** (1020 calls / 30 iterations), i.e. G3's wire-shaped, seeded,
   recursively expanded `instance`, which every `describe()` now builds eagerly (FR-020..FR-025).
   Per-type figure is ~65 µs. This is the cost of the feature the budget was set to police, not
   an accident; it was predicted by SC-PERF-002's own wording ("both G3 and S2 change it"). It is a
   warm, per-call cost on an `lru_cache`d path with one caller family (`get_schema_descriptor`),
   so it is **accepted and carried, not mitigated here**. The obvious mitigation — build an
   `instance` lazily on first access, or cache `_instance_for` and hand out copies — is a
   follow-up with its own copy-safety question, because callers mutate instances (the editor's
   tests do).
2. **Suite per-test, absolute: 10.57 ms/test against ≤ 10.3.** The control arm read 10.14 in the same
   contended session (the branch-point record is 8.93 on a quiet box), so ~13% of the figure is the
   box, and the feature's own share is the **+4.3%** relative. 3706 vs 3553 passed: +153 tests.
   Recorded exceeded rather than restated; re-measure on a quiet box before citing 10.57 anywhere.

### SC-005a and SC-010 (T123)

- **SC-005a, repairability invariance**: the 327-row table (schema · type · field · repairability ·
  default) is **identical** to the pre-feature snapshot after normalising the address of one
  callable default — `snapshots/repairability-after.txt`. **Zero entries changed.**
- **SC-010, the union narrowing**: the five sites that reported a one-value choice set now report
  `None` (no closed set), as S2 specifies — `network_map NodeType.uuid`, `settings NodeConfType.uuid`,
  `project_mappings NodeMappingType.uuid`, and both `output_latency_ms` — against
  `('00000000-0000-0000-0000-000000000000',)` / `('auto',)` before. `snapshots/union-enums-after.txt`.

### Release gates, final run (T121, T121a, T122)

`hatch run test.py3.11:lint` → **All checks passed** (606 → 0). `types:check src/cuemsutils` →
**72** (80 → 72). Suite → **3707 passed, 115 skipped, 2 xfailed, 0 failed** in 38.8 s. The branch-point
failures are all closed: the show-load line by the band (FR-079), the four cross-repository
assertions by the tag resolver (FR-080), and `test_no_version_bump`'s sibling read, a fifth of the
same class found on the way, re-pointed at the tag.
