# Migration map — 005 object model unification

**Feature**: `005-object-model-unification` | **Tasks**: T003 (skeleton), T044 (completion)
**Requirement**: FR-UX-001, FR-019 | **Input to**: feature 008 (consumer migration)
**Baseline**: `79632c3` — see [baseline.md](./baseline.md)

Unlike [004's migration map](../004-xml-serialization-core/migration-map.md), which enumerated
deprecated *symbols* and their consumer call sites, this feature renames nothing and deprecates
nothing. Every entry below is a **behaviour** delta: the same call, on the same symbol, now
returns something different. That is why the form differs — before/after values rather than
old-path/new-path — and why no cross-checkout call-site sweep is repeated here. Consumers are
not edited by this feature (FR-027); feature 008 owns that, informed by this document.

**No file outside this repository is edited by feature 005.**

## Status

All seven behaviour changes landed. Suite **1485 passed, 47 skipped, 2 xfailed**; all four
golden sets byte-identical; decode 49.6 ms (1.37x the 36.3 ms pre-005 baseline).

| # | Finding | Change | Status |
|---|---|---|---|
| 1 | F18 | Loaded objects gain the internal types built objects already had | landed |
| 2 | F12 / F19 | Region coercion actually runs | landed |
| 3 | F16 | Clearing an identifier clears it | landed |
| 4 | F17 | `except AttributeError` narrows to "no such setter" | landed |
| 5 | F20 | One defaulting protocol; bare construction yields declared defaults | landed |
| 6 | Part 2c §5.4 | The root's `items()` filters to declared fields | landed |
| 7 | F4 | DMX-scene swallow-and-continue removed | landed |

---

## 1 — F18: loaded objects gain the internal types built objects already had

**Before**: `ui_properties` on a decoded cue was a plain `dict`; the same field on a built
cue was a `CuemsDict`. Consumer code taking one branch for built objects and another for
loaded ones was not being defensive — it was correct.

**After**: `CuemsDict` on all three entry points, produced by routing wildcard decode
through the same recursive `helpers.as_cuemsdict` the built path already used, so the two
agree by construction rather than by two implementations that happen to match.

**Consumer-visible consequence**: code that received plain dictionaries from a loaded script
now receives typed objects. `CuemsDict` **is** a `dict`, so every read is unchanged; only
`type(x) is dict` and `isinstance` checks against the exact type see a difference.

**Who is affected**: `cuems-engine` and `cuems-editor` where they inspect `ui_properties`.

---

## 2 — F12 / F19: region coercion actually runs

**Before**: two independent defects compounded. `Media.set_regions` rebound its *loop
variable* instead of the list member, so `Region(r)` was built and discarded on every pass;
and `RegionsType` sat in the decoder's `RAW_TYPES`, so a decoded region stayed a raw
`{'Region': {...}}` wrapper with its timecodes as `{'CTimecode': '...'}` dicts. `RegionType`
was bound to `Region` in the registry the whole time and never reached.

**After**: `list[Region]`, with `in_time`/`out_time` as `CTimecode`, from all four supply
shapes — a single mapping, a list of mappings, a list of `Region`s, and the wrapped form the
reader produces. A fifth, unrecognised shape now **raises** (FR-009a) rather than passing
through as a plain dict, which would be this defect returning silently.

**Consumer-visible consequence**: `media['regions']` members are `Region` objects.
`region['in_time']` is a `CTimecode`, not `{'CTimecode': '...'}` — **this one changes how a
value is read**, and it is the most likely to need a consumer edit.

**Who is affected**: `cuems-engine`'s playback path reads `regions[0].in_time`. It already
expected `CTimecode` (the built path gave it one), so this makes the loaded path match.

---

## 3 — F16: clearing an identifier clears it

**Before**: `Uuid.__init__` mints a fresh uuid4 for any falsy argument, so `script.id = None`
assigned a **new random id**. `create_script` cleared the script and cue-list ids on its way
out and they came back populated.

**After**: uuid-bearing setters delegate to the adapter, which returns `None` for `None` and
`""`. Generating an id stays the job of the `new_uuid` default, at defaulting time.

**Consumer-visible consequence**: the `initial_template` payload ships with **empty** script
and cue-list identifiers, matching the three cue identifiers that already arrived empty.
`project_load` is byte-identical and unaffected.

**Who is affected**: the Angular UI, via `cuems-editor`'s `initial_template`.

> **Open — CHK032.** FR-022 requires this delta be "confirmed harmless to the UI". No task
> owns that confirmation and none was performed here. Assumption 7 argues it is safe
> because three of the five cue identifiers already arrive empty; that is an argument, not a
> verification. **Carry into the PR.**

> A second, unenumerated instance surfaced: `create_script` passed `'id': ''` for both
> `Media` objects and relied on the same minting bug to populate them. They now ask for
> `new_uuid()` explicitly. Without that the generated golden would have moved, which is how
> it was found.

---

## 4 — F17: `except AttributeError` narrows to "no such setter"

**Before**: `CuemsDict.setter` wrapped the attribute *lookup* and the setter *call* in one
`except AttributeError: pass`. A coercion failure inside any setter produced a **silently
missing field** instead of an error, and the object still constructed.

**After**: the lookup is guarded; the call is not. A key with no setter is skipped exactly as
before; an `AttributeError` raised inside a setter propagates.

**Consumer-visible consequence**: a field whose coercion fails now raises instead of
vanishing. No valid document is affected. Exceptions of other types already propagated.

**Who is affected**: nobody on the happy path. This changes how a *defect* presents.

---

## 5 — F20: one defaulting protocol

**Before**: six classes returned an empty object from bare construction — `Cue`,
`CuemsScript`, `Media` and the three `CueOutput` subclasses — while thirteen returned full
defaults. Same question, two answers.

**After**: one protocol. `declared_defaults()` accumulates across the MRO and
`_fill_declared_defaults()` applies it. Fields declared `Unset` stay **absent**, which is
what keeps six newly-defaulted classes from emitting elements their documents never had.

**Consumer-visible consequence**: `Cue()` and `CuemsScript()` are no longer empty. `Media()`
and the three outputs still are, by design (`Unset`). See
[defaults-audit.md](./defaults-audit.md) for the per-field record and the sweep for code
relying on the old empty result — **none found in production**.

**Who is affected**: nobody found. The sweep is recorded rather than assumed.

> A latent bug surfaced and was fixed: `ensure_items` **mutated its argument**, and every cue
> `__init__` does `if not init_dict: init_dict = REQ_ITEMS`. A single bare `AudioCue()`
> therefore wrote `Media` and `outputs` into `AudioCue`'s module-level `REQ_ITEMS`,
> permanently and process-wide. It now works on a copy.

---

## 6 — the root's `items()` filters to declared fields; stray keys dropped and logged

**Before**: ten `items()` definitions in the model, each layering its own `REQ_ITEMS`, and
the root leaked undeclared keys into the JSON projection while cues filtered them. The
engine used neither — `_fill` iterated `obj.keys()`, so stray keys reached the **XML** from
every object.

**After**: one `items()` on `CuemsDict`, filtered to `declared_fields()`; the engine asks the
object for the same rule. An undeclared key is absent from every projection and produces
exactly one DEBUG record per key per object, naming the class and the key and never the
value.

**Consumer-visible consequence**: stray keys the root previously leaked stop being emitted.
Wildcard `ui_properties` content is **not** filtered — it is declared nowhere, and filtering
it would delete real editor state.

**Who is affected**: anything relying on a non-schema key surviving a save. None found.

---

## 7 — F4: DMX-scene swallow-and-continue removed

**Before**: feature 004 carried a named `DmxSceneCompatibility` object reproducing
`DmxSceneXmlBuilder`'s `except Exception`, with `REMOVAL_TARGET = "005"`. A show whose DMX
scene failed to serialize **saved cleanly with the scene missing**.

**After**: the compatibility object is deleted. It had no call sites in the engine — the
engine already propagated the exception — but it said nothing about *which* scene. The write
now fails with an error identifying the scene by `id` (or zero-based index when it has none)
and naming the originating cue. The guard is scoped to DMX scenes; no ambient
`except Exception` replaces it.

**Consumer-visible consequence**: a write that used to succeed and quietly drop a scene now
raises `DmxSceneWriteError`. No valid document is affected.

**Who is affected**: `cuems-engine`'s save path, on a defect that previously produced a
corrupt file instead of an error.

> The **legacy** `XmlBuilder` keeps its own swallow. It is the frozen legacy tree,
> unreachable from the engine and removed with the deprecation shims in feature 006.

---

## Deliberate carry-over — the standing validation asymmetry

Required by FR-006b, recorded so a later reader can tell "deliberate" from "overlooked".

The same value can be **rejected** when assigned through a property setter and **accepted**
when decoded, depending on which construction strategy its type happens to reach. Repeated
members are built through the model constructor and run their `__init__` validation;
everything else is populated by `from_decoded`, which coerces without validating.

This feature neither widens nor narrows it. No value-rejecting rule was added to a setter,
and none changed which types it reaches. The two legacy corpus documents pinned as *rejected*
still fail with the same `ValueError` from the same call site —
`VideoCueOutput.__init__` → `_classify_output_name` (`CueOutput.py:154`), **not** the
`set_output_name` setter.

**Correction to the spec, found while implementing.** `_initialized` — the flag that keeps
those gated rules off the load path — was documented as gating `VideoCueOutput` alone. It
gates **three** classes: `ActionCue.set_action_target` (`ActionCue.py:58`),
`FadeCue.set_action_type` (`FadeCue.py:100`) and `VideoCueOutput`'s setters
(`CueOutput.py:178,199,211`). Same requirement, wider blast radius; all three are pinned by
`tests/unit/test_runtime_state.py`.

Resolving the asymmetry is feature 006's recorded decision stop
(`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §9.2).

---

## Open scope question — SC-001

SC-001 asks for **zero** type differences between built and loaded objects. Measured, the
harness found **44** pre-005; feature 005 closed **30**. The remaining **14** are in three
groups that FR-019 does not enumerate and no task closes:

| group | count | why it is not reachable in 005 |
|---|---|---|
| `ui_properties` wildcard `None`/`int` → `"None"`/`"0"` | 6 | the schema states nothing about a wildcard's children, so there is no type to decode back to. Feature 004 recorded it as a known defect, deferred because fixing it rewrites editor state for every cue in every project |
| `DmxCue` fields left raw (`Mapper.OPAQUE_TYPES`) | 4 | decoded with `model(body)` without recursing — a deliberate 004 decision that keeps `channels` wrappers intact |
| `output_geometry` `x_scale`/`y_scale` `int` → `float` | 4 | `VideoOutputGeometryType` is GENERIC-bound, a plain dict with no model class, so no adapter table reaches into it |

**Built vs JSON-decoded is exact — zero differences.** Only the XML leg diverges, and every
remaining difference is a text round-trip artefact. Pinned with exact counts in
`tests/integration/test_construction_parity.py`.

**What holds is zero differences in the enumerated groups.** Whether SC-001 should be
narrowed to that, or the three groups absorbed into 006, is an open decision.

---

## Fail-then-pass evidence (SC-003)

Seven changes, seven pairs. The "before" half is run at `79632c3`.

| # | Change | Test | Before (at `79632c3`) | After |
|---|---|---|---|---|
| 1 | F18 internal types | `tests/unit/test_decode_internal_types.py` | 5 failed, 8 passed | 21 passed |
| 2 | F12/F19 regions | `tests/unit/test_region_coercion.py` | 10 failed, 1 passed | 11 passed |
| 3 | F16 id clearing | `tests/unit/test_id_clearing.py` | 6 failed, 3 passed | 9 passed |
| 4 | F17 setter swallow | `tests/unit/test_setter_error_propagation.py` | 3 failed, 4 passed | 7 passed |
| 5 | F20 defaulting | `tests/unit/test_defaulting_protocol.py` | 7 failed, 63 passed | 70 passed, 4 skipped |
| 6 | root `items()` / stray keys | `tests/contract/test_stray_keys.py` | 9 failed, 2 passed | 11 passed |
| 6 | one `items()` definition | `tests/unit/test_items_single_definition.py` | 11 failed | 11 passed |
| 7 | F4 DMX failure path | `tests/contract/test_dmx_failure_path.py` | asserted the swallow | 8 passed, inverted |

Each "before" figure was recorded by running that file against the pre-005 tree before its
implementation task landed. A test that passes before its change is not evidence.
