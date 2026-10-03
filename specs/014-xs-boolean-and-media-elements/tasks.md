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

- [ ] **T001** [P] Red-first: a `MediaType` document carrying all four new elements validates, and
      one carrying none of them still validates. Add the fixtures under `tests/data/corpus/`;
      neither exists today
- [ ] **T002** [P] Red-first: the range and the refusals, per plan.md §10.1 — `file_size` accepts
      `107374182400` (100 GiB) and `9223372036854775808`, and **refuses** `0` and `-1`; the same
      refusals for the pixel pair. This is the test that pins the >100 GB requirement against a
      future "let's make it `xs:long`"
- [ ] **T003** [P] Red-first: `file_hash` accepts 32 lowercase hex and refuses uppercase, 31
      characters, 33 characters and non-hex (plan.md §10.2). The uppercase case is the one that
      records the decision rather than the mechanism
- [ ] **T004** Add the four elements to `script.xsd`'s `MediaType` after `regions`, all
      `minOccurs="0"`, plus the new `cms:Md5HashType`. **Update `CURRENT_SCHEMA_HASHES` in
      `tests/contract/test_schema_scope.py` in the same commit**, with the reason in the message —
      that pairing is the whole mechanism (execution doc §7.5) — depends on T001–T003
- [ ] **T005** Four `DECLARED_DEFAULTS` entries (**all `Unset`**) and four `set_<name>` accessors on
      `Media`. Both halves or the key is dropped in silence (plan.md §10.4) — depends on T004
- [ ] **T006** [P] Red-first then implement: `test_coherence.py` must agree that `MediaType`'s
      schema fields and `Media`'s model fields match. It fails automatically on T004 without T005,
      which is the check working; confirm that, do not route around it
- [ ] **T007** Cherry-pick `9c17418` from `origin/main` for `ease_in`/`ease_out` on
      `FadeCurveType`, with its schema hash moving in the same commit. Verified absent from this
      branch: a project saved by a `main`-line editor with an `ease_in` fade **fails T1 here today**
- [ ] **T008** [P] Record in [`migration-guide.md`](migration-guide.md) that the media block is
      **four** elements and why (`file_hash` added, `file_size` named not `size`, `0` invalid by
      design), so `cuems-editor` and `cuems-engine` read one statement rather than inferring from
      the input document's three

**Checkpoint**: the schema admits four new optional elements and two new curve values; nothing on
disk is invalidated; no conversion exists yet because none is needed.

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
- [ ] **T015** Re-cut the **six** goldens (`tests/golden/xml/` ×5, `tests/golden/generated/` ×1) and
      hand-rewrite the **two** already-version-2 corpus documents the registry cannot reach
      (`fade_showcase`, `unicode_showcase`). **Diff every file to confirm the change is only what
      was intended** — FR-021 stands: a golden is never regenerated to make a test pass
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

- [ ] **T024** The rule-4 release note in [`migration-guide.md`](migration-guide.md) — the one
      deliverable `specs/agreements/schema-evolution-convention.md` demands that cannot be inferred
      from anything else: **what has to be converted, and when the old form stops being accepted**.
      Rule 4's own sentence is the standard to meet — *"'We will just update the files on the nodes'
      is not a conversion path. Nobody knows where all the files are"*
- [ ] **T025** Document the nine already-version-2 files and the out-of-band rewrite in the same
      note (plan.md §2.1). Version 2 is briefly ambiguous and the registry cannot resolve it; say
      so plainly rather than leaving it to be discovered
- [ ] **T026** Validate the three budgets in `baseline.md` §5 and record each, **including any that
      is exceeded — recorded as exceeded rather than restated as passing**
- [ ] **T027** [P] Re-measure the descriptor and the suite after Phase 2, and state whether removing
      three `simpleType`s and retyping five elements to a built-in helped, hurt or did neither.
      013's identified mechanism (`elementpath` rebuilding a node tree per `xs:alternative`
      evaluation) is **untouched** by this feature, so a flat result is the expected one
- [ ] **T028** Measure the siblings in arms, not by inference — the lesson 012 and 013 each learned
      once: `cuems-engine`, `cuems-power-bridge`, `cuems-nodeconf`, `cuems-common` fixtures carry
      **51 unmarked + 1 version-2** boolean documents between them. ⚠ The engine's control arm is
      **unavailable** (its candidate is coupled to 012 from `c31734c`), so design the comparison
      before a run goes red, not after
- [ ] **T029** Record the frontend hand-off: `cuems-frontend`'s 001 began its SDD path 2026-10-03,
      and its `sequence.component.ts:997` is **mutually** hard-coupled to this feature (plan.md
      §6.2 item 2). 014 can be implemented and tested without it; it cannot **ship** without it.
      Update that repository's `06-amendment-feature-014.md` status line only if asked — it is
      their document now
- [ ] **T030** Delete `../planning/booltype-silent-false-coercion-defect.md` once this feature
      lands, on the `dmx-universe-channel-conversion-defect.md` → `specs/009-*/` precedent. **Not
      before**: it is the record of why the work exists until the work exists

---

## Dependencies

```
Phase 1 (additive)      independent — can land alone
Phase 2 (X1)            T009,T010 → T011 → T012 → T013 → T014; T015,T016,T017,T018 after T013
Phase 3 (ingestion)     after Phase 2 (descriptor must report booleans natively)
Phase 4 (migration)     after the phases it measures
```

**Parallel within a phase**: tasks marked `[P]` touch different files and may run together.

**The one thing this order must not permit**: T012 before T011. Retyping the schema while the
adapter still writes `"True"` makes every save fail, because `save` validates before writing — the
same mechanism plan.md §1.3 uses to argue `_Bool` cannot be deleted.
