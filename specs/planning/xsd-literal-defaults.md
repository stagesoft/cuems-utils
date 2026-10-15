<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Literal defaults in the schemas — implementation plan

**Opened**: 2026-10-15. **Status**: planned, not started. Its first slice has landed (§2).
**Scope**: `cuems-utils` only. Inside the unreleased `script` 1 → 2 step, so no version 3.

> ⚠ **This document deletes itself.** Per the deletion policy in `CLAUDE.md` ("specs/planning
> and specs/agreements"), once every phase below is implemented and the result is recorded in
> `CLAUDE.md`'s "Recent Changes", **this file MUST be deleted in the commit that records it**.
> Commit the plan first, so that git keeps it.

---

## 1. The goal, stated as narrowly as it can actually be met

**Every literal default value lives in the XSD. Python declares only what XSD cannot express.**
A test enforces the split.

"The schemas are the single source of truth for defaults" is **not** achievable, and this plan
does not claim it. Of the 52 distinct default declarations in the library (all in the `script`
models; every configuration model declares none), only 22 are literals XSD can carry. The other
30 are inherently Python (§3.1).

Two other default sources exist and are **out of scope**:
- `system-defaults.toml` (feature 011): seed data for the configuration documents
  `cuems-init-node` writes. These are values like a port or a path, not model defaults.
- The descriptor's facet-derived seeding rules 1–8 (feature 015): "the zero of the type" for a
  field that has no default at all.

## 2. Already landed: the first slice (2026-10-15)

`script.xsd` carries `default="…"` on `output_vol` (80), `channel_vol` (80), `x_scale` (1) and
`y_scale` (1). The descriptor's **seeding rule 0** (`descriptor._xsd_declared_default`) uses a
declaration's XSD default as its seed, after the model default and before rules 1–8. This closed
015's `consumers_works.md` row 4: `cuems-frontend` no longer hand-authors starting values.

The slice is deliberately a **seed only**. It never becomes `FieldDescriptor.default`, so
repairability and the read path are unchanged (FR-026a). §4 D1 decides whether the full
migration keeps that separation.

## 3. Measured facts (2026-10-15, hatch `test.py3.11`)

### 3.1 The 52 declarations

| Kind | Count | XSD? |
|---|---|---|
| Literal on a simple-typed element (`name='empty'`, `enabled=True`, `master_vol=100`, `post_go='pause'`, `loop=1`, …) | 20 | **yes** |
| Enum member (`FadeCue.curve_type = FadeCurveType.linear`) | 1 | **yes**, as its lexical value |
| Optional attribute (`DmxUniverse.universe_num = 0`) | 1 | **yes**; for an attribute XSD's default means "when absent", which matches Python |
| `None` placeholder ("no value yet") | 17 | no; XSD has no null |
| `class` discriminator (`'audio'`, `'video'`, `'dmx'`) | 6 | no; it selects the `xs:alternative`, so one default per element would contradict the dispatch |
| Callable factory (`new_uuid`, `new_datetime`) | 4 | no; each object needs a fresh value |
| Class or list factory (`CTimecode`, `CueList`, `[]`) | 3 | no |

Reproduce with the classification script described in §6 T0.1.

### 3.2 Performance: nothing measurable

- **Cold path: no new cost.** The first model constructed already compiles all six schemas
  (`AudioCue()` in a fresh process: 251 ms, `get_schema` cache size 0 → 6), through
  `coercion._resolve`. Reading defaults from the compiled schema happens once per class and
  is cached in `_DECLARED_DEFAULTS`, as today.
- **Warm construction: unchanged.** It reads the same cached dict.
- **Decode: no measurable change.** 19 `default=` attributes were added to a scratch copy of
  `script.xsd`, and `CuemsScript.load(complex_test/script.xml)` was timed in fresh processes,
  six samples per arm, alternating: medians 16.87 ms without and 16.71 ms with. The `to_wire()`
  output was byte-identical.

### 3.3 Semantics, the real cost

- **An XSD element default is not "the value when absent".** It applies only to an element that
  is present and **empty**, and never to a missing one. Python's model default is "the value a
  new object starts at". The library would be *reading* the XSD default as its own default.
  That is a legitimate use, but it is not what the XSD says to another reader.
- **This library ignores even the XSD meaning.** A document with `<master_vol/>` is refused
  (`invalid literal for int() with base 10: ''`) **with or without** `default="100"`. Plain
  `xmlschema` accepts the same document: `is_valid` is true, and `to_dict(use_defaults=True)`
  decodes it as 100. So the library and a bare XSD validator would disagree on such a document.
  `cuems-editor` validates against `/etc/cuems/script.xsd` with its own code. That divergence
  exists today for every other rule the library enforces beyond XSD; this would add a case to
  it, not create it.
- **Names collide across declarations.** `channel` is an integer in `DmxChannelType` and a
  complex type in `AudioChannelsType`. A default belongs to one element declaration, so every
  edit is per declaration, never by field name. The scratch prototype's first attempt failed on
  exactly this.

## 4. Decisions to make before phase 1

- **D1. Does an XSD default make a field repairable?** Today "has a model default" means "is
  repairable on load" (`_repairability` rule 1). If XSD defaults replace model defaults, the
  same must hold, or the 22 moved fields silently become unrepairable, which is a read-path
  change. Then rule 0's seed-only position from §2 either stays a separate category (two kinds
  of default in one schema) or is promoted, making the four row-4 fields repairable too.
  *Recommendation*: promote. One meaning of `default=` per schema, stated once, and the four
  fields gain the same repair the other 22 already have.
