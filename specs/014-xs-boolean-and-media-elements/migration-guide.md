<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 014

**This document is also the rule-4 release note.**
`specs/agreements/schema-evolution-convention.md` rule 4 requires three things of a versioned
file-format migration: *a version marker that lets a reader tell old from new; a conversion that
runs on read, or a documented tool that runs once; and a release note naming what has to be
converted and when the old form stops being accepted.* The first two exist by design
([`plan.md`](plan.md) §2); **§4 below is the third**, and it is the one deliverable that cannot be
inferred from anything else in this feature.

**It accumulates as the work lands** rather than being written at the end — 010's T002 precedent.
Sections marked *(pending)* have a task against them in [`tasks.md`](tasks.md).

---

## 1. What changes, in four sentences

1. **Booleans become real booleans.** `cms:BoolType` — an `xs:string` enum of `True`/`False` — is
   retyped to the standard `xs:boolean`, so XML text becomes `true`/`false` and the JSON wire
   carries `true`/`false` instead of `"True"`/`"False"`.
2. **`MediaType` gains four optional elements**: `pixel_width`, `pixel_height`, `file_size` and
   `file_hash`.
3. **`FadeCurveType` gains `ease_in` and `ease_out`**, cherry-picked from `main`.
4. **`ConfigManager.from_json(SchemaName, payload)`** is new: the first public way to build a
   configuration document from JSON, which is what `cuems-editor`'s `config_save` has been waiting
   for.

**No new schema version.** All of it lands in the **existing, unreleased** `script` 1 → 2 and
`network_map` 1 → 2 steps. `0.1.0rc16` does not move.

## 2. The media block is **four** elements, not three *(T008)*

The input document
([`../planning/media-pixel-dimensions-for-xml-refactor.md`](../planning/media-pixel-dimensions-for-xml-refactor.md)
§1) specifies three. **Read this instead**, and note two naming points it is easy to get wrong:

| Element | Type | Note |
|---|---|---|
| `pixel_width` | `xs:positiveInteger` | the media's **original** size, as `ffprobe` reports it — not the layer's size on screen. `width`/`height` already mean something else in `CanvasRegionType` |
| `pixel_height` | `xs:positiveInteger` | |
| `file_size` | `xs:positiveInteger` | **`file_size`, not `size`.** Bytes. Holds a file well past 100 GB — see below |
| **`file_hash`** | `cms:Md5HashType` | **the fourth, new in this feature.** 32 **lowercase** hex characters |

All four are `minOccurs="0"`, appended after `regions`. **Every existing project stays valid.**

⚠ **The test fixture is *not* in `tests/data/corpus/`**, which T001 originally said. Corpus
membership requires a **pre-refactor verdict** in `tests/golden/outcomes.json`, and a document
carrying these four elements cannot have one — the pre-014 schema rejects it. Inventing an entry
would be fabricating a verdict for a document that did not exist when those verdicts were taken.
It lives in `tests/data/media_block/`; the reasoning is in `tests/data/corpus/PROVENANCE.md`.

**Three rules that are one rule:** absent means *unknown*; `0` is **not** a value and is refused by
the type; never write an empty element. `<pixel_width/>` fails `xs:positiveInteger` — which is
deliberate, since a zero-byte or zero-pixel file is not playable media.

**`file_size` holds a file larger than 100 GB, verified.** 100 GiB is 107,374,182,400 bytes, which
overflows a 32-bit int. `xs:positiveInteger` has **no upper bound** and decodes to an
arbitrary-precision Python `int`; 2⁶³ validates too. Nothing to configure.

**`file_hash` is lowercase-only**, matching `UuidType`'s existing `[a-f0-9]` pattern. `md5sum`,
`hashlib` and `ffmpeg` all emit lowercase. Uppercase is refused on purpose: a wider ingestion
vocabulary than the schema's means a value legal on the wire that can never appear in a file.

### 2.1 The setters' contract, as implemented (T005)

What a consumer can hand these four, measured against the landed code:

