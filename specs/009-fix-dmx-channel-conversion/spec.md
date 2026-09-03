# Feature Specification: Stop `DmxUniverse` from silently corrupting DMX channel data on construction

**Feature Branch**: `009-fix-dmx-channel-conversion`
**Created**: 2026-09-03
**Status**: Draft
**Input**: User description: "use @specs/planning/dmx-universe-channel-conversion-defect.md to
develop a new fix feature that addresses the `DmxChannel` conversion error. Use remediation
proposal 1 also looking for a xsd structure extension if needed"

**Defect record** (authoritative, read before planning):
`specs/planning/dmx-universe-channel-conversion-defect.md` — characterizes the defect,
its reachability from document load, precedent (feature 005's `DmxSceneWriteError` on the
write path), and three remediation proposals. This feature implements **proposal 1**: raise
instead of swallowing, mirroring feature 005's pattern on the read side.

**Scope note**: this is a narrow, self-contained bugfix in one method
(`DmxUniverse.set_dmx_channels`, `src/cuemsutils/cues/DmxCue.py:372-396`), not part of the
xml-rebuild feature sequence (008/009-consumer-migration in `specs/planning/xml-rebuild/`).
This feature's own branch number (009) collides in name only with the "feature 009" referenced
there — they are unrelated pieces of work; no dependency in either direction.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A corrupt DMX universe fails to construct, loudly and precisely (Priority: P1)

