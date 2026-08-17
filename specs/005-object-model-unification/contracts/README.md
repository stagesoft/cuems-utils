# Contracts — 005 object model unification

Each contract below is a checkable guarantee with a named test file. `C1`–`C4` are
**preservation** contracts (they must hold before and after); `C5`–`C11` are **change**
contracts (they must fail before and pass after — constitution principle II).

The library exposes no network or CLI interface, so "contract" here means the observable
behaviour of the object model and its projections, which is what consumers bind to.

---

## Preservation contracts

### C1 — Goldens are byte-identical, all four sets

`tests/golden/xml/*`, `tests/golden/dict/*`, `tests/golden/generated/*` and
`tests/golden/outcomes.json` are unchanged by this feature. Measured basis: the generated
document restamps the ids F16 stops randomising before serialization, so even change 3 leaves
it untouched (research R8).

- **Test**: existing `tests/contract/test_byte_identity_xml.py` and
  `test_byte_identity_dict.py`, both **unmodified**. `tests/integration/test_d14_chain.py` is
  **extended, not altered**: T011 adds the built-vs-loaded leg (FR-026) and every assertion it
  carries today must survive untouched, which `git diff` on that file makes reviewable in
  isolation. Its module docstring's "green after the swap without having been edited" refers to
  004's swap; T011 updates that sentence rather than leaving it false.
- **Enforcement**: `git diff --stat tests/golden/` must be empty in the feature's final diff.
  A changed golden is a failed feature, not a passed test.
- **If a golden is found to be genuinely wrong** — encoding a defect rather than the intended
  output — that halts this feature. It is corrected in its own change, with its own evidence,
  never inside 005, because a golden edited mid-feature stops being independent evidence that
  the refactor did not leak.

### C2 — Accept/reject parity, in both directions

Every corpus document keeps its pinned outcome. Specifically: the two legacy documents
rejected at object decode stay rejected **with the same rule firing at the same call site**.
Measured 2026-08-17: that site is `VideoCueOutput.__init__`, which calls the module-level
`_classify_output_name` (`src/cuemsutils/cues/CueOutput.py:154`) *before* `super().__init__`,
raising `ValueError`. It is **not** the `set_output_name` property setter — that exists, also
calls `_classify_output_name`, and is a different entry point whose additional
region-consistency rules are gated on `_initialized` (see C12). Parity means the same
exception type from the same call site, not merely two documents that still fail.

The nil-UUID payloads in `tests/data/sample_script.json` stay accepted.

- **Test**: existing `tests/contract/test_accept_reject_parity.py` — whose
  `test_legacy_documents_validate_but_do_not_build_objects` already pins
  `error_type == "ValueError"` and names `_classify_output_name` — plus a new case naming the
  nil UUID explicitly (T012a).
- **Spec**: FR-006, FR-006a, FR-024, SC-007.

### C3 — Emission order is unchanged, root included

A decoded `CuemsScript` re-serializes with its source key order. Construction must not route
decode through the sorting path.

- **Test**: `test_byte_identity_xml.py` (existing) covers it in aggregate; new
  `tests/contract/test_root_key_order.py` (T012b) pins the root key order of a hand-authored
  document directly, so the failure names the cause rather than a 24 KB byte diff. It is
  written in Phase 2, green on today's code, before T024/T025 can break it.
- **Spec**: FR-005, research R10.

### C4 — The UI payload is untouched

`read()`'s dict — what `cuems-editor` transmits verbatim on `project_load` — is byte-identical,
repeated-element shape included. This feature changes objects, not that projection.

- **Test**: existing `tests/contract/test_ui_payload_contract.py`.
- **Spec**: FR-022 (hard constraint).

---

## Change contracts

### C5 — Identical internals across entry points (change 1)

For every corpus document, a recursive field-by-field type comparison of
built / XML-decoded / JSON-decoded objects reports zero differences, `ui_properties`
(`CuemsDict`) and `regions` (`list[Region]`) included.

- **Test**: new `tests/integration/test_construction_parity.py`, the promoted
  `probe_construction` comparison, wired into the D14 chain.
- **Fails before**: `ui_properties` is `dict` and `regions` is `list[dict]` on the decoded side.
- **Spec**: FR-007–FR-011, SC-001.

> **Measured 2026-08-17 at `79632c3`: the divergence is wider than FR-019 enumerates.**
> The harness reports **44** type differences between a built object and the same content
> decoded, in four groups:
>
> | group | count | closed by |
> |---|---|---|
> | `ui_properties`: `CuemsDict` → `dict` | 4 | BC1 (T028) |
> | region wrapper shape and its structural cascade | 24 | BC2 (T024/T026) |
> | built side uncoerced — `int`→`float`, `action_target` `str`→`Uuid` | 6 | FR-001, once coercion runs on the programmatic path |
> | **`ui_properties` wildcard `None` → `"None"`** | 6 | **nothing in 005** |
> | **`DmxCue` fields left raw (`Mapper.OPAQUE_TYPES`)** | 4 | **nothing in 005** |
>
> The last two groups are inherited from 004 and deliberate *there*: the wildcard round-trip is
> recorded at `mapper.py:344` as "it reads like a bug, and it is one", deferred because fixing
> it rewrites editor state for every cue in every project; and `OPAQUE_TYPES` decodes a
> `DmxCue` with `model(body)` without recursing, so its `autoload`/`enabled`/`timecode` stay
> strings. Neither is enumerated in FR-019 and neither has a task.
>
> **Consequence: SC-001's "zero type differences" is not reachable within 005's enumerated
> scope.** The question is open — widen 005, narrow SC-001 to the enumerated groups, or defer
> both to 006. `test_the_unenumerated_divergence_is_exactly_as_measured` pins the counts so the
> answer is deliberate rather than discovered at T032.

