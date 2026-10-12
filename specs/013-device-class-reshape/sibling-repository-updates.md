<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Sibling repository measurement — feature 013

**Feature**: `013-device-class-reshape` | **Task**: T068 | **Measured**: 2026-10-01
**Criteria**: SC-008, SC-013

Feature 012 measured a call-site census to be the weaker instrument: both risks
its census predicted produced zero failures, while the real breakage was in test
*data* a census cannot see. So this feature runs the suite, both arms, and does
not infer the result.

`cuems-engine`'s virtualenv resolves `cuemsutils` through an editable install
pointing at `/disk/Projects/StageLab/cuems-utils/src`, so the two arms are the
same checkout at two commits. The branch-point arm was run with `PYTHONPATH` set
to a detached worktree at `ce05645`.

**Every change made to `cuems-engine` below was a measurement and was reverted.**
That repository's working tree is clean at `1662a99`, verified after each step.

---

## `cuems-engine` — the three runs

| Arm | `cuemsutils` | Engine fixtures | Result |
|-----|--------------|-----------------|--------|
| A | `ce05645` (branch point) | as committed | **923 passed**, 0 failed |
| B | `8702b46`+ (this branch) | as committed | **70 failed, 827 passed, 26 errors** |
| C | this branch | reshaped by `cuems-reshape-devices` | **1 failed, 922 passed** (twice, identical) |

### Arm B: 96 failures, one cause, zero source changes

Every failure and every error traces to **old-shape XML fixtures in
`cuems-engine`'s own tree**, grouped by the message:

| Count | Message |
|-------|---------|
| 57 + 38 + 29 | `settings document … is in the pre-013 device shape (<videoplayer>/<audioplayer>/<dmxplayer> on <node>)` — `dev/test_xml_files/settings.xml` and the per-test temporary copies built from it |
| 6 | `script document … is in the pre-013 device shape` — `projects/complex_test/script.xml` and `projects/complex_test_v2/script.xml` |
| 6 | bare `AssertionError`, each downstream of one of the above |
| 1 | `RuntimeError: Network error: … Could not open port: 53407` — environmental, unrelated |

**No engine source file is implicated.** The migration guide's §2 claim — all
fifteen measured call sites keep resolving correctly — holds as measured: the
compatibility surfaces (`node_hw_outputs`, `node_mappings["audio"]`,
`node_conf["videoplayer"]`) are doing exactly what they were built to do, and
nothing in `NodeEngine.py` had to change.

What broke is data, which is why the guide tells each maintainer to run their
suite rather than read a diff.

### Arm C: the fixtures migrate with one tool invocation

`cuems-reshape-devices dev/test_xml_files/**/*.xml` reported **5 reshaped, 2
already current, 2 not applicable, 10 skipped**. The ten skipped are the
fragments and namespace-typo documents this library already records as
non-loading (`sample_*.xml`, `script_one_*.xml`, `outputs.xml`); they are
rejected for those reasons either way and the device shape is irrelevant to them.

That takes the suite from 96 failures to **one**.

### The one residual failure, and why it is not this feature's

`tests/test_project_go.py::test_project_go_from_controller`,
`TimeoutError: node never reached load=complex_test (got '')`. Reproducible —
twice in the full suite, twice in isolation.

It is the migration guide's **half-migrated library** edge case (§4), arrived at
honestly: the tool *refused* one document in that project, so the project's
settings moved to the new shape while its mappings did not, and the project no
longer loads.

The tool refused it because
`dev/test_xml_files/projects/complex_test/project_mappings.xml` **is invalid
against `project_mappings.xsd` independently of this feature**, and not once but
twice:

1. its `<output>` elements carry `<name>` with **no `<id>`**, while `PutType`
   declares `id` first — the same staleness `cuems-utils`'
   `tests/data/corpus/PROVENANCE.md` already records for its vendored copy
   ("the fixture predates a schema change and was never updated");
