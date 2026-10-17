# Quickstart — running and verifying the consumer migration

**Date**: 2026-09-03 | **Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

Seven repositories, six waves, one release. This is the operator's-eye view: what to run, in what
order, and how to know each wave actually worked rather than merely merged.

## Before anything

```bash
# This repository's baseline — re-measure, do not inherit.
uvx hatch run test.py3.11:run -- -q     # `hatch test` lacks hypothesis on this box (CLAUDE.md)
# Measured 2026-10-17 (T067): 3785 passed, 112 skipped, 2 xfailed, 7 failed — the seven are
# pre-existing (six strict-XPASS tag tripwires, one engine-version pin in 012's guide).
```

> **Walked 2026-10-17 (T067)** and corrected where it was wrong. Every command below that runs on a
> development box was run; the corrections are marked. Production steps are marked as such.

Every repository branches to `feat/xml-refactor`. Five of the seven have no spec-kit and acquire it
on their first run; the per-repository flows are in
`specs/planning/xml-rebuild/010-consumer-prompts/`.

**Run the `cuems-power-bridge` (formerly `cuems-wsclient`) flow first**, even though nothing depends on it. It is last by
dependency and worst by current state: its shutdown fan-out resolves zero nodes, skips the
reachability poll, and arms the mains relay against machines nothing asked to stop.

## Wave 0 — publish the descriptor *(this repository)*

```bash
uvx hatch run test.py3.11:run -- -q tests/contract/test_public_descriptor.py tests/contract/test_descriptor_laziness.py
```

Verify by hand that the boundary did not move:

```bash
grep -n '__all__' src/cuemsutils/xml/__init__.py   # must still be: __all__: list[str] = []
```

## Wave 1 — the independent repairs *(four tracks, parallel)*

Each track's own suite, plus the discriminating test that gives it meaning:

```bash
# 1a wsclient — the repository's FIRST test. It must fail against the old comparison.
cd /disk/Projects/StageLab/cuems-power-bridge && pytest   # was cuems-wsclient, renamed 2026-06

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

Payload check — against the **enumerated-delta** statement, never unconditional identity. It was
two deltas when written; it is **five** since 014 (corrected 2026-10-16). The definition is
`cuems-editor`'s `tests/ws-command-responses.txt`, "project" frame, pinned by its
`tests/test_project_payload.py`:

```
(a) schemaLocation absent                                              006
(b) Media.duration == {"CTimecode": "HH:MM:SS.mmm"}                    008
(c) hardware cue key "Cue" / "CueOutput" with "class"                  013
(d) a model default projected for an absent optional (e.g. opacity)   ruled 2026-10-02
(e) autoload, enabled, timecode are JSON booleans, not "True"/"False"  014
everything else identical, INCLUDING key order
doc_version absent  (it is not a delta)
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

*(Done, T039: `cuems-nodeconf`'s `tests/packaging/release-gate-demo.sh` in an `mmdebstrap`
bookworm chroot, 9/9, recorded in `specs/016-coordinated-minor-bump/evidence/cuems-nodeconf/`.
Re-run it after rule 4.)*

**Upgrading reshapes `/etc/cuems` for you** (postinst, T040). Watch for its warning, and
answer it with `cuems-reshape-devices --check`. The **show library** is yours to convert, with
**two** commands, and the order matters. *(Corrected 2026-10-17: this section ran
`cuems-convert-documents` alone, and walked on a scratch library it **skipped** every old-shape
document, `1 converted, 1 skipped`.)*

**Check the rollback boundary before converting anything** (writes nothing):

```bash
cuems-reshape-devices --check --library <library>       # old-shape documents; exit 0 = none
#   (it also reads /etc/cuems, or --conf <dir>, which must hold settings.xml)
cuems-convert-documents --check <library>/projects/*/script.xml
#   <path>: version 1, current 2 — needs conversion
#   2 documents: 2 needs conversion
```

**Make room first**: measured, a migrated document's directory grows to **2.29–2.41×**, because
backups are kept and the rewritten document is indented. Budget **2.5×** the library (guide §6.3).

**Convert, at library scale, nodes upgraded first** (guide §6.2):

```bash
cuems-reshape-devices --library <library>                # reshape FIRST
cuems-convert-documents <library>/projects/*/script.xml  # then convert
#   2 documents: 1 converted, 1 current
```

Scripts are found by **root element**, not by name: `script.xml` above is the common case, and
`cuems-reshape-devices` discovers the rest itself.

Then verify the properties that matter. A summary line is not enough, so check each:

```bash
# 1. Every document converted: both checks exit 0, and the summary says "N current".
cuems-reshape-devices --check --library <library> && cuems-convert-documents --check <library>/projects/*/script.xml

# 2. Every rewritten document has a backup. Count DOCUMENTS with one, not .bak files:
#    one document can carry several (one per tool, plus one from an attempt that was skipped).
for f in <library>/projects/*/script.xml; do ls "$f".*.bak >/dev/null 2>&1 || echo "no backup: $f"; done

# 3. Resumability: run the same command again. Already-done documents report "already current"
#    and get no second backup (pinned by tests/integration/test_conversion_resume.py).
```

**The restore point** is each document's **oldest** backup (FR-102b); the newer ones are
intermediates.

**Both rollback drills — executed, not written:**

```
Drill A (pre-conversion):  downgrade the packages. No document is touched. Service returns.
Drill B (post-conversion): downgrade the packages AND restore from the .bak files.
```

**The cluster upgrade**, controller plus at least one node. Safe order: **nodes first**. Afterwards:
every node discovered, adoption preserved, and a show loadable on each.

## Wave 5 — removal *(moved to `v0.1.2`)*

**Moved 2026-10-03** to `specs/planning/deprecated-surface-removal-v0-1-2.md` (R1–R12); nothing is
removed in `0.1.1`. The census still gates it and still reads **zero**, re-run 2026-10-17 with its
paths corrected (this section named `cuems-wsclient/src` and a top-level `cuemsnodeconf`, neither of
which exists, and `tee`'d into a path relative to the wrong directory):

```bash
cd /disk/Projects/StageLab
grep -rn 'cuemsutils\.xml\.XmlReaderWriter\|cuemsutils\.xml\.Parsers\|cuemsutils\.xml\.Settings\|cuemsutils\.xml\.CMLCuemsConverter\|cuemsutils\.timeoutloop\|from cuemsutils.xml import \(NetworkMap\|Settings\|ProjectMappings\|ProjectSettings\|XmlReaderWriter\|CuemsParser\)' \
  cuems-engine/src cuems-editor/src cuems-common cuems-nodeconf/cuemsnodeconf cuems-frontend/src cuems-power-bridge/src 2>/dev/null \
  | grep -v '/\.venv\|/tests\?/\|/specs/' | wc -l      # 0
```

## The ecosystem-wide count

```bash
specs/010-consumer-migration/tools/count-retired-vocabulary.sh   # run from this repository
```

It finds its own denominator (every checkout that reads `network_map.xml`) and de-duplicates by
root commit. 2026-10-17: 57 shipped occurrences, **all exempt, zero live** (guide §5). *(It
replaces a hand-written `grep … */src */cuemsnodeconf`, which named paths by convention and would
have missed a repository laid out differently.)*

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
3. Render it in the UI — unchanged but for the enumerated deltas: **five** since 014 ((a)–(e) in
   `cuems-editor`'s `tests/ws-command-responses.txt`, "project" frame; corrected 2026-10-16).
4. Upgrade a controller and at least one node; the cluster comes back with its topology intact.
