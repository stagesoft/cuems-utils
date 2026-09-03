# Feature 010 — `cuems-utils`: descriptor path, deprecation removal, the guide

**Status:** ready to run — **starts first, finishes last**
**Date:** 2026-09-03 (scope corrected the same day — see "What is actually left")
**Repository:** `/disk/Projects/StageLab/cuems-utils`
**Run order:** 00 of 06 — ITEM 1 is a precondition of
[02 `cuems-editor`](02-cuems-editor.md) and [05 `cuems-frontend`](05-cuems-frontend.md);
ITEM 2 is gated on **all six** consumer flows. See the [index](README.md).

## What is actually left in this repository, and why it is not zero

Part 4 §8 framed feature 010 as "this spec lives in `cuems-utils` and defines the
contract and guide; the edits happen in each consumer repo as its own PR". That
made it easy to read this repository's own share as empty. Checked against the
goal documents on 2026-09-03, it is not — three items remain, and one of them is
the last gate before the ecosystem can release.

Everything in the target design's §12 table (`xml-rebuild-06-target-design.md`)
is a **consumer** row: `cuems-engine`, `cuems-editor`, `cuems-nodeconf` (already
done by 007 — `CuemsNode.py` and `NodeXmlBuilders.py` are confirmed deleted),
`cuems-common`, `cuems-frontend`. `cuems-utils` has no row there. But §8's own
"WHAT MUST BE TRUE WHEN DONE" list carries three library obligations that §12
never tabulated:

| Obligation | Source | State 2026-09-03 |
|---|---|---|
| A migration guide in this repo mapping every removed or changed entry point to its replacement, with before/after examples | §8, and Constitution III ("the migration guide is the UX deliverable") | **not started** — 006, 007 and 008 each have one; there is no `specs/010-*` directory at all |
| Deprecated entry points removed from `cuemsutils`, **only after** all consumers are on the new API | §8; `_deprecation.REMOVAL_RELEASE = "v0.1.1"` | **not started, and correctly so** — it is gated on the six consumer flows |
| The descriptor reachable from a public path | D34 / C4 | **not started** — `SchemaDescriptor` is in `cuemsutils.xml`, whose `__all__` is `[]` |

Everything else 010 asks of this repository already exists and was verified
rather than assumed: `NetworkMap.partition_by_adoption` (`xml/settings.py:209`),
`cuems-convert-documents` (`xml/convert_documents.py` + `[project.scripts]`),
`cuemsutils.errors`' public `LoadReport`/`Outcome`/`RepairRecord`/
`ConversionRecord`, and the strict load path with its three outcomes. Those
landed in 007 and 008 and need confirming, not redoing.

**So the spec-kit path is still needed here, and its content is not what §8
implied.** It is not a cross-repo coordination spec — the six consumer files are
that now. It is a small, real library feature with an unusual shape: ITEM 1
unblocks two other repositories and must land early; ITEM 2 cannot land until all
six have finished; ITEM 3 accumulates as they do.

---

## 0. State of this repository, measured 2026-09-03

| | |
|---|---|
| Current branch | `feat/xml-refactor` @ `7c5896c` — **already the target branch** |
| Working tree | 3 modified planning files (this prompt set); commit or stash before starting |
| Spec-kit | present (`0.5.1.dev0`, 9 skills) |
| Constitution | present — `.specify/memory/constitution.md`, v1.0.0 |
| Existing features | `specs/001-*` … `specs/008-*` on `feat/xml-refactor`; **this is `010-consumer-migration`**, renumbered from `009` on 2026-09-03 because `specs/009-fix-dmx-channel-conversion/` — a small, unrelated bugfix, unplanned in advance — landed the `009` slot first on its own branch. Confirm no `specs/009-*` exists on `feat/xml-refactor` before running `/speckit.specify`; if the branches have merged by then, this repository's next free number may have moved again. |
| Tests | `hatch test --show` — **2573 passed, 96 skipped, 2 xfailed in 53.34 s = 20.73 ms/test** |
| Version | `0.1.0rc15` |

**The suite baseline is 20.73 ms/test, not the 20.8 recorded 2026-09-03 before
today.** Re-measured after `specs/009-fix-dmx-channel-conversion/` (11 new
tests) and the `009`→`010` renumbering landed on `feat/xml-refactor`
(`7a1893f`) — neither changed per-test cost measurably, but the count moved,
so the figure is re-measured rather than inherited, same discipline this
document already applies to 008's number. Principle IV budgets derive from
20.73.

