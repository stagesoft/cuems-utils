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