2. with that corrected, the document is still rejected for a **missing
   `<new_nodes>`**, which the schema has required at `minOccurs="1"` since long
   before this feature.

**Verified, not assumed**: the branch-point library rejects the same file with
`Unexpected child with tag 'name' at position 1`. So arm A's 923 passes never
included a successful load of this document — the engine tolerated its failure —
and arm C's single failure is the tool correctly declining to rewrite a document
that was never valid.

### What `cuems-engine` has to do

1. Run `cuems-reshape-devices` over `dev/test_xml_files/`. Five documents move;
   that is the whole of it.
2. Update `tests/test_port_handler.py`, which names the old player elements.
3. Separately, and not because of this feature, repair
   `projects/complex_test/project_mappings.xml`: add the missing `<id>` to each
   `<output>`/`<input>` and the missing `<new_nodes>`. Until then that project
   cannot be migrated and `test_project_go_from_controller` cannot pass against a
   migrated settings document.

Item 3 is the finding worth carrying forward: a fixture that has been invalid for
several releases was invisible while nothing required it to validate, and this
feature's migration tool is what surfaced it — by refusing to write it, which is
the behaviour T034 specified.

---

## Old-shape XML elsewhere, measured 2026-10-01

Grepped across the sibling trees for the reshaped element names. None of these is
a call site; all are fixtures or documentation, and all of them are **axis C**
(`settings`), which is why the count is dominated by one repository.

| Repository | Files | Kind |
|------------|-------|------|
| `cuems-power-bridge` | 9 × `tests/fixtures/network_map/map-*/settings.xml` | test fixtures |
| `cuems-nodeconf` | `tests/fixtures/etc_cuems/settings.xml`, `…/settings_sentinel.xml` | test fixtures |
| `cuems-engine` | `dev/test_xml_files/settings.xml`, `tests/test_port_handler.py` | fixture + test source |
| `cuems-common` | `docs/latency-tuning.md` | documentation |
| `cuems-editor` | none **at the time of this measurement** — see below | — |

The fix in every fixture case is the one the tool performs: wrap the three
players in `<players>`, give each a `class`, leave `<audiomixer>` alone.
`cuems-power-bridge` and `cuems-nodeconf` were **not** run here — their suites are
outside this task's scope (T068 names `cuems-engine`) — so this table is a
prediction for them and a measurement only for the engine.

### `cuems-editor`, re-measured 2026-10-02 at `bf57d95`

Its migration landed, and the row above needs one correction and one addition.

**It now carries an old-shape script fixture on purpose.** `tests/fixtures/script_minimal.xml` is
pre-013 (`<AudioCue>`, `<VideoCue>`) and is kept, with its checksum and provenance recorded in that
repository's `tests/fixtures/README.md`, for two jobs a migrated fixture cannot do: it is the source
of the pre-migration `project` payload capture (the only thing that can prove a delta list is
complete), and it is the fixture that must be reported `SKIPPED_INVALID` by the duration-repair
tool. Beside it sits `script_minimal_013.xml`, produced by running **`cuems-reshape-devices`** over
a copy — the first use of this feature's tool by a sibling repository, and the only change is each
`<AudioCue>`/`<VideoCue>` becoming `<Cue class="audio">`/`<Cue class="video">`.

So a grep for old-shape elements in that tree is **expected** to hit, and a later sweep must not
"fix" it. The distinction the table above did not need until now: an old-shape document in a sibling
is a defect when something loads it expecting success, and a **test input** when something loads it
expecting refusal.

**Its `settings` fixture is new-shape**, `<players><player class="…">`, copied from this
repository's `tests/data/` — so axis C needed no work there.

**Suite, measured against this branch**: **154 passed / 2 skipped / 1 xfailed** (5.21 s). The xfail
is strict and is a gap in *this* library's public surface, not a device-class matter —
`cuems-editor` UR-5, no public way to build a configuration document from JSON. One arm only: that
repository's pre-013 arm is not meaningful, because its own migration and this feature landed in the
same window and its branch point did not import at all.
