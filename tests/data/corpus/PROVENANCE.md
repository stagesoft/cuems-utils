# Regression corpus — provenance

**Feature**: `004-xml-serialization-core` | **Frozen**: 2026-08-11 | **Task**: T007

Every XML document under `tests/data/corpus/` is recorded here with its origin repository,
the commit that last touched it, and that commit's date. Nothing enters this tree without a
row in one of the tables below.

**Refresh rule**: see **FR-021**. This file does not restate it — FR-021 is the authority,
and duplicating a rule is how the two copies come to disagree. In short: goldens captured
from these documents are never regenerated to make a test pass. Adding a *new* document is
permitted and is picked up automatically (FR-021, SC-016); the prohibition binds existing
goldens.

**Self-containment**: this tree is the only XML input the suite reads. No test resolves a
path outside this repository (FR-022b, SC-015), asserted by
`tests/contract/test_corpus_coverage.py`. Cross-repo access was a **one-time** vendoring
operation on the date above, not an ongoing dependency.

---

## Pinned counts

These numbers are the corpus. "Whatever those directories happen to hold" is not a corpus —
a count that can drift silently cannot anchor SC-PERF-001's new-suite budget, and a document
that vanishes without the count changing takes its coverage with it.

| Directory | Documents |
|---|---|
| `cuems-utils/` | **5** |
| `cuems-engine/` | **16** |
| `cuems-editor/` | **1** |
| `cuems-common/` | **1** |
| `legacy/` | **2** |
| `negative/` | **3** |
| **Total** | **28** |

Generated documents from `src/cuemsutils/create_script.py` are **not** counted here: they
are produced by the harness at capture time rather than vendored, and their goldens live
under `tests/golden/generated/` (T012).

---

## `cuems-utils/` — this repository's own fixtures

Source: `tests/data/`, at `bb71010` (2026-08-11). Copies, not moves — the originals stay
where the existing suite expects them.

| File | md5 (8) | Last touched | Date |
|---|---|---|---|
| `settings.xml` | `b119e7e8` | `ae37389` | 2026-05-15 |
| `network_map.xml` | `3edebe4c` | `b57d0eb` | 2025-11-14 |
| `project_mappings.xml` | `99e60090` | `5ac1d46` | 2026-04-21 |
| `default_mappings.xml` | `ad253162` | `5ac1d46` | 2026-04-21 |
| `outputs.xml` | `cd178d84` | **derived — see below** | 2026-08-11 |

`settings_bad_dmx_auto.xml` is vendored under `negative/` instead, since its whole purpose
is to be rejected.

### `cuems-utils/outputs.xml` is derived, not vendored — and why it had to be

This is the **one** document in the corpus that was not copied from somewhere. It is
`cuems-engine/outputs.xml` with **one character added**: the namespace URI's trailing
slash.

```
engine:  xmlns:cms="https://stagelab.coop/cuems"      <- no trailing slash
schema:  targetNamespace="https://stagelab.coop/cuems/"
```

The engine's `outputs.xml` — the only `outputs.xsd` instance that exists anywhere across
the four repositories — therefore **does not load**:

```
XMLSchemaKeyError: "the namespace 'https://stagelab.coop/cuems' is not loaded"
```

Without a corrected copy, `outputs.xsd` would have **zero** loadable instances and SC-009
("at least one real instance document for each of the six schemas") would be unmeetable —
byte-identity for the outputs path would be asserted against nothing. The original stays
vendored, unmodified, with its rejection pinned by T018; this copy is what gives the sixth
schema an accepted document.

**New finding, recorded for T066.** This is not the `OutputsType` collision of research R4
— that one explains why `outputs.xsd` is never *loaded alongside* `script.xsd`. This is a
second, independent reason nothing has ever validated against it: the only instance in
existence has a namespace typo. Both point the same way — the outputs path has never run.

---

## `cuems-engine/` — the widest source

Source: `cuems-engine/dev/test_xml_files/`, repo at `afff04a` (branch `rc_1`, 2026-08-10).
The only source of an `outputs.xml` instance, of `project_settings.xml`, and of complete
project directories.

