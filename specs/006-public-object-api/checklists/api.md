# API Surface Checklist: Public object API — one surface, internal machinery

**Purpose**: Validate that the public API is specified well enough to implement from — every
method's contract, its error behaviour, its deprecation counterpart, the byte-equality
evidence for `to_wire()`, and the boundary that keeps `xml/` symbols off the public surface
**Created**: 2026-08-18
**Feature**: [spec.md](../spec.md) · [contracts/public-api.md](../contracts/public-api.md) ·
[contracts/wire-format.md](../contracts/wire-format.md) ·
[contracts/deprecations.md](../contracts/deprecations.md)
**Depth**: Pre-implementation readiness — run before T001, by the author
**Scope**: C1 (`CuemsScript`'s six methods) **and** C2 (`ConfigManager`/`ConfigBase` accessors)

**Note**: This is a *unit test suite for the requirements*, not for the implementation. Each
item asks whether something is **specified**, not whether it works. A failing item means the
contract is underspecified and an implementer would have to guess.

## Public Method Contract Completeness (C1)

- [x] CHK001 Is the return type of all six public methods stated, including what `save()`
      returns and the precise shape `to_wire()` produces? [Completeness, Contracts §C1]
- [x] CHK002 Does any artifact state whether `to_wire()` validates before projecting, and is
      that answer made consistent with `to_json()`? The spec raises this question in Edge
      Cases and does not answer it. [Gap, Spec §Edge Cases]
      - **Resolved 2026-08-18 — it does NOT validate, and the consequence is documented.** Now
        **FR-005a** and a contract paragraph: a projection is not a gate, `save()` is; a
        partial object yields a partial payload rather than raising; a caller wanting a
        guarantee calls `validate()` first. Reason is measured — running T1 here would cost
        roughly the 15.49 ms the direct projection exists to avoid, against a 5 ms budget.
        Asserted by T022b.
- [x] CHK003 Is `to_json()`'s serialization form specified beyond "`json.dumps(to_wire())`" —
      separators, `ensure_ascii`, key ordering — given the output is transmitted and compared
      for equality? [Gap, Contracts §C1]
      - **Resolved 2026-08-18 — specified, not excluded.** Now **FR-005b** with a parameter
        table in C1: `separators=(", ", ": ")`, **`ensure_ascii=False`**, `sort_keys=False`.
        Pinned explicitly rather than inherited from `json.dumps` defaults, so a future stdlib
        change cannot move the bytes. `sort_keys=False` matters most — sorting would reorder
        the payload the UI receives, against W3.
      - **`ensure_ascii` reversed from an earlier draft** when the UTF-8 requirement landed
        (FR-036c). Both settings round-trip losslessly — `ç` and `ç` decode to the same
        codepoint — so this is a readability and payload-size choice, not a correctness one.
        `False` is the more direct reading: the transport is a UTF-8 WebSocket text frame.
- [x] CHK004 Are `from_json()`'s accepted input forms enumerated exhaustively (JSON string,
      decoded mapping) **and** the rejected forms named (bytes, a JSON array, a mapping that
      decodes to something other than a script)? [Coverage, Spec §FR-002]
- [x] CHK005 Is the `ValidationReport` shape specified precisely enough to document without
      reading its source — falsiness when empty, iteration, and each violation's field set?
      [Clarity, Contracts §C1]
- [x] CHK006 Is "location" on a violation defined for both cue-level rules and
      document-level rules, which have different natural addressing? [Ambiguity, Contracts §C1]
- [x] CHK007 Is `__hash__` specified alongside the declared-field `__eq__`? Defining equality
      alone makes the objects unhashable, which would silently break any consumer putting
      cues in a set or dict key. [Gap, Spec §FR-028b]
      - **Resolved 2026-08-18 — recovered, not added.** `Cue.__hash__` already exists
        (`Cue.py:314`, `hash(self.id)`) and stays **correct** under declared-field equality,
        because `id` is itself a declared field: equal-on-all-declared-fields ⟹ equal `id` ⟹
        equal hash. It becomes non-minimal (same-`id` cues collide), which is legal. Now
        **FR-028d**, and T029 requires preserving it.
      - **Second finding, larger than the item asked**: `Cue.__eq__` (`Cue.py:301`) compares by
        `id` **alone** today. FR-028b silently changes it. Now enumerated as **behaviour
        change 5** — the spec said "there are four".
- [x] CHK008 Does the copy requirement state whether it governs `copy.copy`,
      `copy.deepcopy`, or both? [Clarity, Spec §FR-028c]