| Input | Result |
|---|---|
| `int` ≥ 1 | stored |
| a string of digits (`"107374182400"`) | stored as `int` |
| `None` | **the key is removed**, not set to `None`. Absent means unknown, and that is the only way to say so |
| `0`, a negative | **`ValueError`** |
| `1.5`, `"1.5"`, a list, a dict | **`ValueError`** — deliberately *not* `int(value)`, which truncates. `1.5` would have stored 1: a wrong value that looks right, which is the defect class this feature exists to remove |
| `True` / `False` | **`ValueError`** — `bool` is an `int` subclass, so without the guard `media.pixel_width = True` would store 1 |
| `file_hash` uppercase | **`ValueError`**, not lowercased. Normalising would leave the object and the document disagreeing about what is valid |

**Raising at the assignment rather than at the save is the point.** The schema would refuse these
at `save()` anyway; failing earlier names the field and the line that caused it.

**For `cuems-engine`**: a hash is a strictly stronger "was this file replaced under the same name?"
test than comparing `file_size` against `os.stat` — a replacement of identical length passes the
size check and fails the hash. **What you compare is your decision**, including whether hashing a
multi-gigabyte file at arm time is acceptable where `os.stat` was free. The element is optional, so
an engine that ignores it is correct.

## 3. The boolean change, per consumer

| Repository | What it must do |
|---|---|
| `cuems-engine`, `cuems-nodeconf`, `cuems-power-bridge`, `cuems-common` | **no source change** — they hold objects, which were always real `bool`s. **Fixtures only**; the paths are in §4.1 |
| `cuems-editor` | **no source change** for the boolean — it returns `to_wire()` and its own FR-012 forbids touching the dict. One payload-version bump. Fixtures per §4.1. **Its T059 does *not* close by re-run — see §3.1** |
| `cuems-frontend` | **one line is hard-coupled and mutual**: `sequence.component.ts:997` writes `'True'`, which this feature makes a **refused** spelling, so saving fails without it — and this feature cannot ship without it. Its own `06-amendment-feature-014.md` is the authority; its 001 began its SDD path 2026-10-03 |

### 3.1 `cuems-editor`'s T059 needs an edit there after all *(T023 — correction)*

**T023 said the editor's T059 "closes by re-run only". Measured, it does not.** Its
`test_config_save_of_settings_persists_through_save_settings` is still **XFAIL**, not XPASS, with
`ConfigManager.from_json` present and the editor's hatch environment resolving `cuemsutils` to this
working tree (verified: `0.1.0rc16`, `/disk/Projects/StageLab/cuems-utils/src/cuemsutils/__init__.py`).

**Why.** `CuemsWsUser.config_save` does not *attempt* an ingestion and fall back. It validates the
schema name, applies `CONFIG_SAVE_REFUSED`, and then calls `notify_error_to_user` for all four
configuration domains **unconditionally** — the message naming UR-5. There is no call site for a
library ingestion to satisfy, so no library change can turn that test green. T023's premise was
that the workaround was a guarded fallback; it is a hard-coded refusal.

**What the library owes, and it is complete.** The whole of UR-5's "Expected" is shipped, including
the payload shape that repository actually sends:

- `ConfigManager.from_json(SchemaName, payload)` exists, takes the three forms, and returns the root
  object the matching `save_*` writes;
- the payload in T059 is `manager.to_wire('settings')`, which is **one level deeper** than the
  `settings` document (`Settings.main_key` is `'Settings'`, so `ConfigBase.settings` is the root's
  field, not the root). That exact shape is accepted — pinned by
  `tests/integration/test_config_ingestion.py::test_from_json_ingests_this_librarys_own_settings_projection`,
  which exists for no other reason.

**What is left is in that repository**: replace `config_save`'s final `notify_error_to_user` with
the ingestion, the save and a `{'type': 'config_save', 'value': 'OK'}` frame — the four `save_*`
paths it already names in its own docstring. Roughly six lines. **Not done here**: T023 says *"Do
not edit that repository"*, and that instruction is kept.