| File | md5 (8) | Last touched | Date | Loads today |
|---|---|---|---|---|
| `settings.xml` | `5d5c3913` | `dd7358a` | 2026-05-15 | ✅ |
| `network_map.xml` | `f9e570da` | `da895f6` | 2025-11-20 | ✅ |
| `project_mappings.xml` | `3fb9770b` | `dfcf21f` | 2026-04-20 | ✅ |
| `default_mappings.xml` | `fef906dc` | `f89d279` | 2026-07-16 | ✅ |
| `project_settings.xml` | `7bd31034` | `0c93d46` | 2025-06-05 | ✅ |
| `projects/complex_test/script.xml` | `cb551344` | `91617c2` | 2026-07-22 | ✅ |
| `projects/empty_test/script.xml` | `dc24a9ec` | `caa6bbf` | 2025-08-04 | ✅ |
| `outputs.xml` | `94bf0c53` | `0c93d46` | 2025-06-05 | ❌ namespace |
| `projects/complex_test/project_mappings.xml` | `786028c1` | `40ce93b` | 2025-12-02 | ❌ stale `PutType` |
| `script_one_simple_cue.xml` | `9d708788` | `0c93d46` | 2025-06-05 | ❌ namespace |
| `script_one_cue_in_a_cuelist.xml` | `2b765ed5` | `0c93d46` | 2025-06-05 | ❌ namespace |
| `sample_cue.xml` | `71ebe02b` | `4329254` | 2025-03-06 | ❌ fragment |
| `sample_cuelist.xml` | `ad0d9be8` | `4329254` | 2025-03-06 | ❌ fragment |
| `sample_audiocue.xml` | `a57a10a3` | `4329254` | 2025-03-06 | ❌ fragment |
| `sample_videocue.xml` | `923890e3` | `4329254` | 2025-03-06 | ❌ fragment |
| `sample_dmxcue.xml` | `65318511` | `4329254` | 2025-03-06 | ❌ fragment |

### The "loads today" column is data, not a defect list

Nine of these sixteen are rejected by the current library. **That is not a problem to fix
here** — it is the behaviour T018 pins. The engine may never start rejecting what today's
parser accepts (FR-015), and equally it may not start *accepting* what today's parser
rejects; a document whose rejection is recorded is doing real work in this corpus.

Three distinct causes, all pre-existing and all out of scope for 004:

1. **Namespace without trailing slash** (`outputs.xml`, `script_one_*.xml`) — the same
   typo as the outputs case above. `https://stagelab.coop/cuems` vs the schema's
   `https://stagelab.coop/cuems/`.
2. **Bare-fragment roots** (`sample_*.xml`) — these are `<AudioCue>`, `<Cue>`, `<CueList>`,
   `<VideoCue>`, `<DmxCue>` documents whose root is a cue rather than `CuemsProject`.
   `script.xsd` declares one global element; a fragment cannot validate against it by
   construction. They remain useful as per-cue-type *content* samples and as reject-parity
   cases.
3. **Stale content model** (`complex_test/project_mappings.xml`) — its `<output>` elements
   put `name` before `id`, while `PutType` declares `id` first. The fixture predates a
   schema change and was never updated.

---

## `cuems-editor/` — the library-written reference

Source: `cuems-editor/tests/fixtures/`, repo at `ef74136` (branch `rc1`, 2026-07-09).

| File | md5 (8) | Last touched | Date | Loads today |
|---|---|---|---|---|
| `script_minimal.xml` | `30fb4314` | `0c1cf25` | 2026-07-06 | ✅ |

The most load-bearing single document in the corpus. It was **written by this library**,
not hand-authored, so its root element order is the evidence behind research R2: the
`xs:all` `CuemsScript` type emits alphabetically, not in declaration order. If the `xs:all`
tie-break regresses, this file's golden is what catches it.

---

## `cuems-common/` — the deployed artifact

Source: `cuems-common/etc/cuems/`, repo at `0be3506` (branch `rc_1`, 2026-07-31).

| File | md5 (8) | Last touched | Date | Loads today |
|---|---|---|---|---|
| `network_map.xml` | `fdc5cf12` | `aba0f1c` | 2025-12-11 | ❌ `CuemsNodeDict` |

The file actually shipped to `/etc/cuems/` on nodes — and it **does not validate**. Its
root child is `<CuemsNodeDict>`; `network_map.xsd` expects `<node_list>`. Recorded, pinned
by T018, and left alone: the node-identity contract belongs to feature 007, and changing
either side here would be a behaviour change (FR-015).

