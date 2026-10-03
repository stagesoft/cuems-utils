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
- [X] **T003** [P] Red-first: `file_hash` accepts 32 lowercase hex and refuses uppercase, 31
      characters, 33 characters and non-hex (plan.md §10.2). The uppercase case is the one that
      records the decision rather than the mechanism ✅ 3 accept, 7 refuse, plus `Md5HashType` asserted to be a named type restricting `xs:string` like `UuidType`.
- [X] **T004** Add the four elements to `script.xsd`'s `MediaType` after `regions`, all
      `minOccurs="0"`, plus the new `cms:Md5HashType`. **Update `CURRENT_SCHEMA_HASHES` in
      `tests/contract/test_schema_scope.py` in the same commit**, with the reason in the message —
      that pairing is the whole mechanism (execution doc §7.5) — depends on T001–T003 ✅ Four elements after `regions`, `Md5HashType` beside `UuidType`, hash re-pinned twice (once for this, once after T007). ⚠ `--` is **illegal inside an XML comment** — the first draft of the comments broke the schema with `ParseError: not well-formed`.
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
      **four** elements and why (`file_hash` added, `file_size` named not `size`, `0` invalid by
      design), so `cuems-editor` and `cuems-engine` read one statement rather than inferring from
      the input document's three ✅ `migration-guide.md` §2, plus a new §2.1 recording the setters' contract as implemented.

**Checkpoint**: ✅ **PASSED 2026-10-03.** The schema admits four new optional elements and two new
curve values; nothing on disk is invalidated; no conversion exists because none is needed. Suite
**3496 passed / 112 skipped / 2 xfailed** (from 3432 — 64 new tests).

---

## Phase 2: X1 — the breaking half

**Goal**: `cms:BoolType` becomes `xs:boolean`, in the existing unreleased 1 → 2 step.

**⚠ Order inside this phase is not cosmetic.** The adapter must be able to *write* the new form
before the schema demands it, or the suite cannot be green at any intermediate commit.

- [ ] **T009** [P] Red-first: `to_lexical(True) == "true"`, and the round trip
      `decode(to_lexical(True)) is True`. The round trip is what catches a half-applied change —
      writer updated, reader not (plan.md §1.3)
- [ ] **T010** [P] Red-first: a full save/load cycle asserting the **bytes on disk** contain
      `<enabled>true</enabled>`. A unit test on the adapter cannot catch a `Mapper` path that
      bypasses `_lexical`; `:868`'s attribute call is the one most easily missed since 013 made
      attributes load-bearing
- [ ] **T011** `_Bool`: delete `to_wire` (inherit `_Passthrough`'s, returning the `bool`), add the
      lowercase `to_lexical` map, widen `decode`'s table to `true`/`false`/`1`/`0` plus `bool` with
      `'True'` now **refused**. A swap, not a deletion — plan.md §1.3's table is the specification
      — depends on T009, T010
- [ ] **T012** Retype the five elements and delete the three `BoolType` declarations:
      `script.xsd` (`autoload`, `enabled`, `timecode`), `network_map.xsd` (`adopted`, `online`),
      and `settings.xsd`'s **dead** declaration. Schema hashes in the same commit — depends on T011
- [ ] **T013** The boolean rewrite joins **`_script_1_to_2` and `network_map`'s 1 → 2**, one shared
      conversion, **no new version** (decision 3). It must be **order-independent with respect to
      the media elements** — it rewrites the text of five named elements and must not care whether
      `pixel_width` is present (plan.md §4) — depends on T012
- [ ] **T014** [P] Red-first: a version-1 document with old-form booleans **and** the four media
      elements converts correctly in one pass, in both orders of appearance. This is T013's
      order-independence, asserted
- [ ] **T015** Move **every** golden and out-of-band document the boolean form touches. ⚠ The first
      cut of this task said "six goldens"; **the measured count is fourteen goldens plus the nine
      out-of-band documents**, and the gap was eight **JSON** goldens — which are the *wire* form,
      i.e. precisely what X1 changes. Enumerated here so the red suite at T012 is planned for rather
      than discovered, and so nobody decides mid-implementation whether to regenerate: **FR-021
      stands — a golden is never regenerated to make a test pass.** Diff every file and confirm the
      change is only what was intended.

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
- [ ] **T016** Move the negative corpus with it. `tests/data/corpus/negative/` fixtures fail **for a
      reason**, and a schema change moves which error each one raises — execution doc §7.3 is the
      precedent, where a fixture kept failing while testing the wrong thing and the suite stayed
      green
- [ ] **T017** Update the contract tests whose premise X1 retires: `test_wire_booleans.py` (its
      whole docstring), `test_ui_payload_contract.py`'s boolean section, `test_enum_audit.py`
      (three rows), `test_schema_name_overlap.py:82` (`BoolType` leaves
      `KNOWN_IDENTICAL_DUPLICATES`). **Retire the premise deliberately, in the same commit, with
      what replaces it** — the 010 FR-029b discipline applied to a contract rather than a shim
- [ ] **T018** [P] Red-first then assert: the descriptor reports **`enum_values = None`** and a
      native boolean for all five fields. `baseline.md` §3 is the "before"; this is the acceptance
      criterion for the finding that decided X1, not a hoped-for side effect

**Checkpoint**: booleans are `xs:boolean` end to end — schema, adapter, conversion, goldens,
descriptor — and the wire carries JSON `true`/`false`.

---

## Phase 3: The public configuration ingestion (`cuems-editor` UR-5)

**Goal**: one public JSON → configuration-object call, symmetric with `CuemsScript.from_json`.

**Depends on Phase 2** — plan.md §9.2: build it against a descriptor that reports booleans
natively, not one that calls them a two-value string enum.

- [ ] **T019** [P] Red-first, per domain: `get_schema_descriptor(X).instance` → `from_json(X, …)` →
      `save_X()` → `load_X()` equals what went in. The loop §9.2 describes, asserted
- [ ] **T020** [P] Red-first: after ingestion `network_map`'s `adopted` is a `bool`, `node_role` a
      `NodeRole`, `uuid` a `Uuid` — **and the other three schemas' scalars are still `str`.** The
      second half is what catches an ingestion that "helpfully" coerces everywhere, which is the
      007 regression this feature must not cause
- [ ] **T021** [P] Red-first: `from_json(NETWORK_MAP, {… "adopted": true …})` is accepted and
      `"adopted": "True"` is **refused**. This assertion exists only because both changes land
      together; written against either alone it would be wrong
- [ ] **T022** Implement `ConfigManager.from_json(SchemaName, payload)` — three accepted forms
      (`str`, UTF-8 `bytes`, `Mapping`), decoding through **the same mapper call `load_*` uses**,
      returning the **object** `save_*` writes, not a dict. `doc_version` never expected. `script`
      and `hardware_outputs` keep their refusals — depends on T019–T021
- [ ] **T023** [P] Verify `cuems-editor`'s T059 closes by **re-run only**: its
      `test_config_save_of_settings_persists_through_save_settings` is `xfail(strict=True)` and must
      turn **XPASS**. Record it in [`migration-guide.md`](migration-guide.md). Do not edit that
      repository

**Checkpoint**: 62 of 63 becomes 63 of 63 in `cuems-editor` without a line changing there.

---

## Phase 4: Migration, measurement and the rule-4 release note

- [ ] **T024** Complete the rule-4 release note in
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
- [ ] **T025** Document the nine already-version-2 files and the out-of-band rewrite in the same
      note (plan.md §2.1). Version 2 is briefly ambiguous and the registry cannot resolve it; say
      so plainly rather than leaving it to be discovered
- [ ] **T026** Validate the three budgets in `baseline.md` §5 and record each, **including any that
      is exceeded — recorded as exceeded rather than restated as passing**
- [ ] **T027** [P] Re-measure the descriptor and the suite after Phase 2, and state whether removing
      three `simpleType`s and retyping five elements to a built-in helped, hurt or did neither.
      013's identified mechanism (`elementpath` rebuilding a node tree per `xs:alternative`
      evaluation) is **untouched** by this feature, so a flat result is the expected one
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

