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
