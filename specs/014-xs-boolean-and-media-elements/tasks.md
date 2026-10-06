---
description: "Task list for feature 014 — xs:boolean, the media block, the curve names, the config ingestion"
---

# Tasks: feature 014

**Input**: [`plan.md`](plan.md) (this feature's design, twelve settled decisions),
[`baseline.md`](baseline.md) (budgets, measured before implementation).
**Branch**: `014-xs-boolean-and-media-elements`, cut from `feat/xml-refactor` at `84705b9`.
**Path**: reduced SDD — no `spec.md` story pass, no `research.md` (plan.md §11.1 exception 1).

**Tests**: REQUIRED by the constitution (Principle II). Written first, failing before
implementation. Each task below names its red-first test or says why it has none.

---

## Already settled — do not redo

Two commits are already in this branch's ancestry because they landed on `feat/xml-refactor` before
the branch was cut. They are **preconditions, not part of this feature's diff**, and they are
recorded here so nobody re-derives them.

- [X] **S1** `_Bool.decode` refuses what the schema does not declare — `be3e86e`, 2026-10-02.
      Was `raw == "True"` with a `bool(raw)` fallback, so every other string became `False`
      silently; through `from_json` that wrote `<enabled>False</enabled>` to a schema-valid document
      and disabled a cue with nothing reporting it. 29 red tests first, then four lines. **X1
      widens this table rather than replacing it** (plan.md §1.3), so the work here builds on it
- [X] **S2** `CTimecode.milliseconds` joins the one deprecation message format — `84705b9`,
      2026-10-03. Its notice promised removal *"at the first stable release"*, a date no consumer
      could act on; it now reads `REMOVAL_RELEASE`. Scheduled as R8 item 5 of
      `../planning/deprecated-surface-removal-v0-1-1.md`. Two tests, one red-first
- [X] **S3** The `get_schema` mitigation 013 identified and deliberately left — applied on this
      branch, `baseline.md` §5. **−80%** on the configuration load, **−58%** on the suite, three
      runs. Decision 12. It is in this feature because 014 edits the schemas and so had to measure
      them anyway; it is listed as settled because it is done and measured, not pending

**Baseline is captured** (`baseline.md`): the three load figures, the suite, the descriptor's
current `enum_values`, and the 51/9 document split. Principle IV's targets are stated and are
post-mitigation.

---

## Phase 1: The additive half — no conversion, no wire change

**Goal**: the media block and the curve values land first, because they are rule-1 additive and
independent of everything else. If X1 were abandoned tomorrow these would still be correct.

- [X] **T001** [P] Red-first: a `MediaType` document carrying all four new elements validates, and
      one carrying none of them still validates. Add the fixtures under `tests/data/corpus/`;
      neither exists today ✅ `tests/data/media_block/media_block_showcase.xml` (one cue with all four, one with none) and `tests/unit/test_media_block.py`. ⚠ **Not in `tests/data/corpus/`** as this task said: corpus membership needs a pre-refactor verdict in `outcomes.json`, and a document carrying elements this feature *adds* cannot have one — the pre-014 schema rejects it. Recorded in `tests/data/corpus/PROVENANCE.md`. The attempt also cost a cascade worth knowing about: adding it there broke `test_manifest_and_disk_agree`, the pinned count, `test_every_document_has_a_golden` and six `test_accept_reject_parity` cases.
- [X] **T002** [P] Red-first: the range and the refusals, per plan.md §10.1 — `file_size` accepts
      `107374182400` (100 GiB) and `9223372036854775808`, and **refuses** `0` and `-1`; the same
      refusals for the pixel pair. This is the test that pins the >100 GB requirement against a
      future "let's make it `xs:long`" ✅ 6 accept cases up to 2⁶³, 18 refuse cases. `xs:positiveInteger` is unbounded and decodes to an arbitrary-precision `int`, so >100 GB needed no facet.
- [X] **T003** [P] Red-first: `file_md5` accepts 32 lowercase hex and refuses uppercase, 31
      characters, 33 characters and non-hex (plan.md §10.2). The uppercase case is the one that
      records the decision rather than the mechanism ✅ 3 accept, 7 refuse, plus `Md5Type` asserted to be a named type restricting `xs:string` like `UuidType`.
- [X] **T004** Add the four elements to `script.xsd`'s `MediaType` after `regions`, all
      `minOccurs="0"`, plus the new `cms:Md5Type`. **Update `CURRENT_SCHEMA_HASHES` in
      `tests/contract/test_schema_scope.py` in the same commit**, with the reason in the message —
      that pairing is the whole mechanism (execution doc §7.5) — depends on T001–T003 ✅ Four elements after `regions`, `Md5Type` beside `UuidType`, hash re-pinned twice (once for this, once after T007). ⚠ `--` is **illegal inside an XML comment** — the first draft of the comments broke the schema with `ParseError: not well-formed`.
- [X] **T005** Four `DECLARED_DEFAULTS` entries (**all `Unset`**) and four `set_<name>` accessors on
      `Media`. Both halves or the key is dropped in silence (plan.md §10.4) — depends on T004 ✅ Four `Unset` entries (eight total on `Media`) and four accessor pairs. ⚠ The setter refuses a **non-integral float**: `int(1.5)` truncates to 1, which is the silent-wrong-value class this whole feature exists to remove, so `int` or a string of digits only. `bool` is refused for the same reason — it is an `int` subclass, so `pixel_width = True` would have stored 1.
- [X] **T006** [P] Red-first then implement: `test_coherence.py` must agree that `MediaType`'s
      schema fields and `Media`'s model fields match. It fails automatically on T004 without T005,
      which is the check working; confirm that, do not route around it.
      **Also assert the writer claim** (plan.md §10.4): a `Media` built with the four keys **in any
      order**, and one with some of them absent, round-trips to **schema order with no empty
      element**. That claim — *"no writer change is needed on this branch"* — is currently asserted
      and never verified; it is the input document's third utils deliverable dropping out, so it is
      worth one test rather than an assumption ✅ `test_coherence` failed on T004-without-T005 exactly as predicted, and passed on T005 — the check working. The writer claim is now asserted, not assumed: four keys assigned in reverse order emit in schema order, and an absent field emits nothing rather than an empty element.
- [X] **T007** Cherry-pick `9c17418` from `origin/main` for `ease_in`/`ease_out` on
      `FadeCurveType`, with its schema hash moving in the same commit. Verified absent from this
      branch: a project saved by a `main`-line editor with an `ease_in` fade **fails T1 here today** ✅ Cherry-picked as `7825d80`, Ion Reguera as author. `test_enum_audit`'s `FadeCurveType` row moved with it in the same commit.
- [X] **T008** [P] Record in [`migration-guide.md`](migration-guide.md) that the media block is
      **four** elements and why (`file_md5` added, `file_size` named not `size`, `0` invalid by
      design), so `cuems-editor` and `cuems-engine` read one statement rather than inferring from
      the input document's three ✅ `migration-guide.md` §2, plus a new §2.1 recording the setters' contract as implemented.

**Checkpoint**: ✅ **PASSED 2026-10-03.** The schema admits four new optional elements and two new
curve values; nothing on disk is invalidated; no conversion exists because none is needed. Suite
**3496 passed / 112 skipped / 2 xfailed** (from 3432 — 64 new tests).

### Phase 1 amendment — the rename, 2026-10-06 (T037)

- [X] **T037** **`file_hash` → `file_md5`, `Md5HashType` → `Md5Type`** across schema, model, tests,
      fixture and documents, with `CURRENT_SCHEMA_HASHES` re-pinned in the same change. Driven by
      the input document's successor,
      [`../planning/stored-media-values-preimplementation.md`](../planning/stored-media-values-preimplementation.md)
      (D18, 2026-10-05), which ships the **fourth** element too and names it `file_md5` — a name
      rc15 has **already shipped**, back-patched into rc14 and `pre_release_1`. Recorded as plan.md
      **decision 13** and argued in **§10.5**.
      **Red-first: none, and deliberately.** A rename has no new behaviour to pin; the existing
      T001–T006 suite *is* the test, and the evidence is that it still passes under the new names.
      The one assertion that had to be added is prose, not code: `test_media_block.py`'s docstring
      now records why the element half is load-bearing (an element name is an instance-document
      name) and the type half is not.
      ✅ Eleven files. Suite **3483 passed / 12 failed**, byte-identical to the pre-rename baseline
      — measured by stashing the change and re-running, so "no new failures" is verified rather
      than claimed. All twelve are pre-existing and environmental: four absent sibling checkouts,
      `tests/unit/test_ctimecode.py` uncollectable (no `hypothesis` in the hatch-test env), the API
      snapshot, the published-scripts set, the load budget, and two packaging premises.
      ⚠ `\b` word boundaries do **not** match `get_file_hash`/`set_file_hash`/`test_file_hash_*` —
      `_` is a word character, so the first `sed` pass left the accessors behind while renaming the
      property that pointed at them. The suite caught it; a grep for the old name is the cheaper
      check and is worth running after any rename in this package.

- [X] **T038** [P] Record the two obligations that document places on `cuems-utils` and that are
      **already met at `69acaef`** — verified by measurement, not by reading (plan.md §10.7):
      (a) *"never coerce `file_md5`"* — an all-digit md5 loads as a `str`, because the adapter
      table binds **types** rather than key names and `Md5Type` restricts `xs:string`, so
      `STRING_TYPED_KEYS`' defect class cannot recur here; (b) *"please keep the old file's mode"* —
      `write_tree` already `chmod`s the temporary to the target's mode before `os.replace`
      (`xml/documents.py:273-333`), landed as **010 T080**. The request is stale.
      ✅ Both measured; recorded in plan.md §10.7 as a table.

- [ ] **T039** **The two obligations this feature pushes outward**, neither of which is
      `cuems-utils` work and both of which would otherwise be owned by a sentence and no task:
      **(a) `cuems-editor` must `.lower()` a client md5 before assigning it.** This branch's setter
      raises on uppercase where rc15's lowercased (plan.md §10.6). Safe on both lines — `.lower()`
      is a no-op against rc15's setter — so it should land **before** the merge, not during it.
      **(b) the AudioCue pixel rule has no validator.** `MediaType` is shared, so only the editor's
      strip keeps a pixel size off an AudioCue; `script.xsd`'s comment and migration-guide §2 now
      state it, but nothing enforces it. If it is worth enforcing, the place is the editor's fill,
      not this schema.
      Carry both into the sibling-gate correspondence rather than this repository's tasks.

- [X] **T040** [P] Bind `Md5Type` to `_String()` in `ADAPTERS`. It resolves to `PASSTHROUGH` today
      and is correct **by consequence**, which is exactly what the table's own `NodeUuidType`
      comment says to avoid — those names were bound *"so that a future element naming one directly
      does not silently fall through to the passthrough"*. Same argument, same type family
      ✅ One line in `adapters.py` plus `test_md5_is_bound_explicitly_and_never_coerced`, which pins
      **both** halves of the input document's §5 warning: an all-digit md5 **and** the "digits with
      one `e`" case that an old parser read as a float in exponent notation. Suite 3488 passed, the
      failure set byte-identical to baseline.

- [X] **T041** Answer *"should `pixel_width`/`pixel_height` belong to `VideoCue` rather than to
      `Media`?"* — asked 2026-10-06. **No**, and the reason is structural rather than a preference:
      the model cannot move without the schema, the schema cannot express the split by extension,
      and the split would convert a silent editor-side correction into a hard save failure. Argued
      in full as plan.md **§10.8**, because a question worth asking once is worth not re-deriving.

---

## Phase 2: X1 — the breaking half

**Goal**: `cms:BoolType` becomes `xs:boolean`, in the existing unreleased 1 → 2 step.

**⚠ Order inside this phase is not cosmetic.** The adapter must be able to *write* the new form
before the schema demands it, or the suite cannot be green at any intermediate commit.

- [X] **T009** [P] Red-first: `to_lexical(True) == "true"`, and the round trip
      `decode(to_lexical(True)) is True`. The round trip is what catches a half-applied change —
      writer updated, reader not (plan.md §1.3) ✅ The pre-014 boolean block in `tests/unit/test_adapters.py` was **retired deliberately** rather than edited: its two premises (`"True"` decodes; `to_wire` must *not* return a `bool`) are named in a comment as retired, and what survives — `decode` is strict because `from_json` has no document to validate against — is stated as surviving. 99 passed.
- [X] **T010** [P] Red-first: a full save/load cycle asserting the **bytes on disk** contain
      `<enabled>true</enabled>`. A unit test on the adapter cannot catch a `Mapper` path that
      bypasses `_lexical`; `:868`'s attribute call is the one most easily missed since 013 made
      attributes load-bearing ✅ `tests/integration/test_xs_boolean.py`, 12 passed. Asserts the **bytes on disk**, the whole-document absence of any capitalised boolean (covering all five `_lexical` call sites at once, including `element.set`), the round trip, and the wire.
- [X] **T011** `_Bool`: delete `to_wire` (inherit `_Passthrough`'s, returning the `bool`), add the
      lowercase `to_lexical` map, widen `decode`'s table to `true`/`false`/`1`/`0` plus `bool` with
      `'True'` now **refused**. A swap, not a deletion — plan.md §1.3's table is the specification
      — depends on T009, T010 ✅ The swap, as specified. ⚠ **And the feature's sharpest self-inflicted bug**: `ADAPTERS` is keyed by type *name*, so retyping to the built-in meant `_Bool` **stopped being reached at all** — `_Passthrough.to_lexical` wrote `str(False)` → `"False"`, and the schema then refused the document the library had just written. **292 failures from a lookup that silently fell through.** Now keyed on both `{…XMLSchema}boolean` and `boolean`, with the story in the comment.
- [X] **T012** Retype the five elements and delete the three `BoolType` declarations:
      `script.xsd` (`autoload`, `enabled`, `timecode`), `network_map.xsd` (`adopted`, `online`),
      and `settings.xsd`'s **dead** declaration. Schema hashes in the same commit — depends on T011 ✅ Five elements retyped, three declarations deleted (`script`, `network_map`, and `settings`' dead one). Three schema hashes re-pinned in the same commit.
- [X] **T013** The boolean rewrite joins **`_script_1_to_2` and `network_map`'s 1 → 2**, one shared
      conversion, **no new version** (decision 3). It must be **order-independent with respect to
      the media elements** — it rewrites the text of five named elements and must not care whether
      `pixel_width` is present (plan.md §4) — depends on T012 ✅ Both steps. ⚠ **`network_map` had no 1 → 2 conversion to join** — feature 012 made it a *deliberate identity step*, so this feature had to **write** one and remove `("network_map", 1)` from `DELIBERATE_IDENTITY_STEPS`. 012's reasoning is untouched (the identity half is still cross-document and still repaired by `--remint`); what changed is that the step now also carries a per-document transformation, so its absence from the registry stopped being true. The bidirectional contract test said so itself: *"Remove the entries."*
- [X] **T014** [P] Red-first: a version-1 document with old-form booleans **and** the four media
      elements converts correctly in one pass, in both orders of appearance. This is T013's
      order-independence, asserted ✅ `tests/unit/test_boolean_conversion.py`, **14 passed**. Both
      steps, both orders (`media-first` / `media-last` parametrisation), and three properties the
      rest of the feature leans on without saying so: **idempotence** — which is *why* the migrated
      top-tier corpus can stay unmarked at version 1, since the conversion runs over
      already-converted documents on every read and `_BOOLEAN_LITERALS` is keyed on the **old**
      spellings; a non-literal value **left alone rather than guessed at**, so the strict decode
      refuses it by name; and the step **reporting** what it rewrote. It also closes T015a's
      thin-coverage note explicitly: an assertion that `pre-008/script_v1_all_transforms.xml` still
      carries an old-form boolean, so a future edit to that fixture cannot silently remove the
      rewrite's only in-corpus evidence
- [X] **T015** Move **every** golden and out-of-band document the boolean form touches. ⚠ The first
      cut of this task said "six goldens"; **the measured count is fourteen goldens plus the nine
      out-of-band documents**, and the gap was eight **JSON** goldens — which are the *wire* form,
      i.e. precisely what X1 changes. Enumerated here so the red suite at T012 is planned for rather
      than discovered, and so nobody decides mid-implementation whether to regenerate: **FR-021
      stands — a golden is never regenerated to make a test pass.** Diff every file and confirm the
      change is only what was intended. ✅ **Fourteen goldens** (6 XML + 8 JSON `.reader.json`), the **two** corpus showcases, `MANIFEST.sha256` (34 entries), and my own new fixture — which turned out to be a tenth version-2 document. `outcomes.json` deliberately untouched and verified to carry no boolean form. Every rewrite asserted case-only (`new.lower() == s.lower()`), so nothing but the spelling moved.

      **(a) The nine out-of-band documents** — already `doc_version` ≥ 2, so the registry's 1 → 2
      step cannot reach them (plan.md §2.1):

      | # | File | How |
      |---|---|---|
      | 1–5 | `tests/golden/xml/{cuems-editor__script_minimal, cuems-engine__projects__complex_test__script, cuems-engine__projects__empty_test__script, cuems-utils__fade_showcase, cuems-utils__unicode_showcase}.xml` | re-cut |
      | 6 | `tests/golden/generated/example_script.xml` | re-cut |
      | 7–8 | `tests/data/corpus/cuems-utils/{fade_showcase,unicode_showcase}.xml` | **hand-rewritten** — authored, not generated |
      | 9 | `../cuems-engine/dev/test_xml_files/projects/complex_test_v2/script.xml` | **the ninth, and it is in a sibling.** Owned here because this task owns the nine; coordinate with T028a |

      **(b) The eight JSON goldens** — not `doc_version`-marked documents, so they are absent from
      the nine, but every one pins `"enabled": "True"` or `"adopted": "True"`:

      ```
      tests/golden/dict/cuems-editor__script_minimal.reader.json
      tests/golden/dict/cuems-engine__network_map.reader.json
      tests/golden/dict/cuems-engine__projects__complex_test__script.reader.json
      tests/golden/dict/cuems-engine__projects__empty_test__script.reader.json
      tests/golden/dict/cuems-utils__fade_showcase.reader.json
      tests/golden/dict/cuems-utils__network_map.reader.json
      tests/golden/dict/cuems-utils__unicode_showcase.reader.json
      tests/golden/generated/example_script.reader.json
      ```

      **The two `network_map` ones carry `adopted`/`online`** — the only place in the golden corpus
      where that half of X1 is visible, so they are the regression net for `network_map`'s 1 → 2.

      **(c) `tests/golden/MANIFEST.sha256`** (34 lines) moves with them, in the same commit.

      **(d) `tests/golden/outcomes.json` is NOT a regeneration target** — execution doc §7.2: it
      records *pre-refactor* verdicts and a test asserts the **difference** between it and live
      behaviour. Running `capture_goldens --force` over it destroys that baseline. Verified: it
      contains no boolean form, so this feature must not touch it
- [X] **T016** Move the negative corpus with it. `tests/data/corpus/negative/` fixtures fail **for a
      reason**, and a schema change moves which error each one raises — execution doc §7.3 is the
      precedent, where a fixture kept failing while testing the wrong thing and the suite stayed
      green ✅ **Verified unaffected rather than assumed**: all three negative fixtures carry **zero** boolean elements, and `test_negative_fixtures_after_narrowing.py` passes (11). So no fixture is failing for a newly-wrong reason — which is what §7.3 asks be re-checked, and the answer here is "nothing moved".
- [X] **T012a** *(added mid-flight)* Deprecate `read`, `read_to_objects`, `write_from_object` and
      `validate_object` on the **current** `XmlReaderWriter`, pointing at `to_wire`/`load`/`save`/
      `validate`. **Why it was needed and not foreseen**: those methods are a *raw* schema decode
      that never applied a version conversion — invisible while every schema change was additive,
      and made observable by X1. The method-level deprecation existed **only on the deprecated
      import path**; the current module's was a live, undeprecated API, which is why the failures
      read as a regression rather than a deprecated surface narrowing. Private cores
      (`_raw_decode`, `_write_object`) extracted first, because `read_to_objects` called `read()`
      and `write_from_dict` called `write_from_object` — deprecating those would have tripped
      contract C8 on the library itself. Verified: no internal caller remains
- [X] **T015a** *(added mid-flight)* **Migrate the top-tier corpus** — 116 elements across 10
      documents, `doc_version` untouched. This replaced an estimated ~20 files of test edits, and
      the precedent decided it: `corpus/cuems-engine/.../complex_test/script.xml` is **unmarked
      (version 1)** yet already carries 008's wrapped duration *and* 013's device shape, so the top
      tier has always held current content unmarked and relied on idempotent conversion. 008 and
      013 each did this and each left a `pre-NNN/` tier behind; **no `pre-014/` is needed** —
      `pre-008/script_v1_all_transforms.xml` is read through the registry and carries an old-form
      boolean, so the rewrite has in-corpus evidence (thin: one element, which **T014 should assert
      explicitly** rather than rely on). Also fixed: 16 inline XML literals in 7 test modules, the
      `NodeSpec` fixture's `"True"` defaults, and the golden harness, which was itself calling the
      surface T012a deprecates (contract C8)
- [X] **T017** Update the contract tests whose premise X1 retires: `test_wire_booleans.py` (its
      whole docstring), `test_ui_payload_contract.py`'s boolean section, `test_enum_audit.py`
      (three rows), `test_schema_name_overlap.py:82` (`BoolType` leaves
      `KNOWN_IDENTICAL_DUPLICATES`). **Retire the premise deliberately, in the same commit, with
      what replaces it** — the 010 FR-029b discipline applied to a contract rather than a shim
      ✅ **Twenty modules, 56 → 0 failures.** Every premise inverted or narrowed, never deleted, with
      the retirement recorded in the docstring or comment that held it.

      **The four the task named**: `test_wire_booleans.py` (whole-file premise — its docstring *was*
      X1's deferral note, now the assertion that the deferral is discharged, 21 passed);
      `test_ui_payload_contract.py` (inverted, **and the negative rule narrowed** to exempt exactly
      the three declared booleans rather than relaxed); `test_enum_audit.py` (three rows removed);
      `test_schema_name_overlap.py` (the entry removed — **the second duplicate resolved by
      deletion**, after 012's `UuidType`, which is the only state in which the stale-entry test
      demands the removal).

      **Sixteen the task did not name**, which is the part worth recording — the premise sat in
      places a grep for `BoolType` does not reach:
      `test_encode_wire_scalars.py` (`test_booltype_encodes_as_capitalized_strings` →
      `test_booleans_encode_as_real_json_booleans`), `test_descriptor_enums.py` (now asserts the
      deletion is **total** across all three schemas — a declaration creeping back into one and not
      the others is the X14-class defect the original guarded),
      `test_node_field_coercion.py` (vocabulary moved to `true|false|1|0`, **plus** a new refusal
      test for `"True"`), `test_config_wire.py` and `test_reader_configs.py` (both held a
      `bool` → `str` **bridge** that is now an identity; kept as named identities, because the
      bridge is the thing those tests claim they no longer need, and the comment says which
      direction a future one would go), `test_version_steps.py`
      (`NO_LONGER_AN_IDENTITY_STEP = {"network_map"}` named, with the other-direction assertion),
      `test_payload_parity.py`, `test_node_typing.py`,
      `test_type_coercion_live_paths.py`, `test_xml.py::test_json_readwrite` (**difference (a) of
      three closed** — 006 unified the two editor payloads *on the string form*; X1 removed the
      cause, so what was an enumerated difference is now the round trip holding),
      `test_repair.py` ("zero silent" **narrowed, not loosened** — the count is still exact, taken
      over the `fade_profiles` records alone, because an unfiltered length check would start passing
      for the wrong reason the next time that step grows),
      `test_pre_step_documents_load.py` (the identity wording still binds for the two schemas it
      still applies to), `test_init_node_overlay.py`, `test_init_node_triple.py`,
      `test_remint_preserves_adoption.py` (a row's spelling now **survives** instead of being
      re-encoded), and `test_network_map_roundtrip.py`.

      ⚠ **Two findings worth more than the edits.**

      **(a) `test_construction_parity.py`'s `opaque_dmx` group went 4 → 1, and nothing in this
      feature aimed at it.** `Mapper.OPAQUE_TYPES` decodes a `DmxCue` without recursing, so its
      `autoload`, `enabled`, `timecode` and scene `id` were all strings. Retyping to the built-in
      closed **three of the four** — `xmlschema` decodes `xs:boolean` to a Python `bool` itself, so
      the value arrives typed before the missing recursion could matter. The group was never about
      opacity for those three; it was about the declared type. 005's recorded residual drops from
      **14 to 11**, and what remains (`DmxScene/id`) genuinely *is* the opacity.

      **(b) 007's `pre-state/` was not rewritten to keep its own test green.**
      `test_network_map_roundtrip.py` compares a written document against
      `specs/007-node-model-migration/pre-state/network_map.xml`, which carries `True`. The
      normalisation went on the side that **moved**, beside the existing `doc_version` strip and for
      the same reason — a landed feature's directory is frozen historical record, not a fixture
      to retrofit. CLAUDE.md's rule, applied where it actually came up
- [X] **T018** [P] Red-first then assert: the descriptor reports **`enum_values = None`** and a
      native boolean for all five fields. `baseline.md` §3 is the "before"; this is the acceptance
      criterion for the finding that decided X1, not a hoped-for side effect ✅ All five fields now report `enum_values = None` and a boolean type, asserted in `test_xs_boolean.py`. `baseline.md` §3 is the recorded "before".

**Checkpoint**: ✅ **PASSED 2026-10-05.** `3535 passed, 113 skipped, 2 xfailed in 26.36 s`
(**7.47 ms/test** — the `get_schema` mitigation T002 applied dominates this figure; the number is
not comparable to any pre-014 baseline and Phase 4's T027 is where it gets stated properly).

Booleans are `xs:boolean` end to end — schema, adapter, conversion, goldens, descriptor — and the
wire carries JSON `true`/`false`.

**The red suite went 292 → 56 → 0, and the three numbers mean different things.** 292 was a genuine
bug (T011's `ADAPTERS` key fall-through). 56 was **retired premises**, not breakage: tests asserting
the string form *as the contract*, which is exactly what this phase changes. 0 is T017, which
inverted or narrowed every one of them in place.

**The byte-identity contracts settled themselves** — `test_byte_identity_dict`,
`test_byte_identity_xml` and `test_roundtrip_stability` are **142 passed**, because T015a moved both
sides together. They were expected to need a judgement call and did not.

**Two things this phase learned that the plan did not predict**: the premise lives in places a grep
for `BoolType` cannot find (T017 named sixteen modules the task did not), and retyping to a built-in
closed three residual divergences in `test_construction_parity.py` that no task was aimed at, because
`xmlschema` types the value itself and no adapter had to reach it (T017 ⚠(a)).

---

## Phase 3: The public configuration ingestion (`cuems-editor` UR-5)

**Goal**: one public JSON → configuration-object call, symmetric with `CuemsScript.from_json`.

**Depends on Phase 2** — plan.md §9.2: build it against a descriptor that reports booleans
natively, not one that calls them a two-value string enum.

- [X] **T019** [P] Red-first, per domain: `get_schema_descriptor(X).instance` → `from_json(X, …)` →
      `save_X()` → `load_X()` equals what went in. The loop §9.2 describes, asserted ✅
      `tests/integration/test_config_ingestion.py`, **30 passed** (25 red first; the 4 that were
      green from the start are the descriptor-shape half, which already held). The loop is asserted
      in **two** halves because a round trip cannot reach the first: that the descriptor's root
      `instance` names *exactly* the keys the ingestion accepts, per domain — otherwise the loop
      would close only for documents that never came from the descriptor.
      ⚠ **`save_X()` is not the persistence step, and could not be.** `save_*` writes what the
      *manager holds*, and two of the four domains hold it on a private attribute
      (`_settings_document`, `_project_settings_document`). The round trip therefore persists
      through the root object's own public `save(path)` — the same body all four `save_*` delegate
      to — and then reads back through `load_network_map()` / `load_base_settings()` where a public
      accessor answers with the root. Recorded in `migration-guide.md` §3.1 so no consumer goes
      looking for an installer that is deliberately absent
- [X] **T020** [P] Red-first: after ingestion `network_map`'s `adopted` is a `bool`, `node_role` a
      `NodeRole`, `uuid` a `Uuid` — **and the other three schemas' scalars are still `str`.** The
      second half is what catches an ingestion that "helpfully" coerces everywhere, which is the
      007 regression this feature must not cause ✅ Both halves. ⚠ **"still `str`" is the wrong
      instrument and the test says so**: some of those scalars were never `str` — `xmlschema`
      decodes `xs:int` to an `int` with no adapter involved, and feature 012's per-**field** opt-in
      makes `settings`' own `node/uuid` a `Uuid`. A literal reading would have had to grant two
      exceptions and would then have stopped catching the regression it exists for. So the
      assertion is **identical types to what `load_*` itself produces**, compared scalar by scalar
      over a recursive type map, plus the direct check that no `bool` appears anywhere in the three
      non-opted-in schemas. That is strictly stronger than the task's wording and is the same
      guarantee (007 SC-010a)
- [X] **T021** [P] Red-first: `from_json(NETWORK_MAP, {… "adopted": true …})` is accepted and
      `"adopted": "True"` is **refused**. This assertion exists only because both changes land
      together; written against either alone it would be wrong ✅ Both, and the refusal is a
      `SchemaError` naming the offending value — it comes from `_Bool.decode`'s table through the
      same `Mapper` call `load_*` uses, not from a check written for the ingestion
- [X] **T022** Implement `ConfigManager.from_json(SchemaName, payload)` — three accepted forms
      (`str`, UTF-8 `bytes`, `Mapping`), decoding through **the same mapper call `load_*` uses**,
      returning the **object** `save_*` writes, not a dict. `doc_version` never expected. `script`
      and `hardware_outputs` keep their refusals — depends on T019–T021 ✅ As specified, plus four
      things the task did not foresee:

      **(a) The three-form stage is factored, not copied.** `CuemsScript._ingest` had it inline;
      writing it a second time would have made the feature that exists to remove a second decoder
      ship one. It is now `cuemsutils._ingest.payload_as_mapping`, private like `_deprecation`, and
      what stays at each call site is the part that genuinely differs — which body shape counts as
      a document of that kind. `CuemsScript`'s `import json` became dead and was removed; one
      refusal message gains the word "payload" (nothing pinned it, verified across all six
      checkouts).

      **(b) ⚠ A pre-existing projection/ingestion asymmetry, found by being the first caller to
      close the loop.** `encode_wire` wraps a repeated member that decoded **bare** in its *class*
      name, and `decode_config` had no branch for that key. `project_settings` is the one schema
      where that happens (`<setting>` repeats *directly* under the root, so its members are bare
      `SettingType` objects), so its own wire form — `{"setting": [{"SettingType": {…}}]}` — was
      **not ingestible by its own library**: the body was stored as undescribed content and the
      document would not save. Fixed in `Mapper._decode_config_item`, **not** in `from_json`, so
      the ingestion keeps decoding through exactly the call `load_*` uses. It cannot move a
      recorded golden — `xmlschema` never emits a *type* name as a dict key, so no document decode
      has ever reached the new branch, and the suite's byte-identity and golden-immutability
      contracts confirm it.

      **(c) One named tolerance, for `settings` only.** `ConfigManager.to_wire('settings')` projects
      the root's `Settings` **field**, one level deeper than the document, because
      `Settings.main_key` is `'Settings'` and not `''`. That is the payload `cuems-editor`'s T059
      actually sends. A public ingestion that cannot read its own library's public projection is a
      gap, not a strictness, so the inner body is accepted and re-wrapped — generalised over "the
      root declares exactly one non-repeated complex field", which is `settings.xsd` and nothing
      else among the six. Pinned by its own test so a future reader deleting it is told by name.

      **(d) SC-004 needs its third recorded exception**, and it is argued differently from the two
      above it. `get_schema_descriptor` and `generate_example` are exempt because describing a
      schema is *meta*; `from_json` builds a document, which is domain work. It is exempt because
      **a JSON payload carries no type**: `CuemsScript.from_json` names no schema only because the
      class carries `SCHEMA_NAME`, and the symmetric design — `CuemsSettingsType.from_json` — is
      unreachable, since `cuemsutils.config` exports nothing by decision and that is precisely why
      UR-5 asked for this shape. Four per-domain methods would make the one consumer that asked
      build a dispatch table to get back to the parameter it started with. Recorded with the
      argument in `tests/contract/test_public_api_surface.py`, and
      `test_the_exceptions_take_the_enum_not_a_string` now covers all three
- [X] **T023** [P] Verify `cuems-editor`'s T059 closes by **re-run only**: its
      `test_config_save_of_settings_persists_through_save_settings` is `xfail(strict=True)` and must
      turn **XPASS**. Record it in [`migration-guide.md`](migration-guide.md). Do not edit that
      repository ⚠ **Measured, and the task's premise is false: it stays XFAIL.** Recorded as a
      correction in `migration-guide.md` §3.1 rather than worked around.

      Run with that repository's own hatch environment resolving `cuemsutils` to this working tree
      (verified `0.1.0rc16`, `/disk/Projects/StageLab/cuems-utils/src/cuemsutils/__init__.py`):
      `12 passed, 1 xfailed`. **Why**: `CuemsWsUser.config_save` does not *attempt* an ingestion and
      fall back — after the schema-name check and `CONFIG_SAVE_REFUSED` it calls
      `notify_error_to_user` for all four configuration domains **unconditionally**, with the
      message naming UR-5. There is no call site a library change can satisfy. T023 assumed a
      guarded fallback; it is a hard-coded refusal.

      **The library's half is complete, including the payload shape that repository actually
      sends** — pinned by `test_from_json_ingests_this_librarys_own_settings_projection`, which
      exists for no other reason. What is left is ~6 lines in `config_save`, in that repository,
      and **this task says not to edit it**, so it is not edited. It belongs with T032.

      Also measured while there: `cuems-editor`'s full suite is **5 failed / 149 passed / 2 skipped
      / 1 xfailed**, and the **same 5 fail at `e295289` with Phase 3 stashed** — they are Phase 2
      (X1) fixture casualties and are T032's, not Phase 3's. Phase 3 adds **zero** editor failures.

**Checkpoint**: ⚠ **NOT MET, and it was unreachable from this repository.** 62 of 63 stays 62 of 63
until `cuems-editor` edits `config_save`; the checkpoint's "without a line changing there" was the
mistaken part, not the close itself.

---

## Phase 4: Migration, measurement and the rule-4 release note

- [X] **T024** Complete the rule-4 release note in
      [`migration-guide.md`](migration-guide.md) §4 — the one deliverable
      `specs/agreements/schema-evolution-convention.md` demands that cannot be inferred from
      anything else. Rule 4's own sentence is the standard to meet: *"'We will just update the files
      on the nodes' is not a conversion path. Nobody knows where all the files are"*.

      **Acceptance criteria**, because "write a release note" is not checkable:
      1. **Every path named**, not counted — the 51 automatic by glob or directory, the nine
         out-of-band by filename (T015 has the list), and the two live locations that are neither:
         `/etc/cuems/network_map.xml` and each node's project library.
      2. **One sentence stating when the old form stops being accepted**, with its date or release.
         The current draft says "immediately on this feature"; that is the answer, and it must
         survive review rather than be softened into a grace period nothing implements.
      3. **The reshape-then-convert order** for a document needing both migrations.
      4. **A reader who has never read `plan.md` can act on it.** That is the test: the note is for
         an operator and a sibling maintainer, not for this feature's author

      ✅ `migration-guide.md` §4, rewritten against all four criteria. §4.1 names every one of the
      51 by path and per repository with its gate task, **and names the 18 this repository
      deliberately leaves old-form** (the `pre-008`/`pre-013` tiers and 007's frozen `pre-state/`)
      with the reason, which the criteria did not ask for and a sibling maintainer will otherwise
      read as 18 missed files. §4.3 is the two live locations. §4.4 is the one sentence. §4.5 is the
      order. Also added, because it is what makes the note actionable rather than descriptive: the
      `grep -rlE` one-liner that finds the files on any node, and the measured fact that **no
      `settings.xml`, `mappings.xml` or project `settings.xml` needs converting at all** —
      `settings.xsd`'s `BoolType` declaration was dead and the other two config schemas declare no
      boolean, so only `script.xml` and `network_map.xml` are affected. Verified against all five
      schemas rather than assumed
- [X] **T025** Document the nine already-version-2 files and the out-of-band rewrite in the same
      note (plan.md §2.1). Version 2 is briefly ambiguous and the registry cannot resolve it; say
      so plainly rather than leaving it to be discovered ✅ `migration-guide.md` §4.2 — all nine by
      filename, each with its status, and the ambiguity stated as a consequence of putting the
      rewrite in the *existing unreleased* version 2 rather than as a quirk.
      ⚠ **Item 9 is still old-form, verified 2026-10-05**:
      `../cuems-engine/dev/test_xml_files/projects/complex_test_v2/script.xml`. T015's table claimed
      it and T015's completion note does not mention it, so it was **missed, not deferred**. It is a
      sibling file and T028 was written to "verify the result in place", so it is named as
      outstanding rather than rewritten from here — **and T028 must now rewrite it, not check it.**
      A plain `cuems-convert-documents` pass will not fix it: the file is already `doc_version="2"`,
      which is the whole of §4.2
- [X] **T026** Validate the three budgets in `baseline.md` §5 and record each, **including any that
      is exceeded — recorded as exceeded rather than restated as passing** ✅ `baseline.md` §6.
      **SC-014-PERF-002 met** (7.12–7.30 ms/test against ≤ 7.79, three runs). **SC-014-PERF-001 and
      SC-014-PERF-003 exceeded**, by 0.1–8.6% and 0.01–4.3%, and recorded as exceeded.
      ⚠ **The overrun is the instrument, and a control arm proves it rather than arguing it**: the
      same three measurements on `2cc5506` — the commit that applied the `get_schema` mitigation and
      *nothing else*, i.e. the exact tree §5 measured at 3.690 / 1.646 / 13.311 — read **4.05–4.17 /
      1.95–2.02 / 14.46–14.99** today. SC-014-PERF-001 is exceeded *by the tree it was calibrated
      on*, before a schema byte moved, and all three arms (`2cc5506`, Phase 2, Phase 3) are mutually
      indistinguishable. The finding that outlives the numbers: **a 110%-of-baseline budget sits
      below this instrument's resolution** — the run-to-run spread on one unchanged tree is ±4–8%.
      No mitigation applied, because there is nothing measured to mitigate
- [X] **T027** [P] Re-measure the descriptor and the suite after Phase 2, and state whether removing
      three `simpleType`s and retyping five elements to a built-in helped, hurt or did neither.
      013's identified mechanism (`elementpath` rebuilding a node tree per `xs:alternative`
      evaluation) is **untouched** by this feature, so a flat result is the expected one ✅
      **Neither** — the predicted result, now measured. `baseline.md` §7: cold descriptor build in a
      *fresh process* per measurement (`derive` is `lru_cache`d, so an in-process repeat measures
      the cache), three processes per schema, HEAD against `2cc5506` in the same session. Every band
      overlaps: `script` 230.7–235.3 against 228.5–236.2, `network_map` 106.1–107.2 against
      106.0–109.1, `settings` 122.9–135.2 against 122.6–134.8. The **number of described types is
      unchanged too** (34 / 3 / 10) — correctly, since the descriptor describes *complex* types and
      a `simpleType` was never one. The facet cost removed is three enumeration pairs on five
      elements, against a per-evaluation `elementpath` tree rebuild this feature does not touch, so
      flat is the prediction confirmed rather than a missing win. Suite: 7.12–7.30 ms/test

**Checkpoint (T024–T027)**: ✅ **PASSED 2026-10-05.** The rule-4 release note names every path, the
nine out-of-band files are named individually with one recorded as outstanding, and all three
budgets are measured against a same-session control arm — one met, two exceeded and recorded as
exceeded with the mechanism identified. Suite **3565–3566 passed, 112–113 skipped, 2 xfailed in
25.39–26.02 s**.

The sibling gates T028–T036 are **not started** — they were outside this pass's scope.

### The sibling gates (E3)

**One task per repository, each with the instruction that repository needs.** The single "measure
the siblings" task this replaces was a coverage gap: it measured and nobody converted. The split
follows 010's pattern — a gate task *here* that names the artifact and either finds it or does not,
with the edit itself belonging to that repository.

**What every sibling is being told, once, so it is not repeated five times**: your fixtures carry
`<adopted>True</adopted>`-style text. After this feature the library **refuses** it. Run
`cuems-convert-documents` over your fixture tree; it is the registry's 1 → 2 step and it rewrites
the boolean text. **No source change is needed in any of these four** — they hold objects, which
were always real `bool`s. If your suite goes red on anything that is *not* a fixture, that is a
finding for this feature and should come back here.

- [X] **T028** [P] **`cuems-engine`** — 6 unmarked documents under `dev/test_xml_files/`, plus the
      **one already-version-2** file T015 owns
      (`dev/test_xml_files/projects/complex_test_v2/script.xml`; T015 rewrites it, this task
      verifies the result in place). ⚠ **Corrected 2026-10-05 by T025: T015 did *not* rewrite it.**
      Verified still old-form, so this task **rewrites** it rather than verifying it — and
      `cuems-convert-documents` will not, because the file is already `doc_version="2"`
      (`migration-guide.md` §4.2). The other six are the automatic kind. **Measure in arms, not by inference** — the lesson 012 and 013
      each learned once, where the breakage was in *data* a call-site census cannot see: run at the
      branch point, after the library change, and after one conversion pass. ⚠ **The control arm is
      unavailable**: that candidate is coupled to feature 012 from `c31734c` onward
      (`coerce_identity` does not exist before it), so it cannot be tested against an older library
      to isolate a failure. Design the comparison **before** a run goes red
- [X] **T029** [P] **`cuems-power-bridge`** — 10 unmarked documents,
      `tests/fixtures/network_map/map-*/settings.xml` and siblings. ⚠ **Expect it to be red before
      you start**: measured 2026-10-02 it was already **55 failed / 221 passed** against this
      branch, all of it 013's old device shape (183 `pre-013 device shape` refusals). **Reshape
      first, then convert** — that order, or neither completes. Its 276/276 green state predates 013
      ✅ **Done in that repository**, 2026-10-05, `dd1256f`, GPG-signed. **Arms A and B identical,
      confirmed by diffing the failing-test sets — so 014 caused *zero* failures here.** Arm C
      **276 / 0**. Recorded in [`baseline.md`](baseline.md) §8.3.
      ⚠ **8 of 10, not 10.** `map-incomplete` and `map-pre007` exist to test `NETWORK_MAP_INVALID`
      and `NETWORK_MAP_RETIRED_VOCABULARY`; the tool correctly refused both and converting them
      would defeat their purpose. **The general rule that replaces §4.1's enumeration: a fixture
      whose purpose is to be refused keeps the form it is refused for** — third instance, after the
      editor's `script_minimal.xml`.
      ⚠ **It also hand-fixed nine `settings.xml`** and independently confirmed the 013/F3 dead end
      ([`../planning/settings-reshape-defeats-f3-conversion-defect.md`](../planning/settings-reshape-defeats-f3-conversion-defect.md)):
      **9 of 9 were pre-013 *and* pre-F3**, zero migrable by any shipped tool. Correctly declined to
      re-file an existing defect
- [X] **T030** [P] **`cuems-nodeconf`** — 1 unmarked document
      (`tests/fixtures/etc_cuems/settings.xml` and `settings_sentinel.xml` per 013's table). Also
      the one repository that **writes** `network_map.xml` every 30 s, so confirm its write path
      emits the new boolean form after the library moves — it is the only sibling whose output this
      feature changes ✅ **Done in that repository**, 2026-10-05, `4d7c91d` + `61c5705`, reported
      back at `2045897` in `../cuems-nodeconf/specs/sibling-gates/014-xs-boolean-and-media-elements.md`.
      Arms 32/142 → 33/141 → 32/142, then **174/174**. Recorded in [`baseline.md`](baseline.md) §8.2.
      ⚠ The document it had to convert was `network_map.xml`, not `settings.xml` — this task named
      the wrong file: `settings.xsd` declares no boolean, so `settings.xml` and `settings_sentinel.xml`
      needed nothing, and the report says so explicitly rather than leaving them unmentioned.
      The write-path check was done **on bytes**, as asked.

      🔴 **And it returned a finding that outranks the gate**: 013's `reshape_players` defeats F3's
      `settings` 1 → 2 conversion, because `reshape_file` reshapes before
      `_as_the_load_path_sees_it` runs the conversion, whose paths are the pre-013 flat ones.
      Reproduced here in both tool orders. **Not 014's, and it blocks the coordinated tag** —
      [`../planning/settings-reshape-defeats-f3-conversion-defect.md`](../planning/settings-reshape-defeats-f3-conversion-defect.md)
- [X] **T031** [P] **`cuems-common`** — ⚠ **corrected 2026-10-05: 3 documents, not 2**, and no
      mirror to move. The third is `etc/cuems/network_map.xml.example`, which a `*.xml` glob misses
      and which **breaks a test**: `tests/test_documented_validation.py::test_documented_command_accepts_valid_maps[example]`
      validates it directly against this repository's `network_map.xsd` **with no version
      conversion**, so `True` is simply invalid there. Two of its test modules also carry **inline
      XML literals** (`test_controller_resolution.py`, `test_network_map_conversion.py`); in the
      latter they are the input *and* the expected output of `cuems-migrate-network-map`, which
      never touches a boolean — so convert **both sides or neither**.
      ⚠ **It no longer mirrors the schemas**: feature 011 transferred custody and `debian/postinst`
      copies this repository's own `/usr/share/cuems/schemas/network_map.xsd`, so there is no stale
      mirror. Verified. See [`migration-guide.md`](migration-guide.md) §4.1
      ✅ **Done in that repository**, 2026-10-05, `e595e67`. Arms **104/104 → 102/104 → 104/104**,
      and **both arm-B failures were the `.xml.example`** — exactly what the forecast predicted and
      nothing else. It confirmed both corrections above (no mirror; `postinst`'s `node_type` step
      unaffected) and corrected one of mine: `tests/fixtures/maps/{converted,unconverted}.xml` are
      **orphaned**, not an input/expected pair, so "both sides or neither" did not apply. Recorded in
      [`baseline.md`](baseline.md) §8.4.
      🔴 **And it found a property of a tool *this* repository ships**:
      `cuems-convert-documents` **silently destroys every XML comment** (measured: 10 → 0, 40 lines
      → 24, exit 0) — it *"nearly ran over a doc file unattended"*. Not new and not 014's — but 014
      is the first release note telling operators to run it over **live** files, and
      `/etc/cuems/network_map.xml` is a conffile they edit. Undocumented and untested; warning added
      to `migration-guide.md` §4.1 and §4.3, and to the gate prompt.
      ⚠ **Scoped on review, because the report bundled a benign item with the serious one**:
      whitespace **survives** (it is text — the 40 → 24 is exactly the 16 comment lines) and so does
      **`xsi:schemaLocation`**, verified. What is dropped beside the comments is an **unused**
      `xmlns:xsi` declaration, which carries no information. The one thing to protect is the comments.
      ⚠ **One correction to that report** (`baseline.md` §8.4a): its arm A was taken at `c02f35c`,
      called "the true 014 branch point". That is **013's landing commit**; the branch point is
      `84705b9`, 14 commits later. Its arm A is still sound — that repository imports no
      `cuemsutils` and none of the 14 touches a schema — but `be3e86e` (**S1**, a *precondition*) is
      among them, so the same substitution would corrupt `cuems-engine`'s arm A. The prompt now says
      so explicitly
- [X] **T032** [P] **`cuems-editor`** — 4 unmarked documents, of which
      `tests/fixtures/script_minimal.xml` is **deliberately pre-013 and must stay that way** (its
      own `tests/fixtures/README.md` records why: it is the pre-migration payload capture *and* the
      `SKIPPED_INVALID` fixture). So this gate is **not** "convert everything" — it is "convert the
      three and confirm the fourth is still refused, for the right reason" ✅ **Done in that
      repository**, 2026-10-05, `8f8b46e`. Arm B was **5 failed / 149 passed — exactly the figure
      the gate prompt forecast**, which is what the forecast was for. Two `network_map.xml` fixtures
      converted; `script_minimal.xml` confirmed refused **for its device shape, not a boolean**;
      `script_minimal_013.xml` left to the on-read conversion. The retired premise was inverted, not
      deleted, and `test_project_payload` gained a **fifth** sanctioned delta — note that against
      010's recorded four. Recorded in [`baseline.md`](baseline.md) §8.1.

      **It also closed its own T059 in the same session** (`365d57f`, `d6fa83b`), so UR-5 is
      **resolved** and the `xfail(strict=True)` is gone — 161 passed / 2 skipped. §3.1 of
      [`migration-guide.md`](migration-guide.md) predicted the ~6 lines and that they were that
      repository's to write.
      ⚠ **One new report, verified here: `cuems-editor` UR-6** — `conf_path`/`project_path` refuse
      the file a first save would create, so a project's *first* `config_save` cannot resolve a
      write target. All three claims confirmed by test, including the pivotal one (`.save()` does
      **not** require the path to pre-exist). Collected in
      [`../planning/upcoming-feature-requirements-2026-10-02.md`](../planning/upcoming-feature-requirements-2026-10-02.md) §8
- [X] **T033** Record every arm in [`baseline.md`](baseline.md), per repository, **including any
      that is still red and why**. A sibling left red with the reason named is a result; a sibling
      not run is not — ✅ **COMPLETE, five of five**: [`baseline.md`](baseline.md) §8 records every
      gate — `cuems-editor` (T032), `cuems-nodeconf` (T030), `cuems-power-bridge` (T029),
      `cuems-common` (T031) and `cuems-engine` (T028) — **all five green**, each with its findings
      and each red arm attributed. Arm counts are **attributed to those repositories' own
      measurements, not re-derived** (`cuems-nodeconf`'s suite needs `zeroconf`, absent from this
      test environment); every claim each report makes *about this repository's code* was verified
      here, and three were corrected.
      **§8.0 is the result**: **eight failures attributable to 014 across five repositories, against
      183 that were already there.** Without arm A, `cuems-engine` and `cuems-power-bridge` would
      between them have reported **151 failures against this feature, every one someone else's**.
      🔴 **The cross-cutting finding of the whole round: 013's device migration was never completed
      in *three* of the five siblings**, so 014's gates paid the debt — 11 `settings.xml`
      hand-rewritten plus five documents reshaped in `cuems-engine`. **015 must close its own
      sibling fixtures in its own feature**, or the next feature's gates discover them with its own
      signal buried underneath.
      §8.6 also records a **defect in the gate prompt itself**, found by being used: its arm-A
      instruction had each session switch the shared `../cuems-utils` checkout, which races as soon
      as two `[P]` gates run at once. Now a per-session `git worktree` — **confirmed working
      mid-flight by T029**, which took arm A from a disposable worktree and reported it as the right
      practice for parallel sessions
- [ ] **T034** Record the frontend hand-off: `cuems-frontend`'s 001 began its SDD path 2026-10-03,
      and its `sequence.component.ts:997` is **mutually** hard-coupled to this feature (plan.md
      §6.2 item 2). 014 can be implemented and tested without it; it cannot **ship** without it.
      Update that repository's `06-amendment-feature-014.md` status line only if asked — it is
      their document now
- [ ] **T035** Delete `../planning/booltype-silent-false-coercion-defect.md` once this feature
      lands, on the `dmx-universe-channel-conversion-defect.md` → `specs/009-*/` precedent. **Not
      before**: it is the record of why the work exists until the work exists
- [ ] **T036** **The closing documentation pass** (C3) — 013 had one and this list did not.
      `CLAUDE.md`'s "Active Technologies" and "Recent Changes", following the house shape: what
      landed, what was measured rather than assumed, and the load-bearing facts the next feature
      inherits. Specifically: the four media elements with `file_size`'s unbounded type and
      `file_md5`'s lowercase rule; `_Bool` as a **swap** rather than a deletion, with
      `Mapper._lexical` as the only producer of element text on a stdlib-`ElementTree` write path;
      the `doc_version="2"` ambiguity and the nine files; `ConfigManager.from_json` as the new public
      name; and the `get_schema` result with the note that it does **not** touch 013's dominant
      mechanism. Also update `specs/planning/etc-cuems-first-install-execution.md` §5's step 6 from
      SCAFFOLDED to LANDED, and follow `specs/agreements/documentation-prompt.md` if a
      README/CHANGELOG pass is wanted

---

## Dependencies

```
Phase 1 (additive)      independent — can land alone
Phase 2 (X1)            T009,T010 → T011 → T012 → T013 → T014; T015,T016,T017,T018 after T013
Phase 3 (ingestion)     after Phase 2 (descriptor must report booleans natively)
Phase 4 (migration)     T024,T025 after T013; T026,T027 after Phase 2
                        T028–T032 after T013 (the conversion must exist), all [P] — different
                        repositories; T033 after them; T034–T036 last
```

**Parallel within a phase**: tasks marked `[P]` touch different files and may run together.

**The one thing this order must not permit**: T012 before T011. Retyping the schema while the
adapter still writes `"True"` makes every save fail, because `save` validates before writing — the
same mechanism plan.md §1.3 uses to argue `_Bool` cannot be deleted.