A component consuming this library (the engine, the editor, or anything constructing a
`DmxUniverse` from external data) builds one from a payload containing at least one malformed
DMX channel entry — one that does not decode cleanly into a channel/value pair. This cannot
happen through a schema-valid `script.xml` (XSD structural validation already rejects a
malformed `<DmxChannel>` before this code ever runs — confirmed by investigation, see "XSD
investigation, resolved" below); it happens when a `DmxUniverse` is built from a payload that
was never validated against the schema — most plausibly a JSON-sourced payload
(`CuemsScript.from_json`, feature 006) coming from an external editor or API caller, or direct
programmatic construction. Today, that construction "succeeds": every channel in that universe,
including the well-formed ones, is silently replaced with the raw, unconverted input, and
lighting output built from it uses garbage data with no indication anything went wrong beyond a
log line most operators never see.

After this fix, the construction fails immediately with a specific, catchable error that names
the universe and the failing channel entry, instead of silently handing corrupted channel data
downstream to whatever eventually drives lighting output.

**Why this priority**: This is the only user story — the defect has one shape and one fix. It is
P1 because the current behavior lets corrupted lighting data reach production output undetected,
which is a safety-adjacent silent-failure defect, not a cosmetic one.

**Independent Test**: Can be fully tested by constructing a `DmxUniverse` directly (or via
`CuemsScript.from_json` with a payload that reaches `set_dmx_channels`) with one malformed
channel entry among otherwise-valid entries, and confirming: (a) a named, catchable error is
raised identifying the universe and the failing entry, (b) no partially-converted or raw fallback
data is stored on the object, and (c) a universe containing only well-formed entries continues to
convert exactly as it does today.

**Acceptance Scenarios**:

1. **Given** a `DmxUniverse` receiving a list of channel entries where every entry is well-formed
   (as it always is when the entries came from decoding a schema-valid `script.xml`, per the XSD
   investigation below), **When** the channels are set, **Then** every entry is converted to a
   `DmxChannel` instance and stored, exactly as today (no observable behavior change for valid
   input, including the ordinary document-load path).
2. **Given** a `DmxUniverse` receiving a list of channel entries where one entry in the middle of
   an otherwise-valid batch cannot be converted (e.g., missing the expected key, or not
   subscriptable), **When** the channels are set, **Then** a named error is raised identifying the
   universe, the failing entry's index, and its type name, and `dmx_channels` is left unset by
   this call rather than populated with a mix of converted and raw data.
3. **Given** the same malformed-entry scenario arrived at via `CuemsScript.from_json` or any other
   non-XML construction path that does not run schema validation, **When** the payload is decoded
   into objects, **Then** construction fails with the same named error, rather than succeeding and
   leaving corrupted channel data reachable by downstream consumers. (Loading a `script.xml`
   document is not itself a reachable path for this specific failure — see "XSD investigation,
   resolved" — but must continue to raise its own existing `SchemaError`/`ValidationError` for a
   structurally malformed `<DmxChannel>`, unaffected by this feature.)
4. **Given** a single malformed entry (not a list), **When** it is passed to `set_dmx_channels`,
   **Then** the same named error is raised (the current single-entry-wrapped-into-a-list behavior
   is preserved for valid input, and applies to the error path too).

### Edge Cases

- What happens when `channels` is an empty list? Today this stores an empty list; this fix MUST
  preserve that (no error — nothing to fail to convert).
- What happens when every entry in the batch is `None`? Today `None` entries are skipped inside
  the loop, and if the resulting `channel_list` is empty this is not treated as an error; this fix
  MUST preserve that (a batch of only `None`s is not a conversion failure).
- What happens when an entry is already a `DmxChannel` instance mixed in with unconverted-but-valid
  dict entries (no malformed entry present)? Today this is not really supported (the `else` branch
  re-stores the *original* `channels` list on a matching iteration, which a later iteration's
  raw-dict conversion then silently overwrites with only the converted entries — a mix loses
  data today, order-dependently). This fix MUST NOT preserve that quirk. Instead, every entry is
  resolved to a proper `DmxChannel` object before it is ever placed in the result — an
  already-`DmxChannel` instance is appended as-is, a raw dict entry is converted and the new
  instance appended, `None` is skipped — with **no raw dict ever reaching `dmx_channels`**,
  consistent with features 005-008's standing direction that decoded content is superseded by
  proper model objects, not left as raw dicts. See FR-004a.
- How does the error surface when raised via `CuemsScript.from_json` versus when
  `DmxUniverse`/`set_dmx_channels` is invoked directly by application code? The error type and
  message MUST be identical in both cases — this feature does not add call-site-specific wrapping.
  (XML document load, via `CuemsScript.load`, is not a reachable path for *this* error at all —
  see "XSD investigation, resolved" — so no wrapping decision is needed there.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `DmxUniverse.set_dmx_channels` MUST raise a named, catchable error when any entry in
  the input cannot be converted to a `DmxChannel`, instead of silently storing the raw,
  unconverted input as `dmx_channels`.
- **FR-002**: The raised error MUST identify the universe (`universe_num`, when available on the
  object being populated), the failing entry's **index** within the input, and the failing entry's
  **type name** (e.g. `dict`, `int`) — never the entry's value or a `repr()` of it, and never the
  whole raw input dumped into the message, mirroring feature 005's `DmxSceneWriteError` precedent
  (identifiers only, not object content, so show content never leaks into an error string or log
  record).
- **FR-003**: A single bad entry MUST cause the whole call to fail — `dmx_channels` MUST NOT be
  left holding a mix of converted `DmxChannel` instances and raw, unconverted entries, and MUST
  NOT be left holding the previous value's fallback (the current "store the whole raw list" branch
  is removed, not preserved as a fallback for some cases).
- **FR-004**: A batch containing only well-formed entries (including a batch of only `DmxChannel`
  instances, or only `None` entries, or empty) MUST continue to load exactly as it does today, for
  every currently-tested/observable behavior (element identity and values) — this fix changes only
  the failure path, not the success path. (The unified loop in FR-004a's resolution builds a new
  `list` object rather than reusing the input list's own identity for the all-already-`DmxChannel`
  case; no test or documented contract relies on `dmx_channels is channels`, only on element-wise
  identity and equality, so this is not an observable behavior change.)
- **FR-004a**: A batch mixing already-`DmxChannel` instances with still-raw (but individually
  valid) dict entries — no malformed entry present — MUST convert every raw entry to a `DmxChannel`
  and append it in input order alongside the already-converted instances, producing one list of
  `DmxChannel` objects with no raw dict surviving into `dmx_channels`. This is a **defined**
  behavior, not a preserved quirk: today's per-iteration overwrite (which silently drops
  already-converted instances from a mixed batch, order-dependently) is corrected as part of this
  fix, matching features 005-008's direction that decoded content is superseded by proper model
  objects rather than left as raw dicts.
- **FR-005**: Both `KeyError`-shaped failures (a dict entry missing the expected key) and
  `TypeError`-shaped failures (a non-subscriptable entry, e.g. a bare `int`) MUST produce the same
  named error type — the fix MUST NOT let one kind of malformed input raise this feature's new
  error while the other kind still falls through to some other, less specific behavior.
- **FR-006**: The new error type MUST be added to `cuemsutils.errors` as a public, catchable
  symbol, consistent with this library's existing convention that a caller must be able to name
  what it catches (see `CuemsError`/`ValidationError`/`SchemaError`/`IngestError`).