## Error Behaviour Specification

- [x] CHK009 Is the exception **type** raised by `save()` on validation failure named, so a
      consumer can catch it rather than catching everything? [Gap, Spec §FR-004a]
      - **Resolved 2026-08-18** — `ValidationError`, carrying the **first** violation in the
        same form `validate()` reports it (FR-034b).
- [x] CHK010 Is the exception type raised by `load()` on a structurally invalid document
      named, and distinguished from the type raised on I/O failure? [Gap, Contracts §C1]
      - **Resolved 2026-08-18** — `SchemaError` for structural rejection; I/O failures are
        **not wrapped** and propagate as `OSError`/`FileNotFoundError` (FR-035), so the two are
        separately catchable without unwrapping.
      - **New public module**, `src/cuemsutils/errors.py`, holding `CuemsError`,
        `ValidationError`, `SchemaError`, `IngestError` (contract **C5**, T023a). This is the
        deliberate exception to the minimal-surface rule: a *returned* type can stay internal
        because the caller only inspects it, but an exception the caller cannot **name** is one
        it cannot **catch**. FR-022's enumerated diff grows by this module — T065 updated.
- [x] CHK011 Are `load()`'s I/O failure modes specified — missing file, unreadable file,
      well-formed XML that is not a script — separately from validation failure?
      [Coverage, Gap]
      - **Resolved 2026-08-18** by FR-035 and C5's table: I/O unwrapped, structural →
        `SchemaError`, not-a-script-at-all → `IngestError`. Asserted by T022a.
- [x] CHK012 Are `save()`'s filesystem failure modes specified distinctly from validation
      failure — parent directory missing, permission denied, failure *during* the write —
      given FR-003 promises no truncation? [Coverage, Gap, Spec §FR-003]
- [x] CHK013 Is "an actionable message naming what was expected" measurable — is there a
      stated criterion for what makes a `from_json` error message acceptable, and is the
      logging requirement for dropped unknown keys specified as to level and record content?
      [Measurability, Spec §Edge Cases, Contracts §C1]
- [x] CHK014 Is the `validate()`-reports / `save()`-raises asymmetry stated identically in
      spec.md and contracts/public-api.md, with no room to read one as overriding the other?
      [Consistency, Spec §FR-004/FR-004a, Contracts §C1]
- [x] CHK015 Are error requirements defined for `to_wire()`/`to_json()` on a partially
      populated or never-validated object, or is the absence of failure modes stated
      deliberately rather than by omission? [Gap, Coverage]

## Deprecation Counterpart Coverage

- [x] CHK016 Does every entry point in the migration map have exactly one stated
      replacement, with any "nothing" mapping justified rather than left blank?
      [Completeness, Contracts §D2]
- [x] CHK017 Is the deprecated set stated consistently between C3 (six names removed) and
      SC-005 (five names exported today)? `CuemsParser`'s public status *before* this feature
      is not stated, and the two counts cannot both be right without it.
      [Conflict, Spec §SC-005, Contracts §C3]
      - **Resolved 2026-08-18 — both numbers are right, they count different things.**
        `__all__` holds exactly **5** names (SC-005 correct, unchanged). **6** supported entry
        points are removed, the sixth being `CuemsParser`, which was never in `__all__` but is
        reached by dotted path. C3 now states both counts in a table.
      - **Conflict found while checking**: feature 004 deliberately made `CuemsParser`
        non-deprecated and **silent**, and contract C8
        (`tests/contract/test_no_internal_deprecation.py`) asserts that silence while the
        library calls it internally. Deprecating it in 006 fails C8 unless the two internal
        callers move first → new task **T061a**.
      - **Still open, minor**: D2 says `CuemsParser` has "3 sites" in `cuems-editor`;
        `Parsers.py` says "five call sites" in two places. One is stale — needs a count against
        the editor repo, deferred to the feature 008 migration guide (T084).
- [x] CHK018 Is the warning **category** specified (`DeprecationWarning` vs
      `FutureWarning`)? Consumers filter by category, and the quickstart assumes
      `DeprecationWarning` without the contract saying so. [Gap, Contracts §D1]
- [x] CHK019 Is "one release" bound to a concrete version — is the release this feature ships
      in named, alongside the existing `REMOVAL_RELEASE = "v0.1.1"`? [Clarity, Spec §Assumptions]
