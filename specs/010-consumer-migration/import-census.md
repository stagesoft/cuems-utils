# Import census — the wave-5 gate

**Purpose**: FR-029/FR-029e. The deprecated surface is removed only after a **measured** count of
live imports across all six consumer repositories returns **zero**. "The consumer flows are merged"
is a different claim, and the difference is a broken daemon.

**This file is the gate's artifact.** Every deletion task in wave 5 declares it as an input and
states the required value. It is re-run **immediately before** the deletions, not once at the close
of wave 4 — a repository can regress between merge and removal (FR-029e).

## Method

```bash
cd /disk/Projects/StageLab
grep -rn --include='*.py' -E \
  'cuemsutils\.xml\.(XmlReaderWriter|Parsers|Settings|CMLCuemsConverter)|cuemsutils\.timeoutloop|from cuemsutils\.xml import .*(NetworkMap|Settings|ProjectMappings|ProjectSettings|XmlReaderWriter|CuemsParser)|cuemsutils\.create_script' \
  cuems-engine/src cuems-editor/src cuems-nodeconf/cuemsnodeconf cuems-wsclient/src cuems-common
```

## Baseline — 2026-09-04, before any consumer flow has run

**9 live imports across 3 repositories. Required value at wave 5: 0.**

| Repository | File:line | Deprecated path |
|---|---|---|
| `cuems-editor` | `src/cuemseditor/CuemsDBProject.py:9` | `cuemsutils.xml.Parsers.CuemsParser` |
| `cuems-editor` | `src/cuemseditor/CuemsDBProject.py:10` | `cuemsutils.xml.XmlReaderWriter` |
| `cuems-editor` | `src/cuemseditor/CuemsWsServer.py:23` | `cuemsutils.xml.NetworkMap` |
| `cuems-editor` | `src/cuemseditor/CuemsWsServer.py:24` | `cuemsutils.create_script` — **already deleted; this is an ImportError today** |
| `cuems-editor` | `src/cuemseditor/repair_durations.py:39` | `cuemsutils.xml.Parsers.CuemsParser` |
| `cuems-editor` | `src/cuemseditor/repair_durations.py:40` | `cuemsutils.xml.XmlReaderWriter` |
| `cuems-engine` | `src/cuemsengine/ControllerEngine.py:12` | `cuemsutils.xml.Settings.NetworkMap` |
| `cuems-engine` | `src/cuemsengine/core/BaseEngine.py:17` | `cuemsutils.xml.XmlReaderWriter` |
| `cuems-nodeconf` | `cuemsnodeconf/CuemsNodeConf.py:26` | `cuemsutils.timeoutloop.Timeoutloop` |

`cuems-common`, `cuems-wsclient` and `cuems-frontend` carry **zero** — `cuems-wsclient` because it
imports nothing from the library at all, which is C1's finding rather than a clean bill of health.

**Nine, against the twelve** `tests/contract/test_deprecation_shims.py`'s docstring names. The
difference is not a discrepancy to reconcile away: this census counts **import statements**, that
docstring counts **call sites**, and a single import serves several. Both are re-measured at wave 5;
neither is assumed.

## Re-runs

| Date | Result | Postdates merge | Notes |
|---|---|---|---|
| 2026-09-04 | **9** | — | baseline, no consumer flow has run |
| 2026-09-17 | **8** | `cuems-nodeconf` @ `aab9b48` (not merged to `main`) | `cuems-nodeconf`'s single entry — `cuemsutils.timeoutloop.Timeoutloop` at `CuemsNodeConf.py:26` — is **gone**, replaced by `cuemsutils.tools.TimeoutLoop.TimeoutLoop`. That repository now carries **zero**. The remaining 8 are `cuems-editor` (5) and `cuems-engine` (3), neither flow started. **Not a gate clearance** — the required value is 0, and T050 additionally requires a census dated after the last consumer *merge*; this one postdates a branch commit, not a merge |
| 2026-10-02 | **0** over shipped source | `cuems-editor` @ `bf57d95` (not merged to `main`) | **The required value, reached.** `cuems-editor`'s five entries are gone — the last repository carrying any. `CuemsDBProject.py` and `repair_durations.py` read through `CuemsScript.load_with_report` / `from_json` / `save`; `CuemsWsServer.py` imports `new_uuid` from `cuemsutils.helpers` and `partition_by_adoption` from `cuemsutils.tools.NodeList`. **Still not a gate clearance**, for one reason only: T050 requires a census dated after the last consumer *merge*, and nothing is merged — every consumer flow sits on a local `feat/xml-refactor`. The deletions stay blocked on the merges, no longer on a consumer's source |

### The 2026-10-02 run — command, denominator and exempt set

Denominator discovered rather than listed (T062, FR-070b), and de-duplicated **by git remote**:
`/disk/Projects/StageLab/cuems-*` with a `.git`, excluding this repository, gives six consumer
remotes — `cuems-common`, `cuems-editor` (remote `cuems_editor`, note the underscore),
`cuems-engine`, `cuems-frontend`, `cuems-nodeconf`, `cuems-power-bridge`. **`../cuems-wsclient` is
no longer on disk**, so the double-count the 2026-09-18 identity correction guarded against can no
longer be made by accident here; the de-duplication rule stays recorded because the next checkout
re-creates the hazard.

```bash
cd /disk/Projects/StageLab
# the gate: shipped source only
grep -rn --include='*.py' -E \
  'cuemsutils\.xml\.(XmlReaderWriter|Parsers|Settings|CMLCuemsConverter)|cuemsutils\.timeoutloop|from cuemsutils\.xml import|cuemsutils\.create_script' \
  cuems-engine/src cuems-editor/src cuems-nodeconf/cuemsnodeconf cuems-power-bridge/src \
  cuems-common cuems-frontend
# → no output, exit 1
```

**Exempt set, with the two reasons stated separately** (FR-072, FR-073a — merging them is how a
working migration diagnostic gets deleted by the next person to run the count):

| Path:line | Reason | Class |
|---|---|---|
| `cuems-editor/tests/test_public_surface.py:37-38` | the guard test's own rejection list — it names `CuemsParser` and `XmlReaderWriter` in order to **forbid** them under `src/` | **exists to detect the retired spelling — permanent** |
| `cuems-engine/tests/test_public_surface.py:21` | same, in a docstring describing what the rule covers | **exists to detect the retired spelling — permanent** |
| `cuems-nodeconf/tests/test_no_injection.py:6`, `:35` | prose naming the injection pattern the test asserts is gone | **exists to detect the retired spelling — permanent** |
| `cuems-editor/tests/test_validate_fade_durations.py:7` | prose explaining why the test exists (the old parser bypassed `FadeCue.set_duration`) | documentation of history — removable, but harmless |
| `cuems-engine/dev/CuemsEngine_old.py:13` | a real `import` statement, and the only one left anywhere | **not shipped** — `pyproject.toml` declares `packages include = "cuemsengine"`; `dev/` is in no artifact. Removable at any time, and it will break at `v0.1.1` if anyone runs it |

The first four are **not** import statements and would not be caught by the gate command above;
they appear only in the wider sweep, and are listed so a later reader does not "fix" them.