- **FR-007**: Constructing a `DmxUniverse` from any non-XML-validated payload containing a
  malformed channel entry (e.g., via `CuemsScript.from_json`, or direct/programmatic
  construction) MUST fail with this error rather than succeeding with corrupted channel data
  silently present in the returned object. A schema-valid `script.xml` document's own existing
  structural failure path (`SchemaError`/`ValidationError` on `CuemsScript.load`) is unaffected —
  investigation confirmed T1 already rejects a malformed `<DmxChannel>` before `set_dmx_channels`
  ever runs on XML-sourced content, so this feature does not change document-load error behavior,
  only what happens for content that bypassed schema validation.
- **FR-008**: This feature MUST NOT change behavior for any document or input that converts
  cleanly today — the existing characterization tests
  (`tests/unit/test_dmx_universe_channels.py`) that pin *valid*-input behavior MUST continue to
  pass unmodified; only the tests pinning the *swallow-and-fallback* behavior are expected to
  change, because that behavior is what this feature removes.
- **FR-XSD-001**: **Resolved — no XSD structure extension is needed.** Investigated and confirmed
  (see "XSD investigation, resolved" below): the decoder guarantees the shape
  `set_dmx_channels` expects for *any* schema-valid `<DmxUniverse>` content, regardless of
  occurrence count, driven purely by the element's declared cardinality — no `minOccurs`/
  `maxOccurs`/wrapper-element change would add a guarantee that does not already exist. This
  feature makes no `.xsd` changes.
- **FR-UX-001**: The new error's message shape, exception chaining (`raise ... from`), and
  "identifiers only, never object repr" rule MUST match the existing `DmxSceneWriteError`
  (`src/cuemsutils/xml/mapper.py:907-944`) precedent and `cuemsutils.errors`'s existing four public
  exception types' conventions (docstring shape, `__all__` placement, `CuemsError` hierarchy) — no
  new error-reporting convention is introduced for this one feature.
- **FR-PERF-001**: `DmxUniverse.set_dmx_channels` MUST NOT regress in per-call latency versus its
  pre-fix baseline. See SC-PERF-001 for the measured budget and methodology.

### Key Entities

- **`DmxChannel`**: a single DMX channel/value pair (`src/cuemsutils/cues/DmxCue.py:428`). Not
  changed by this feature — the fix is entirely in how `DmxUniverse` converts input into
  instances of this class.
- **`DmxUniverse`**: holds `universe_num` and a list of `DmxChannel` instances
  (`src/cuemsutils/cues/DmxCue.py`). This feature changes only its `set_dmx_channels` setter.
- **`DmxChannelDecodeError`** (new, settled in planning — see research.md Decision 1): carries the
  failing universe, the failing entry's index, and the failing entry itself (for programmatic
  inspection only, never rendered into the message); raised by `set_dmx_channels`, catchable by
  name from `cuemsutils.errors`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any construction of a `DmxUniverse` from a payload containing one malformed DMX
  channel entry fails 100% of the time, rather than "succeeding" with corrupted channel data as it
  does today.
- **SC-002**: The failure identifies the specific universe and channel entry at fault, so a person
  fixing the payload does not need to bisect it by hand to find the bad entry.
- **SC-003**: Zero behavior change for any input that converts cleanly today, including every
  schema-valid `script.xml` document — every existing passing test outside the
  swallow-and-fallback characterization tests continues to pass unmodified.
- **SC-PERF-001**: `set_dmx_channels` completes in **≤ 3 ms** for a realistic DMX universe (≤ 32
  channels — comfortably above typical fixture/channel counts in a show). Measured pre-fix
  baseline (Python 3.11.9, pyenv, this project's pinned test runtime, `hatch run test:python`, 5000
  calls, 8-entry batch): **0.71 ms/call** — already well under budget, so this is a non-regression
  bar, not a new constraint the fix must strain to meet. Separately, for the DMX-spec maximum of
  512 channels in one universe, the pre-fix baseline measures **37.07 ms/call**, dominated by
  today's per-iteration `dmx_channels` reassignment inside the conversion loop (FR-004a's fix
  removes that pattern as a side effect of assigning once after the loop, which is expected to
  improve this case too, though no specific post-fix number is promised without measuring the
  actual implementation — see the Polish-phase verification task). For the 512-channel case, the
  bar is **no regression versus the measured 37.07 ms/call baseline**, not the 3 ms figure, which
  applies to realistic universe sizes only.