- [ ] **T028** [P] **`cuems-engine`** — 6 unmarked documents under `dev/test_xml_files/`, plus the
      **one already-version-2** file T015 owns
      (`dev/test_xml_files/projects/complex_test_v2/script.xml`; T015 rewrites it, this task
      verifies the result in place). **Measure in arms, not by inference** — the lesson 012 and 013
      each learned once, where the breakage was in *data* a call-site census cannot see: run at the
      branch point, after the library change, and after one conversion pass. ⚠ **The control arm is
      unavailable**: that candidate is coupled to feature 012 from `c31734c` onward
      (`coerce_identity` does not exist before it), so it cannot be tested against an older library
      to isolate a failure. Design the comparison **before** a run goes red
- [ ] **T029** [P] **`cuems-power-bridge`** — 10 unmarked documents,
      `tests/fixtures/network_map/map-*/settings.xml` and siblings. ⚠ **Expect it to be red before
      you start**: measured 2026-10-02 it was already **55 failed / 221 passed** against this
      branch, all of it 013's old device shape (183 `pre-013 device shape` refusals). **Reshape
      first, then convert** — that order, or neither completes. Its 276/276 green state predates 013
- [ ] **T030** [P] **`cuems-nodeconf`** — 1 unmarked document
      (`tests/fixtures/etc_cuems/settings.xml` and `settings_sentinel.xml` per 013's table). Also
      the one repository that **writes** `network_map.xml` every 30 s, so confirm its write path
      emits the new boolean form after the library moves — it is the only sibling whose output this
      feature changes
- [ ] **T031** [P] **`cuems-common`** — 2 unmarked documents. It ships `network_map.xml` and
      mirrors the schemas to `/etc/cuems`, so the **mirrored `.xsd` moves too**: a node with the old
      mirrored schema and the new library validates against the wrong file. Check
      `debian/` and whatever its postinst copies
- [ ] **T032** [P] **`cuems-editor`** — 4 unmarked documents, of which
      `tests/fixtures/script_minimal.xml` is **deliberately pre-013 and must stay that way** (its
      own `tests/fixtures/README.md` records why: it is the pre-migration payload capture *and* the
      `SKIPPED_INVALID` fixture). So this gate is **not** "convert everything" — it is "convert the
      three and confirm the fourth is still refused, for the right reason"
- [ ] **T033** Record every arm in [`baseline.md`](baseline.md), per repository, **including any
      that is still red and why**. A sibling left red with the reason named is a result; a sibling
      not run is not
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
      `file_hash`'s lowercase rule; `_Bool` as a **swap** rather than a deletion, with
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
