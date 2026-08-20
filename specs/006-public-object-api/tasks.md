---
description: "Task list for feature 006 — Public object API: one surface, internal machinery"
---

# Tasks: Public object API — one surface, internal machinery

**Input**: Design documents from `/specs/006-public-object-api/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: REQUIRED by constitution principle II. Every behaviour change carries a
fail-before/pass-after test; the wire byte-equality test is the feature's **gating** test.

**Organization**: grouped by user story so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1…US6, mapping to the user stories in [spec.md](spec.md)

## Path Conventions

Single project: `src/cuemsutils/`, `tests/` at repository root. Non-code artifacts go to
`specs/006-public-object-api/` (feature-specific) or `specs/planning/` (cross-feature), per
`CLAUDE.md`.

## Standing rules that constrain these tasks

1. **No existing golden is ever regenerated to make a test pass.** Exactly two tasks (T065,
   T080) **modify** a recorded golden, and only because it records an enumerated behaviour
   change; each writes its justification to a feature artifact. No other task may modify one.
   *Adding* a golden is different and is allowed: T002 creates `MANIFEST.sha256`, T003b and
   T003c capture goldens for corpus documents that have none, and T040a records the config
   accessor inventory. Every addition updates the manifest in the same commit. The rule is
   about **overwriting evidence**, not about the directory being read-only — stating it as
   "no task may touch `tests/golden/`" made four legitimate tasks look like violations.
2. **Reading never becomes stricter.** T2 runs on `save()`/`validate()` only.
3. **No `.xsd` file is edited in this feature.**
4. **The two `from . import … as _shim` lines at the top of `src/cuemsutils/xml/__init__.py`
   must survive T062.** Removing them resurrects `TypeError: 'module' object is not callable`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: capture the arbiter of every "unchanged" claim before anything moves.

- [X] T001 Record the pre-implementation baseline in `specs/006-public-object-api/baseline.md`: run `PYENV_VERSION=3.11.9 pyenv exec hatch test 2>&1 | tail -3` (expect 1485 passed / 47 skipped / 2 xfailed), `pyenv exec hatch run python specs/006-public-object-api/bench_to_wire.py`, and `ruff check src tests` — capture counts, wall time, the four bench timings and the lint result
- [X] T002 Add a golden-immutability guard: write SHA-256 of every file under `tests/golden/` to `tests/golden/MANIFEST.sha256`, and assert it in a new `tests/contract/test_golden_immutability.py` so an accidental regeneration fails the suite (T065 and T080 update the manifest with recorded justification). **Runs after T003b/T003c**, not in parallel with them — hashing a directory those tasks are still adding files to pins a state that is obsolete by the end of the phase, which is why this is not marked `[P]`
- [X] T003 [P] Add a `script_documents()` accessor to `tests/support/corpus.py` returning only the corpus entries bound to the `script` schema, so every 006 contract test enumerates the same set, and record its count in `specs/006-public-object-api/baseline.md` so SC-001's "100%" is checkable rather than aspirational (CHK024). Take the count **after** T003b/T003c land, so the recorded number is the population every later "100%" claim is measured against
- [X] T003a [P] Add a shared dict-equality predicate to `tests/support/roundtrip.py` implementing contracts §W1a — recursive structure, exact scalar type via `type(a) is type(b)` (not `==`, since `True == 1`), key order against the golden, text compared as `str` codepoints. Every byte-equality test in this feature uses **this one** predicate: T005, T030, T043a (CHK022, CHK023, CHK029)
- [X] T003b [P] Add a corpus document carrying Latin-locale characters — accented vowels, `ç`, `ñ`, an apostrophe — in show name, cue names and `ui_properties` text, with its provenance entry in `tests/data/corpus/PROVENANCE.md` and its schema binding in `tests/support/corpus.py`, then capture its goldens with the **pre-feature** harness (`tests/support/capture_goldens.py`) and add them to T002's manifest. **The corpus contains zero non-ASCII bytes today** (measured 2026-08-18), so no existing test can catch an encoding regression. Goldens for a new document are missing and therefore generated freely — but they must be generated **now**, while the pre-feature reader is still the thing generating them (contracts §W1a/W1b) (FR-036d, SC-019)
- [X] T003c [P] Add a corpus document containing a **fade cue** under `tests/data/corpus/`, with its provenance entry in `tests/data/corpus/PROVENANCE.md` and its schema binding in `tests/support/corpus.py`, and capture its goldens with the pre-feature harness exactly as T003b does. This is the coverage FR-024b requires for the 8 unexercised `FadeCue`/`FadeProfile` rules. **It is added here, in Phase 1, and not in US5 where the rules are relocated** (contracts §W1b): a golden captured after the projection changed is generated by the code it is meant to arbitrate, so the document would enter the corpus already exempt from the byte-identity guarantee every other document carries — and nothing in the suite would say so. The document's *content* does not depend on the feature, so there is no reason to add it late (FR-024b)

**Checkpoint**: baseline recorded, goldens pinned, corpus accessor available, and **both new
corpus documents are in the population before any projection code exists** — so "100% of corpus
script documents" names one set from here on, not a proven set plus two late passengers.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the wire projection and the runtime declaration. Both P1 stories depend on these;
neither is publicly reachable yet. This is plan.md sequencing steps 1 and 3, and step 1 lands
*before* any public surface deliberately — the guarantee is proven against current behaviour
before the surface that depends on it exists.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

### Tests (write first, must FAIL)

- [X] T004 [P] Write the round-trip oracle contract test in `tests/contract/test_wire_oracle.py`: for every corpus script document, `Mapper('script').encode_wire(obj) == schema.to_dict(build_document(obj))` — R1's oracle, the property that makes the fast path safe. Note the signature pinned in data-model.md §6: the **schema is bound at construction**, and `spec` is an optional recursion parameter resolved from the object's class when omitted — so no call site in this feature passes it. Fails: `encode_wire` does not exist
- [X] T005 [P] Write the **gating** byte-identity test in `tests/contract/test_wire_byte_identity.py`: for every corpus script document, `encode_wire` output equals `tests/golden/dict/*.reader.json` with the `{http://www.w3.org/2001/XMLSchema-instance}schemaLocation` key removed from the expectation — comparing structure **and** scalar types (`"True"` is not `true`, `"0"` is not `0`)
- [X] T006 [P] Write scalar-form unit tests in `tests/unit/test_encode_wire_scalars.py` covering data-model.md §6: `BoolType` → `"True"`/`"False"` strings, `PercentType`/`LoopType` → `int`, `UnitFloat` → `float`, `CTimecodeType` → `{"CTimecode": "…"}`, enum → member name, wildcard (`ui_properties`, `xs:anyType`) scalars → strings, unparseable uuid → raw string
- [X] T007 [P] Extend `tests/unit/test_runtime_state.py`: `RUNTIME_FIELDS` accumulates across the MRO like `REQ_ITEMS`; defaults are **factories** so two cues never share a `CTimecode`; `_initialized` is declared as NOT set by the hook; the count of hand-written per-class `_init_runtime` bodies is 0 (SC-014); a runtime attribute added without a declaration fails the suite. **Also assert FR-027d directly**: every runtime attribute named in data-model.md §4 is present on a freshly constructed cue and is writable under its current name — `_player`, `_osc_route`, `_go_thread`, `_start_mtc`, `_end_mtc`, `_armed_list`, `_local`, `_stop_requested`, `_end_reached`, `_target_object`, `_conf`, `_action_target_object`. Converting imperative bodies to data is precisely the change that can rename an attribute silently, and the engine reading these names is in another repository, so this must not ride on the rest of the suite passing

### Implementation

- [X] T008 Implement `Mapper.encode_wire(obj, spec=None) -> dict` in `src/cuemsutils/xml/mapper.py` with the signature pinned in data-model.md §6 — schema bound at construction, `spec` an optional recursion parameter resolved from the object's class through the registry when omitted — mirroring `decode`/`_decode_field` and reusing the **same** `Adapter` instances so encode and decode cannot disagree by construction; walking declared fields only, never `to_dict` (T004, T006 go green)
- [X] T009 Implement the repeated / wrapper / cue-wrapping encode paths in `src/cuemsutils/xml/mapper.py` (`_encode_repeated`, `_encode_wrapper`), reproducing `CMLCuemsConverter`'s current decode shape exactly and preserving key order — W3 is a frontend contract, not an internal convention (T005 goes green). **The `schemaLocation` key is absent from `encode_wire`'s output from the start** — not emitted here and dropped later. T005 compares against the golden *minus* that key, so a projection that emits it is failing its own gate; there is no "drop the key" step anywhere downstream, and T031 is a **guard** against reintroduction rather than a fail-then-pass test (FR-011, FR-031, contracts §W4)
- [X] T010 Add `RUNTIME_FIELDS` MRO accumulation and the one inherited `_init_runtime` implementation driven by it in `src/cuemsutils/helpers.py`, replacing the generic body at `helpers.py:222`; `_initialized` is declared as the named exception and the hook must never touch it (`helpers.py:236-247`)
- [X] T011 [P] Declare `RUNTIME_FIELDS` on `src/cuemsutils/cues/Cue.py` (`_target_object`, `_conf`, `_armed_list`, `_start_mtc`, `_end_mtc`, `_end_reached`, `_go_thread`, `_stop_requested`, `_local`) and delete its `_init_runtime` body at `Cue.py:50`
- [X] T012 [P] Declare `RUNTIME_FIELDS` on `src/cuemsutils/cues/AudioCue.py` (`_player`, `_osc_route`) and delete its `_init_runtime` body at `AudioCue.py:40`
- [X] T013 [P] Declare `RUNTIME_FIELDS` on `src/cuemsutils/cues/VideoCue.py` and delete its `_init_runtime` body at `VideoCue.py:39`
- [X] T014 [P] Declare `RUNTIME_FIELDS` on `src/cuemsutils/cues/DmxCue.py` and delete its `_init_runtime` body at `DmxCue.py:53`
- [X] T015 [P] Declare `RUNTIME_FIELDS` on `src/cuemsutils/cues/ActionCue.py` (`_action_target_object`) and delete its `_init_runtime` body at `ActionCue.py:43`, leaving the `self._initialized = False` / `= True` bracket at `ActionCue.py:30,41` untouched

**Checkpoint**: `encode_wire` matches the goldens and the oracle; runtime state is declared.
Suite still ≥ 1485 passing, and nothing public has changed yet.

---

## Phase 3: User Story 1 - One supported way to move show data in and out (Priority: P1) 🎯 MVP

**Goal**: `CuemsScript` gains `load`/`save`/`validate`/`from_json`/`to_json`/`to_wire`, and
those six become the only supported way script data enters or leaves the library.

**Independent Test**: exercise `load → mutate → validate → save → load` on every corpus script
document, and `from_json → to_json → from_json` on the editor's sample payload, **without
importing anything from `cuemsutils.xml`** and without passing a schema name.

### Tests for User Story 1 (REQUIRED) ⚠️

> Write these FIRST; all must FAIL before implementation.

- [X] T016 [P] [US1] Contract test in `tests/contract/test_public_script_api.py`: the six methods exist on `CuemsScript`, none accepts a `schema_name` argument (SC-004), and each is reachable without importing `cuemsutils.xml`
- [X] T017 [P] [US1] Contract test in `tests/contract/test_coercion_guarantee.py`: recursive class-and-type comparison at every depth between a script built in memory, one from `load()`, and one from `from_json()` — zero differences (FR-001, C1)
- [X] T018 [P] [US1] Contract test in `tests/contract/test_save_atomicity.py`: an invalid script saved over a pre-existing file raises and leaves that file **byte-unchanged**; the target path is not created when it did not exist (FR-003)
- [X] T019 [P] [US1] Contract test in `tests/contract/test_validate_report.py`: a script with ≥3 distinct violations gets all three named by `validate()`, while `save()` on the same script raises **once** and writes nothing (FR-004, FR-004a)
- [X] T020 [P] [US1] Unit test in `tests/unit/test_script_equality.py`: equality compares declared fields only, so `load(save(x)) == load(x)` holds after mutating playback state on one side; copying a cue yields **fresh** runtime state, not shared thread handles, under **both** `copy.copy` and `copy.deepcopy` (CHK008). **Assert hashability explicitly** (FR-028d): a cue survives insertion into a `set` and use as a `dict` key, and two equal cues hash equal. Defining `__eq__` without restating `__hash__` sets it to `None` and makes every cue unhashable — a breakage that is invisible in review, produces no failure in any test that does not itself hash a cue, and surfaces in a consumer repository. Preserving it in the source is not enough; it has to be asserted (FR-028b, FR-028c, FR-028d)
- [X] T021 [P] [US1] Contract test in `tests/contract/test_from_json_ingestion.py`: `from_json` accepts **all three** input forms contracts §C0 enumerates — a JSON string, UTF-8 **bytes**, and a decoded mapping; a payload that is not a script (a JSON array, a scalar, a mapping whose root is unrecognised) fails with `IngestError` and a message naming what was expected, not a structural error from inside the machinery; undeclared keys are dropped **and logged**, one record per key naming class and key. Also assert FR-023a: a payload whose value is rejected by its adapter raises `SchemaError` from `from_json()` — the decode-time structural check is what T1 means on this path, and it is distinct from `IngestError` (FR-002, FR-023a, FR-036c)
- [X] T022 [P] [US1] Extend `tests/integration/test_d14_chain.py` with a public-API-only variant of the chain `xml → object → json → object → xml`, asserting byte-identical XML for every corpus script document and asserting the test module imports nothing from `cuemsutils.xml` (FR-008, SC-002)
- [X] T022a [P] [US1] Contract test in `tests/contract/test_error_types.py`: each failure path raises its declared type from `cuemsutils.errors` and none raises a bare `ValueError`/`RuntimeError`; a validation failure is catchable as `ValidationError` and a structural one as `SchemaError` without catching the other; `IngestError` is distinct from both; an unreadable file raises `OSError` **unwrapped**; and every public method's docstring has a `Raises:` entry. **Assert FR-034b's carried violation**: the `ValidationError` raised by `save()` carries a `Violation` whose `tier`, `rule`, `location` and `message` match what `validate()` reports for the same document — implementing it is not enough, because the failure mode is a consumer catching the exception and finding nothing on it to show a user (FR-034, FR-034a, FR-034b, FR-035, FR-035a, SC-018)
- [X] T022c [P] [US1] Contract test in `tests/contract/test_utf8_roundtrip.py`: the T003b fixture survives `load → to_wire → to_json → from_json → save → load` with **zero** character differences; the written XML is byte-identical to its golden; the document carries `<?xml version="1.0" encoding="utf-8"?>`; `to_json()` output contains the literal characters and **no** `\uXXXX` escapes; `from_json()` accepts the UTF-8 bytes of that string and rejects invalid UTF-8 rather than guessing a codec (FR-036, FR-036b, FR-036c, SC-019)
- [X] T022d [P] [US1] Run the T022c assertions again under a **hostile locale** — `LC_ALL=C`/`LANG=C`, via `monkeypatch.setenv` plus a subprocess so the interpreter actually starts under it. This is the environment where a missing `encoding=` stops being invisible and starts raising `UnicodeEncodeError`; a test that only passes under a UTF-8 locale does not test this requirement (FR-036e)
- [X] T022b [P] [US1] Contract test in `tests/contract/test_projection_does_not_validate.py`: `to_wire()` and `to_json()` on a semantically invalid **and** on a structurally invalid object both return a payload rather than raising, while `save()` on the same object raises — the projection/gate separation, asserted rather than assumed (FR-005a, FR-006)

### Implementation for User Story 1

- [X] T023 [US1] Add the `ValidationReport` and `Violation` types to `src/cuemsutils/xml/validators.py`, beside the `run_rules` that produces them (T072): a violation names its tier (T1/T2), its rule name and its location; a report collects them, is falsy when empty and iterates its violations. **Both stay internal** — they are what `validate()` returns, not something a consumer imports or constructs, so they add no name to the public surface and no entry to the API golden (FR-019, FR-022). `validate()`'s docstring (T086) states the report's shape, which is the only thing a caller needs
- [X] T023b [US1] Build the `run_rules(obj) -> list[Violation]` **seam** in `src/cuemsutils/xml/validators.py`, wrapping the semantic checks that module already holds (`check_canvas_region_containment`, `check_one_custom_template_per_node`, and `Media.set_duration`'s duration rule) and returning them as `Violation`s. **This task exists because T027/T028 call `run_rules` two phases before T072 builds the registry** — without it, US1's implementation references a function no task has created, and the cross-story note's "until US5 lands, `save()`/`validate()` run T1 plus the three semantic rules `validators.py` already holds" describes behaviour nothing produces. T072 then **fills** this seam with the registry rather than introducing it, so the signature `save()`/`validate()` bind to never changes (FR-004, FR-024)
- [X] T023a [US1] Create `src/cuemsutils/errors.py` with the public exception hierarchy — `CuemsError(Exception)`, `ValidationError(CuemsError)` carrying the first `Violation`, `SchemaError(ValidationError)`, `IngestError(CuemsError)` (Contracts §C5, FR-034, FR-034a, FR-034b). **The one new public module this feature adds**: a returned type can stay internal because the caller only inspects it, but an exception the caller cannot name is one it cannot catch. I/O failures are **not** wrapped — `OSError`/`FileNotFoundError` propagate unchanged (FR-035)
- [X] T024 [US1] Implement `CuemsScript.load(path)` as a classmethod in `src/cuemsutils/cues/CuemsScript.py`, delegating to `Mapper('script').decode_document`; runs T1 and raises `SchemaError` on a structurally invalid document, lets `OSError`/`FileNotFoundError` propagate unwrapped, runs **no** T2, and returns an object whose runtime state is already initialized with no promotion step. Docstring carries a `Raises:` entry naming both paths (FR-001, FR-028, FR-035, FR-035a)
- [X] T025 [US1] Implement `CuemsScript.from_json(payload)` in `src/cuemsutils/cues/CuemsScript.py`, accepting **`str | bytes | Mapping`** — the three forms contracts §C0 enumerates. `bytes` is **decoded as UTF-8 only**, raising rather than guessing another codec (FR-036c); `str` is `json.loads`-ed; all three then delegate to the same decode path as `load()`, for the same coercion guarantee and validation posture. Structural validation here is the **decode-time** check (FR-023a) — not a second pass that builds a document, which would pay the projection cost FR-005a exists to avoid on the editor's hottest ingestion path. Raises `IngestError` when the payload is not a script at all, `SchemaError` when it is a script that fails the structural check; the `Raises:` docstring entry names both and states the FR-023a asymmetry (a payload accepted here can still fail `save()`'s document-level check). **`bytes` is not optional** — T021 and T022c both exercise it (FR-002, FR-023a, FR-034, FR-035a, FR-036c)
- [X] T026 [US1] Implement `to_wire()` and `to_json()` **on the shared `CuemsDict` base in `src/cuemsutils/helpers.py`**, not on `CuemsScript` — one body from the start, so T056a *binds* the config models to it rather than relocating or duplicating a method (contracts §C2, data-model.md §6, FR-014a). `CuemsScript` gets them by inheritance and needs no override. Note the counted consequence: every `CuemsDict` subclass — every cue class, not only `CuemsScript` — now exposes `to_wire()`/`to_json()` publicly. That is intended and free, but it is an addition to the recorded API surface and **must appear in T057a's enumerated diff** or T065's "exactly the enumerated set" fails on names nobody listed. `to_wire()` calls `Mapper.encode_wire`; `to_json()` is `json.dumps(self.to_wire())` with the form **pinned explicitly** — `separators=(", ", ": ")`, **`ensure_ascii=False`**, `sort_keys=False` — rather than relying on defaults that a future stdlib change could move (FR-005, FR-005b, FR-014a, FR-036c). `ensure_ascii=False` emits real UTF-8 rather than `\uXXXX` escapes; both forms round-trip losslessly, so this is a readability and payload-size choice, not a correctness one. **Neither validates**, and both docstrings say so, naming the consequence: a partial object yields a partial payload, and a caller wanting a guarantee calls `validate()` first (FR-005a)
- [X] T027 [US1] Implement `CuemsScript.validate() -> ValidationReport` in `src/cuemsutils/cues/CuemsScript.py`: no file involved, runs T1 then T2 through the `run_rules` seam **built by T023b** and filled by US5's registry (T072), **collects** every violation (FR-004). Its docstring **documents the returned report in full** — falsy when empty, iterates its violations, each naming tier (T1/T2), rule name and location — because `ValidationReport` is internal (T023) and so gets no documentation page of its own: this docstring is the only place the shape is published (contracts/public-api.md C1)
- [X] T028 [US1] Implement `CuemsScript.save(path)` in `src/cuemsutils/cues/CuemsScript.py`: validate T1 **and** T2 raising `ValidationError` (or `SchemaError` for a structural failure) at the first violation and carrying that violation on the exception, then write via a temporary file and atomic rename so no file is created, truncated or partially written on failure; persists declared fields only and does **not** refuse mid-show. `Raises:` entry names the validation types and notes that filesystem errors propagate unwrapped. **The temporary-file write MUST pass `encoding="utf-8"` and `xml_declaration=True`** — the existing writer does (`xml_reader_writer.py:71-75`) and this is the one place an atomic rewrite could silently introduce the package's first locale-dependent path (FR-003, FR-004a, FR-028a, FR-034b, FR-035a, FR-036a, FR-036b)
- [X] T029 [US1] Implement `__eq__` over declared fields and `__copy__`/`__deepcopy__` producing fresh runtime state on the shared base in `src/cuemsutils/helpers.py`, so the rule holds for every cue class rather than only `CuemsScript`. This **widens** `Cue.__eq__` from id-only (`src/cuemsutils/cues/Cue.py:301`) — enumerated as behaviour change 5. **Preserve `Cue.__hash__` (`Cue.py:314`) rather than deleting it**: `hash(self.id)` stays consistent with the wider equality because `id` is a declared field, and dropping it would set `__hash__ = None` and make every cue unhashable (FR-028b, FR-028c, FR-028d)

**Checkpoint**: US1 fully functional. A consumer can move script data in and out with six
methods, no schema name and no `xml` import — while the old entry points still work.

---

## Phase 4: User Story 2 - The UI payload does not move under the editor's feet (Priority: P1)

**Goal**: `project_load` is byte-identical minus one stray XML artifact, and
`initial_template` stops disagreeing with it.

**Independent Test**: for every corpus script document, `CuemsScript.load(p).to_wire()` equals
the pre-feature `read()` golden minus `schemaLocation` — zero differences. Separately, render
one script through both payload paths and diff field by field.

**Note on FR-031**: the two wire-format changes are **not symmetrical**, and treating them as
one commit was an error this task list carried until 2026-08-18. The key's absence from the
wire dict is a property of `encode_wire` from T009 — T005 asserts against the golden *minus*
that key, so there is never a moment when the projection correctly emits it. Only the written
attribute (T037) is an edit to existing output. FR-031's unit is therefore the **release**: no
version exists in which one has moved and the other has not. US6 verifies the write-side half;
it does not make it. T031 is a **guard against reintroduction**, not a fail-then-pass test.

### Tests for User Story 2 (REQUIRED) ⚠️

- [X] T030 [P] [US2] Fail-then-pass parity test in `tests/contract/test_payload_parity.py`: render one script through the template path and the project-load path and diff field by field — **zero** differences. Must fail before T035/T036 (today it differs on every boolean and on `ui_properties` integers) and pass after. This is behaviour change 1's evidence (SC-003)
- [X] T031 [P] [US2] Contract test in `tests/contract/test_wire_no_schemalocation.py`: enumerate the wire dict's keys at every depth and assert no `schemaLocation` key is present (FR-011)
- [X] T032 [P] [US2] Contract test in `tests/contract/test_wire_booleans.py`: for every boolean-typed field in every corpus script document, assert the value **is** `"True"`/`"False"` and **is not** `True`/`False` — converting to JSON booleans is forbidden here (FR-010)
- [X] T033 [P] [US2] Contract test in `tests/contract/test_wire_no_runtime_state.py`: no name from any class's `RUNTIME_FIELDS` appears at any depth of `to_wire()`, `to_json()` or a written document, and the test fails if a new runtime attribute escapes the enforcement (FR-027, SC-012)
- [X] T034 [P] [US2] Extend `tests/contract/test_ui_payload_contract.py` with one explicit test naming the repeated-element shape, so a future change to `CMLCuemsConverter`'s decode shape fails loudly rather than silently (W3, F22)

### Implementation for User Story 2

- [X] T035 [US2] **Delete seven** of the eight hand-written `__json__` bodies: `src/cuemsutils/cues/Cue.py:322`, `MediaCue.py:169`, `DmxCue.py:484`, `FadeCue.py:21`, `FadeProfile.py:63`, `FadeProfile.py:157`, `CueOutput.py:105`. The eighth — `CuemsScript.py:292` — is **replaced rather than deleted**, by T036; do not remove it here. `Uuid.__json__` and `CTimecode.__json__` are scalar adapters and stay. SC-006's "0 hand-written JSON projection methods" is satisfied by all eight bodies being gone: seven removed, one reduced to a delegation that projects nothing itself (FR-013, SC-006)
- [X] T036 [US2] Replace the body of `CuemsScript.__json__` in `src/cuemsutils/cues/CuemsScript.py:292` with a one-line delegation to `to_wire()`, so the editor's existing `initial_template` call site receives the aligned payload before feature 008 migrates it — this is what closes F21 without editing a consumer repository. Pairs with T035, which leaves this one method for it (FR-012)
- [X] T037 [US2] Change `build_document` in `src/cuemsutils/xml/mapper.py` to write the bare schema filename (`script.xsd`) instead of the installed package's absolute path (FR-029, behaviour change 4). **This is the whole of the wire-format edit** — the read-side half is not a step. The `schemaLocation` key is absent from `encode_wire`'s output from T009 onward, because T005 compares against the golden *minus* that key and a projection emitting it fails its own gate. FR-031 requires the two to ship in one **release**, not one commit: making the key's absence a later "drop" step would mean writing the projection wrong on purpose so something remained to change, and neither half is reachable by a consumer until the public surface ships (FR-011, FR-029, FR-031, contracts §W4)
- [X] T038 [US2] Record the evidence that no consumer reads the schema-location key in `specs/006-public-object-api/schemalocation-evidence.md`, to a **stated standard** (CHK027): the repositories searched (`cuems-engine`, `cuems-editor`, `cuems-nodeconf`, the Angular frontend), the branch and commit of each, the patterns searched (`schemaLocation`, `schema_location`, `xsi:`), and the date. A negative result is only evidence if what was searched is recorded. **If the result is positive** (CHK042), FR-011 and D2a are what get revisited — the wire change is blocked, not the assumption quietly amended (FR-011)

**Checkpoint**: both P1 stories complete. The UI payload is proven unmoved and the two
payloads are one projection. **This is the MVP.**

---

## Phase 5: User Story 3 - Configuration answers with objects, not nested dictionaries (Priority: P2)

**Goal**: config accessors return typed objects; the three shape compensations and the two
fossilised `check_mappings` bodies are deleted rather than relocated.

**Independent Test**: call every `ConfigManager`/`ConfigBase` accessor against the corpus
config files and assert each returns a typed object or a scalar, never a raw nested dict; then
delete the three compensations and show the accessors still return the same values.

**006/007 boundary** (data-model.md §2): 006 defines `node`/`node_list` as `CuemsDict`
containers with derived fields and binds them so `network_map` returns objects. 006 must
**not** implement node behaviour — the Avahi helpers, the identity fields and the 106-case
coercion regression test are feature 007's, and its evidence lives in the other repository.

### Tests for User Story 3 (REQUIRED) ⚠️

- [X] T040a **[US3, FIRST — not [P]]** Record the **pre-feature accessor inventory** — every public name on `ConfigBase` and `ConfigManager` with its current return type — to `tests/golden/api/config_accessors.json`, generated by introspection before any US3 change lands. Without a recorded "before", FR-018's "every name that exists today" is assertable but not verifiable (CHK035). Add it to `tests/golden/MANIFEST.sha256` (CHK038: an accessor passes when `type(value) is not dict` — legitimately dict-shaped wildcard content is a declared-field object, not a raw dict). **This runs before every other US3 task, including the other tests**, which is why it is not marked `[P]`: once T048/T055 land there is no "before" left to record. It is also the authoritative answer to CHK036 — the per-accessor object/scalar split lives here, not in prose, because the prose has already drifted (contracts §C2 groups accessors; T055 says "~15 scalar" where data-model.md says "~18")
- [X] T039 [P] [US3] Contract test in `tests/contract/test_config_object_surface.py`: every `ConfigManager`/`ConfigBase` accessor returns a declared-field object or a scalar — never a raw nested dict — including `network_map` (FR-014, SC-007)
- [X] T039a [P] [US3] Contract test in `tests/contract/test_config_errors.py`: a missing or unreadable config file raises `OSError`/`FileNotFoundError` **unwrapped** from the accessor, and a file that fails schema validation raises `SchemaError` naming the offending element — never the same exception type for both. Include the measured **X13** case (`gradient_osc_port` added to `settings.xsd` as required, invalidating settings files written before it) as the schema-failure fixture: it is *reported* here and *fixed* under the schema evolution convention, not in this feature. A node with no config and a node with a corrupt one are different operational problems (FR-014b, SC-020, CHK037)
- [X] T040 [P] [US3] Contract test in `tests/contract/test_config_accessor_names.py`: every accessor name present on `ConfigBase`/`ConfigManager` before this feature is present after and means the same thing, asserted against the T040a inventory rather than against a list retyped into the test (FR-018, C2)
- [X] T041 [P] [US3] Extend `tests/unit/test_coherence.py` to the config model classes: set equality between MRO-accumulated declared fields and the XSD type's elements, for all 22 complex types across the four config schemas
- [X] T042 [P] [US3] Extend `tests/contract/test_config_parity.py`: every accessor returns the **same values** after the compensations are deleted, asserted against `tests/golden/dict/*.config.json`
- [X] T043 [P] [US3] Unit test in `tests/unit/test_mappings_shape.py`: the mappings data has exactly **one** declared shape, identical at every call site, and no unreachable alternative survives (FR-017, SC-007)
- [X] T043a [P] [US3] Contract test in `tests/contract/test_config_wire.py`: for every corpus **config** document, the config object's `to_wire()` equals the recorded `tests/golden/dict/*.config.json` golden — structure and scalar types, the same predicate the show projection uses. Goldens already exist and are **not** regenerated (FR-014a, SC-017, Contracts §W8)
- [X] T043b [P] [US3] Contract test in `tests/contract/test_one_projection.py`: the config path and the show path reach the **same** `encode_wire`, and no second projection function exists anywhere in the package — the assertion that keeps FR-014a from decaying into the parallel definition it exists to prevent (SC-017)

### Implementation for User Story 3

- [X] T044 [US3] Create `src/cuemsutils/config/__init__.py` — the config domain module named by target design §10 and designated by D11 as the node model's landing site
- [X] T045 [P] [US3] Create `src/cuemsutils/config/settings.py` with `CuemsDict` models for `settings.xsd`'s 7 types (`NodeConfType`, `PlayerType`, `VideoPlayerType`, `AudioPlayerType`, `AudioMixerType`, `DmxPlayerType`, `CTimecodeType`) and `project_settings.xsd`'s `SettingType`, declared fields derived from the XSD
- [X] T046 [P] [US3] Create `src/cuemsutils/config/mappings.py` with `CuemsDict` models for `project_mappings.xsd`'s 11 types (`NewNodesType`, `NodesType`, `NodeType`, `DeviceType`, `PutGroupType`, `PutType`, `VideoDeviceType`, `VideoPutGroupType`, `VideoPutType`, `CanvasRegionType`, `MappedToType`) — naming each level of the nesting T051 stops rediscovering
- [X] T047 [P] [US3] Create `src/cuemsutils/config/network_map.py` with `node` / `node_list` as `CuemsDict` containers over `network_map.xsd`'s 3 types (`NodeDictType`, `NodeType`, `PutType`). Containers only — feature 007 fills in behaviour. The `"NodeType.<name>"` wire format is a cross-repo contract with `cuems-engine` and does **not** change
- [X] T048 [US3] Replace the `GENERIC` bindings for the four config schemas in `src/cuemsutils/xml/registry.py` (`registry.bind(type_name, GENERIC)` at the config-schema registration, ~line 250-267) with bindings to the T045–T047 model classes
- [X] T049 [US3] Bind the readers in `src/cuemsutils/xml/settings.py` (`Settings`, `NetworkMap`, `ProjectMappings`, `ProjectSettings`) to the config models instead of handing back raw dicts, closing the gap that module's own docstring names
- [X] T050 [US3] Delete **compensation #1** — the hand flattening of a list of single-key dicts into one dict in `ConfigManager.load_project_settings` (`src/cuemsutils/tools/ConfigManager.py:187`); the derived `SettingType` states the shape (FR-016)
- [X] T051 [US3] Delete **compensation #2** — the five-level nested walk in `ConfigManager.load_net_and_node_mappings` (`src/cuemsutils/tools/ConfigManager.py:155-164`); the nesting stays in the document, what goes is rediscovering it by iteration at every level (FR-016)
- [X] T052 [US3] Delete **compensation #3** — the generic structural walk in `ConfigManager.check_project_mappings` (`src/cuemsutils/tools/ConfigManager.py:270-288`), addressing named fields now that the shape is stated (FR-016)
- [X] T053 [P] [US3] Delete the unreachable `check_mappings` body in `src/cuemsutils/cues/VideoCue.py:91-110` (dead behind `return super().check_mappings()` at line 100) — removed, not corrected: a shape assumption no test can reach is not a contract (FR-017)
- [X] T054 [P] [US3] Delete the unreachable `check_mappings` body in `src/cuemsutils/cues/AudioCue.py:139-156` (dead behind `return super().check_mappings()` at line 148) (FR-017)
- [X] T055 [US3] Update the accessors in `src/cuemsutils/tools/ConfigBase.py` so `node_conf` and the player sections return objects; the ~15 scalar accessors (`library_path`, `tmp_path`, `database_name`, `editor_url`, `templates_path`, …) keep returning scalars and keep their names (FR-018)
- [X] T056 [US3] Delete the dead `data2xml` / `buildxml` / `process_network_mappings` from `src/cuemsutils/xml/settings.py` (D3)
- [X] T056a [US3] Bind the config models to the projection T026 already put on the shared `CuemsDict` base in `src/cuemsutils/helpers.py` — each config model resolves its `Mapper` from its own schema, and inherits `to_wire()`/`to_json()` unchanged. **No method is written here and none is moved**: T026 placed the single body on the base precisely so this task is a binding, not a second definition or a relocation. `CuemsScript.to_wire()` and a config object's `to_wire()` differ only in which `Mapper` they hold, which is what makes SC-017's "1 implementation" true of the code rather than of the intent (FR-014a, data-model.md §6)
- [X] T056b [US3] Expose the projection on the config facade in `src/cuemsutils/tools/ConfigManager.py` — the accessors that return objects gain nothing new, but a caller holding one can project it. Configuration is **not** transmitted to the UI in this feature; this is the seam the planned follow-on work uses, and building it here is what stops a second projection being written then (Contracts §W8)

**Checkpoint**: config answers with objects; three compensations and two fossils are gone.

---

## Phase 6: User Story 4 - The machinery is machinery (Priority: P2)

**Goal**: `cuemsutils.xml` exports nothing; the former entry points work for one release and
say what to move to; the frozen legacy tree is deleted.

**Independent Test**: assert the `xml` package exports nothing; assert the public API golden
contains no `xml` symbol; assert every removed entry point still resolves, still works and
warns with its replacement and removal release.

### Tests for User Story 4 (REQUIRED) ⚠️

- [X] T057 [P] [US4] Extend `tests/contract/test_public_api_surface.py`: `cuemsutils.xml.__all__ == []`, `from cuemsutils.xml import *` binds nothing, and no public signature anywhere accepts a `schema_name` argument (FR-019, FR-021, SC-004, SC-005). Assert `__all__ == []` **only** — dotted access stays functional this release and must NOT be asserted against, because the shims resolve through those same paths (FR-019a; lockdown is feature 008's)
- [X] T057a [P] [US4] Define "public name" for the golden's purposes in `specs/006-public-object-api/api-surface-diff.md` — module-level names not underscore-prefixed, plus public methods on exported classes, excluding dunders and inherited stdlib members — and write the **enumerated expected diff as one explicit list** rather than leaving it distributed across the spec, so T065's "exactly the enumerated set" has something to compare against (CHK032, CHK036, FR-022). The list MUST include the **inherited** additions, not only the headline ones: T026 puts `to_wire`/`to_json` on the shared `CuemsDict` base, so **every** `CuemsDict` subclass gains them — every cue class, not just `CuemsScript` and the config models. Intended and free, but unlisted names are exactly what makes T065 fail on a diff nobody expected. Also record here how FR-007 is met this release: "the six are the only supported way" is satisfied by FR-019 (`__all__ == []`) plus FR-022 (the recorded surface names the six and nothing else), **not** by unreachability — FR-019a keeps dotted access working because the shims resolve through it, and genuine lockdown is feature 008's
- [X] T058 [P] [US4] Contract test in `tests/contract/test_shim_import_order.py`: `from cuemsutils.xml import Settings` yields a **class**, not a module, and is callable — the guard for the `TypeError: 'module' object is not callable` hazard that has been diagnosed and fixed once already (D1)
- [X] T059 [P] [US4] Extend `tests/contract/test_deprecation_shims.py`: each of the six removed entry points resolves, works, produces a result equal to the new API's, warns **once per call** (call twice → two warnings) and names both the replacement and `v0.1.1` in the one existing message format (FR-020, SC-010)
- [X] T060 [P] [US4] Prove the legacy tree unreachable before deleting it: run the suite under coverage restricted to `src/cuemsutils/xml/Parsers.py` and record zero hits below `CuemsParser.parse()` in `specs/006-public-object-api/legacy-coverage.md` (D4)

### Implementation for User Story 4

- [X] T061 [US4] Add deprecation shims for `XmlReaderWriter`, `CuemsParser`, `Settings`, `NetworkMap`, `ProjectMappings`, `ProjectSettings`, each naming its replacement from the D2 migration map and `REMOVAL_RELEASE = "v0.1.1"`. Add an optional `note` parameter to `deprecation_reason()` in `src/cuemsutils/xml/_deprecation.py` — still **one** function producing every message, so the standing "no second warning system" rule holds — and use it on the `read()` shim alone to append `note: the returned dict no longer contains the schemaLocation key` (D2a). Every other message renders byte-identically to today
- [X] T061a [US4] **Before T061 attaches the `CuemsParser` shim**, move the two internal callers off it — `src/cuemsutils/xml/xml_reader_writer.py:78` and `:119` — to `Mapper.decode_document`. Contract C8 (`tests/contract/test_no_internal_deprecation.py`) asserts no internal caller invokes a deprecated symbol and exercises `CuemsParser` **expecting silence**; deprecating it while the library still calls it fails that test. C8 is satisfied, not amended (Contracts §C3)
- [X] T062 [US4] Set `__all__ = []` in `src/cuemsutils/xml/__init__.py` while **keeping** the two `from . import … as _shim` lines and their comment block intact (FR-019, standing rule 4 above). **Update the module docstring in the same edit**: it currently opens *"The public surface is the five names in `__all__`"* (`xml/__init__.py:3-4`), which this task makes false. Replace it with the FR-019a position — the package exports nothing; dotted access remains functional but **unsupported** for one release because the deprecation shims resolve through it; genuine lockdown is feature 008's. A module whose docstring contradicts its own `__all__` is the first thing a maintainer reads (FR-019, FR-019a)
- [X] T063 [US4] Delete the frozen legacy tree — the ~430 unreachable lines below `CuemsParser.parse()` in `src/cuemsutils/xml/Parsers.py`, keeping `parse()`'s delegation to `Mapper.decode_document` and the module's deprecation facade (D3)
- [X] T064 [US4] Migrate `validate_template` in `src/cuemsutils/create_script.py:209` from `XmlReaderWriter(schema_name="script", xmlfile=None).validate_object(...)` to `script.validate()`, and drop the now-unused `from .xml import XmlReaderWriter` at line 12 — the one first-party consumer that migrates *in* this feature
- [X] T065 [US4] Update `tests/golden/api/public_api.json` **deliberately**, and record the diff in `specs/006-public-object-api/api-surface-diff.md` showing it is exactly the set T057a enumerates — six entry points removed (5 from `__all__` plus `CuemsParser`, see C3's two counts), six methods added on `CuemsScript`, `to_wire`/`to_json` added on the shared `CuemsDict` base and therefore on **every** subclass (T026), the `cuemsutils.errors` module and its four types added (T023a), `schema_name` gone. Update `tests/golden/MANIFEST.sha256` (T002) in the same commit. This and T080 are the only two tasks that **modify** a recorded golden (standing rule 1) (FR-022)

**Checkpoint**: two public entry points, one deprecated surface, no legacy tree.

---

## Phase 7: User Story 5 - Semantic rules are a named tier, not a side effect of assignment (Priority: P3)

**Goal**: one definition per rule, registered by name and bound to the (type, field) pairs it
applies to, invoked from both the setter and the write/validate tier.

**Independent Test**: enumerate the registered rules; run each against a document that
violates it and one that satisfies it; confirm the structural tier ran first and that the two
tiers report distinguishably.

**Two constraints from measurement, both non-negotiable** (research.md R5, data-model.md §5):

1. `_initialized` must keep gating the setter path in `ActionCue`, `FadeCue` and
   `VideoCueOutput`. Delegation moves the rule **body**, never the gate.
2. `VideoCueOutput.__init__` calls `_classify_output_name` **before** `super().__init__`, and
   that constructor call — not the setter — is what pins two legacy corpus documents as
   `to_objects: error`. Feature 005 had to correct this same misreading in flight.

### Tests for User Story 5 (REQUIRED) ⚠️

- [X] T066 [P] [US5] Unit test in `tests/unit/test_t2_registry.py`: enumerate the registry and assert it contains `canvas_region_containment`, `one_custom_template_per_node` and `media_duration` plus the relocated setter rules; assert each rule has exactly **one** definition reachable from both call sites (FR-024, FR-024c, SC-015); and run each rule against one violating and one satisfying input
- [X] T067 [P] [US5] Contract test in `tests/contract/test_tier_separation.py`: a structurally valid but semantically wrong document (a canvas region extending past its canvas) reports a **named semantic rule**, distinguishable from a schema failure; a structurally invalid document reports the structural failure without the semantic tier masking or absorbing it (FR-024)
- [X] T068 [P] [US5] Contract test in `tests/contract/test_semantic_not_on_read.py`: `load()` and `from_json()` run **zero** semantic rules — a semantically invalid document loads successfully and fails only on `save()` (FR-026, SC-016)
- [X] T069 [P] [US5] Extend `tests/contract/test_accept_reject_parity.py`: every document accepted today is still accepted, and the two documents pinned as `read: ok` / `to_objects: error` in `tests/golden/outcomes.json` keep exactly those outcomes after delegation (FR-024d, FR-025, SC-008)
- [X] T070 [P] [US5] Extend `tests/unit/test_id_clearing.py`: the uuid4 shape check is **not** in the registry and stays a coercion concern — an unparseable identifier, including the nil UUID the editor sends in ordinary traffic, is preserved as its raw string on the read path (FR-024a)
- [X] T071 [P] [US5] Extend `tests/unit/test_setter_error_propagation.py`: after delegation, programmatic assignment still fails immediately and with the current message, and `_initialized` still holds the rules off during population in all three gating classes

### Implementation for User Story 5

- [X] T072 [US5] Build the named-rule registry in `src/cuemsutils/xml/validators.py`: a `register(name, applies_to=[(type, field), …])` decorator and a `RULES` lookup, then **fill T023b's existing `run_rules(obj) -> list[Violation]` seam** with it — the signature `save()`/`validate()` already bind to does not change. Extends the module 004 established as the tier's home rather than creating a `validation/` package
- [X] T072a [US5] **Derive or retire `SEMANTIC_RULES`** (`src/cuemsutils/xml/validators.py:115-120`). It is a hand-written closed tuple of three prose names — `"canvas_region containment"`, `"at most one custom template per node"`, `"media duration"` — that `test_config_parity` and the coherence test read to assert the tier has not grown silently. Once `RULES` exists, keeping both is **two inventories of one thing**, which is FR-024c's prohibition one level up and precisely the mechanism behind F15's three incompatible shapes. Either generate it from `RULES` or delete it and point its two readers at the registry. Note the name *form* changes with it — prose with spaces becomes identifiers (`canvas_region_containment`) — so both readers must be updated; **rule messages, which are what users see, are preserved unchanged** (FR-024c, SC-015)
- [X] T073 [US5] Move the 14 value-rejecting setter rule bodies into registry entries and make each setter call its named rule — `src/cuemsutils/cues/ActionCue.py` (`action_target_required`), `FadeCue.py` (4 `fade_*` rules), `FadeProfile.py` (4 `fade_profile_*` rules), `CueOutput.py` (`output_name_shape`, `canvas_region_containment`), `MediaCue.py` (`media_duration`, `fade_profile_caps`), `CuemsScript.py` (`cuelist_shape`). One definition, two call sites (FR-024c)
- [X] T074 [US5] Preserve the pre-`super().__init__` `_classify_output_name` call in `VideoCueOutput.__init__` (`src/cuemsutils/cues/CueOutput.py:174-199`) when it starts delegating — the constructor call, not the setter, is what pins the golden outcomes (FR-024d)
- [X] T075 [US5] Wire the two call sites in `src/cuemsutils/cues/CuemsScript.py`: `save()` calls `run_rules` and raises at the **first** violation writing nothing; `validate()` calls it and **collects** every violation into the internal `ValidationReport` from T023 (FR-004, FR-004a)
- [X] T076 [US5] Exercise the 8 `FadeCue`/`FadeProfile` rules against the fade-cue corpus document **T003c already added in Phase 1**: assert each rule fires on a violating variant of it and passes on the document itself. The document is not added here — moving it to Phase 1 is deliberate (contracts §W1b): goldens captured after the projection changed are generated by the code they are meant to arbitrate, which would have made this document exempt from the byte-identity guarantee every other corpus document carries, invisibly (FR-024b)
- [X] T077 [US5] Update `specs/006-public-object-api/corpus-sweep.md` with a post-implementation section recording which of the 15 rules now have corpus coverage and which remain unproven — the gap is recorded, never read as a clean result (FR-024b)

**Checkpoint**: the tier is a registry, not an archaeology exercise; reading is no stricter.

---

## Phase 8: User Story 6 - Documents are portable, and the next schema change does not strand them (Priority: P3)

**Goal**: a written document carries no machine-local path, and there is a written rule that
stops the next schema change invalidating every file on disk.

**Independent Test**: write the same object under two installation layouts and compare the
bytes; then check the convention document exists and states all four rules with its measured
precedent.

**Note**: the write-side change itself is T037 (US2), because FR-031 requires both wire-format
changes to ship in one commit. This phase verifies it and adopts the convention.

### Tests for User Story 6 (REQUIRED) ⚠️

- [ ] T078 [P] [US6] Contract test in `tests/contract/test_schema_location_portability.py`: write the same object with the package's schemas directory monkeypatched to two different installation layouts and assert byte-identical output, and assert the written document contains no absolute filesystem path (FR-029, SC-009)
- [ ] T079 [P] [US6] Extend `tests/contract/test_legacy_compatibility.py`: documents already on disk with an absolute, a relative, or an absent schema location all still load and validate to **equal** results, and one whose attribute points at a path that does not exist still loads (FR-030, SC-009)

### Implementation for User Story 6

- [X] T080 [US6] Update `tests/golden/xml/*.xml` **deliberately**: `schemaLocation="https://stagelab.coop/cuems/ @@SCHEMAS_DIR@@/script.xsd"` becomes `"https://stagelab.coop/cuems/ script.xsd"` across **every file in that directory** — three today, more once T003b/T003c's documents land, which is why this is stated as a glob and never as a count (contracts §W6). `SCHEMA_PATH_PLACEHOLDER` in `tests/support/capture_goldens.py:52` becomes a no-op the harness no longer needs. Record the justification in `specs/006-public-object-api/golden-changes.md` as enumerated behaviour change 4, and update `tests/golden/MANIFEST.sha256` in the same commit. **This and T065 are the only tasks that modify a recorded golden** (standing rule 1)
- [ ] T081 [US6] Write `specs/planning/schema-evolution-convention.md` stating all four rules — an element added to an existing complex type is optional; it carries a model-layer default so a document omitting it loads to the same object; required elements appear only in new types; anything else is a versioned file-format migration with a conversion path — together with the X13 measured precedent that motivated them (FR-032, SC-013)
- [ ] T082 [US6] Record the existing violation as scheduled work in `specs/planning/schema-evolution-convention.md`: `gradient_osc_port` was added to `settings.xsd` as required and invalidated every settings file written before it, including two this project shipped. **No `.xsd` file is edited in this feature** (FR-033)

**Checkpoint**: all six stories independently functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T083 Validate the performance budgets and record before/after in `specs/006-public-object-api/baseline.md`, **with the measurement context stated** so the numbers are reproducible by someone other than their author (CHK041): machine and CPU, Python 3.11.9 under pyenv, warm process, median of 30 samples, the 24 KB `complex_test/script.xml` — the method `bench_to_wire.py` already uses. Budgets: `load()` + `to_wire()` ≤ **25 ms** (baseline `read()` = 16.95 ms), `to_wire()` alone ≤ **5 ms** (tree build = 1.09 ms), suite ≤ 10% over 44.57 s, write path ≤ 10% regression. If `to_wire()` lands near 16 ms the direct projection has silently become the round trip — check `encode_wire` is not calling `to_dict` (FR-PERF-001, SC-PERF-001)
- [ ] T084 [P] Write `specs/006-public-object-api/migration-guide.md` from the D2 map: every removed entry point, its replacement, and the consumer sites in `cuems-engine`, `cuems-editor` and `cuems-nodeconf` — the deliverable feature 008 executes against. Consumer repositories are not edited here (FR-UX-001)
- [ ] T085 [P] Write `specs/006-public-object-api/frontend-note.md` documenting that both UI payloads now agree, that **no frontend change is required** because the `=== true || === 'True'` dual-check already absorbs it, and that removing the dual-check is theirs to schedule (FR-UX-001)
- [ ] T086 [P] Docstring sweep across the six public methods in `src/cuemsutils/cues/CuemsScript.py` and the changed accessors in `src/cuemsutils/tools/ConfigBase.py` / `ConfigManager.py`: each states its contract **and its error behaviour**, because `validate()` reports and `save()` raises first and a reader must not have to infer that (constitution I). Verify T027's `validate()` docstring still describes the report in full and that the generated documentation renders it — no public method may return a type whose shape a reader can only learn by opening an internal module (contracts/public-api.md C1). Confirm **every** public method carries a `Raises:` entry naming each exception type and the condition producing it — for most consumers the generated docs are the only place they will look (FR-035a, SC-018)
- [ ] T087 [P] Correct the stale baseline in `CLAUDE.md`: replace the "557 passed in ~7.4 s" figure with the measured suite result, and add the 006 entry to Recent Changes
- [ ] T088 [P] Correct the same stale "557 passed in ~7.4 s" figure in `specs/planning/xml-rebuild-07-speckit-prompts.md`
- [ ] T089 Run `ruff check src tests` — clean, no new warnings; confirm the feature is net line-negative against T001's recorded count (SC-QUALITY-001)
- [ ] T089a [P] Audit that spec.md, **plan.md**, contracts/ and tasks.md name the **same** set of deliverable artifacts — `schemalocation-evidence.md`, `api-surface-diff.md`, `migration-guide.md`, `frontend-note.md`, `legacy-coverage.md`, `golden-changes.md`, `baseline.md`, `specs/planning/schema-evolution-convention.md` — with none named in one and absent from another. plan.md is in the audit set because its documentation tree was the artifact that drifted: it listed only `checklists/requirements.md` while spec.md cited `checklists/api.md` throughout, and predated all eight artifacts above (CHK040)
- [ ] T090 Walk `specs/006-public-object-api/quickstart.md` sections 1–7 end to end and confirm each command produces its stated result, and add a section 9 covering the UTF-8 round trip under `LC_ALL=C` (FR-036e)
- [ ] T091 Run `PYENV_VERSION=3.11.9 pyenv exec hatch test --show` — green, ≥ 1485 passing, and record the final counts in `specs/006-public-object-api/baseline.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup — **blocks US1 and US2**
- **US1 (Phase 3)**: depends on Foundational
- **US2 (Phase 4)**: depends on Foundational; T030 also depends on US1's `to_wire()` (T026)
- **US3 (Phase 5)**: depends on **Foundational** (T008/T009 — the config projection is the
  same `encode_wire`), and T043b and T056a additionally depend on **US1's T026**, which places
  the shared `to_wire()` they bind to. Everything else in US3 — the models, the registry
  bindings, the three compensations, the two fossils — depends on Setup only. *This corrected a
  claim of "Setup only — genuinely independent of the P1 stories", which was true of most of
  the story but not of the four projection tasks.* **T040a runs first within the story**, before
  its own sibling tests: it records a "before" that T048/T055 destroy
- **US4 (Phase 6)**: depends on US1 (the replacements must exist before the old surface is
  hidden) and on US3 (the `Settings`/`NetworkMap`/`ProjectMappings`/`ProjectSettings` shims
  must point at working config accessors)
- **US5 (Phase 7)**: depends on US1's `run_rules` seam — **built by T023b** and consumed by
  T027/T028 — and on Foundational's `_initialized` handling (T010). T076 depends on Setup's
  T003c, not on a corpus addition of its own
- **US6 (Phase 8)**: depends on US2's T037, which makes the change US6 verifies
- **Polish (Phase 9)**: depends on all desired stories

### Cross-story couplings (deliberate, not accidental)

- **FR-031**: the release, not the commit, is the unit — see the Phase 4 note. T037 makes the
  one real edit (the written attribute); the key's absence is a property of `encode_wire` from
  T009. US6's T078/T080 verify and record; they do not make the change.
- **US1 ↔ US5**: **T023b** builds the `run_rules` seam, T027/T028 consume it, and T072/T072a
  fill it with the registry. Until US5 lands, `save()`/`validate()` run T1 plus the three
  semantic rules `validators.py` already holds — correct behaviour, just not yet the full
  registry. Without T023b, US1 would call a function no task creates.
- **US1 → US3**: T026 places `to_wire()`/`to_json()` on the shared `CuemsDict` base; T056a
  binds the config models to that one body rather than writing a second. T043b asserts there is
  no second body, so it cannot run before T026 either.
- **US3 → US4**: T061's config shims need T049's readers to work.
- **Setup → US5**: T003c adds the fade-cue corpus document in Phase 1 so its goldens are
  captured pre-feature; T076 only exercises the rules against it.

### Within Each User Story

- Tests are written and FAIL before implementation
- Models before services; services before public methods
- Story complete before moving to the next priority

### Parallel Opportunities

Counts below are stated explicitly so they can be checked against the phase bodies rather than
trusted; they were wrong in every line of this list until 2026-08-18.

- Setup: T003a, T003b, T003c together after T001; then T003 (counts the population they
  create) and T002 (hashes the directory they add to) — **neither is `[P]`**, both must follow
  the corpus additions
- T004–T007 (all **four** Foundational tests) together; then T011–T015 (**five** cue files) together
- T016–T022b (all **eleven** US1 tests: T016–T022 plus T022a, T022b, T022c, T022d) together
- T030–T034 (all **five** US2 tests) together
- **T040a first, alone**; then T039, T039a, T040, T041, T042, T043, T043a, T043b (the other
  **eight** US3 tests) together; then T045–T047 (three new config modules); then T053/T054
- T057–T060 (all **five** US4 tests: T057, T057a, T058, T059, T060) together
- T066–T071 (all **six** US5 tests) together
- T078, T079 (both US6 tests) together
- T084–T088 in Polish
- **Most of US3 can be developed in parallel with US1 and US2** — different files, different
  schemas. The exceptions are the four projection tasks (T043a, T043b, T056a, T056b), which
  need Foundational's `encode_wire` and US1's T026, and T040a, which must precede its own story

---

## Parallel Example: User Story 1

```bash
# Launch all eleven US1 tests together (all must fail first):
Task: "Contract test the six public methods in tests/contract/test_public_script_api.py"
Task: "Contract test the coercion guarantee in tests/contract/test_coercion_guarantee.py"
Task: "Contract test save() atomicity in tests/contract/test_save_atomicity.py"
Task: "Contract test validate() collects vs save() raises first in tests/contract/test_validate_report.py"
Task: "Unit test declared-field equality, fresh-runtime copy and hashability in tests/unit/test_script_equality.py"
Task: "Contract test from_json ingestion — str, bytes and Mapping — in tests/contract/test_from_json_ingestion.py"
Task: "Integration test the public-API-only D14 chain in tests/integration/test_d14_chain.py"
Task: "Contract test the error types and the carried violation in tests/contract/test_error_types.py"
Task: "Contract test the UTF-8 round trip in tests/contract/test_utf8_roundtrip.py"
Task: "Contract test the same round trip under LC_ALL=C in tests/contract/test_utf8_roundtrip.py"
Task: "Contract test that projection does not validate in tests/contract/test_projection_does_not_validate.py"
```

## Parallel Example: Phase 2 runtime declarations

```bash
# After T010 lands the mechanism, all five cue classes convert independently:
Task: "Declare RUNTIME_FIELDS on src/cuemsutils/cues/Cue.py"
Task: "Declare RUNTIME_FIELDS on src/cuemsutils/cues/AudioCue.py"
Task: "Declare RUNTIME_FIELDS on src/cuemsutils/cues/VideoCue.py"
Task: "Declare RUNTIME_FIELDS on src/cuemsutils/cues/DmxCue.py"
Task: "Declare RUNTIME_FIELDS on src/cuemsutils/cues/ActionCue.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

Both P1 stories are the MVP, and they are one MVP rather than two: US1 gives consumers the
surface, US2 proves the heaviest path across a repository boundary has not moved. Shipping US1
without US2 would mean exposing a projection whose byte-identity nobody has asserted.

1. Phase 1: Setup
2. Phase 2: Foundational — **critical**, blocks both P1 stories
3. Phase 3: US1 → stop and validate
4. Phase 4: US2 → **stop and validate against the goldens**
5. The library is usable and the UI is provably safe

### Incremental Delivery

1. Setup + Foundational → `encode_wire` proven against goldens and oracle, runtime declared
2. US1 → the public surface exists; old entry points still work → validate
3. US2 → the payload is proven unmoved and the two payloads agree → **MVP**
4. US3 → config answers with objects → validate
5. US4 → machinery goes internal, legacy tree deleted → validate
6. US5 → the semantic tier becomes a registry → validate
7. US6 → documents portable, convention adopted → validate
8. Polish → budgets measured, migration guide written, baselines corrected

### Parallel Team Strategy

1. Everyone through Setup + Foundational
2. Then: Developer A on US1 → US2 (the critical path); Developer B on US3 → US5, starting with
   T040a and holding the four projection tasks (T043a, T043b, T056a, T056b) until A lands T026;
   Developer C on US6's convention document and the Polish artifacts (T084, T085, T087, T088),
   which depend on nothing
3. US4 lands last of the implementation stories because it depends on US1 and US3

---

## Notes

- **110 tasks**: 6 setup, 12 foundational, 20 US1, 9 US2, 24 US3, 11 US4, 13 US5, 5 US6,
  10 polish. *(This line said "91 tasks: 3/12/14/9/18/9/12/5/9" until 2026-08-18 — a count
  taken before the lettered tasks were added and never retaken. Every sub-count was wrong. If
  you add a task, retake the count or delete the line; a stale census is worse than none.)*
- **The five enumerated behaviour changes** each have a fail-then-pass test:
  1. **Payload parity** → T030, which must fail first (today the two payloads differ on every
     boolean and on `ui_properties` integers)
  2. **`schemaLocation` dropped from the wire dict** → T031. Note this one is a **guard, not a
     fail-then-pass test**: `encode_wire` never emits the key (T009), because the gating test
     T005 compares against the golden *minus* it. There is no state in which the projection is
     correct and the key is present, so nothing can fail first. It is listed because the change
     is real from a consumer's view, not because the test is red at any point
  3. **Derived projection replaces the eight `__json__` methods** → T035/T036 with T030
  4. **Relative schema location** → T078
  5. **Cue equality widens from `id` alone to all declared fields** → T020, with T029 as the
     change. *This was missing from the list until 2026-08-18: the enumeration in spec.md has
     said five since the API checklist found change 5 (CHK007), while this note, SC-TEST-001
     and plan.md's test gate all still said four.*
- **T005 is the gating test.** It crosses into a repository this feature does not edit and its
  failure mode is invisible here
- Commit after each task or logical group; commits are GPG-signed (retry on "gpg failed to
  sign", never `--no-gpg-sign`)
- Stop at any checkpoint to validate a story independently
