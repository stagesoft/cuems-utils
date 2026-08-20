# The recorded public API surface, and every change to it (T057a, T065)

**Feature**: 006-public-object-api · **Date**: 2026-08-20

`tests/golden/api/public_api.json` is a snapshot of what `cuemsutils.xml`
exports and what each exported class publicly offers. T065 is one of exactly
**two** tasks in this feature permitted to modify a recorded golden (standing
rule 1); this file is its justification, and the list below is what T065's
"exactly the enumerated set" is compared against.

---

## 1. What counts as a "public name"

Stated once here, because the golden's contents depend on it and the spec left
it distributed:

- a **module-level** name not prefixed with `_`;
- a **public method** on an exported class — again, no leading `_`, with
  `__init__` the single dunder exception, because its signature is part of how
  a class is used.

Excluded: every other dunder; members inherited from the standard library
(`dict.get`, `object.__reduce__`); anything a class acquires from `deprecated`'s
machinery.

## 2. How FR-007 is met this release, and how it is not

FR-007 says the six methods are *"the only supported way"* script data moves.
That is satisfied by **FR-019** (`cuemsutils.xml.__all__ == []`) plus **FR-022**
(the recorded surface names the six and nothing else) — **not** by
unreachability.

`FR-019a` deliberately keeps dotted access working for one release, because the
deprecation shims resolve through those same paths. `from cuemsutils.xml import
XmlReaderWriter` still works and warns. Genuine lockdown is **feature 008's**.
Stating this here stops a later reader concluding the requirement was missed.

---

## 3. The enumerated diff

Every entry below is a change this feature makes on purpose. A name in the
golden's diff that is not on this list is a defect, not a surprise.

### 3a. Added — `cuemsutils.errors` (T023a)

The one new **public module**. A returned type can stay internal because the
caller only inspects what it is handed; an exception the caller cannot name is
an exception the caller cannot catch.

| Name | Kind |
|---|---|
| `CuemsError` | class, `Exception` |
| `ValidationError` | class, `CuemsError` — carries `.violation` |
| `SchemaError` | class, `ValidationError` |
| `IngestError` | class, `CuemsError` |

### 3b. Added — six methods on `CuemsScript` (T024–T028)

`load`, `from_json`, `save`, `validate`, `to_wire`, `to_json`.

`load` and `from_json` are **classmethods**. No signature takes a schema name.

### 3c. Added — `to_wire` / `to_json` on **every** `CuemsDict` subclass (T026)

Counted rather than discovered. The projection lives on the shared base so that
the config models *bind* to one body rather than duplicating it (SC-017), and
the consequence is that every cue class exposes both methods publicly:

`Cue`, `CueList`, `AudioCue`, `VideoCue`, `DmxCue`, `ActionCue`, `FadeCue`,
`MediaCue`, `Media`, `Region`, `CueOutput` and its three subclasses,
`DmxScene`, `DmxUniverse`, `DmxChannel`, `FadeProfile`,
`FadeFunctionParameter`, `CuemsScript`, plus the twenty-two
`cuemsutils.config` models.

Intended and free — a cue projecting itself is meaningful — but unlisted names
are exactly what makes T065 fail on a diff nobody expected.

### 3d. Removed — hand-written `__json__` bodies (T035, behaviour change 3)

Six deleted outright (`Cue`, `Region`, `DmxChannel`, `FadeFunctionParameter`,
`FadeProfile`, `CueOutput`); `CuemsScript.__json__` reduced to unwrapping the
document body. `__json__` is a dunder and so is not a *public name* by §1 — it
is listed because SC-006 counts it.

**One is kept, and the task list's reference to it was a mis-identification.**
`FadeCue.py:21` names `FadeCurveType.__json__` — a method on an **Enum**, not
on a model object. It is a scalar hook of exactly the kind T035 explicitly
preserves for `Uuid` and `CTimecode`, and deleting it would make
`json.dumps(FadeCurveType.linear)` raise. SC-006's "0 hand-written JSON
projection methods" concerns projections of *objects*; a one-line
enum-to-scalar conversion is not one.

### 3e. Removed — `Settings.data2xml`, `Settings.buildxml` (T056, US3)

A generic dict→ElementTree builder on a class with no working write path:
building XML from a settings dict raised `AttributeError` inside the legacy
`XmlBuilder`, which is why the config classes' byte-identity contract has always
been the read dict (C2) and never the written bytes. No caller exists in this
repository, `cuems-engine`, `cuems-editor` or `cuems-nodeconf`.

These are inherited by `NetworkMap`, `ProjectMappings` and `ProjectSettings`, so
they leave the golden four times each.

### 3f. Removed — `ProjectMappings.process_network_mappings` (T056, US3)

Its own docstring said what it was: *"Temporary process instead of reviewing
xml read and convert to objects."* It was F15's **third** incompatible reading
of the node mappings, and nothing called it.

### 3g. Added — `ConfigManager.to_wire` (T056b)

The facade delegation, so a caller holding a config object can project it.
Configuration is **not** transmitted to the UI in this feature; this is the seam
the planned follow-on uses, and building it here is what stops a second
projection being written then.

### 3h. Removed — the six deprecated entry points from `__all__` (T062, US4)

`XmlReaderWriter`, `Settings`, `NetworkMap`, `ProjectMappings`,
`ProjectSettings` — the five in `__all__`, which is SC-005's number — **plus**
`CuemsParser`, which was never in `__all__` but is a supported entry point
reached by dotted path. Both counts are right; they measure different things
(contract C3).

### 3i. Removed — `schema_name` from every public signature (FR-021)

It is a property of the type, not of the caller. Passed at six call sites across
three repositories today; the migration guide (T084) lists them.

---

## 4. Sequencing

The golden is updated **twice**, and both updates are recorded here rather than
one being folded silently into the other:

| When | Why | Sections |
|---|---|---|
| US3 | the config layer removes three inherited methods from four classes | 3e, 3f, 3g |
| US4 | `__all__` empties and the errors module and the six methods are recorded | 3a, 3b, 3c, 3h, 3i |

`tests/golden/MANIFEST.sha256` is updated in the same commit as each, per
standing rule 1.