### C6 — Regions are typed from every source (change 2)

Regions supplied as a single mapping, a list of mappings, a list of `Region`s, or the wrapped
`{'Region': {…}}` shape the reader produces all yield `list[Region]`, with `in_time`/`out_time`
as `CTimecode`.

- **Test**: new `tests/unit/test_region_coercion.py` (four shapes) plus C1 for the emission.
- **Fails before**: `Media.set_regions` rebinds its loop variable and discards the coercion.
- **Spec**: FR-009, SC-006.

### C7 — Clearing an id clears it (change 3)

`script.id = None` leaves the field empty; generating an id remains the job of the `new_uuid`
default at construction time, not of assignment.

- **Test**: new `tests/unit/test_id_clearing.py`, plus an assertion on `create_script()`'s
  returned template.
- **Fails before**: `Uuid(None)` mints a uuid4, so the template ships two random ids.
- **Spec**: FR-019 row 3.

### C8 — A failing setter is not swallowed (change 4)

A key with no setter is skipped, exactly as today. An `AttributeError` raised *inside* a
setter propagates.

Exceptions of other types raised inside a setter already propagate today — the blanket guard
is `except AttributeError` (`helpers.py:33-36`) — and this change does not affect them. Only
`AttributeError` changes meaning, from "swallowed wherever it came from" to "swallowed only
when it came from the `getattr` lookup".

- **Test**: new `tests/unit/test_setter_error_propagation.py` (both halves).
- **Fails before**: the blanket `except AttributeError: pass` swallows both.
- **Spec**: FR-019 row 4.

### C9 — One defaulting protocol (change 5)

Bare construction of every model class yields that class's declared defaults, by the same
mechanism. **Six** classes that return an empty object today gain declared defaults — `Cue`,
`CuemsScript`, `Media` and the three `CueOutput` subclasses (data-model §2, `bare = 0`).
Separately, **five** classes gain a declared *field set* — `Media`, `Region` and the three
`CueOutput` subclasses (data-model §3) — and that is what moves coherence coverage to 18/18.
The two counts describe different sets and must not be conflated.

- **Test**: new `tests/unit/test_defaulting_protocol.py` (parametrized over every model
  class); `tests/unit/test_coherence.py` updated so the uncovered set is empty.
- **Fails before**: `Cue()`, `CuemsScript()`, `Media()` and the three `CueOutput` subclasses
  return empty objects.
- **Spec**: FR-017, FR-018, SC-005.

### C10 — One declared-field rule, stray keys dropped and logged (change 6)

`items()` has exactly one definition; the engine selects fields by the same rule for model
objects; a key the rule does not recognise is absent from every projection and produces
**exactly one log record per dropped key per object**, at DEBUG, naming class and key, with no
value in the message. A document dropping the same key on five cues therefore emits five
records; the INFO budget is untouched, which is what keeps 004's logging budget intact.

- **Test**: new `tests/contract/test_stray_keys.py` — root and cue, XML and JSON projections,
  plus the log assertion and a wildcard-subtree case proving `ui_properties` content is *not*
  filtered.
- **Fails before**: the root emits stray keys while cues drop them silently.
- **Spec**: FR-014, FR-015, FR-015a, SC-004.

### C11 — DMX scene failure raises (change 7)

A DMX scene that cannot be serialized aborts the write with an error identifying the scene by
its `id` — falling back to its zero-based index in the cue's scene contents when no `id` is
present — and naming the originating cue. No ambient `except Exception` replaces it.

- **Test**: `tests/contract/test_dmx_failure_path.py`, inverted from "swallowed" to "raised".
- **Fails before**: the write succeeds and the document is missing the scene.
- **Spec**: FR-023, SC-003.

### C12 — Runtime state survives every entry point

Every cue class arrives from all three entry points with its runtime attributes initialized,
and none of them appears in `items()`, the XML, or either wire projection.

> **`_initialized` is not an ordinary runtime attribute.** `VideoCueOutput.__init__` sets it
> `False` *before* population on purpose (`CueOutput.py:146`), and `set_output_name`'s
> region-consistency rules are gated on it (`CueOutput.py:178`). `CuemsDict.setter` does
> resolve and call those setters during construction (`helpers.py:33-35`), so that gate is the
> only reason those rules do not reach the load path today. `_init_runtime()` MUST NOT set
> `_initialized` true before population, in either construction mode. Doing so widens setter
> reach — which FR-006b forbids — and the resulting failure is *arrival-order dependent*: a
> `custom` `output_name` arriving before `canvas_region` raises, while the reverse order does
> not. C2 catches it, but only for documents whose key order happens to expose it.

- **Test**: new `tests/unit/test_runtime_state.py`, parametrized over the cue classes,
  including an explicit case that `_initialized` is false while a decoded object is being
  populated and true afterwards.
- **Fails before**: not a regression today — it is a guarantee this feature must not lose
  while replacing the constructor path. It is written first for exactly that reason.
- **Spec**: FR-004a, SC-004a.

---

## Performance contract

### C13 — Decode budget, spent once

Decode of the largest corpus document (24 KB) stays **≤ 2×** its pre-005 measurement **and**
**≤ 75 ms** absolute. Full-suite wall time and the write path stay within 10% of the
2026-08-12 baseline (1251 passed, 43 skipped, 36.71 s; decode 36.3 ms). The adapter table is
built once per class, never per object, and no value passes through an adapter twice.

- **Test**: new `tests/integration/test_construction_performance.py`, capturing the pre-005
  number **before** the first behaviour change lands, plus a ≥1000-cue construction benchmark
  as a baseline for later features.
- **Spec**: FR-PERF-001, SC-PERF-001, SC-PERF-002, SC-PERF-003.