---

## 1. Branch

Already on `feat/xml-refactor`. Nothing to create. Commit or stash the working
tree first — `/speckit.specify` writes into `specs/`.

Spec-kit's sequential branch numbering will want a branch of its own. **Stay on
`feat/xml-refactor`**; let it name `specs/010-consumer-migration/` only.

---

## 2. Constitution — check, do not amend

Read `.specify/memory/constitution.md`. Principle IV (Performance Budgets Are
Requirements) is the one that binds here, and its baseline is the 20.73 ms/test
figure above. No amendment is needed: this task adds a public accessor and
deletes no behaviour.

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything:
  specs/planning/xml-rebuild/xml-rebuild-06-target-design.md       THE TARGET DESIGN — authoritative
  specs/planning/xml-rebuild/xml-rebuild-08-extension-audit.md     feature 008 evidence (E1-E26)
  specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md      feature 010 evidence (C1-C12) — C4 is this task
  specs/008-rebuild-extension/migration-guide.md                   what 008 handed to 010
  specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md §2  the FULL settled-decision list (D1-D35)

SETTLED — the decisions that bind THIS task. Do not reopen; do not propose
alternatives. Anything outside this subset: read §2 of the prompts file above.
  D12 public surface returns objects, never raw dicts
  D15 public objects are CuemsScript (show) and ConfigManager/ConfigBase (config)
  D16 consumer-repo modifications ARE allowed from feature 008 onward; a cuems-utils
      change inside a consumer-migration feature is the same permission read the other way
  D25 template/config generation lives on a schema-derived descriptor covering all six
      schemas, emitting per type: field name, XSD type, cardinality, restricted
      xs:enumeration values, AND model-layer defaults
  D34 SchemaDescriptor is exposed to consumers THROUGH ConfigManager -- the existing public
      config object (D15) -- covering ALL SIX schemas, script included. This deliberately
      widens ConfigManager's role beyond the config domain; the alternative is two public
      paths for one mechanism. Q14 therefore stands. cuems-nodeconf's existing
      cuemsutils.xml.mapper / cuemsutils.xml.settings imports move onto public equivalents
      in the same feature rather than being grandfathered (C4).
  D27 nothing in the ecosystem releases until every 010 flow lands. This repository holds
      the LAST step of that gate: the deprecated surface cannot be removed until all six
      consumer flows are done, and the release cannot happen until it is removed.
  Q14 -> (i) xml/ is internal machinery

