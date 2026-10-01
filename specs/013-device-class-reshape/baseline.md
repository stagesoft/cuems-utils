<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Baseline — feature 013, measured before any `src/` edit

**Branch**: `013-device-class-reshape` at `ce0564586ea6f395358996ff64a9a354e17967f3`
**Date**: 2026-10-01
**Interpreter**: pyenv 3.11.9, `PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:…`

T004's denominators. SC-PERF-001 is a ratio to the mappings-document row.
SC-PERF-002 stays ≤ 18.04 ms/test. SC-PERF-003's budget is the calibration
range below; T062 compares against it and does not choose another.

---

## E1 — `xs:alternative` decodes, and the discriminator is in the item dict

**Pass.** Both children decode. The `video` child keeps `extra`. No fallback.

Stock `XMLSchema11.decode` (attribute prefix `@`):

```text
{'d': [{'@class': 'audio', 'a': 'x'}, {'@class': 'video', 'a': 'y', 'extra': 'z'}]}
```

`XMLSchema11(..., converter=CuemsConverter).to_dict` (`attr_prefix=""`):

```text
[{'d': {'a': 'x', 'class': 'audio'}}, {'d': {'a': 'y', 'extra': 'z', 'class': 'video'}}]
```

The discriminator is the bare key `class`. Dispatch reads the dict. It does
not call `xsd_element.get_type`.

## E2 — the test is a string on `XsdAlternative.path`

**Pass.** No `xs:appinfo` fallback. T012 reads `.path` and nothing else.

```text
particle: xmlschema.validators.elements.Xsd11Element
alternatives: [XsdAlternative(type='V', test="@class='video'"), XsdAlternative(type='B', test=None)]
alt 0: path="@class='video'"  token=<_EqualsSignOperator>  type name=V
alt 1: path=None              token=None                   type name=B
```

`.test` is a bound method, not the test text. The unconditional alternative
has `path is None`.

## E3 — `distinct-values` rejects a duplicate

**Pass.** T022 uses `xs:assert`, not `xs:unique`.

```text
count(d) = count(distinct-values(d/@class))
two classes:  True
duplicate:    False
```

The defaults assert is the same construct with a composite key. Measured in
the same session, not part of E3's question:

```text
count(default) = count(distinct-values(default/concat(@class,'/',@direction)))
audio input + audio output:  True
two audio inputs:            False
```

## A constraint E1 did not surface

