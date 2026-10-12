# Quickstart — running and verifying the consumer migration

**Date**: 2026-09-03 | **Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

Seven repositories, six waves, one release. This is the operator's-eye view: what to run, in what
order, and how to know each wave actually worked rather than merely merged.

## Before anything

```bash
# This repository's baseline — re-measure, do not inherit.
hatch test --show
# Expected starting point: 2573 passed, 96 skipped, 2 xfailed in ~53.3 s = 20.73 ms/test
```

Every repository branches to `feat/xml-refactor`. Five of the seven have no spec-kit and acquire it
on their first run; the per-repository flows are in
`specs/planning/xml-rebuild/010-consumer-prompts/`.

**Run the `cuems-wsclient` flow first**, even though nothing depends on it. It is last by
dependency and worst by current state: its shutdown fan-out resolves zero nodes, skips the
reachability poll, and arms the mains relay against machines nothing asked to stop.

## Wave 0 — publish the descriptor *(this repository)*

```bash
hatch test --show     # all six schemas, public == internal; instances validate; laziness holds
```

Verify by hand that the boundary did not move:

```bash
grep -n '__all__' src/cuemsutils/xml/__init__.py   # must still be: __all__: list[str] = []
```

## Wave 1 — the independent repairs *(four tracks, parallel)*

Each track's own suite, plus the discriminating test that gives it meaning:

```bash
# 1a wsclient — the repository's FIRST test. It must fail against the old comparison.
cd /disk/Projects/StageLab/cuems-wsclient && pytest

# 1b editor — the only check that matters at this stage is that it starts.
cd /disk/Projects/StageLab/cuems-editor
python -c "import cuemseditor.CuemsWsServer"      # must not raise ImportError

# 1c engine
cd /disk/Projects/StageLab/cuems-engine && pytest

# 1d Avahi — BOTH repositories, merged together. Never one without the other.
cd /disk/Projects/StageLab/cuems-common && pytest
cd /disk/Projects/StageLab/cuems-nodeconf && pytest
```

**The 1d end-to-end check is the one that counts**: run the migrated publisher on one machine and
the migrated listener on another, and confirm the node is discovered *with its role*. A green suite
on each side proves nothing about a key that is the wire between them.

## Wave 2 — editor and node daemon

```bash
cd /disk/Projects/StageLab/cuems-nodeconf && pytest   # 008's characterization tests must pass UNCHANGED
cd /disk/Projects/StageLab/cuems-editor && pytest
```

Payload check — against the **two-delta** statement, never unconditional identity:

```
1. schemaLocation absent
2. Media.duration == {"CTimecode": "HH:MM:SS.mmm"}
3. everything else identical, INCLUDING key order and the STRING boolean form
4. doc_version absent  (it is not a third delta)
```

## Wave 3 — the UI

**Characterization tests first, then the port** — in that order, or the port has nothing to prove
it preserved behaviour:

```bash
cd /disk/Projects/StageLab/cuems-frontend
ng test        # write the specs for projects.service, sequence.component, settings.component FIRST
ng test        # re-run after the port: the same specs, still green
```

Then look at the screen: a media duration renders as a duration, not `[object Object]`; adopt and
unadopt still work; the mixer screens still read their mappings.

## Wave 4 — rollout, gate and data migration

**The packaging demonstration — run it, do not describe it:**

```bash
# In a disposable container. The expected outcome is a REFUSAL.
dpkg -i <library .deb newer than the pinned consumer> <unmigrated consumer .deb>
# Success here means dpkg says no.
```

**Check the rollback boundary before converting anything** (this is what the no-write mode is for):

```bash
cuems-convert-documents --check /projects/*/script.xml    # reports versions; writes nothing
```

**Convert, at library scale:**

```bash
cuems-convert-documents /projects/*/script.xml
```

Then verify the three properties that matter, none of which a summary line proves:

```bash
# 1. Every document converted — counted, not sampled.
cuems-convert-documents --check /projects/*/script.xml | grep -c 'version 2'

# 2. Every document has a retained backup.
ls /projects/*/script.xml.*.bak | wc -l

# 3. Resumability — interrupt a run, re-run it, and confirm the remainder completes with
#    nothing converted twice and no second backup. (Already true by construction; verify it.)
```

**Disk space**: backups sit beside the documents and are never reclaimed automatically, so a
library roughly doubles its size until an operator reclaims them. Record the measured figure.

**Both rollback drills — executed, not written:**

```
Drill A (pre-conversion):  downgrade the packages. No document is touched. Service returns.
Drill B (post-conversion): downgrade the packages AND restore from the .bak files.
```

**The cluster upgrade**, controller plus at least one node. Safe order: **nodes first**. Afterwards:
every node discovered, adoption preserved, and a show loadable on each.

## Wave 5 — removal *(gated on a measured zero)*

```bash
# The census. Required value: ZERO. Re-run immediately before deleting anything —
# a repository can regress between merge and removal.
cd /disk/Projects/StageLab
grep -rn 'cuemsutils\.xml\.XmlReaderWriter\|cuemsutils\.xml\.Parsers\|cuemsutils\.xml\.Settings\|cuemsutils\.xml\.CMLCuemsConverter\|cuemsutils\.timeoutloop\|from cuemsutils.xml import \(NetworkMap\|Settings\|ProjectMappings\|ProjectSettings\|XmlReaderWriter\|CuemsParser\)' \
  cuems-engine/src cuems-editor/src cuems-common cuems-nodeconf cuemsnodeconf cuems-frontend/src cuems-wsclient/src 2>/dev/null | tee specs/010-consumer-migration/import-census.md | wc -l
```

Only then delete the five shim modules, the seven aliases and the four deprecated-symbol sites,
retire the 22 contract tests **deliberately**, and move `__version__` to the release every warning
since feature 006 has promised.

```bash
cd /disk/Projects/StageLab/cuems-utils && hatch test --show
# The suite should be FASTER — 22 contract tests retire. If it is not, something else changed.
```

## The ecosystem-wide count

```bash
cd /disk/Projects/StageLab
grep -rn 'node_type\|NodeType\.' */src */cuemsnodeconf 2>/dev/null | wc -l
```

**This count has an enumerated exempt set, and the exemptions have two different reasons that must
not be merged** (FR-071/FR-073a):

| Exempt | Reason | Lifetime |
|---|---|---|
| `cuems-utils` `errors.py`, `tools/ConfigBase.py`, `config/network_map.py`, `network_map.xsd` (16 sites) | exists to **detect** the retired spelling | permanent |
| `cuems-common`'s conversion command and its tests | exists to **convert** it | permanent |
| `cuems-engine` `dev/network_map.xml`, `dev/test_xml_files/network_map.xml`, `dev/CuemsEngine_old.py`; `cuems-nodeconf` `test_run_nodeconfig.py` | **not shipped** | removable at any time |

A count that flags the first two categories pushes someone to delete a working migration diagnostic
to make a number reach zero. Everything outside this list counts.

## The final verification (spec SC-005, SC-016)

1. Save a project in the editor.
2. Load it in the engine.
3. Render it in the UI — unchanged but for the two deltas.
4. Upgrade a controller and at least one node; the cluster comes back with its topology intact.