MEASURED DEPRECATION SURFACE (ITEM 2), verified 2026-09-03 -- this is what "the deprecated
surface is removable" actually means, in files:
  _deprecation.REMOVAL_RELEASE = "v0.1.1"; current __version__ = "0.1.0rc15"
  FIVE whole shim modules exist only to keep pre-rename import paths alive:
    src/cuemsutils/xml/Settings.py          (Settings, NetworkMap, ProjectMappings,
                                             ProjectSettings)
    src/cuemsutils/xml/XmlReaderWriter.py   (CuemsXml, XmlReaderWriter, XmlWriter,
                                             XmlReader, get_pkg_schema)
    src/cuemsutils/xml/Parsers.py           (CuemsParser, GenericDict, str_to_value)
    src/cuemsutils/xml/CMLCuemsConverter.py (CMLCuemsConverter)
    src/cuemsutils/timeoutloop.py           (Timeoutloop -> tools.TimeoutLoop.TimeoutLoop)
  SEVEN aliases in src/cuemsutils/xml/__init__.py:81-91 (XmlReaderWriter, CuemsParser,
    Settings, NetworkMap, ProjectMappings, ProjectSettings -- 006's six retirements)
  Plus deprecated_symbol sites in xml/settings.py:170 (get_nodes_by_adoption),
    xml/XmlBuilder.py:362, xml/Parsers.py:199/:205
  tests/contract/test_deprecation_shims.py -- 22 tests pinning contract C9. Its own
    docstring says "Twelve known call sites across cuems-editor, cuems-engine and
    cuems-nodeconf import from the pre-rename paths". THOSE TWELVE ARE THE GATE: this item
    lands when they are zero, and that is the six consumer flows' work, not this one's.
  KNOWN LIVE CONSUMERS of these paths as of 2026-09-03, none yet migrated:
    cuems-engine  core/BaseEngine.py:17 (xml.XmlReaderWriter), ControllerEngine.py:12
                  (xml.Settings.NetworkMap)
    cuems-editor  CuemsWsServer.py:23 (xml.NetworkMap), CuemsDBProject.py:10/:9
                  (xml.XmlReaderWriter, xml.Parsers.CuemsParser),
                  repair_durations.py:39/:40
    cuems-nodeconf CuemsNodeConf.py:26 (timeoutloop.Timeoutloop), :22-23 (xml.mapper,
                  xml.settings)

THE COUNT'S EXEMPT SET (C12) -- this repository's own src/ carries SIXTEEN node_type
occurrences and every one is correct code that must survive: errors.py:106-110's
"NodeType.*" -> role mapping, errors.py:120-135's network_map_node_type_message diagnostic,
tools/ConfigBase.py:6/:46/:76 wiring it in, plus prose in config/network_map.py and a
comment in xml/schemas/network_map.xsd. A migration diagnostic has to name what it detects.
Do not delete these to make a count reach zero.

MEASURED STARTING STATE (C4, 2026-09-03):
  - SchemaDescriptor, generate_script_example and generate_settings_example live in
    src/cuemsutils/xml/descriptor.py.
  - src/cuemsutils/xml/__init__.py sets __all__ = [] (006 FR-019 / SC-005). So every
    symbol in that package is internal by an explicit, tested decision.
  - cuemsutils.errors IS public and already carries LoadReport/Outcome/RepairRecord/
    ConversionRecord. That is the precedent for what "public" means here: 006's rule that
    an exception the caller cannot name is one it cannot catch, applied to a returned type.
  - cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:22-23 imports cuemsutils.xml.mapper
    (Mapper, read_config_document) and cuemsutils.xml.settings (NetworkMap) TODAY. No
    feature has ever recorded this as a violation. It is one, and this task ends it.

PERFORMANCE BASELINE (Principle IV): 2573 passed, 96 skipped, 2 xfailed in 53.34 s
  = 20.73 ms/test, measured 2026-09-03 on feat/xml-refactor @ 7a1893f, after the
  DMX-fix feature (009-fix-dmx-channel-conversion, +11 tests) and the 009->010
  renumbering landed. Do NOT inherit 008's 22.06 ms/test or the earlier 20.8
  figure recorded before those two commits.
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Complete cuems-utils' own share of feature 010: publish the schema descriptor, remove the
deprecated surface once every consumer is off it, and write the migration guide that maps
what changed to what replaced it. THREE ITEMS, and their timing differs sharply — ITEM 1
must land before two consumer flows can start, ITEM 2 cannot land until all six have
finished, and ITEM 3 accumulates across the whole feature. Write the spec so that ordering
is structural rather than a note; a task list that lets ITEM 2 run early would break six
repositories at once.

ITEM 1 — THE PUBLIC DESCRIPTOR PATH (D34/C4). Blocks flows 02 and 05.

WHAT MUST BE TRUE WHEN DONE:
- ConfigManager exposes the descriptor for ALL SIX schemas, script included. State in the
  spec that this deliberately widens a config-domain object's role to cover the show
  schema, and why: the alternative is two public paths for one mechanism, and the editor
  that serves config forms is the same one that serves the script template. A reader who
  finds a script descriptor on a config object must find the reason next to it.
- The returned descriptor answers, per type: field name, XSD type, cardinality, the legal
  value list where the type is a restricted enumeration, and the model-layer default —
  the same five facts descriptor.py already produces. This task PUBLISHES that surface;
  it does not redesign it.
- The example generators (generate_script_example, generate_settings_example) are reachable
  from the same public path, since retiring initial_template-as-an-instance is what the
  editor and frontend do with them.
- cuemsutils.xml.__all__ stays []. Nothing about this task weakens Q14; it strengthens it,
  by giving the one legitimate external consumer a door that is not the back one.
- The two internal imports cuems-nodeconf makes today (cuemsutils.xml.mapper's Mapper and
  read_config_document, cuemsutils.xml.settings's NetworkMap) have public equivalents, so
  that repository's own 010 flow has something to move onto. Where a public equivalent
  already exists (ConfigManager covers most of it), say so rather than adding a synonym —
  the deliverable is a stated, tested migration target per import, not necessarily new code.
- The migration guide for 010 records the public path at call-site granularity, the way
  007's and 008's guides do, so 02 and 05 can be written against it without reading source.

WHAT THIS TASK DOES NOT DO:
- No new descriptor capability. If a consumer needs something descriptor.py does not
  emit — 05's getTemplateOutputStructure needs a constructible instance per complex type,
  not a field default (C5) — that is a real gap, but it belongs to a decision this spec
  RECORDS rather than resolves. Say so explicitly; do not quietly grow the descriptor to
  cover it.
- No change to what the descriptor computes, and no change to the six schemas.

The public surface is a contract, so treat naming as part of the deliverable rather than an
implementation detail: whatever the accessor is called, it is the name five other
repositories will import for years.

ITEM 2 — REMOVE THE DEPRECATED SURFACE. Gated on ALL SIX consumer flows.

This is the last step before the ecosystem can release, and it is the one that is dangerous
to run early: five whole shim modules, seven aliases and four deprecated_symbol sites exist
precisely because twelve call sites across cuems-engine, cuems-editor and cuems-nodeconf
still import through them (the measured list is in the context block, and none of them is
migrated yet).

WHAT MUST BE TRUE WHEN DONE:
- The precondition is MEASURED, not assumed. Before a single deletion, count the live
  imports of every deprecated path across all six consumer repositories on disk and show the
  count is zero. "The consumer flows are merged" is not the same claim, and the difference
  is a broken daemon.
- The five shim modules are deleted (xml/Settings.py, xml/XmlReaderWriter.py, xml/Parsers.py,
  xml/CMLCuemsConverter.py, timeoutloop.py), along with the seven aliases in
  xml/__init__.py:81-91 and the deprecated_symbol sites in xml/settings.py:170,
  xml/XmlBuilder.py:362 and xml/Parsers.py:199/:205.
- tests/contract/test_deprecation_shims.py's 22 tests are RETIRED DELIBERATELY, and the spec
  says what replaces them. They pin contract C9 — "consumer imports still resolve, and say
  so on every use" — a contract this item deliberately ends. Deleting a contract test as a
  side effect of deleting the thing it guards is correct here and needs saying out loud, or
  it reads as coverage quietly disappearing.
- __version__ moves to the release that REMOVAL_RELEASE has been promising ("v0.1.1"). If it
  moves to something else, REMOVAL_RELEASE was wrong in every warning this library has
  emitted for two features, and the spec says so rather than silently diverging.
- CuemsParser's SILENCE is preserved or its removal is deliberate. test_deprecation_shims'
  docstring records that CuemsParser must stay silent under contract C8 (it is the engine's
  delegating facade, not a retired path) while 006 retired the cuemsutils.xml.CuemsParser
  alias as one of its six. Those are two different symbols; check which is which before
  deleting either.

ITEM 3 — THE 010 MIGRATION GUIDE. Accumulates across the whole feature.

WHAT MUST BE TRUE WHEN DONE:
- specs/010-*/migration-guide.md exists and maps every removed or changed entry point to its
  replacement, with before/after examples — the same shape 006's, 007's and 008's have, and
  Constitution III's UX deliverable for this feature.
- It records cuems-wsclient as a consumer (C1). That repository was absent from 007's guide,
  008's guide and Part 4 §8's repository list, and that absence is why a silently-broken
  shutdown path survived two features. The next ecosystem-wide sweep should reach it by
  construction, not because someone remembered.
- It carries the ecosystem-wide node_type count WITH ITS EXEMPT SET ENUMERATED (C12). This
  repository's own src/ has sixteen occurrences, all of them migration-detection code that
  must survive. A guide that reports "zero except where it matters" without saying where is
  how a working diagnostic gets deleted by the next person to run the count.
- It states, in one place, which of 010's obligations landed in which repository — because
  seven spec-kit flows produce seven tasks.md files and no single view of the whole.
```

---

## 5. Clarify

```
/speckit.clarify
```

Two questions worth forcing if they do not surface on their own:

- **Is the accessor a method on `ConfigManager`, or a property returning a
  descriptor object?** The difference is whether a consumer holds the descriptor
  across calls, which matters to the editor (which serves it per WS connection)
  and the frontend (which caches it in `localStorage`).
- **Does ITEM 2 ship as `v0.1.1`, and does this feature cut that release?**
  `REMOVAL_RELEASE` has promised `v0.1.1` in every warning this library has
  emitted since 006. If the answer is "some later version", every one of those
  warnings has been wrong, and the guide has to say so.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Scope, by item:
- ITEM 1: src/cuemsutils/tools/ConfigManager.py (the public accessor),
  src/cuemsutils/xml/descriptor.py (unchanged in behaviour; re-exported).
- ITEM 2: the five shim modules, xml/__init__.py:81-91, the four deprecated_symbol sites,
  tests/contract/test_deprecation_shims.py, and __version__.
- ITEM 3: specs/010-*/migration-guide.md.

SEQUENCING IS THE HARD PART OF THIS PLAN, and it is not a note — it is the structure.
ITEM 1 blocks flows 02 and 05, so it lands first and alone. ITEM 2 is blocked BY ALL SIX
consumer flows and lands last in the entire feature 010, across every repository; its tasks
must be unrunnable until a measured check says twelve live imports have become zero. Do not
let /speckit.tasks interleave them: a task list that permits ITEM 2 to start early is a task
list that can break six repositories at once, and that possibility should not exist in the
file rather than being avoided by care.

Constitution check:
- I: the accessor is small and does one thing. If it needs a paragraph of explanation to
  justify living on ConfigManager, that paragraph belongs in the docstring — see D34.
- II: for ITEM 1, a test that the public path returns the same descriptor the internal one
  does, for every one of the six schemas — not a smoke test on one. For ITEM 2, the gate is
  the measured zero-live-imports check across the six consumer repositories, and it is a
  precondition rather than a test: the suite here cannot see another repository's imports.
- III: the migration guide is the UX deliverable, and its audience is six other
  repositories' spec-kit flows plus whoever runs the next ecosystem sweep.
- IV: baseline 20.73 ms/test. A public re-export should cost nothing measurable; if the
  accessor eagerly builds all six descriptors where the internal path built one lazily,
  that IS measurable and is a design error, not a budget overrun to accept. ITEM 2 should
  make the suite FASTER (22 contract tests retire); if it does not, something else changed.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Readiness, per item. ITEM 1: the accessor covers all six schemas with a
test per schema; cuemsutils.xml.__all__ is still []; every cuems-nodeconf internal import
has a named public replacement (or a recorded reason it needs none); and the descriptor's
known gap for per-type constructible instances (C5) is RECORDED as a decision for flow 05,
not silently half-implemented. ITEM 2: the zero-live-imports precondition MEASURED across
all six consumer repositories on disk before any deletion, not inferred from merged PRs; all
five shim modules, seven aliases and four deprecated_symbol sites gone, counted; contract
C9's 22 tests retired deliberately with the reason recorded; __version__ matching what
REMOVAL_RELEASE has been promising; and CuemsParser's two distinct symbols told apart before
either is deleted. ITEM 3: the guide exists, maps every changed entry point with before/after
examples, records cuems-wsclient as a consumer, carries the node_type count WITH its exempt
set enumerated (C12), and says which obligation landed in which repository.
```
```
/speckit.analyze
```
```
/speckit.implement
```

Then the quality loop — [Part 4 §9](../xml-rebuild-07-speckit-prompts.md):
`/speckit.check-integration`, `/speckit.optimize`, implement, `/speckit.verify`.

---

## 8. Exit criteria

**ITEM 1** (early): the public accessor returns, for each of the six schemas, the
same descriptor the internal module returns, proven per schema rather than
sampled; `cuemsutils.xml.__all__` is still `[]`; every `cuemsutils.xml.*` import
`cuems-nodeconf` makes today has a named public replacement; the example
generators are reachable from the same path; and flows 02 and 05 can be written
without reading `cuemsutils` source.

**ITEM 2** (last in all of feature 010): a measured zero live imports of every
deprecated path across all six consumer repositories; the five shim modules,
seven aliases and four `deprecated_symbol` sites gone; contract C9's 22 tests
retired with the reason recorded; `__version__` matching `REMOVAL_RELEASE`'s
promise.

**ITEM 3**: `specs/010-*/migration-guide.md` complete, including
`cuems-wsclient` as a consumer, the `node_type` count with its exempt set
enumerated, and a single statement of which obligation landed where.

Suite green at or under 20.73 ms/test throughout — and faster after ITEM 2.

**This repository closes the gate it does not open.** D27 holds: nothing in the
ecosystem releases until all seven flows land, and ITEM 2 is the last of them.
