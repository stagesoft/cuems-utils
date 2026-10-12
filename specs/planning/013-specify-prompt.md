<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Prompt — start feature `013-device-class-reshape`

**Paste everything below the rule into a new session in `cuems-utils`.** Short
on purpose: 013 runs in this repository, so the session has `CLAUDE.md` and the
planning documents already. Only what those do *not* say is inlined.

---

Start the specification for **`013-device-class-reshape`** (F6) in `cuems-utils`.

Branch from **`feat/xml-refactor`** at `fee13e8`, where feature 012 merged
2026-10-01. Suite baseline there: **3247 passed, 115 skipped, 2 xfailed, ~53 s**.

## Read

| Document | For |
|---|---|
| `specs/planning/etc-cuems-first-install-execution.md` → "Feature 013" | the brief: scope, dependency, kind |
| `specs/planning/etc-cuems-first-install.md` §8.4 | the design and the **~20-site cost table** this feature exists to collapse |
| `specs/agreements/schema-evolution-convention.md` | binding. 013 is a **rule-4** migration |
| `specs/012-uuid4-convergence/` | the precedent to follow — and to differ from, see below |
| `specs/planning/refactor-sequencing-2026-10-01.md` | why 013 is next, and what waits on it |

## What it delivers

A new hardware class costs **data, not schema**. Today it costs ~20 sites across
four schemas and four repositories:

- `settings.xsd`, `project_mappings.xsd`, `script.xsd`, `hardware_outputs.xsd` —
  a declaration each
- `ConfigManager.py:69` — `_DEVICE_SECTIONS = ('audio', 'video', 'dmx')`,
  a hardcoded triple, consumed at `:386` and `:659`
- `ConfigManager.py:160` — `node_hw_outputs`' six fixed keys
  (`audio_inputs`/`audio_outputs`/`video_inputs`/`video_outputs`/`dmx_inputs`/`dmx_outputs`)
  become per-class
- `cuems-frontend` — four cue-type unions, at
  `src/app/components/projects/project-edit/sequence/sequence.component.ts:294-304`

Mechanism: `<device class="…">` with XSD 1.1 `xs:alternative` conditional type
assignment.

## Four things the documents do not say, or say less sharply

1. **The mechanism is already proven; the migration is the work.** Measured
   2026-09-23 under the pinned `xmlschema==3.4.3`: a document carrying
   `<device class="lighting">` validates with **no schema change**, while
   `<canvas_region>` on a non-video device is still rejected. Do not re-litigate
   feasibility in the spec — scope the migration.

2. **Unlike 012, this one needs a registered conversion.** 012 registered
   **none**, deliberately: its repair was cross-document and out-of-band, and
   the registry represents an identity step as the *absence* of an entry. 013
   reshapes documents in place, so it is a version step **and** a `Conversion` —
   the first real exercise of that registry since feature 008's `script` 1→2.
   Read `xml/versioning.py`'s `Conversion` docstring before planning, and note
   `tests/contract/test_version_marker.py`'s `DELIBERATE_IDENTITY_STEPS`
   allowlist: 013's steps must **not** go in it.

3. **`cuems-frontend` is waiting on this feature, by decision.** Its migration
   (flow 05 of feature 010) was deliberately deferred because
   `sequence.component.ts` is both its largest site and 013's. Its US8/T032
   requires characterization tests committed *before* its port — so whatever
   013 settles about the cue-type unions is that flow's input. State the
   contract 013 hands it; do not leave the frontend to infer it.

4. **013 comes before 014 by advice, not by a hard gate** — but 014 moves the
   port inventory out of `project_mappings` and retires `default_mappings.xml`,
   so decide early whether `node_hw_outputs`' reshape belongs here or there, and
   record the split. Two features touching the same accessor in sequence is
   fine; discovering the overlap mid-implementation is not.

## Standing constraints

- **No library version bump.** `0.1.0rc16` is pinned by
  `tests/packaging/test_no_version_bump.py`.
- **Nothing ships from this branch alone** (D27). The coordinated
  `xml-refactor-merge-candidate` tag comes after 011–014.
- **Budgets are stated as values and recorded as measured**, including when
  exceeded. 012's `baseline.md` is the pattern, including its own two exceeded
  budgets and why re-baselining from measurement beat inheriting an estimate.
- **Schema changes move with their pins in one commit**:
  `CURRENT_SCHEMA_HASHES` in `tests/contract/test_schema_scope.py`, and the
  allowlists in `tests/contract/test_schema_name_overlap.py` — whose
  `KNOWN_DIVERGENT_DECLARATIONS` is now **empty** and should stay that way.
- **Commits are GPG-signed.** On `gpg failed to sign`, retry; never
  `--no-gpg-sign`.

## Two open items that may belong here

Both are consumer-reported gaps of one shape — a capability inside
`cuemsutils.xml` with no public path out — recorded in
`specs/010-consumer-migration/migration-guide.md` §5b:

- **UR-1**: `partition_by_adoption` is internal-only; no public call answers
  "which nodes are adopted". `cuems-editor`'s feature 001 will hit this within
  days.
- **UR-5**: `XmlReaderWriter.validate`'s deprecation advice sends every schema
  to `CuemsScript.validate`, which cannot validate a configuration document.
  There is no public stand-alone validator for those.

Decide in `/speckit.clarify` whether 013 absorbs either, or whether they belong
to 014's public-surface pass. Do not leave them unassigned a third time.

## Run

```
/speckit.specify
```