- [x] CHK020 Are requirements stated for a shim whose replacement **changes shape** — the
      `read()` → `to_wire()` counterpart drops `schemaLocation`. Does the deprecated path
      return the old dict or the new one? [Gap, Ambiguity, Contracts §D2]
      - **Resolved 2026-08-18 — the shim returns the NEW shape** (drops the key), and its
        warning carries an *additional* note saying so. Now **contract D2a**. Implemented as an
        optional `note` parameter on the existing `deprecation_reason()`, so there is still one
        function producing every message in the package and every other message is unchanged
        (T061).
- [x] CHK021 Is the criterion separating D3's outright deletions from deprecations ("nothing
      outside the package could reach them") stated in a form that can be checked, rather
      than asserted? [Measurability, Contracts §D3]

## Byte-Equality Evidence for `to_wire()`

- [x] CHK022 Is "byte-identical" **defined** for a dict comparison — structure, scalar type,
      key order — rather than borrowed as a metaphor from the XML goldens where bytes are
      literal? [Ambiguity, Spec §FR-009, Contracts §W1]
- [x] CHK023 Is key order stated as part of the equality predicate, and is that consistent
      with the recorded fact that decode preserves *arrival* order while declared order
      differs? W3 says "key order is unchanged" without saying unchanged *from what*.
      [Conflict, Contracts §W3]
- [x] CHK024 Is the corpus subset the byte-equality claim covers stated precisely, with the
      document count recorded, so "100% of corpus script documents" is checkable rather than
      aspirational? [Measurability, Spec §SC-001]
- [x] CHK025 Is the relationship between this feature's byte-equality claim and feature 005's
      **unresolved** 14 type differences stated, so SC-001 is not silently inherited as
      already met? [Gap, Conflict]
- [x] CHK026 Is the round-trip oracle stated as a *requirement* in the spec, or does it exist
      only in research.md and the contract — given it is the entire reason the direct
      projection is considered safe? [Traceability, Contracts §W7]
- [x] CHK027 Is the standard of evidence for "no consumer reads `schemaLocation`" specified —
      which repositories, which branches, and what counts as proof of a negative?
      [Measurability, Spec §FR-011]
- [x] CHK028 Are wire-format requirements stated for **config** documents, or is their
      exclusion from the wire contract made explicit? The contract covers script documents
      only. [Coverage, Gap]
      - **Resolved 2026-08-18 — specified, and scope grew: config objects GET a `to_wire()`.**
        Now **FR-014a**, contract **W8**, SC-017, tasks T043a/T043b/T056a/T056b. Rationale is
        forward-looking: opening configuration files to the UI is planned follow-on work, and
        building the projection once, here, is what stops a second parallel definition being
        written then — the exact drift mechanism behind F15's three incompatible mappings
        shapes.
      - Cheap to build (`encode_wire` is already schema-generic and the config types become
        registry-bound here anyway) and **testable immediately with no new evidence**: the
        byte-identity target `tests/golden/dict/*.config.json` already exists, captured
        pre-feature by the same harness as `*.reader.json`. No golden is regenerated.
- [x] CHK029 Is the payload-parity claim scoped to a stated set of fields or documents, so
      "0 differing fields" is a checkable number? [Measurability, Spec §SC-003]

## Public Surface Boundary — no `xml/` symbol reachable

- [x] CHK030 Is "the `xml` package exports nothing" defined as `__all__ == []` or as genuine
      unreachability? `from cuemsutils.xml.mapper import Mapper` stays importable under the
      first reading, and the requirement does not say which it means.
      [Ambiguity, Spec §FR-019]
- [x] CHK031 Is there a stated rule for `xml/`-defined types reaching consumers **as return
      values** rather than as imports — the `ValidationReport` case? The contract now records
      the decision; the spec's FR-019 does not state the general rule.
      [Gap, Contracts §C1]
- [x] CHK032 Is "public name" defined for the API golden's purposes — module attributes,
      class methods, dunders, inherited members — and is the enumerated set FR-022 requires
      the diff to equal written down as one explicit list rather than distributed across the
      spec? [Clarity, Gap, Spec §FR-022]
- [x] CHK033 Is the requirement that the two `_shim` imports survive stated as a
      **requirement**, or does it live only in a code comment, a research note and a task
      description? A constraint that has already broken once should be traceable to a
      requirement. [Traceability, Contracts §D1]
- [x] CHK034 Is there a stated requirement that no public **signature** accepts a schema
      name, distinct from the measured count SC-004 reports? [Traceability, Spec §FR-021/SC-004]

## Config Accessor Surface (C2)

- [x] CHK035 Is the complete inventory of accessor names existing today **recorded**, so
      FR-018's "every name that exists today must continue to exist" is verifiable rather
      than merely assertable? [Measurability, Spec §FR-018]
