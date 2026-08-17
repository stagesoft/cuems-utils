# Defaults audit — 005 object model unification

**Written**: 2026-08-17 | **Task**: T036 | **Requirement**: FR-017, FR-019 row 5
**Gate**: every row below must leave `git diff --stat tests/golden/` empty.

Change 5 gives six classes a declared defaults dict. Each one changes what bare
construction returns, and — because `_instantiate` used to call `model()` first — could
have changed what a *decoded* object contains and therefore what gets emitted. The `Unset`
sentinel is what keeps that from becoming an output change; this file is the per-field
record that it did.

## One row per newly declared default

`Unset` = declared but **not** inserted; the key stays absent rather than present-and-empty.

| Class | Field | Choice | Why, and the output-neutrality evidence |
|---|---|---|---|
| `Cue` | the 13 in `REQ_ITEMS` | values | Already the defaults every cue subclass applied via `ensure_items`; `Cue` simply never applied them to itself. Subclasses were already emitting all 13, so nothing new appears. Evidenced by every corpus golden. |
| `CuemsScript` | the 7 in `REQ_ITEMS` | values | Same: the root applied them when given an init dict and not otherwise. `tests/golden/xml/*.xml` and `generated/create_script.xml` unchanged. |
| `Media` | `file_name`, `id`, `duration`, `regions` | **all `Unset`** | All four are schema-required, but a bare `Media()` is a placeholder the caller fills in. Defaulting them to `None` would emit four empty elements into every media document. `Media()` therefore stays empty — which is also why `tests/unit/test_media_duration.py`'s five bare `Media()` call sites keep working untouched. |
| `AudioCueOutput` | `output_name`, `output_vol`, `channels` | **all `Unset`** | Outputs are constructed from a body or not at all; an empty output is not a valid document element. |
| `VideoCueOutput` | `output_name`, `output_geometry`, `canvas_region` | **all `Unset`** | `canvas_region` is `minOccurs="0"` and an alias output must **not** carry it — inserting `None` would both emit an absent element and trip `__init__`'s own alias/custom consistency rule. |
| `DmxCueOutput` | `output_name` | **`Unset`** | Single required field; same reasoning as the other two outputs. |

Two further classes gained a *fill* they had been missing, without gaining a new
declaration:

| Class | Field | Why |
|---|---|---|
| `Region` | `id`, `loop`, `in_time`, `out_time` | `REGION_REQ_ITEMS` existed and **nothing read it**; `__init__` used a local `empty_keys = {"id": "0"}` literal instead. Promoting the dict to the real declaration is what moved coherence coverage to 18/18. |
| `DmxUniverse` | `dmx_channels` | `set_dmx_channels` swallows a `None` rather than storing it, so the setter alone left a declared field absent. `_fill_declared_defaults` writes through `dict.__setitem__` for exactly this reason. |

## The sweep FR-019 row 5's edge case requires

> *"Bare construction of an abstract-ish base (`Cue()`): now returns declared defaults; any
> code that relied on the empty result must be found."*

Searched `src/` and `tests/` for bare construction of the six classes, and for the falsy
checks that would depend on an empty result (`if not obj`, `len(obj)`, `== {}`).

**Result: no production code relies on it. Recorded explicitly, because an unrecorded
sweep is indistinguishable from a skipped one.**

| Finding | Verdict |
|---|---|
| `tests/unit/test_media_duration.py:21,28,35,41,47` — five bare `Media()` | **Unaffected.** `Media`'s defaults are all `Unset`, so `Media()` is still empty. This is the file T048 names as a hazard; it is untouched. |
| `src/cuemsutils/xml/validators.py:102` — `if not output` | **Not a match.** Operates on raw config dicts from `project_mappings`, not on model objects. |
| `src/cuemsutils/xml/mapper.py:467` — `value == {}` | **Not a match.** `_omit`'s emptiness test for optional *fields*, applied to values already read off an object, not to a constructed one. |
| Bare `Cue()`, `CuemsScript()`, `AudioCueOutput()`, `VideoCueOutput()`, `DmxCueOutput()` in `src/` | **None found.** |

## Gate

- `git diff --stat tests/golden/` — **empty** after change 5 landed.
- Full suite green: 1482 passed, 47 skipped, 2 xfailed.
- `tests/unit/test_defaulting_protocol.py` asserts the table above per class, including
  that `Unset` fields stay absent.
