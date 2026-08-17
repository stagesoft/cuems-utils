# Research — 005 object model unification

**Date**: 2026-08-12 | **Feature**: `005-object-model-unification`
**Method**: every finding below was produced by running the code on this branch (post-004),
not by reading it. Commands are given so each can be re-run.

---

## R1 — Where coercion can live without an import cycle

**Decision**: model classes resolve their coercion table **lazily**, through a new neutral
module `src/cuemsutils/coercion.py`, which imports `cuemsutils.xml.spec` and
`cuemsutils.xml.registry` *inside the function*, caches `{field → Adapter}` per model class,
and is called on first construction of that class.

**Rationale**: measured import direction is one-way today — `xml/` imports `cues/`
(`registry.py:133-145`, `adapters.py:260`), and `cues/` imports nothing from `xml/`.
Importing the adapters at module scope from `cues/` would close the cycle. A lazy call site
does not, because by the time any model object is constructed both packages are importable.
The adapters themselves stay where 004 put them; `coercion.py` is a resolver, not a second
copy.

**Alternatives considered**: (a) move `adapters.py` up to the package root — larger diff, and
004's contract tests import it from `cuemsutils.xml.adapters`; (b) declare the adapter per
field in `REQ_ITEMS` — duplicates what the schema already states, and D2 forbids a second
source of truth; (c) inject the table from `xml/` at import time — reintroduces the implicit
registration 004 deleted.

**Consequence**: D2 holds. The field's *type* still comes from the XSD via `TypeSpec`; only
the lookup direction is new.

---

## R2 — Two decode strategies exist today, and they disagree