⚠ **There is no public installer, by decision.** `from_json` hands back the object; the object
carries `save(path)`, which is the same body `save_settings` / `save_network_map` /
`save_project_settings` / `save_project_mappings` delegate to. Those accessors write what a
`ConfigManager` *holds*, and two of the four domains hold it on a private attribute
(`_settings_document`, `_project_settings_document`), so an installer would have been four new
public names against the one this is specified as ([`plan.md`](plan.md) §9.3). The consumer path is:

```python
manager  = ConfigManager(load_all=False)
document = manager.from_json(SchemaName.SETTINGS, payload)
document.save(manager.conf_path('settings.xml'))
```

### 3.2 One asymmetry this closed on the way through *(T022)*

`encode_wire` wrapped a repeated member that decoded **bare** in its *class* name, and
`decode_config` had no branch for that key — so `project_settings`' wire form
(`{"setting": [{"SettingType": {…}}]}`) was not ingestible by its own library: the body was stored
as undescribed content and the document would not save. Every other repeated block in every other
configuration schema decodes with an element wrapper (`{"node": …}`, `{"device": …}`) which is
re-encoded in place, which is why nothing saw this until a configuration wire form was fed back in
for the first time.

Fixed in `Mapper._decode_config_item`, **not** in `from_json`, so the ingestion keeps decoding
through exactly the call `load_*` uses. It cannot move a recorded golden: `xmlschema` never emits a
*type* name as a dict key, so no document decode has ever reached the new branch — and the golden
manifest is unchanged apart from `api/public_api.json` gaining the one new method.

## 4. The release note — what must be converted, and when the old form stops being accepted

> **Rule 4's third deliverable** (T024, T025). Rule 4's own sentence is the standard: *"'We will
> just update the files on the nodes' is not a conversion path. Nobody knows where all the files
> are."* So the paths below are **named, not counted**.

**What must be converted**: every XML document carrying `<autoload>`, `<enabled>`, `<timecode>`,
`<adopted>` or `<online>` with the text `True` or `False`. Nothing else in any schema is affected —
`settings.xsd`'s `BoolType` declaration was dead (no element referenced it) and
`project_mappings.xsd`/`project_settings.xsd` declare no boolean at all, so **no `settings.xml`,
`mappings.xml` or project `settings.xml` needs converting**. Only `script.xml` and
`network_map.xml` documents do.

**Find them with this, in any checkout or on any node:**

```bash
# NOT --include='*.xml'. That filter misses two real classes, both measured:
#   cuems-common/etc/cuems/network_map.xml.example   (a shipped document)
#   inline XML literals in test sources (.py)
grep -rlE '<(autoload|enabled|timecode|adopted|online)>(True|False)</' . \
  --exclude-dir=.git --exclude-dir=tmp
```

⚠ **A grep for the element form is necessary and not sufficient.** It does not find a document
assembled from an f-string, nor a Python literal `'True'` assigned to one of these fields, nor a
*docstring* that teaches the retired spelling. All three exist in the tree — see §4.1's last two
rows — so each repository's own suite going green is the check, not the grep going quiet.

**Three routes, and which one a file takes is decided by its `doc_version`:**

| | Count at the branch point | Route |
|---|---|---|
| **No `doc_version`**, or version 1 | **51 files** | **Automatic.** The registry's 1 → 2 step carries the rewrite and runs on read. `cuems-convert-documents` persists it |
| Already marked **`doc_version="2"`** | **9 files** | **Manual, out of band** — §4.2. The registry will not touch them: they are already current, so there is no step to run |
| **Live, on a node** | not countable | **`cuems-convert-documents`, per node** — §4.3 |

### 4.1 The 51 automatic ones, by path

Ten are already converted (this repository, T015a). The remaining **41** are below. The tool is the
same everywhere:

