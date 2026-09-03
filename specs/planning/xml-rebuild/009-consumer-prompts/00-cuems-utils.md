# Feature 009 — `cuems-utils`: the public descriptor path

**Status:** ready to run — **run this first**
**Date:** 2026-09-03
**Repository:** `/disk/Projects/StageLab/cuems-utils`
**Run order:** 00 of 06 — precondition of [02 `cuems-editor`](02-cuems-editor.md)
and [05 `cuems-frontend`](05-cuems-frontend.md); see the
[index](README.md).

This is the one `cuems-utils` task in feature 009, permitted by D16 and required
by D34. It is small, it is not optional, and it comes first: two consumer flows
are written against an interface that does not exist publicly yet.

---

## 0. State of this repository, measured 2026-09-03

| | |
|---|---|
| Current branch | `feat/xml-refactor` @ `7c5896c` — **already the target branch** |
| Working tree | 3 modified planning files (this prompt set); commit or stash before starting |
| Spec-kit | present (`0.5.1.dev0`, 9 skills) |
| Constitution | present — `.specify/memory/constitution.md`, v1.0.0 |
| Existing features | `specs/001-*` … `specs/008-*`; **this is `009-consumer-migration`** |
| Tests | `hatch test --show` — **2562 passed, 96 skipped, 2 xfailed in 53.24 s = 20.8 ms/test** |
| Version | `0.1.0rc15` |

**The suite baseline is 20.8 ms/test, not 008's recorded 22.06.** Forty tests
landed after that measurement (`TimeoutLoop`, `StringSanitizer`,
`CopyMoveVersioned`). Principle IV budgets derive from 20.8.

---

## 1. Branch

Already on `feat/xml-refactor`. Nothing to create. Commit or stash the working
tree first — `/speckit.specify` writes into `specs/`.

Spec-kit's sequential branch numbering will want a branch of its own. **Stay on
`feat/xml-refactor`**; let it name `specs/009-consumer-migration/` only.

---

## 2. Constitution — check, do not amend

Read `.specify/memory/constitution.md`. Principle IV (Performance Budgets Are
Requirements) is the one that binds here, and its baseline is the 20.8 ms/test
figure above. No amendment is needed: this task adds a public accessor and
deletes no behaviour.

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything:
  specs/planning/xml-rebuild/xml-rebuild-06-target-design.md       THE TARGET DESIGN — authoritative
  specs/planning/xml-rebuild/xml-rebuild-08-extension-audit.md     feature 008 evidence (E1-E26)
  specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md      feature 009 evidence (C1-C11) — C4 is this task
  specs/008-rebuild-extension/migration-guide.md                   what 008 handed to 009
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
  Q14 -> (i) xml/ is internal machinery

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

PERFORMANCE BASELINE (Principle IV): 2562 passed, 96 skipped, 2 xfailed in 53.24 s
  = 20.8 ms/test, measured 2026-09-03 on feat/xml-refactor @ 7c5896c. Do NOT inherit
  008's 22.06 ms/test: 40 tests landed after that measurement.
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Give the schema descriptor a public path, so that feature 009's consumer repositories can
serve and consume it without importing cuemsutils.xml — a package this library declares
internal by an explicit, tested decision (__all__ == [], 006 FR-019/SC-005).

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
  that repository's own 009 flow has something to move onto. Where a public equivalent
  already exists (ConfigManager covers most of it), say so rather than adding a synonym —
  the deliverable is a stated, tested migration target per import, not necessarily new code.
- The migration guide for 009 records the public path at call-site granularity, the way
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
```

---

## 5. Clarify

```
/speckit.clarify
```

One question is worth forcing if it does not surface on its own: **is the
accessor a method on `ConfigManager`, or a property returning a descriptor
object?** The difference is whether a consumer holds the descriptor across
calls, which matters to the editor (which serves it per WS connection) and the
frontend (which caches it in `localStorage`). Resolve it here, not in review.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Scope: src/cuemsutils/tools/ConfigManager.py (the public accessor),
src/cuemsutils/xml/descriptor.py (unchanged in behaviour; re-exported), and the 009
migration guide.

Constitution check:
- I: the accessor is small and does one thing. If it needs a paragraph of explanation to
  justify living on ConfigManager, that paragraph belongs in the docstring — see D34.
- II: a test that the public path returns the same descriptor the internal one does, for
  every one of the six schemas, is the gate. Not a smoke test on one schema.
- III: the migration guide entry is the UX deliverable, and its audience is five other
  repositories' spec-kit flows.
- IV: baseline 20.8 ms/test. A public re-export should cost nothing measurable; if the
  accessor eagerly builds all six descriptors where the internal path built one lazily,
  that IS measurable and is a design error, not a budget overrun to accept.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Public-surface readiness: the accessor covers all six schemas with a
test per schema; cuemsutils.xml.__all__ is still []; every cuems-nodeconf internal import
has a named public replacement (or a recorded reason it needs none); the migration guide
entry is written at call-site granularity; and the descriptor's known gap for
per-type constructible instances (C5) is RECORDED as a decision for 05, not silently
half-implemented.
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

The public accessor returns, for each of the six schemas, the same descriptor the
internal module returns, proven per schema rather than sampled;
`cuemsutils.xml.__all__` is still `[]`; every `cuemsutils.xml.*` import
`cuems-nodeconf` makes today has a named public replacement recorded in the
migration guide; the example generators are reachable from the same path; the
suite is green at or under 20.8 ms/test; and 02 and 05 can be written without
reading `cuemsutils` source.

**This does not ship on its own.** D27 holds: nothing in the ecosystem releases
until all seven flows land.