**Measured**: `mapper._decode_member` builds repeated members with `model(body)` — the real
constructor, setters and validation included ([mapper.py:183](../../src/cuemsutils/xml/mapper.py#L183))
— while `_instantiate` populates everything else with raw `dict.__setitem__`
([mapper.py:419-422](../../src/cuemsutils/xml/mapper.py#L419)).

Visible consequences, both measured:

| | result |
|---|---|
| `outputs` members | **already typed** — `AudioCueOutput`, `VideoCueOutput` |
| `regions` members | **plain dicts**, still wrapped: `{'Region': {…}}`, with `in_time`/`out_time` left as `{'CTimecode': '…'}` |
| two legacy corpus documents | **rejected at decode** by `CueOutput`'s `output_name` rule, pinned in `tests/golden/outcomes.json` as `read: ok` / `to_objects: error` |

**Decision**: the unified path must reproduce **each document's current outcome**, not adopt
either strategy wholesale. Unifying on the permissive one would make those two documents
start loading; unifying on the strict one would reject documents that load today.

**Reproduce**:
```bash
PYENV_VERSION=3.11.9 pyenv exec python -c "
from cuemsutils.xml.xml_reader_writer import XmlReaderWriter as R
s=R(schema_name='script',xmlfile='tests/data/corpus/cuems-engine/projects/complex_test/script.xml').read_to_objects()
m=s['CueList']['contents'][2]['Media']; print(type(m['regions'][0]), m['regions'][0])"
```

---

## R3 — Bare construction today: 6 classes empty, 13 with defaults

**Measured** (`cls()` with no arguments, key count):

| empty (0 keys) | defaults applied |
|---|---|
| `Cue`, `CuemsScript`, `Media`, `AudioCueOutput`, `VideoCueOutput`, `DmxCueOutput` | `AudioCue` 17, `VideoCue` 17, `MediaCue` 15, `ActionCue` 15, `FadeCue` 18, `DmxCue` 17, `CueList` 14, `FadeProfile` 4, `FadeFunctionParameter` 2, `DmxScene` 2, `DmxUniverse` 1, `DmxChannel` 2, `Region` 1 |

`Region` is the odd one: it has a `REGION_REQ_ITEMS` dict that nothing reads, and an
`empty_keys = {"id": "0"}` literal inside `__init__` that it uses instead
([MediaCue.py:33-46](../../src/cuemsutils/cues/MediaCue.py#L33)).

**Decision**: F20's "one protocol" is implemented as **declared defaults applied identically
on every path**, with an explicit `Unset` sentinel for fields that must stay *absent* rather
than present-and-empty. The **six** classes with no defaults dict get one — consistent with the
next paragraph's "six empty classes", and not to be confused with the **five** that gain
declared *field sets* (R4, C9); `Region`'s dead `REGION_REQ_ITEMS` becomes the real one.

**Rationale**: `_instantiate` calls `model()` first, so today's decode already inherits
whatever bare construction does. Giving the six empty classes defaults therefore changes what
a decoded object contains — and, through `obj.keys()`, what gets emitted. The sentinel is
what keeps that from becoming an output change; the goldens are the gate that proves it.

**Alternatives considered**: decode applies no defaults at all — would strip defaults the 13
classes inject today, an output change in the opposite direction.

---

## R4 — 004's coherence test already names this feature's work

`tests/unit/test_coherence.py::test_uncovered_classes_are_the_expected_ones` asserts the
uncovered set is exactly `{Media, Region, AudioCueOutput, VideoCueOutput, DmxCueOutput}`, with
the comment *"Giving them defaults dicts is an object-model change, which feature 004
explicitly does not make."*

**Decision**: 005 gives all five a declared field set, coverage goes **13/18 → 18/18**, and
that test inverts: the uncovered set becomes empty and the assertion becomes
`UNCOVERED == set()`. This is an expectation test changing with a spec'd behaviour change —
not a golden.

---

## R5 — The declared-field rule has two consumers, and they differ today

**Measured**: 10 `items()` overrides in the model (`Cue`, `AudioCue`, `VideoCue`, `ActionCue`,
`FadeCue`, `DmxCue`, `CueList`, `MediaCue`, `CueOutput`, `CuemsScript`), each layering its own
`REQ_ITEMS`; and the engine does **not** use `items()` at all — `mapper._fill` iterates
`obj.keys()` ([mapper.py:254](../../src/cuemsutils/xml/mapper.py#L254)).

**Decision**: one `items()` on `CuemsDict`, filtered by declared fields accumulated across the
MRO, and `_fill` switches to the same rule **for model objects only**. Wildcard containers
(`ui_properties` subtrees), plain dicts and lists keep passing everything through — they have
no declared field set, and filtering them would delete real content.

**Rationale**: FR-015 asks for one rule, not one code path. The MRO accumulation already
exists, written for the coherence test (`test_coherence.declared_fields`), and can move into
the model as the single definition both it and `items()` use.

---

## R6 — Emission of regions after they become `Region` objects

**Measured**: `RegionsType` derives to a single repeated child element named `Region`
(`[('Region', 'RegionType', True)]`), and `RegionType` is *already bound* to the `Region`
class in the registry — the binding exists and is not reached.

Today's list member is a `dict` whose class name is in `TRANSPARENT_LIST_ITEMS`, so
`_fill_list_item` recurses and the `{'Region': {…}}` key supplies the element name. After 005
the member is a `Region`, so the other branch runs: `_tag_for_item` finds `Region` among the
declared children and emits the same tag.

**Decision**: no mapper change is needed for the tag; the change is in what decode produces.
The byte-identity risk is concentrated in **timecode fields inside a region** — today
`{'CTimecode': '00:00:17.500'}` emits through the mapping branch, after 005 a `CTimecode`
object emits through the value-object branch (`SubElement(type(obj).__name__).text = str(obj)`).
Both produce `<CTimecode>00:00:17.500</CTimecode>`, which the generated golden already
demonstrates for the built path. **Proof obligation**: a corpus golden containing regions with
timecodes — `complex_test/script.xml` has three — must stay byte-identical.

---

## R7 — F16 is a coercion-location fix, not a setter special case

**Measured**: `Uuid.__init__` mints a uuid4 when its argument is falsy and raises on anything
that fails the uuid4 regex ([Uuid.py:13-19](../../src/cuemsutils/tools/Uuid.py#L13)). So
`script.id = None` → `set_id` → `Uuid(None)` → a fresh random id. Meanwhile 004's
`_UuidAdapter.decode` already returns `None` for `None`/`""` and keeps an unparseable value as
its raw string ([adapters.py:135-143](../../src/cuemsutils/xml/adapters.py#L135)).

**Decision**: setters delegate to the adapter. `None` then clears, because that is what the
adapter does; *generating* an id stays where it belongs — the `new_uuid` callable in
`REQ_ITEMS`, which runs at defaulting time, not at assignment time.

**Consequence**: this also preserves the nil-UUID acceptance, because the adapter's
raw-string fallback is what handles it — the setter never calls `Uuid()` directly again.

---

## R8 — The generated golden is insulated from F16

**Measured**: `capture_goldens._make_template_writable` restamps the ids `create_script`
clears, using raw `script["id"] = new_uuid()`, precisely so the template can be written and
compared ([capture_goldens.py:279-296](../../tests/support/capture_goldens.py#L279)). The two
ids F16 stops randomising are restamped before serialization, and `normalize_uuids` maps by
first appearance **in the output bytes**, which never contained the discarded values.

**Decision**: **zero goldens change in this feature** — `xml/`, `dict/`, `generated/` and
`outcomes.json` all stay byte-identical. That is a stronger, checkable claim than "goldens are
not regenerated to make a test pass", and it is the feature's primary gate.

---

## R9 — Which 004 tests legitimately change

Goldens never change (R8). These **expectation** tests do, each because a spec'd behaviour
change makes their current assertion false:

| Test | Why it changes |
|---|---|
| `tests/contract/test_dmx_failure_path.py` | asserts the swallow is preserved; change 7 removes it → asserts a raise naming the scene |
| `tests/unit/test_coherence.py::test_uncovered_classes_are_the_expected_ones` | five classes gain declared *field sets* — `Media`, `Region`, the three `CueOutput` subclasses — → uncovered set becomes empty (R4). Not the same five as the **six** classes gaining *defaults*; see C9 |
| `tests/contract/test_registry_totality.py::test_generic_bindings_are_explicit_not_absent` | `UiPropertiesType` must now yield a `CuemsDict` on decode |
| `tests/contract/test_semantic_roundtrip.py` | its docstring excludes built-vs-loaded "because F18 belongs to 005"; that exclusion is lifted |

Four further files are **extended, never altered** — no existing assertion in them may change:

| Test | What is added |
|---|---|
| `tests/integration/test_d14_chain.py` | the built-vs-loaded leg (FR-026, T011/T030) |
| `tests/contract/test_logging_budget.py` | the drop-and-log record's budget arithmetic (T020) |
| `tests/integration/test_create_script_completeness.py` | the cleared-template assertions (T038) |
| `tests/contract/test_accept_reject_parity.py` | the explicit nil-UUID case (C2, T012a) |

Everything else in the suite must pass **unchanged**. A change to any other test file is a
signal to stop and re-read the spec.

---

## R10 — Key order, and the one way to break every script file

**Measured**: a decoded root preserves the *document's* key order
(`['id','name','description','created','modified','ui_properties','CueList']` for
`complex_test`), while `ensure_items` sorts alphabetically
([helpers.py:98](../../src/cuemsutils/helpers.py#L98)). `CuemsScript` is an `xs:all` type, so
`spec.order_keys` returns keys as given and **emission order is arrival order**.

**Decision**: two construction *modes*, one coercion path:

- `cls(init_dict)` — programmatic. Applies declared defaults, keeps `ensure_items`' sorted
  order. Unchanged from today.
- `cls.from_decoded(mapping)` — decode. Preserves arrival order, then appends any defaulted
  field that the document omitted.

**Rationale**: this is the single most dangerous change available in the feature. Routing
decode through `cls(init_dict)` would re-sort the root of every hand-authored script on save.
FR-005 states it; `tests/contract/test_byte_identity_xml.py` proves it.

---

## R11 — The JSON projection, and the hack that must not simply be deleted

**Measured**: 8 hand-written `__json__` methods in `cues/` (plus `Uuid` and `CTimecode`, which
are value types and stay). `Cue.__json__` self-wraps as `{ClassName: {...}}`;
`CuemsScript.__json__` returns a bare dict and un-wraps its children by testing
`if k.lower() != k` ([CuemsScript.py:298-299](../../src/cuemsutils/cues/CuemsScript.py#L298)).

**Decision**: replace the casing heuristic with a **declared** class attribute
(`JSON_SELF_WRAPS`, true for cues and cue lists, false for the root), leaving the emitted
payload identical. Replacing `__json__` with the derived projection is feature 006's change 3
and is **not** done here.

**Second-order effect, and a real work item**: once regions decode to `Region` objects, the
JSON of a *loaded* script loses the `{'Region': …}` wrapper it carries today, matching what a
built script already produces. The D14 chain test's json leg must therefore rebuild regions
from the unwrapped shape — `test_d14_chain` asserts `rebuilt == obj`, so both legs move
together or the test fails loudly. That is the intended detection mechanism.

---

## R12 — Performance: where the new cost is

**Measured**: the largest corpus document (24 KB, `complex_test/script.xml`) decodes in
**36.3 ms** (mean of 5, `read_to_objects`). Full suite: **1251 passed, 43 skipped, 36.71 s**.

Coercion currently does not run for most decoded fields, so the new cost is real: `Uuid` and
`CTimecode` construction per field, plus one dict lookup per field for the adapter table.
Schema walking is already cached per `(schema, type)` by 004 and is not on this path.

**Decision**: budget as clarified — decode ≤ **2×** the pre-005 measurement **and** ≤ **75 ms**
for the largest corpus document; suite wall time and the write path keep the 10% rule. The
adapter table is cached per class, built once, never per object. A `≥1000`-cue construction
benchmark is added because no construction baseline exists today.

**Alternatives considered**: a 10% delta on decode — rejected during clarification; it would
have made the budget, not the design, drive the implementation.