```bash
# ⚠ cuems-convert-documents takes FILES, not a directory. A directory argument
# is reported "skipped ([Errno 21] Is a directory)" and exits 1 — verified.
find <directory> -name '*.xml' -print0 | xargs -0 cuems-convert-documents
```

Each converted document gets a sibling backup named `<file>.<YYYYmmddTHHMMSS>.bak` before a byte is
rewritten, and a backup failure is fatal **for that document only** — the batch continues. The tool
is idempotent, so a second pass over an already-converted tree reports `already current` and
changes nothing.

🔴 **It silently destroys every XML comment in the document.** Found by `cuems-common`'s gate
(T031) and measured here: `etc/cuems/network_map.xml.example` went **10 comments → 0, 40 lines →
24**, with no warning and exit 0. `cuems-reshape-devices` behaves the same way — both write through
`write_tree`, i.e. stdlib `ElementTree`, which does not retain comment nodes on parse.

**What survives, measured, because the blast radius matters and the first report overstated it:**

| | |
|---|---|
| XML comments | 🔴 **destroyed**, all of them, silently |
| Indentation and whitespace | ✅ **preserved** — it is text, so ElementTree keeps it. The 40 → 24 above is exactly the 16 comment lines, nothing else moved |
| `xsi:schemaLocation` | ✅ **preserved** — verified on a corpus document that carries one |
| `xmlns:xsi` with **nothing using it** | ⚠ dropped — and **harmless**: an unused namespace declaration carries no information. T031 reported this alongside the comments; it is correct as observed and is not the same severity |

So the one thing to protect is the comments.

This is **not** new behaviour and **not** 014's, but 014 is the first release note that tells
operators to run the tool over live files, so it is the first time it matters:

- **Hand-rewrite any document whose comments are part of its value** — what that gate did for its
  annotated example, and what `cuems-nodeconf` did to carry one dmx-latency comment into its
  reshaped `<player>` block.
- **`/etc/cuems/network_map.xml` is a `dpkg` conffile that operators edit** (see `cuems-common`'s
  `debian/postinst`, which reasons at length about `.dpkg-dist`/`.dpkg-old`). If a node's map carries
  operator comments, the `.bak` is the only copy afterwards — and nobody reads a `.bak`.
- The property is **undocumented and untested** here: no test asserts either preservation or loss,
  so nothing would catch it changing in either direction. Worth a pinning test whichever way it is
  decided, and that decision is not 014's.

⚠ **`cuems-reshape-devices` is not symmetric with it**, which matters for §4.5: given paths it also
takes files, but given *no* paths it **discovers** a tree from `--conf` / `--library` (or
`CUEMS_CONF_PATH`). `cuems-convert-documents` has no discovery mode at all. So the two tools cannot
be handed the same argument, and the `find | xargs` form above is the one that works for both.

