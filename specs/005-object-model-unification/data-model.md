# Data model — 005 object model unification

**Date**: 2026-08-12 | **Feature**: `005-object-model-unification`

This feature adds no new domain entity. It gives the existing ones **one construction
protocol**, and turns three conventions into declarations: the declared field set, the
defaults, and the JSON wrapping rule.

---

## 1. `CuemsDict` — the model base, after this feature

```
CuemsDict(dict)
├── declared_fields()      classmethod → tuple[str, ...]   accumulated across the MRO
├── declared_defaults()    classmethod → dict[str, Any]    same accumulation, values kept
├── coercion_table()       classmethod → dict[str, Adapter]  cached; delegates to coercion.adapter_table(cls)
├── __init__(init_dict)    programmatic mode  — defaults applied, ensure_items order
├── from_decoded(mapping)  classmethod, decode mode — arrival order preserved
├── _init_runtime()        hook: non-persisted attributes; runs in BOTH modes
├── setter(mapping)        narrowed: skips only keys with no setter (F17)
├── items()                the single definition, filtered to declared_fields()
├── build(parent)          unchanged
└── JSON_SELF_WRAPS: bool  class attribute; replaces the key-casing heuristic
```

Everything above is inherited. `CuemsScript` joins the hierarchy and defines none of it
itself — that is the point of change 6 and of user story 2.

`coercion_table()` is a classmethod on the base rather than a resolver called only from `xml/`
(settled 2026-08-17, T004b): the caller asks the object, exactly as T019 has the mapper ask for
`declared_fields()`. Three verified consequences — the import direction stays one-way because
the `cuemsutils.xml.*` imports inside `coercion.py` are function-local (R1), not because of the
classmethod; the public-API golden does not move because none of the five exported symbols
derives from `CuemsDict`; and the method takes no schema argument while registries are per
schema, which is safe only because every model class is bound in exactly one registry today.
T004's guard raises if that ever stops being true — it stops being true in 006. Full reasoning
in `plan.md` §Project Structure.

### Construction modes

| | `cls(init_dict)` | `cls.from_decoded(mapping)` |
|---|---|---|
| entry point | keyword/dict, `create_script`, editor payload assembly | the mapper, for every decoded object |
| declared defaults | applied | applied for fields the document omits |
| key order | `ensure_items` sorted (unchanged) | **arrival order**, defaults appended (FR-005, R10) |
| coercion | adapter table | adapter table — *the same one* |
| runtime attributes | `_init_runtime()` | `_init_runtime()` (FR-004a) |
| property setters | run, for ergonomics | not the coercion site; reach unchanged (FR-006a) |

One coercion path, two orderings. The orderings differ because arrival order is load-bearing
for `xs:all` types and sorted order is what every generated document already contains.

### The `Unset` sentinel

A declared field whose default is `Unset` is **not inserted** — the key stays absent rather
than present-and-empty. It exists so that the **six** classes gaining a defaults dict (§2,
`bare = 0`) do not start emitting elements they never emitted, and so that "one defaulting
protocol" does not become "every field always present". Do not read that six off §3, which
lists the **five** classes gaining declared *field sets* — a different set, and the one that
moves coherence coverage to 18/18.

---

## 2. Per-class inventory

`bare` = key count from `cls()` today (measured, R3). `declared` = where the field set comes
from today.

| Class | bare | declared today | change in 005 |
|---|---|---|---|
| `Cue` | 0 | `REQ_ITEMS` | bare yields declared defaults (change 5) |
| `AudioCue` | 17 | `REQ_ITEMS` | `items()` override removed |
| `VideoCue` | 17 | `REQ_ITEMS` | `items()` override removed |
| `MediaCue` | 15 | `REQ_ITEMS` | `items()` override removed |
| `ActionCue` | 15 | `REQ_ITEMS` | `items()` override removed |
| `FadeCue` | 18 | `REQ_ITEMS` | `items()` override removed (incl. its hand-ordered variant) |
| `DmxCue` | 17 | `REQ_ITEMS` | `items()` override removed |
| `CueList` | 14 | `REQ_ITEMS` | `items()` override removed |
| `CuemsScript` | 0 | `REQ_ITEMS` | **becomes a `CuemsDict`**; duplicated `setter` deleted; `items()` and `__json__` unwrap hack removed (changes 6, and user story 2) |
| `DmxScene` | 2 | `SCENE_REQ_ITEMS` | none beyond the base protocol |
| `DmxUniverse` | 1 | own dict | none |
| `DmxChannel` | 2 | `DMXCHANNEL_REQ_ITEMS` | none |
| `FadeProfile` | 4 | own dict | none |
| `FadeFunctionParameter` | 2 | own dict | none |
| `Media` | 0 | **none** | gains a declared field set: `file_name`, `id`, `duration`, `regions`; `set_regions`' discarded coercion removed (change 2) |
| `Region` | 1 | `REGION_REQ_ITEMS` (**dead**) | dead dict becomes the real one; `empty_keys` literal deleted; produced by decode (change 2) |
| `AudioCueOutput` | 0 | **none** | gains a declared field set |
| `VideoCueOutput` | 0 | **none** | gains a declared field set; its `__init__` validation is untouched (FR-006b) |
| `DmxCueOutput` | 0 | **none** | gains a declared field set |