---

## `legacy/` — historical, still valid (FR-035d)

Compatibility evidence: documents written by **older** code that must keep loading. Recovered
from release tags and sibling fixture history.

| File | md5 (8) | Origin | Loads today |
|---|---|---|---|
| `script_complex_test-engine-e6fc6c9.xml` | `7f518a9b` | `cuems-engine` `e6fc6c9`, `dev/test_xml_files/projects/complex_test/script.xml` | ✅ |
| `script_complex_test-engine-e7215ae.xml` | `662c1388` | `cuems-engine` `e7215ae`, same path | ✅ |

Both are earlier revisions of the `complex_test` script, distinct from the current
`cb551344` and from each other, and both still load. That is exactly the property FR-035a
asserts.

### What T006a expected to find here, and what the measurement actually said

T006a named `settings.xml` at `v0.1.0rc11` and `v0.1.0rc14` as qualifying legacy documents.
They do validate — but they are **byte-identical to the current fixture** (`b119e7e8`,
which is also what `v0.1.0rc8` shipped). Vendoring them would add a third and fourth copy
of a file already in the corpus and zero coverage, so they are not vendored.

The search was then widened rather than abandoned, across every tag and both sibling
histories:

| File | Distinct historical variants | Still valid |
|---|---|---|
| `cuems-utils` `settings.xml` | 9 | only the current one |
| `cuems-utils` `network_map.xml` | 3 | only the current one |
| `cuems-utils` `project_mappings.xml` | 3 | only the current one |
| `cuems-utils` `default_mappings.xml` | 3 | only the current one |
| `cuems-engine` `complex_test/script.xml` | 3 | **all three** ← vendored |
| `cuems-engine` `outputs.xml` | 2 | none |

The pattern is consistent and worth stating plainly: **every configuration schema has
broken compatibility with its own history at least once**, while `script.xsd` — the format
that actually holds user work — has not. Config files are regenerated on deploy; scripts
are the thing on disk that must survive. So the two vendored script revisions are the real
compatibility obligation, and their absence from the config side is a finding rather than
a gap in the search.

---

## `negative/` — parity cases only (FR-015, FR-035a)

**These are not compatibility obligations.** They are documents the current library rejects,
vendored so that it keeps rejecting them for the same reason. See
[`negative/README.md`](./negative/README.md) — out of scope per FR-035a, recorded as X13.

| File | md5 (8) | Origin | Rejected by |
|---|---|---|---|
| `settings_bad_dmx_auto.xml` | `341f8a1a` | `cuems-utils` `tests/data/`, `ae37389` (2026-05-15) | `XMLSchemaDecodeError` |
| `settings-utils-v0.1.0rc2.xml` | `f7bf0a4a` | `cuems-utils` tag `v0.1.0rc2` | `XMLSchemaChildrenValidationError` |
| `settings-utils-v0.1.0rc7.xml` | `07b7023d` | `cuems-utils` tag `v0.1.0rc7` | `XMLSchemaChildrenValidationError` |

---

## Coverage: all six schemas have an accepted instance

Confirmed by `tests/contract/test_corpus_coverage.py` (T008), which fails if any schema
loses its last loadable document.

| Schema | Accepted instances |
|---|---|
| `script` | `cuems-editor/script_minimal.xml`, `cuems-engine/projects/complex_test/script.xml`, `cuems-engine/projects/empty_test/script.xml`, both `legacy/` revisions |
| `settings` | `cuems-utils/settings.xml`, `cuems-engine/settings.xml` |
| `network_map` | `cuems-utils/network_map.xml`, `cuems-engine/network_map.xml` |
| `project_mappings` | `cuems-utils/project_mappings.xml`, `cuems-utils/default_mappings.xml`, `cuems-engine/project_mappings.xml`, `cuems-engine/default_mappings.xml` |
| `project_settings` | `cuems-engine/project_settings.xml` |
| `outputs` | `cuems-utils/outputs.xml` — **the only one**, and it exists only because of the namespace correction documented above |

`project_settings` and `outputs` each rest on a single document. Neither has a second
instance anywhere in the four repositories.