- **SC-QUALITY-001**: No new lint/type warnings introduced; the new error type follows the
  existing `cuemsutils.errors` module's conventions exactly (docstring shape, `__all__` entry,
  base-class placement in the `CuemsError` hierarchy).
- **SC-TEST-001**: The characterization tests in `tests/unit/test_dmx_universe_channels.py` that
  pin today's swallow-and-fallback behavior fail against the old code's intended replacement
  *before* this feature's change lands (i.e., are rewritten to assert the new raise-based
  behavior) and pass after; every other test in that file (the valid-input paths) passes
  unmodified both before and after.

## Assumptions

- **Remediation proposal 1 is the chosen shape**, per explicit instruction: raise a named error
  instead of swallowing, mirroring `DmxSceneWriteError`. Proposals 2 (per-entry recovery/skip) and
  3 (log-only) are explicitly out of scope for this feature.
- **This is an application-level (Python) validation tier, not a T1 (XSD) concern** — confirmed by
  investigation, not just the defect record's stated hunch (**FR-XSD-001**). Every schema-valid
  `<DmxUniverse>`/`<dmx_channels>` document, at any occurrence count, decodes into exactly the
  shape `set_dmx_channels` already expects (a list of `{'DmxChannel': {...}}` dicts, or `None` at
  zero occurrences) — the converter derives list-vs-dict purely from the element's declared
  cardinality in the schema (`maxOccurs="512"`), never from how many occurrences are actually
  present, so the very first occurrence of a repeated element is always wrapped in a one-item
  list. No additive `.xsd` change closes a gap here, because there is no gap on the document-decode
  path: the malformed shapes this feature guards against (a dict missing the `'DmxChannel'` key, a
  non-subscriptable entry) can only arise when `DmxUniverse`/`set_dmx_channels` is constructed or
  called directly by application code with a hand-built argument — bypassing XML document decode
  entirely (e.g., programmatic construction, or a JSON-sourced payload via `CuemsScript.from_json`
  that was never validated against the schema in the first place). The fix in FR-001 through
  FR-008 protects exactly that boundary, which is the correct place for it regardless of how a
  caller reaches it.
- **This is a breaking change for any document that currently "loads" with corrupted DMX channel
  data.** Per the defect record's own framing, this could turn a document that loads today (with
  garbage in `dmx_channels`) into one that fails to load at all. This is accepted as the intended,
  correct behavior change (the whole point of proposal 1), not a regression to avoid — a document
  with corrupted lighting data was never safe to run, only silently permitted to.
- **No new document-loading report/repair mechanism (feature 008's `LoadReport`) is reused.**
  `dmx_channels` is show content, not config, and feature 008's repair machinery does not cover
  the show-content path; this feature raises, it does not repair.

## XSD investigation, resolved

Traced the real decode pipeline (`XmlReaderWriter.read_to_objects` →
`Mapper.decode_document`) end to end against the golden test document and two schema-valid
variants (0 and 2 `<DmxChannel>` occurrences), with a spy on `set_dmx_channels`, to answer
whether schema-valid XML alone can reach the malformed shape this defect depends on.

- **1 or more occurrences**: `set_dmx_channels` receives a list of `{'DmxChannel': {...}}`
  dicts — the shape it already converts correctly. `CuemsConverter._decode_content`
  (`src/cuemsutils/xml/converter.py:121-167`) decides list-vs-dict from the schema's declared
  cardinality (`xsd_child.is_single()`), not from how many occurrences are actually present, so
  even a lone occurrence is wrapped in a one-item list — never a bare dict lacking the
  `'DmxChannel'` key.
- **0 occurrences** (`<dmx_channels></dmx_channels>`, valid per `minOccurs="0"`): `channels`
  arrives as `None`, gets wrapped to `[None]`, and the existing `if r is not None` guard skips it
  — `dmx_channels` is left unset entirely. This is a **separate, already-documented** gap
  (`DmxCue.py:343-344`, tracked independently as FR-017) and is explicitly **not** in this
  feature's scope — it is not the KeyError/TypeError swallow this feature fixes, and this feature
  MUST NOT change that behavior (see Edge Cases).

**Conclusion**: valid `script.xml` cannot trigger this defect. The malformed shapes this feature
guards against are reachable only by constructing `DmxUniverse` or calling `set_dmx_channels`
directly with a hand-built argument that never passed through XML schema validation — most
plausibly a JSON-sourced payload via `CuemsScript.from_json` (feature 006), or direct programmatic
misuse. **FR-XSD-001 is therefore resolved as "no XSD change": this feature makes no `.xsd`
edits.**