Coherence coverage moves 13/18 → **18/18** (R4). The two denominators in this feature are
different on purpose: **19** model classes exist (the rows above), **18** of them are
schema-bound and therefore in scope for the coherence test. Defaulting is parametrized over 19;
coverage is counted over 18.

---

## 3. Declared field sets to be written

Derived from the schema, cross-checked by the coherence test. Defaults chosen for
output-neutrality (§1, `Unset`):

| Class | Fields (schema order) | Notes |
|---|---|---|
| `Media` | `file_name`, `id`, `duration`, `regions` | `MediaType`, measured |
| `Region` | `id`, `loop`, `in_time`, `out_time` | matches the dead `REGION_REQ_ITEMS` |
| `AudioCueOutput` | `output_name`, `output_vol`, `channels` | from `AudioCueOutputsType` |
| `VideoCueOutput` | `output_name`, `output_geometry`, `canvas_region` | `canvas_region` optional → `Unset` |
| `DmxCueOutput` | `output_name` | from `DmxCueOutputsType` |

Exact field lists are asserted by the coherence test rather than trusted from this table; any
disagreement fails the suite with both sides named.

---

## 4. Field-level type contract

The internal type of every field, identical on all three entry points (FR-007). Bold marks
what changes in this feature.

| Field | built today | loaded today | after 005 |
|---|---|---|---|
| `id`, `target`, `action_target` | `Uuid` / `None` | `Uuid` / `None` | unchanged |
| `offset`, `prewait`, `postwait` | `CTimecode` | `CTimecode` | unchanged |
| `FadeCue.duration` (`CTimecodeType`) | `CTimecode` | `CTimecode` | unchanged |
| `Media.duration` (`TimecodeType`) | **`str`** | **`str`** | **unchanged — see the warning below** |
| `ui_properties` | `CuemsDict` | **`dict`** | **`CuemsDict`** |
| `Media` | `Media` | `Media` | unchanged |
| `Media.regions` | `list[Region]` | **`list[dict]`**, wrapped `{'Region': …}` | **`list[Region]`** |
| `Region.in_time` / `out_time` | `CTimecode` | **`dict`** `{'CTimecode': …}` | **`CTimecode`** |
| `outputs` members | `CueOutput` subclass | `CueOutput` subclass | unchanged (closed in 004) |
| `contents` members | `Cue` subclasses | `Cue` subclasses | unchanged |
| runtime attributes | initialized | initialized | unchanged, now **required** on both paths (FR-004a) |

> **`duration` is two different fields.** `FadeCueType.duration` is a `CTimecodeType` and
> emits as a wrapped child, `<duration><CTimecode>00:00:02.000</CTimecode></duration>`.
> `MediaType.duration` is a `TimecodeType` — a restricted **string** — and emits as bare text,
> `<duration>00:00:00.000</duration>`. `Media.set_duration` canonicalises to `str` and its
> getter contract is `str`, asserted by `tests/unit/test_media_duration.py:21-33`.
>
> Unifying them would change the emitted element for every media document and break that
> contract for `cuems-engine`. **`Media.duration` is out of scope for every coercion change in
> this feature**, and the goldens are what would catch a mistake here — after the fact. Read
> this row before touching either setter.

---

## 5. Runtime state — declared, not inferred

Non-persisted attributes carried by cue objects, measured across `cues/`:

`_target_object`, `_conf`, `_armed_list`, `_start_mtc`, `_end_mtc`, `_end_reached`,
`_go_thread`, `_stop_requested`, `_local`, `_player`, `_osc_route`, `_initialized`,
`_action_target_object`.

They stay instance attributes and stay out of every projection. This feature only guarantees
they are initialized on **every** construction mode, via `_init_runtime()`.

> **`_initialized` is not inert, and must not be treated as one of the others.**
> `VideoCueOutput.__init__` sets it `False` *before* population (`CueOutput.py:146`) and
> `set_output_name`'s region-consistency rules are gated on it (`CueOutput.py:178`).
> `CuemsDict.setter` does call those setters during construction (`helpers.py:33-35`), so that
> gate is the only reason the rules do not reach the load path today. `_init_runtime()` must
> preserve the ordering — false during population, true after — in **both** modes. Setting it
> true first gives 14 inventoried setters new reach on decode, which FR-006b forbids, and the
> resulting failure depends on arrival key order (`custom` `output_name` before
> `canvas_region` raises; the reverse does not), so the corpus catches it only by luck. Deciding whether
the runtime/persisted split should be *declared* rather than conventional is feature 006's
first decision stop (`specs/planning/xml-rebuild-06-target-design.md` §8.1).

---

## 6. What this feature does not model

- No new public type, method or signature (FR-027).
- No schema change; every declared field set is cross-checked against the XSD, never the
  other way round (D2, D3).
- No semantic-validation tier. The 14 value-rejecting setters keep exactly the reach they
  have (FR-006, FR-006a); relocating them is 006.