- [x] CHK036 Is the split between accessors that change return type and those that stay
      scalar stated **per accessor**, rather than as the rule "only where the value is a
      structure"? [Clarity, Spec §FR-018, Contracts §C2]
      - **Answer relocated 2026-08-18, after `/speckit.analyze` found the prose still listing
        accessors in groups** ("and the project settings/mappings accessors"), with counts
        disagreeing across artifacts (~15 vs ~18). A per-accessor list maintained by hand is
        the same drift this feature exists to close. The authoritative split is now the
        **recorded inventory** `tests/golden/api/config_accessors.json` (T040a), generated by
        introspection before any US3 change; Contracts §C2 points at it and FR-018 is asserted
        against it. T040a is sequenced ahead of every other US3 task for this reason.
- [x] CHK037 Are error requirements defined for config accessors when the underlying file is
      missing, unreadable, or fails schema validation — including the measured X13 case where
      a schema gained a required element? [Gap, Coverage, Spec §Edge Cases]
      - **Reopened and properly closed 2026-08-18.** `/speckit.analyze` found this item checked
        while only the X13 half had an answer anywhere — nothing covered a **missing or
        unreadable** config file, and no task tested any of it. Now **FR-014b** and Contracts
        §C2's error table: missing/unreadable → unwrapped `OSError`, matching FR-035's posture
        on the show side; schema-invalid → `SchemaError` naming the element. A node with no
        config and a node with a corrupt one are different operational problems and must not
        arrive as one exception. SC-020 measures it; T039a asserts it.
- [x] CHK038 Is "no accessor returns a raw nested dict" measurable, given some values are
      legitimately dict-shaped (`ui_properties`, wildcard content)? [Measurability, Contracts §C2]
- [x] CHK039 Is the 006/007 boundary for `node`/`node_list` stated in the spec itself, or only
      in data-model.md — given FR-014 requires typed objects **here** and D11 assigns the
      model to 007? [Traceability, Gap, Spec §FR-014]

## Cross-Artifact Consistency, Assumptions & Residual Gaps

- [x] CHK040 Do spec.md, contracts/ and tasks.md agree on which artifacts are deliverables —
      the schemaLocation evidence, the migration guide, the frontend note, the schema
      evolution convention — with none named in one and absent from another? [Consistency]
      - **Scope widened 2026-08-18**: `/speckit.analyze` found `plan.md`'s documentation tree
        stale — it listed only `checklists/requirements.md` (omitting this file, which spec.md
        cites) and predated all eight implementation-produced artifacts. The audit set is now
        spec.md, plan.md, contracts/ **and** tasks.md; plan.md carries the full list explicitly,
        and T089a checks it.
- [x] CHK041 Is the performance budget's measurement context specified — hardware, warm vs
      cold, sample count, which document — so "≤ 25 ms" is reproducible by someone other than
      its author? [Measurability, Spec §FR-PERF-001]
- [x] CHK042 Is there a stated requirement for what happens if the "no consumer reads
      `schemaLocation`" assumption proves **false** when the evidence is gathered? The
      assumption is load-bearing for an enumerated behaviour change. [Assumption, Gap]
- [x] CHK043 Are concurrency requirements stated for projecting a script while the engine
      mutates its cues? `save()` is defined as safe mid-show; `to_wire()` on a live document
      is not addressed. [Gap, Coverage]
      - **Closed 2026-08-18 as out of scope, by decision rather than omission.** Now an Edge
        Cases entry: explicitly **undefined**, documented as the caller's responsibility. The
        library never observes playback (FR-028a), so acquiring a lock here would contradict a
        requirement rather than satisfy one.

## Notes

- Check items off as completed: `[x]`
- Record findings inline under the item, and promote anything material into spec.md or the
  relevant contract — this checklist is a **finding instrument**, not a place for the answer
  to live
- 43 items; 40 carry a traceability reference (93%)
- **All 43 resolved 2026-08-18.** Findings are recorded inline where the item turned up
  something; the answers themselves live in spec.md and contracts/, never here
- **One item was checked without an answer, and `/speckit.analyze` caught it**: CHK037 was
  marked resolved while nothing in spec.md or contracts/ covered a missing or unreadable config
  file. Recorded here as the instrument's own failure mode — a checklist item is closed by the
  answer existing somewhere citable, not by the box being ticked. CHK036 and CHK040 were
  narrowed and widened respectively for related reasons; see their inline notes