`xmlschema` refuses an alternative whose type is not derived from the
element's declared type (`XMLSchemaParseError: type 'V' is not derived from
…'B'`). The data-model snippet that puts `type="cms:DeviceType"` on
`device` and points `@class='video'` at `VideoDeviceType` does not compile:
`VideoDeviceType` does not extend `DeviceType`, and it cannot, because an
extension appends particles and cannot replace `PutGroupType` with
`VideoPutGroupType`.

What does compile, and what T020 uses:

- the element's declared type is a class-only base both concrete types extend;
- the conditional alternative names `VideoDeviceType`;
- the unconditional alternative names `DeviceType`.

An unknown class then validates as `DeviceType` (outputs and inputs, no
`canvas_region`). `FieldSpec.child` records that unconditional alternative,
so the decoder's `member.child` fallback is `DeviceType` and not the empty
base. With no alternatives, `child` stays `element.type`, which is every
type today.

The same constraint hits axis D. `DmxCueType` extends `CueType`, not
`MediaCueType`, so a `Cue` element declared as `MediaCueType` cannot
alternative to `DmxCueType`. The three cue-output types share no base.
Those schemas grow a class-only base the same way. Players do not: 
`VideoPlayerType`, `AudioPlayerType` and `DmxPlayerType` already extend
`PlayerType`.

---

## E4 — denominators

### Suite, three runs, unmodified tree

`test_descriptor_laziness` did not move the totals on these runs.

| Run | Result | Wall | Per test |
|-----|--------|------|----------|
| 1 | 3247 passed, 115 skipped, 2 xfailed, 215 warnings | 54.63 s | 16.24 ms |
| 2 | 3247 passed, 115 skipped, 2 xfailed, 215 warnings | 55.19 s | 16.41 ms |
| 3 | 3247 passed, 115 skipped, 2 xfailed, 215 warnings | 56.09 s | 16.67 ms |

Per test is wall ÷ (passed + skipped + xfailed) = wall ÷ 3364.

**Range: 16.24–16.67 ms/test.** SC-PERF-002's ceiling stays 18.04 ms/test.

One earlier run, taken while the machine was already busy, failed
`test_the_prediction_stays_within_the_measured_pessimism_bound[10]`
(predicted 0.0718 s against 0.0251 s, 2.9×, past that test's recorded 2.7×).
The three runs above do not reproduce it. It is feature 012's estimate
bound, not a 013 denominator.

### Document load

Best of 3 medians of 5 warm runs, the method in
`tests/integration/test_read_path_regression.py`. One warm call before the
trials. Fresh process.

| Document | Path | Best | The three medians |
|----------|------|------|-------------------|
| `project_mappings` | `tests/data/corpus/cuems-utils/project_mappings.xml` via `load_config_document(ProjectMappings, …)` | **15.153 ms** | 15.226, 15.153, 15.166 |
| `settings` | `tests/data/corpus/cuems-utils/settings.xml` via `load_config_document(Settings, …)` | **13.725 ms** | 13.729, 14.381, 13.725 |
| `script` | `tests/data/corpus/cuems-engine/projects/complex_test/script.xml` via `CuemsScript.load` | **12.939 ms** | 13.568, 13.147, 12.939 |
| `hardware_outputs` | `tests/data/corpus/cuems-utils/outputs.xml` via `read_document` | **0.405 ms** | 0.424, 0.406, 0.405 |

SC-PERF-001's budget is 110% of 15.153 ms = **16.668 ms**.

### SC-PERF-003 calibration

`remint_200`: 400 files, 3,937,400 bytes. Read every file and atomically
rewrite it (`os.open` `O_EXCL`, `os.replace`), no device-class substitution.
Three repeats:

| Repeat | Elapsed | Throughput |
|--------|---------|------------|
| 1 | 13.5 ms | 292.1 MB/s |
| 2 | 13.7 ms | 288.0 MB/s |
| 3 | 13.8 ms | 286.2 MB/s |

**Budget: 286.2–292.1 MB/s.** T062 compares the tool with this range.

---

## T006

`spec.md` already records M10–M13, FR-012a, the widened FR-030, FR-032,
FR-033, FR-042, and A4's three arms. No research was folded back in.

## Failing-first (phase 2)

Recorded before `class_alternatives` existed:

```text
ImportError: cannot import name 'class_alternatives' from 'cuemsutils.xml.spec'
ERROR tests/unit/test_fieldspec_alternatives.py
1 error in 0.29s
```

The same collection error covers T008 and T010. T009 (the convention test)
passes on the pre-change schemas and was not part of that failure.

---

## Failing-first (phase 7, axis D)

Recorded before any `script.xsd` edit, with `test_cue_class_dispatch.py` and
`test_cue_wire_key.py` in the tree:

```text
16 failed, 3 passed in 1.92s
```

The three that passed are the import check, the `ActionCue`/`FadeCue`/`CueList`
wire-key check and its sibling — all three are claims the pre-change schema
already satisfied, which is the point of stating them separately.

---

## T054 — the ratchet, at each schema commit rather than only at the tip

Three commits on this branch edit a schema. Each was checked out into a detached
worktree and `tests/contract/test_schema_scope.py` and
`tests/contract/test_schema_name_overlap.py` were run **there**, not read from
the diff (SC-009).

| Commit | Schema edited | `test_schema_scope.py` + `test_schema_name_overlap.py` |
|---|---|---|
| `522664a` | `project_mappings.xsd` (axis A) | 16 passed, 1 skipped |
| `c0a41c0` | `settings.xsd` (axis C) | 16 passed, 1 skipped |
| `23dd444` | `script.xsd`, `hardware_outputs.xsd` (axis D) | 16 passed, 1 skipped |

So every hash pin and every overlap-allowlist entry moved **in the commit that
moved its schema**. No corrective commit was needed and no history was rewritten.

### A method note, because the first run of this audit reported a failure that was not one

The first pass reported `test_every_schema_matches_its_recorded_hash` failing at
`23dd444` for `script.xsd` and `hardware_outputs.xsd` — while the hashes
recorded in that commit matched the files in that commit exactly, verified by
hand with `git show | sha256sum`.

The cause was **stale bytecode**, not drift. `test_schema_scope.py` differs
between consecutive commits here only in two 64-character hex digests, so the
file's **size is identical** across them, and three `git checkout`s inside one
second give identical mtimes. CPython validates a cached `.pyc` on source mtime
and size, so it reused the previous commit's compiled module and compared the
new schemas against the old pins.

Anyone repeating this audit must clear `__pycache__` between checkouts, or run
with `PYTHONDONTWRITEBYTECODE=1`. Recorded because the failure is convincing:
it names real files and a real assertion, and the tempting conclusion — "the
hash pin lagged, add a corrective commit" — would have been wrong.

---

## T055 / T056 — the pins this feature did not move

Measured against this feature's branch point, `ce05645`.

| Claim | Result |
|---|---|
| `KNOWN_DIVERGENT_DECLARATIONS` is empty | **empty** — feature 012's completion marker still holds |
| `KNOWN_IDENTICAL_DUPLICATES` names every new cross-schema type | one entry changed: `NonEmptyString` gains `hardware_outputs` and `script`, so all six schemas now declare it |
| `test_version_marker.py` unmodified (`EXPECTED_VERSIONS`, `DELIBERATE_IDENTITY_STEPS`) | **unmodified** — zero-line diff against `ce05645` |
| `xml/versioning.py` unmodified (`CURRENT_VERSION`, the conversion registry) | **unmodified** — zero-line diff |
| `tests/packaging/test_no_version_bump.py` still pins `0.1.0rc16` / `1.3.0-23` / `0.1.0-8` | **unmodified** |

`NonEmptyString` is the only type this feature declares in a schema that already
declared it elsewhere. The three new named types in `script.xsd`
(`CueClassType`, `CueOutputClassType`, `CueOutputType`) and
`hardware_outputs.xsd`'s `OutputGroupsType` are each declared once;
`test_schema_name_overlap.py` would fail if any of them collided, and it passes.