- **D2. Where the merged default lives.** `DECLARED_DEFAULTS` cannot be deleted: its key order
  is load-bearing (`declared_defaults()` order → `items()` → `__json__` → the editor's payload
  key order, `helpers.py`). *Recommendation*: keep the dict for order, and replace each moved
  value with a `FromSchema` sentinel that `declared_defaults()` resolves once per class.
- **D3. A class bound to several XSD types.** `_class_type_keys` shows classes bound to more than
  one `TypeKey`. A sentinel must resolve to one value, or refuse if the bound declarations
  disagree.

## 5. Not doing

- The 30 non-literal defaults (§3.1) stay in Python by nature.
- Configuration seeds (`system-defaults.toml`) are a different concern with their own feature
  (011).
- Making the library honour XSD element defaults on **read** (`<master_vol/>` → 100). That would
  relax the read path, which is a separate decision from where defaults are declared.

## 6. Phases

Each phase ends with the suite green, ruff 0 and mypy at no more than its current count.

- **Phase 0, pin.** T0.1: commit the classification as a test fixture: the 52 declarations,
  their kind, and the declaration each literal maps to. T0.2: snapshot every model's
  `declared_defaults()` as typed values, which phase 2 must reproduce exactly. T0.3: snapshot
  the repairability table (327 rows; 015's `snapshots/repairability-after.txt` method).
- **Phase 1, schema.** Add `default=` to the 22 declarations, per declaration (§3.3). Update
  `test_schema_scope.py`'s hash, with the reason. Extend `test_rule_0_covers_exactly_the_declared_defaults`
  to the full list.
- **Phase 2, resolution.** Add `FromSchema` (D2), resolved through the existing adapter table:
  `'false'` → `False`, `'linear'` → `FadeCurveType.linear`, `'100'` → `100`. Resolve D3. The
  T0.2 snapshot must match exactly, in value **and type**.
- **Phase 3, the rule.** A contract test: no model may declare a literal default for a field whose
  XSD declaration can carry one. It fails naming the class and field. The 30 non-literals pass
  by kind.
- **Phase 4, repairability** (per D1). If promoted, the four row-4 fields become repairable. That
  is the only intended repairability change, so T0.3's table must differ in exactly those rows.
- **Phase 5, measure** with `tests/support/perf_descriptor.py` and an interleaved show-document
  load, both against the phase 0 tree: 16 samples in three windows (`CLAUDE.md`'s sampling
  lesson). Expect no change, per §3.2.
- **Phase 6, record and delete.** Add a `CLAUDE.md` "Recent Changes" entry and a `CHANGELOG.md`
  line. **Delete this file in that commit.**

## 7. Acceptance

| # | Criterion |
|---|---|
| A1 | Every model's `declared_defaults()` equals the T0.2 snapshot in value and type |
| A2 | No literal default is declared in Python where the XSD can hold it (phase 3 test) |
| A3 | Goldens unchanged; the repairability table changes only as D1 decides |
| A4 | Show-document load and warm descriptor within run-to-run spread of phase 0 |
| A5 | Any document valid before is valid after, and the library refuses what it refused before |

---

> ⚠ **Reminder: delete this file when phase 6 lands**, in the same commit as its `CLAUDE.md`
> entry.