| Repository | Paths | Elements | Gate |
|---|---|---|---|
| `cuems-utils` | `tests/data/corpus/{cuems-engine,cuems-editor,cuems-utils}/**`, `tests/data/corpus/cuems-engine/projects/*/script.xml` — **10 documents, 116 elements, done** (T015a) | 116 | — |
| `cuems-engine` | `dev/network_map.xml`, `dev/test_xml_files/network_map.xml`, `dev/test_xml_files/script_one_cue_in_a_cuelist.xml`, `dev/test_xml_files/projects/{complex_test,empty_test,fade_actions_v1}/script.xml` — **6** | 78 (incl. §4.2's one) | T028 |
| `cuems-power-bridge` | `tests/fixtures/network_map/map-{no-self,controller-only,mixed,none-adopted,two-adopted,partial-resolve,unresolvable,no-settings}/network_map.xml` — **8 of 10** ✅ done `dd1256f`. ⚠ **`map-incomplete` and `map-pre007` must stay old-form** — they exist to test `NETWORK_MAP_INVALID` (missing `<mac>`) and `NETWORK_MAP_RETIRED_VOCABULARY` (old `<node_type>`); the tool correctly refused both. Same rule as the editor's `script_minimal.xml`: **a fixture whose purpose is to be refused keeps the form it is refused for**. It also hand-fixed **9 `settings.xml`** for the separate 013/F3 dead end | 46 | T029 |
| `cuems-editor` | `tests/fixtures/conf/network_map.xml`, `tests/fixtures/script_minimal_013.xml`, `specs/001-cuems-utils-migration/evidence/mappings-capture/network_map.xml` — **3 of 4**. ⚠ `tests/fixtures/script_minimal.xml` is the **fourth and must stay old-form**: its own `tests/fixtures/README.md` records why (the pre-migration payload capture *and* the `SKIPPED_INVALID` fixture). This gate is "convert the three and confirm the fourth is still refused, **for the right reason**" | 38 | T032 |
| `cuems-common` | ✅ **done** `e595e67`. `tests/fixtures/maps/converted.xml` **and `etc/cuems/network_map.xml.example`** — **2 documents + 2 test modules + 3 doc files**; `unconverted.xml` deliberately left (orphaned, never schema-valid). ⚠ The example is the one that *breaks a test*: `tests/test_documented_validation.py::test_documented_command_accepts_valid_maps[example]` validates it **directly against cuems-utils' `network_map.xsd` with no version conversion**, so `True` is simply invalid there now. ⚠ It no longer mirrors the XSDs — feature 011 transferred custody and its `postinst` copies cuems-utils' own `/usr/share/cuems/schemas/network_map.xsd`, so there is **no stale mirror to move** (this row said otherwise until 2026-10-05) | 12 | T031 |
| `cuems-nodeconf` | `tests/fixtures/etc_cuems/network_map.xml` — **1**. Also the one repository that **writes** `network_map.xml` every 30 s, so confirm its write path emits the new form | 4 | T030 |

**Two classes a path list does not reach, and both are real:**

| Class | Where | What to do |
|---|---|---|
| **Inline XML literals in test sources** | `cuems-common/tests/test_controller_resolution.py`, `cuems-common/tests/test_network_map_conversion.py` — ✅ **done** `e595e67` | Same treatment as this repository's T015a, which fixed 16 literals across 7 modules. ⚠ My "convert **both sides or neither**" warning here rested on a wrong assumption — that `tests/fixtures/maps/{converted,unconverted}.xml` were a pair consumed by that test. They are not: **both are orphaned**, no test references either, and T031 converted `converted.xml` while deliberately leaving `unconverted.xml`, which predates the `node_type`→`node_role` migration and was never schema-valid regardless of boolean spelling. The *inline* literals were the real work |
| **Docstrings teaching the retired spelling** | `cuems-editor/src/cuemseditor/CuemsWsServer.py:435`, `cuems-nodeconf/CLAUDE.md`, `cuems-nodeconf/specs/001-network-map-object-adoption/quickstart.md` | One-line doc corrections. §3's "no source change" is about *behaviour* and still holds — the editor returns `to_wire()` untouched — but a docstring documenting the old wire form is now wrong |

**Frozen, do not touch**: `cuems-engine/specs/008-cuems-utils-migration/evidence/baseline-suite*.txt`
and `cuems-editor/specs/001-cuems-utils-migration/evidence/suite-after-import.txt` are **captured
test output** in landed feature directories. They record what a run *said* on a given day; rewriting
them would falsify evidence, which is the opposite of what they are for.

**Deliberately *not* converted, in this repository — 18 files, 195 elements.** They carry the old
form because that is what they are *for*, and converting them would delete the evidence the
conversion works:

- `tests/data/corpus/pre-008/**` (12 files) and `tests/data/corpus/pre-013/script.xml` — the
  pre-version corpus tiers, read **through** the registry. `pre-008/script_v1_all_transforms.xml`
  is the rewrite's only in-corpus evidence, and `test_boolean_conversion.py` asserts it still
  carries an old-form boolean so a future fixture edit cannot silently remove it (T014).
- `specs/007-node-model-migration/pre-state/**` (4 files) — a landed feature's directory is frozen
  historical record. `test_network_map_roundtrip.py` normalises on the side that **moved**, beside
  the existing `doc_version` strip (T017 ⚠(b)).

### 4.2 The nine already-`doc_version="2"` ones, by filename *(T025)*

**Why this row exists at all, stated plainly rather than left to be discovered.** This feature puts
the rewrite into the *existing, unreleased* `script` 1 → 2 and `network_map` 1 → 2 steps rather than
adding a version 3. So `doc_version="2"` is **briefly ambiguous** — it means both the pre-boolean
and the post-boolean shape — and **the version marker cannot tell them apart**. The registry sees a
current document and runs nothing. That is feature 012's situation verbatim, and its lesson applies:
the machinery represents such a step by the *absence* of a registry entry, and the repair is
cross-document and out-of-band **by design**. The trade was measured, not assumed: 51 convert free,
nine need hands, and six of the nine were goldens already due for re-cutting.

The ambiguity window closes when the coordinated `xml-refactor-merge-candidate` tag ships, because
nothing outside these checkouts has ever been written at version 2.

| # | File | How | Status |
|---|---|---|---|
| 1 | `tests/golden/xml/cuems-editor__script_minimal.xml` | re-cut | ✅ T015 |
| 2 | `tests/golden/xml/cuems-engine__projects__complex_test__script.xml` | re-cut | ✅ T015 |
| 3 | `tests/golden/xml/cuems-engine__projects__empty_test__script.xml` | re-cut | ✅ T015 |
| 4 | `tests/golden/xml/cuems-utils__fade_showcase.xml` | re-cut | ✅ T015 |
| 5 | `tests/golden/xml/cuems-utils__unicode_showcase.xml` | re-cut | ✅ T015 |
| 6 | `tests/golden/generated/example_script.xml` | re-cut | ✅ T015 |
| 7 | `tests/data/corpus/cuems-utils/fade_showcase.xml` | **hand-rewritten** — authored, not generated | ✅ T015 |
| 8 | `tests/data/corpus/cuems-utils/unicode_showcase.xml` | **hand-rewritten** | ✅ T015 |
| 9 | `../cuems-engine/dev/test_xml_files/projects/complex_test_v2/script.xml` | **hand-rewritten** — the ninth, and it is **in a sibling** | ⚠ **outstanding** |

⚠ **Item 9 is still old-form, verified 2026-10-05.** T015 claimed it and T015's completion note
does not mention it, so it was missed rather than deferred. It is a *sibling* file and T028 is the
gate that was written to "verify the result in place" — so it is named here as outstanding rather
than rewritten from this repository. **T028 must rewrite it, not merely check it.** A plain
`cuems-convert-documents` pass will **not** fix it: the file is already `doc_version="2"`, which is
exactly what §4.2 is about.

**`tests/golden/outcomes.json` is not on this list and must not be touched.** It records
*pre-refactor* verdicts and a test asserts the **difference** between it and live behaviour;
`capture_goldens --force` over it destroys that baseline. Verified: it carries no boolean form, so
this feature does not need to.

### 4.3 The two live locations, which are neither of the above

No glob finds these and no test suite covers them. They are the reason rule 4 exists.

| Where | What | When |
|---|---|---|
| **`/etc/cuems/network_map.xml`**, on **every node** | `<adopted>` and `<online>` per row | Converted on read automatically (it is unmarked), but **`cuems-nodeconf` rewrites it every 30 s** and `CuemsNetworkMapType.save()` bumps the marker — after which an **older** `cuems-utils` refuses it with `DocumentTooNewError`. So: upgrade the package *before* nodeconf restarts, and there is **no rollback** afterwards (012's migration guide §9b, same mechanism). ⚠ **Check for operator comments first** — the tool deletes them (§4.1); nodeconf's next write would have too |
| **Each node's project library** — `<library_path>/projects/*/script.xml` | `<autoload>`, `<enabled>`, `<timecode>` per cue | Converted on read. Persist it with one pass per node: `find <library_path>/projects -name '*.xml' -print0 \| xargs -0 cuems-convert-documents` |

`/etc/cuems/settings.xml`, `/etc/cuems/default_mappings.xml` and each project's `mappings.xml`
**need nothing** — their schemas carry no boolean element (see the top of §4).

**On an offline node** `cuems-convert-documents` is already installed by the package; it needs no
network. The library's own read path converts in memory regardless, so a node that is never
converted still *works* — what it loses is the persistence, and it keeps paying the conversion on
every read.

### 4.4 When the old form stops being accepted

**Immediately on this feature**, for reading *and* writing. `"True"` is a refused spelling at
`from_json` and `True` is invalid XML text in those five elements. **There is no grace period and no
dual-accept window**, deliberately: a wider ingestion vocabulary than the schema's is a value legal
on the wire that can never appear in a file — the same argument that makes `file_hash` lowercase-only
(§2) and the same defect class `_Bool.decode` was fixed for in `be3e86e`.

The date is the coordinated `xml-refactor-merge-candidate` tag, after features 011–015. `0.1.0rc16`
does not move and no stable release cuts here.

### 4.5 The order, if a document needs both migrations

013's device shape and this one:

```bash
find <directory> -name '*.xml' -print0 > /tmp/docs           # one list, used twice
xargs -0 cuems-reshape-devices  < /tmp/docs   # device shape — no version step
xargs -0 cuems-convert-documents < /tmp/docs  # 1 → 2 — now carrying the boolean rewrite
```

**That order, or neither completes**: reshape-first sees a version-1 `<duration>`, convert-first
sees old-shape cues. `cuems-power-bridge` and `cuems-engine` both needed both (T029, T028).

🔴 **A third order exists, for the one class §4.2 is about, and the two above do not cover it.**
Found by `cuems-engine`'s gate (T028) and reproduced here on
`dev/test_xml_files/projects/complex_test_v2/script.xml`. A document that is **already
`doc_version="2"`**, carries **old-form booleans** *and* is **old device shape** fails
reshape-first:

```
cuems-reshape-devices <file>
  -> skipped (would not validate: failed validating 'False' with
     XsdAtomicBuiltin(name='xs:boolean'); Reason: 'False' is not a boolean value)
```

**Why**: reshape validates its output *as the load path will see it*, which applies any **registered
version conversion** — and for a document already at the current version there is none to apply, so
the booleans are never rewritten and the current schema refuses them. §4.2's ambiguity in operational
form.

**The order that works, verified** — booleans by hand *first*, because no tool will do it for a
version-2 document:

```bash
# 1. case-only substitution on the five elements, by hand or by script.
#    Assert case-only: new.lower() == old.lower() for every substitution.
# 2. then the device shape:
cuems-reshape-devices <file>          # -> reshaped
# 3. convert is then a no-op, correctly:
cuems-convert-documents <file>        # -> already current
```

So the full decision is **three-way**, not two:

| Document | Order |
|---|---|
| version 1, old shape | `reshape` → `convert` (§4.5 above) |
| version 1, current shape | `convert` alone |
| **version 2, old shape, old booleans** | **hand-fix booleans → `reshape`** (`convert` is then a no-op) |

On a **node** rather than a checkout, reshape's discovery mode is the better first half
(`cuems-reshape-devices` with no paths, which reads `CUEMS_CONF_PATH` and the library); the second
half still needs the `find | xargs` form, because convert has no equivalent.

## 5. Rollback *(pending)*

## 6. What this feature does not do

- **No `v0.1.1` and no deprecated-surface removal** — `../planning/deprecated-surface-removal-v0-1-1.md`.
- **No `hardware_outputs`** — that is **015**.
- **No descriptor union support** — `NodeUuidType` still reports as an enumeration of one value
  ([`plan.md`](plan.md) §9.5).
- **No frontend code** — unloaded to that repository ([`plan.md`](plan.md) §6.2).