- **3 closed as out of scope by decision, not omission** — CHK025 (005's 14 residual type
  differences → feature 008), CHK030 (genuine `xml/` lockdown → feature 008), CHK043
  (concurrency → undefined, caller's responsibility). Each is now an explicit **Out of Scope**
  entry in spec.md rather than a silence

### Where each cluster landed

| Items | Resolution |
|---|---|
| CHK001, 004, 005, 006, 008 | New **C0 signature table**; `from_json` inputs enumerated with rejections; `ValidationReport` field table; `location` defined as a `(cue_id, field)` pair so nothing has to be parsed out of a string; copy covers both `copy` and `deepcopy` |
| CHK012, 013, 014, 015, 016 | C5 covers the types; `save()`'s filesystem modes stated against the tmp+rename design; `from_json`'s message criterion is *names the expected root and what arrived*; drop-key logging at `DEBUG`; CHK015 answered by FR-005a |
| CHK018, 019, 021 | D1 gains a table: category is `DeprecationWarning`; `__version__` is `0.1.0rc14` so shims ship **v0.1.0** and go **v0.1.1**; D3's deletion criterion **is** T060's coverage proof |
| CHK022, 023, 024, 026, 027, 029 | New **W1a** — one equality predicate for every byte-comparison in the feature (T003a), with key order defined **against the golden** to sidestep the arrival-vs-declared ambiguity; corpus count recorded (T003); evidence standard stated (T038) |
| CHK030, 031, 032, 033, 034, 036, 037 | FR-019a/b/c: `__all__ == []` only, dotted access unsupported-but-functional, lockdown → 008; the return-value-vs-import rule stated generally; "public name" defined and the expected diff written as one list (T057a); the shim imports promoted from comment to requirement |
| CHK035, 038, 039, 040, 041, 042 | Accessor inventory recorded pre-change (T040a); "no raw dict" defined as `type(v) is not dict`; 006/007 boundary lifted into the spec; artifact audit (T089a); perf context stated (T083); positive-evidence contingency stated (T038) |

### Added after the checklist: UTF-8 (FR-036…FR-036e, contract C6)

Not a checklist finding — raised separately — but it exposed the same class of gap the
checklist was built to find. **The corpus contains zero non-ASCII bytes**, documents and
goldens both, measured 2026-08-18. So nothing today could catch an encoding regression.

- The existing writer is already correct (`encoding="utf-8", xml_declaration=True`), and no
  `open()` in `src/` omits an encoding. The risk is **T028's new atomic write** dropping it.
- The failure is environmental, not programmatic: `open()` without `encoding=` uses the
  platform default, which under `LANG=C` is ASCII — so a show file with an accented cue name
  saves on a developer laptop and raises `UnicodeEncodeError` on the node. Review cannot catch
  it, because the source line looks identical either way. Hence T022d runs under `LC_ALL=C`.
- Closed here rather than recorded, unlike the eight unexercised `FadeCue` rules: cheap to
  exercise, and its failure mode reaches production without passing through a test.
- CHK031 records a rule this session settled for `ValidationReport` but which FR-019 still
  does not state in general terms

### What the resolved items changed

| Artifact | Change |
|---|---|
| spec.md | FR-005a, FR-005b, FR-014a, FR-028d, FR-034/a/b, FR-035/a; SC-017, SC-018; **behaviour change 5** (cue equality widens from `id`-only); two Edge Cases answered |
| contracts/public-api.md | C3 two-count table + the C8 sequencing constraint; `to_wire()`/`to_json()` non-validating and pinned form; config projection under C2; **new C5 — Errors** |
| contracts/wire-format.md | **new W8** — config documents project through the same engine; two W7 verification rows |
| contracts/deprecations.md | **new D2a** — the `read()` shim returns the new shape and says so in its warning |
| tasks.md | +8 tasks: T022a, T022b, T023a, T043a, T043b, T056a, T056b, T061a; T024–T028, T029, T061, T065, T086 amended. **91 → 99** |

### Two findings that outgrew the item that found them

1. **Cue equality was silently changing.** CHK007 asked about `__hash__` and found that
   `Cue.__eq__` compares by `id` alone today, so FR-028b was an unenumerated behaviour change
   in a spec that says "there are four". Now five.
2. **Deprecating `CuemsParser` breaks a landed contract test.** CHK017 asked about a count and
   found that feature 004 made `CuemsParser` deliberately silent, with contract C8 asserting
   that silence while the library calls it internally. T061a moves the two internal callers
   first, so C8 is satisfied rather than amended.
