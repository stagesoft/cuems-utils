# Feature Specification: Rebuild extension — one timecode type, a complete config surface, a self-describing schema, and a document lifecycle

**Feature Branch**: `008-rebuild-extension`
**Created**: 2026-08-27
**Status**: Draft — no open questions. Q1 (repair-default semantics) answered 2026-08-27; see
Clarifications. Ready for `/speckit.clarify`, which §7.1 designates as not-skippable for this
feature regardless.
**Input**: Ship five structural changes as one coordinated feature, in dependency order:
timecode typing, config object write paths, the network-map config object, the schema-derived
descriptor, and validate-on-load with document versioning and repair. One feature, two gated
phases: ITEMs A–D land and go green before any ITEM E work starts.

**Planning context** (authoritative, read before planning):
`specs/planning/xml-rebuild/xml-rebuild-01-audit.md` (findings F1–F23, schema audit X1–X12),
`specs/planning/xml-rebuild/xml-rebuild-02-node-model-ownership.md`,
`specs/planning/xml-rebuild/xml-rebuild-03-design-inputs.md` (design constraints, Q11/Q14 rationale),
`specs/planning/xml-rebuild/xml-rebuild-04-object-model.md` (construction paths, measured divergence),
`specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md` (editor↔UI payload contract),
`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` (the target design),
`specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md` §7 (this feature's prompt) and §10 (standing rules),
`specs/planning/xml-rebuild/xml-rebuild-08-extension-audit.md` (**this feature's charter** — evidence E1–E26;
read the revision note first: five findings of the first draft were wrong and are corrected there).

This is feature 5 of 6 in the XML rebuild, inserted after 007 by decision on 2026-08-25: the
rebuild's scope grows *before* consumer migration starts, because several more structural changes
are cheaper as one coordinated pass now than as independent releases later. Feature 009 (consumer
migration) follows and is out of scope here — but is a **hard successor**, not a follow-up (D27).

**Settled decisions** (from the planning phase — not reopened by this spec): D1, D2, D5, D9, D11,
D12, D13, D14, D15, D16, D17, D18, D18b, D19, D20, D21, D22, D23, D24, D25, D26, D27, D28, D29,
D30, D31, Q11→(c), Q14→(i).

**D3 is deliberately relaxed, four times more.** "Wire-compatible with every XML on disk; no
`.xsd` edits" no longer binds any schema absolutely, and the relaxations granted here are of two
distinct characters that must not be conflated:

- **Second exception — `settings.xsd`** (D18): its `CTimecodeType`/`TimecodeType` pair, unreachable
  from any element and wrongly patterned `HH:MM:SS:FF`, is deleted. No document on disk changes.
- **Third exception — `script.xsd`** (D17/D18b): `Media.duration` is promoted from
  `cms:TimecodeType` to `cms:CTimecodeType`. It **changes documents already on disk** — as D18b
  recorded, the only one of the rebuild's first three exceptions to do so — and is granted on the
  condition that the conversion path (ITEM E) carries it. The exception and its migration are one
  decision, not two. The fifth exception below joins it in that category; the fourth does not.
- **Fourth exception — all six schemas, for the version marker** (Clarifications, 2026-08-27): each
  root type gains one **optional attribute** carrying the document's format version. Standing rule 6
  requires a fourth relaxation to have its own decision record; this is it. Its character is
  different from the other three and from 007's: it is **purely additive and breaks nothing**. An
  optional attribute invalidates no document on disk — every existing file simply lacks it, which
  FR-050 defines as the oldest version. This is precisely the case the schema-evolution convention's
  rule 1 already sanctions for elements; the marker extends that sanction to attributes.

- **Fifth exception — `script.xsd`'s `ActionType`** (Clarifications, session (c)): the enumeration
  values `fade_in` and `fade_out` are deleted, superseded by `fade_action` since feature 003. Like the
  third, this is a **narrowing** change that invalidates documents already on disk, and it is granted
  on the same condition — that ITEM E's conversion carries it (FR-051a).
- **Sixth exception — `script.xsd`'s fade-profile surface** (Clarifications, session (d)):
  `FadeProfileType`, `FadeProfilesWrapperType`, `FadeParameterType` and the `fade_profiles` element on
  `AudioCueType` and `VideoCueType` are **deleted**. Also a narrowing change, granted on the same
  condition (FR-051c). Its justification differs from the second exception's and the difference is
  recorded rather than blurred: `settings.xsd`'s dead pair was **unreachable from any element**, while
  the fade-profile surface **is** reachable — from two cue types — but is consumed by nothing outside
  this repository (FR-007b).

Each relaxation is scoped to the one file and change it names; a seventh needs its own record. Counted
honestly, that is **two files edited across five changes**, plus one optional attribute added to all
six roots — not six unrelated schema rewrites. Three of the five are deletions of things nothing
honours; one is the version marker, which breaks nothing; only `Media.duration` changes a live
field's meaning.

**The relaxations are a proper part of this feature — decided, not conceded.** Recorded on the repo
owner's explicit sign-off, 2026-08-27, after the count was put to them as five in one feature.

D3 was adopted to stop schema work leaking into a serialization rebuild. What makes these five a
coherent part of the work rather than an erosion of the rule is that **this is the feature that builds
the conversion machinery**. D3's real purpose was never "never edit a schema"; it was "do not edit a
schema while there is no path for the documents that edit invalidates." After ITEM E there is one, and
three of the five changes are the first things that path exists to carry.

Their characters differ and the difference is the argument:

| Change | Character | Documents on disk |
|---|---|---|
| `settings.xsd` timecode pair | deletes what is unreachable | untouched |
| `ActionType`'s two values | deletes what nothing honours | converted |
| fade-profile surface | deletes what nothing outside this repo consumes | converted |
| version marker | adds what breaks nothing | untouched |
| `Media.duration` | **changes a live field's meaning** | converted |

Only the last one alters something the system actually uses. The other four are the schema catching up
with what was already true.

**What this precedent does not do.** It does not reopen D3 for the deferred schema items (X1–X13),
which stay deferred; it does not license a schema edit in a feature without a conversion path; and it
does not extend past this feature. A seventh exception needs its own record on its own merits.

---

## Why this feature exists

Four of the five items close a gap that 004–007 exposed but did not have standing to fix. The
fifth turns a documented aspiration into a mechanism.

**One kind of value, two typings.** `script.xsd` declares six elements of type `cms:CTimecodeType`
— `offset`, `postwait`, `prewait` on a cue, `in_time`/`out_time` on a region, `duration` on a fade
— and all six already store `CTimecode` objects through one shared coercion helper (E1, E2). A
**seventh** element carries a time value and does not: `Media.duration` (`script.xsd:182`) is typed
`cms:TimecodeType`, a pattern-restricted string, and its setter stringifies deliberately. That was
a recorded choice (task T073) made to avoid disturbing a consumer call site. It leaves one class of
value with two representations, two setter paths, and a three-branch type dispatch that exists only
to bridge them.

**Five schemas, one write path.** Grepping `def save` across the configuration surface finds exactly
one config-domain writer: `CuemsNetworkMapType.save()` and its `ConfigManager` accessor, both new in
007 (E15). `settings`, `project_settings` and `project_mappings` can be read and cannot be written.

**A config object that lives on a daemon.** The network map's domain logic — merge discovered nodes,
adopt, unadopt, refresh, controller-always-adopted, missing-adopted check, change signature — is
reimplemented ad hoc on `cuems-nodeconf`'s 756-line `CuemsNodeConf` class, one of ten responsibilities
bundled there (E11, E12). In `cuems-utils`, `NodeIndex` is a three-method `dict` subclass and
`CuemsNetworkMapType` has only `save()`. The schema lives here; the logic that maintains documents
of that schema does not.

**Two hand-maintained templates and a contract nothing enforces.** `create_script()` hand-builds one
literal instance of every cue type, runs it through full construction and validation, **then** blanks
its ids — so the object actually served to the editor is one that would fail its own check, and its
dangling `action_target` is exactly what `cuems-editor`'s `_clean_dangling_targets` exists to sweep
up (E16, E18: one causal chain documented in three disconnected places). `templates/settings.xml` is
5.1 KB of hand-written reference instance that `settings.xsd`'s own header declares a binding
contract — and which no code, no test and no package references (E26). Meanwhile the schema-derived
engine already knows every field's shape but neither its legal value set nor its default (E17).

**Rule 4 was adopted and never built.** The schema-evolution convention (adopted in 006) calls for
"a version marker that lets a reader tell old from new; a conversion that runs on read, or a
documented tool that runs once." No schema anywhere carries a version marker (E8). 007 satisfied
rule 4 with an *implicit* structural tell — a document has either `<node_type>` or `<node_role>` —
which worked for that one change and generalises to nothing (E9). ITEM A now needs the real
mechanism, because promoting `Media.duration` invalidates **every `script.xml` in every library** the
moment it lands (E24). The versioning machinery is therefore not parallel infrastructure: it is how
ITEM A reaches existing installations at all.

**And reading must become recoverable, not merely stricter.** `load()` runs T1 and deliberately skips
T2 today, on the principle that "reading never becomes stricter" (E7) — asserted independently in
004, 005 and 006. Reversing it naively would make every corrupt document unloadable, which breaks the
tools that repair corrupt documents, since every one of them is a `load()` consumer (E18, E21).
Hence three outcomes, not two.

---

## The phase gate (D30, D31)

This is **one feature**: one `spec.md`, one `plan.md`, one `tasks.md`, one feature number, one
migration guide. The five items are one dependency chain and one release unit; splitting the spec
would mean reviewing that chain twice from two half-views.

It **lands in two gated phases**, split at the A–D / E seam:

| Phase | Items | Character |
|---|---|---|
| **Phase 1** | A, B, C, D | Four bounded changes to machinery that already exists and can be reviewed against it |
| **Phase 2** | E | One new subsystem whose central mechanism is still undesigned (E10), and which is on its own larger than 007 |

**Phase 1 must be merged and green before any Phase 2 task starts.** The rule that applies between
features applies once inside this one.

What the gate buys, beyond a smaller diff: Phase 2 is written against ITEM B's `save()` and ITEM D's
descriptor **as landed code** rather than as planned interfaces — which is the entire reason D28
ordered them first — and if ITEM E's undesigned mechanism turns out larger than the plan assumed,
that is discovered with four items already merged instead of with the whole feature in flight.

**What the gate is not.** It is not a release boundary. D27 holds unchanged: nothing in the ecosystem
ships until feature 009 lands, despite this feature touching no consumer repository directly. And it
is not a scope split — every acceptance criterion below belongs to the same feature.

Every ITEM A–D acceptance criterion in this spec is written to be judgeable **with no part of ITEM E
in the tree**. Any criterion that needs validate-on-load, versioning or repair to be true belongs to
Phase 2 and is stated there.

---

## The item order is a dependency chain (D28)

Not a preference, and not to be re-sequenced for throughput:

```
A  timecode typing          defines the new wire
   ↓                        (and creates the migration E's marker must carry)
B  config write paths       upgrade-and-rewrite and repaired-document saves both WRITE
   ↓                        (three of four config domains cannot today)
C  network-map object       completes the config surface the load path reads and writes through
   ↓
D  schema descriptor        supplies the DEFAULTS the repair path recovers to
   ↓                        (hand-written per-field fallbacks would recreate the drift it ends)
E  validate-on-load,        consumes all four
   versioning, repair
```

Two couplings make the order non-negotiable: ITEM E's upgrade-and-rewrite path writes through ITEM B's
`save()`, and ITEM E's repair-to-default reads ITEM D's defaults and its repairability classification.
Neither is optional plumbing.

---

## Clarifications

### Session 2026-08-27 (a) — during `/speckit.specify`

- **Q: What does "a default state" mean per field for repair-and-notify (D21's middle row)?** The
  descriptor's declared default is the source of truth (FR-045), but for some fields substituting a
  default *changes meaning* rather than restoring it: a dangling `action_target` repaired to `None`
  is a real semantic change, not a recovery, and `cuems-editor` today sweeps exactly that case up
  outside any object contract (E18). The two naive answers both fail — repairing everything makes a
  broken reference silently look valid, and raising on everything means the first-party repair tools
  cannot open the documents they exist to fix (E21).
  → **A: the descriptor carries a per-field repairability classification** (FR-031a). A field
  classified repairable takes D21's second outcome — recovered to its descriptor default and
  reported. A field classified unrepairable takes the third — it raises. Both outcomes stay reachable
  and the choice between them stays **schema-derived**, consistent with FR-045's prohibition on
  hand-written per-field tables. The cost is one further attribute on ITEM D's emitted structure.

  This makes the boundary between D21's second and third outcomes a **Phase 1 deliverable consumed
  by Phase 2**, which is the phase gate working as intended: Phase 2 reads a classification that is
  already landed code rather than negotiating it mid-implementation.

### Session 2026-08-27 (b) — `/speckit.clarify`

Five questions, grouped below by what they settle rather than by the order asked. Two of them — the
backup pair — corrected over-reach this spec had introduced on its own initiative rather than
inherited from the planning decisions.

- **Q: Where does the document-version marker live, and at what granularity?** No schema declares
  `anyAttribute` or a root wildcard — the only attribute in all six schemas is `universe_num`
  (`script.xsd:431`) — so a marker attribute cannot merely be written, it must be **declared**. That
  makes placement a fourth D3 relaxation, which standing rule 6 requires a decision record for.
  → **A: an optional attribute on each schema's root type, versioned per schema** (FR-048a, FR-048b).
  Rejected alternatives, with the reason each lost: a **single ecosystem-wide counter** would age
  every domain's documents whenever any one schema moved — ITEM A is a `script.xsd` change, and a
  shared counter would mark `network_map`, `settings`, `project_settings` and `project_mappings`
  documents stale, forcing four conversions that convert nothing. A **processing instruction** avoids
  the `.xsd` edit entirely, but stdlib `ElementTree` discards processing instructions unless a
  non-default parser target is configured, and the read path runs through `xmlschema` rather than
  ElementTree directly — writable easily, readable only fragilely. A **dedicated child element**
  enters the content model, where required is breaking and optional still shifts element ordering,
  and it would behave differently per schema because `CuemsScript`'s root is `xs:all` while the
  others are `xs:sequence`.

- **Q: Where does the repairability classification's value come from?** The schemas declare **no** `xs:keyref`
  anywhere — only two `xs:unique` constraints, both in the DMX types — so a referential field like
  `action_target` is not mechanically identifiable from the schema, and the case that motivated the
  question cannot be derived structurally.
  → **A: from the registered semantic-rule surface** (FR-031b). Every repair is triggered by a T2 rule
  firing, so the rule is where the knowledge already lives; each rule declares whether its own violation
  is repairable and the descriptor exposes that against the field the rule targets. **15 rule
  declarations to maintain rather than ~200 field annotations** — and an annotation nobody maintains is
  the drift the descriptor exists to end. Rejected: per-field model-layer annotation (the ~200-field
  surface), structural derivation (would be a name heuristic guessing at the one case that matters), and
  default-presence-plus-override-list (the override list is the hand-written field-name table FR-045
  prohibits elsewhere in this same feature).

- **Q: What performance budget binds the load path, given that FR-037 adds semantic validation to every
  read?** The spec required measurement but set a threshold only for the suite, leaving Principle IV's
  "targets before implementation" unmet for the operation the change actually slows.
  → **A: three budgets** (FR-PERF-002) — show-document load at **≤ 200% and ≤ 50 ms absolute** for the
  corpus's largest show document; configuration-domain load at **≤ 110%**, the budget 007 used; the
  suite at **≤ 110%** of 24.79 ms/test. The asymmetry is deliberate and follows FR-039's honesty about
  coverage: show documents carry nearly every semantic rule that exists, so doubling is a real
  allowance for real work, while the configuration domains have zero rules or one and therefore gain
  almost nothing to run — a regression there would be plumbing overhead, not enforcement, and is held
  to the tighter number for exactly that reason.

- **Q: What happens when a backup cannot be written during a load-triggered conversion?** Show libraries
  live on removable and network-mounted media, and repair tooling may run against read-only snapshots,
  so this is an operational case rather than a corner one.
  → **A: the backup obligation attaches to persistence, not to conversion** (FR-041a). A load-triggered
  conversion is in-memory and never rewrites the document, so it proceeds and reports; the standalone
  tool, which does rewrite, treats a backup failure as fatal for that document and continues with the
  rest. **This scopes D21's literal wording**, which attached "timestamped backup written first" to a
  conversion it described in the same clause as in-memory — a tension resolved here deliberately, not
  overlooked. The guarantee is unchanged wherever a file is actually rewritten; what changes is that a
  readable document on read-only media stays loadable, which is the same failure mode D21's middle row
  exists to prevent.

- **Q: What becomes of backups, given the spec had begun requiring one on every in-place config
  overwrite as well as on every converted document?** Unbounded accumulation on constrained nodes was
  the presenting problem; the real one was that the backup obligation had been generalised too far.
  → **A: backups are kept on schema upgrade only. A repaired file overwrites on save, validated by the
  operator after correction** (FR-041b, FR-041c). This narrows the obligation back to 007's actual
  precedent — a timestamped backup before a *migration* rewrote an operator's file — rather than the
  every-write generalisation an earlier draft of this spec had introduced on its own initiative.
  Retention needs no policy as a result: upgrade backups are at most one per document per schema
  version, which is bounded by construction, whereas per-save backups were not.

  The tradeoff is real and is recorded at FR-041c rather than buried: saving a repaired document
  destroys the corrupt original. It rests on the repair report being genuinely informative — the
  operator sees what changed and confirms it before the save. That gives FR-046 a second job beyond
  009's UI forwarding: it is what makes the overwrite safe.

### Session 2026-08-27 (c) — scope addition: the superseded fade actions

Raised by the repo owner: `fade_in` and `fade_out` were superseded by `fade_action` and must be
removed, with any incongruity arising from their presence or their future absence found and recorded.
Placed in **ITEM D**, per that direction and on this rationale: ITEM D is where the schema becomes
authoritative (D2), so the enumerations the descriptor publishes must first be true. Two consequences
land outside ITEM D by necessity — the `.xsd` edit is bookkeeping against D3 (FR-012), and documents
on disk carrying the values need converting, which is ITEM E's (FR-051a).

**The supersession is documented at its origin.** Feature 003's spec input reads: *"Create a new class
FadeCue as a child class of ActionCue to handle and store Fade events (fade_in, fade_out) to target
cues."* `FadeCue` with `action_type` fixed to `fade_action` was built to replace exactly these two.

**They are not dead code, though — they are live and misleading**, which strengthens the removal
rather than complicating it. `cuems-engine`'s `ActionHandler` dispatch table registers all three, and
the two being removed are never-implemented stubs: `fade_in` is *"treated as play (fade envelope not
yet implemented)"* and `fade_out` *"treated as stop"*, the latter carrying a noted zombie-process bug.
A cue labelled "fade in" that does not fade is worse than one that does not exist.

Five incongruities found, each carried as a requirement rather than left as a note:

1. **Schema and semantic rule already disagree.** `ActionType` offers both values to everything
   extending `ActionCueType`, including `FadeCueType` — while the registered T2 rule
   `fade_action_type` forces `FadeCue.action_type` to exactly `fade_action`. For a `FadeCue` the two
   values are schema-legal and semantically forbidden. This is the "facets disagree with the
   Python-side truth" edge case this spec already listed, now with a live instance (FR-029a).
2. **A plain `ActionCue` carrying `fade_in` asks for a fade with no fade parameters** —
   `ActionCueType` declares no `curve_type`, `duration` or `target_value`. That is the structural
   reason the values were superseded (FR-029a).
3. **ITEM D would otherwise republish them.** FR-029 reads legal values from `xs:enumeration` facets,
   so leaving them in hands the frontend's cue-creation UI a dead vocabulary through the very
   machinery built to end drift (FR-029b).
4. **No corpus document uses them** — `fade_action` ×4 and `play` ×7 are the only `action_type` values
   present. No golden churn, but equally no first-party fixture proves the conversion, so one must be
   constructed (SC-012b).
5. **A naming collision makes grep-and-delete unsafe.** `MediaCue.get_fade_profile` accepts
   `'fade_in'`/`'fade_out'` as aliases for the fade *profile direction* `in`/`out` — a different
   concept with the same spelling, and explicitly out of scope (FR-029c).

- **Q: What does an existing `<action_type>fade_in</action_type>` convert to?** Not derivable: the
  name says fade, the engine does play.
  → **A: `fade_in` → `play`, `fade_out` → `stop`** (FR-051a). Behaviour-preserving and lossless — it is
  exactly what the handlers already do, so a converted show runs identically and the cue's name simply
  starts matching what it always did. Rejected: promoting to a real `FadeCue`, which would have to
  invent `curve_type`, `duration` and `target_value` and would change how converted shows behave; and
  raising, which would make any library containing one such cue unopenable with no tool to fix it.

### Session 2026-08-27 (d) — scope addition: the fade-profile surface is deleted

Raised by the repo owner after session (c) exposed a name collision between `FadeProfile` and
`FadeCue`. The first proposal was to rename `FadeProfile` → `Envelope`; the decision landed on
**deletion** instead.

**Measured basis.** Zero references to `fade_profile`, `FadeProfile` or `function_id` across
`cuems-engine`, `cuems-editor` and `cuems-frontend`. The schema declares the surface, this repository
models it and enforces it with five semantic rules, and **nothing anywhere reads it** — the feature was
never implemented end to end. The repo owner confirms no project document depends on it, so the
migration cost is zero and the constraint on refactoring is internal only.

- **Q: Rename the surface to `Envelope`, or delete it?**
  → **A: delete it** (FR-007a — FR-007c). The decisive argument is that renaming would **enshrine a
  shape already known to be wrong**: a `FadeProfile` carries `type`, `mode`, `function_id` and
  `parameters` but neither `duration` nor `target_value`, so it cannot produce the `FadeCue` the
  replacement concept is meant to expand into — and `mode`/`function_id` duplicates `FadeCurveType`'s
  vocabulary for the same question. A good name on a broken shape is worse than an obviously dead entry
  under a poor one, because a good name invites use. Deleting lets the replacement arrive later as a
  **new type**, which the schema-evolution convention already sanctions as the non-breaking path,
  instead of forcing a second migration on documents that would by then hold data.

**Why this is in 008 rather than deferred.** `script.xsd` is already open under a granted exception,
the goldens are already being re-cut once (D29), and the conversion pass already exists. Doing it later
means opening the schema a third time and re-cutting goldens a second time. The one condition that
would reverse this: if the replacement feature is imminent, delete-then-re-add churns the schema twice
— the design work is captured in `specs/planning/envelope-feature.md` precisely so that it is not.

**What was preserved.** The existing design's real content — the preset/parametric distinction, the
parameters list, the one-in/one-out cap — is carried into that planning document rather than lost with
the code.

### Settled during `/speckit.specify` without needing a question

Two further questions §7.1 lists for `/speckit.clarify` are answered here rather than asked,
because a defensible default exists for each:

- **The repair report's shape** is specified behaviourally at FR-046: a caller must be able to answer,
  from the report alone, which document, which field, what was there, what replaced it, and whether
  the file on disk now differs from what was loaded.
- **Whether ITEM A's conversion is also `repair_durations.py`'s Pass B** is settled by E21's split:
  008 ships the standalone conversion tool that rewrites `<duration>` across project documents; 009
  folds Pass B into it rather than maintaining a second XML rewriter. The rewriter is built once,
  here (FR-042, Assumption 9).

### Settled before this spec — not open

- **The release gate.** D27: 008 does not ship independently regardless of touching no consumer
  repository directly.
- **`create_script()`'s fate.** D25: superseded, not preserved. Its output need not stay
  byte-identical and its faulty logic need not be carried forward.
- **Whether the `Media.duration` wire changes.** E4: it does, in XML and JSON alike. The field is
  bound to a passthrough adapter, so there was never a version of this change that left the wire
  alone. No "the wire is unaffected" golden check is written.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One type and one machinery for every time value (Priority: P1, Phase 1)

A maintainer reading a cue's timing does not have to know which element they are holding to know
what it contains. Every element that carries a time value is the same schema type and yields the
same in-memory object, and the setter that populates it is the same helper in all seven places. The
dead code that existed only to bridge the two representations is gone rather than left resolving.

**Why this priority**: it defines the new wire that every later item and every consumer sees, and it
creates the one real migration ITEM E's machinery has to carry. Nothing downstream can be designed
against a wire that is still ambiguous.

**Independent Test**: load every corpus document containing a media duration, assert the value is a
timecode object and not a string, write it back, and compare against the re-cut goldens; assert the
promoted element and the six pre-existing ones are indistinguishable in type, storage and emitted
shape.

**Acceptance Scenarios**:

1. **Given** a script document with a media duration, **When** it is loaded, **Then** the duration is
   a timecode object of the same class the six pre-existing elements yield — not a string.
2. **Given** a media duration set from a string, an integer, a dict or an existing timecode object,
   **When** the setter runs, **Then** all four inputs produce the same object, by the same helper the
   other six elements use, with no type-dispatch branch of its own.
3. **Given** a loaded script, **When** it is written to XML, **Then** the media duration is emitted as
   a nested `<duration><CTimecode>…</CTimecode></duration>`, matching the fade duration's shape.
4. **Given** a loaded script, **When** it is projected to the JSON wire, **Then** the media duration
   is `{"CTimecode": "HH:MM:SS.mmm"}`, matching the fade duration's projection.
5. **Given** the full schema set, **When** every element carrying a time value is enumerated, **Then**
   seven are found, all of one type, and the count of string-stored exceptions is zero.
6. **Given** the settings schema, **When** its dead timecode type pair is searched for, **Then**
   neither the schema types nor the Python class that existed only to bind them is present, and the
   coherence check that motivated that class still passes without an exception list.
7. **Given** the script schema, **When** its `TimecodeType` is searched for, **Then** it is still
   present — it is the lexical type of the inner `<CTimecode>` element and already carries the
   canonical `HH:MM:SS.mmm` pattern.
8. **Given** the golden corpus, **When** it is re-cut, **Then** the re-cut is a single reviewed diff
   whose every changed line is the duration shape change, and the pre-change files still exist under
   a retained old-version fixture path.

---

### User Story 2 - Every configuration domain can persist itself (Priority: P1, Phase 1)

A maintainer holding a settings, project-settings or project-mappings object can write it back to
disk through the same surface that writes a network map — one call, one symmetric shape, no
hand-rolled serialization at the call site. Today only the network map can do this.

**Why this priority**: it is a precondition of ITEM E, not a convenience. Backup-before-convert and
repair-to-default both write, and three of the six domains currently have no write path at all.

**Independent Test**: for each of the three domains, load a corpus document to objects, write it back
without modification, and compare bytes against the input normalised to the writer's output form —
with no part of ITEM E present.

**Acceptance Scenarios**:

1. **Given** a settings document loaded to objects, **When** it is saved, **Then** a valid document is
   written and re-loading it yields an equal object.
2. **Given** a project-settings document and a project-mappings document, **When** each is saved,
   **Then** the same holds for both.
3. **Given** all four config domains that now have a write path, **When** their save surfaces are
   compared, **Then** they take the same shape — the same argument, the same default-path behaviour,
   the same failure mode — as the network map's.
4. **Given** an existing file at the destination, **When** a routine save overwrites it in place,
   **Then** no backup is written — backups belong to schema upgrades, not to ordinary writes — and the
   file holds exactly the saved content.
5. **Given** a save that fails partway, **When** the destination is inspected, **Then** it holds
   either the complete prior content or the complete new content, never a truncated document. This is
   what protects a routine write, in place of a backup.

---

### User Story 3 - The network map becomes a first-party configuration object (Priority: P1, Phase 1)

A maintainer adopting a node, merging a discovery pass, or asking whether the map changed since it
was last written calls a method on the network-map object in the repository that owns
`network_map.xsd` — the same shape the other five schemas already have. That logic exists today only
as loose methods on a daemon class in another repository, mutating a bare index.

**Why this priority**: it completes the configuration surface the load path in ITEM E reads and
writes through, and it is the last piece of the node-model migration 007 started. It is also the
item that ships with no first-party caller, which is why its equivalence has to be measured rather
than asserted.

**Independent Test**: run the characterization tests ported from the daemon's current behaviour
against the new object and assert identical outcomes for merge, adopt, unadopt,
controller-always-adopted and change-signature — before any part of that daemon is edited.

**Acceptance Scenarios**:

1. **Given** a loaded network map and a set of discovered nodes, **When** they are merged, **Then**
   the resulting map matches what the daemon's current merge produces for the same inputs, node for
   node and field for field.
2. **Given** a node in the map, **When** it is adopted and then unadopted, **Then** the resulting
   states match the daemon's current adopt/unadopt outcomes exactly.
3. **Given** a map whose controller node is not adopted, **When** the controller-always-adopted rule
   runs, **Then** the outcome matches the daemon's current behaviour.
4. **Given** two maps, **When** their change signatures are compared, **Then** signatures agree
   exactly when the daemon's current signature function agrees, including for reordered but
   otherwise identical content.
5. **Given** a map with adopted nodes that are no longer present, **When** the missing-adopted check
   runs, **Then** it reports the same set the daemon's current check reports.
6. **Given** the dispatch chain that carries an operator's adopt/unadopt from the settings UI through
   the engine to the map, **When** the new object is examined as that chain's target, **Then** every
   operation the chain performs today has a corresponding method with equivalent behaviour.
7. **Given** the new object, **When** the repository is searched for imports from the daemon's
   repository, **Then** there are none — the object stands alone.

---

### User Story 4 - The schema describes itself, values included (Priority: P1, Phase 1)

A maintainer who needs to know what a document of a given type may contain — which fields, of what
type, how many, which values are legal, and what each one defaults to — asks the schema, through one
descriptor covering all six schemas. Nobody hand-maintains a literal example instance and hopes it
stays in step.

**Why this priority**: it supplies the defaults ITEM E's repair path recovers to, and it is what
feature 009 migrates the frontend's template call sites onto. A shape-only descriptor would satisfy
neither.

**Independent Test**: generate the descriptor for all six schemas and assert, per type, that the
emitted field set equals the schema's content model, that every restricted-enumeration field carries
its legal values as read from the schema's own facets, that every field with a model-layer default
carries that default's value, and that no field is left without a repairability classification — with
no part of ITEM E present. The classification is judgeable here on its own terms even though its only
consumer arrives in Phase 2.

**Acceptance Scenarios**:

1. **Given** any of the six schemas, **When** the descriptor is generated, **Then** every complex type
   appears with its field names, types and cardinality (required, repeated).
2. **Given** a field whose type is a restricted enumeration, **When** the descriptor is generated,
   **Then** its legal values are present and are read from the schema's enumeration facets, not from
   a hand-written Python enumeration.
3. **Given** a field that has a model-layer default, **When** the descriptor is generated, **Then**
   the default's **value** is present — not merely the fact that one exists.
4. **Given** a field with no default, **When** the descriptor is generated, **Then** its absence is
   explicit and distinguishable from a default whose value happens to be empty or null.
4a. **Given** any field in any of the six schemas, **When** the descriptor is generated, **Then** it
   carries a repairability classification, and the count of unclassified fields is zero. A field with
   no default classifies as unrepairable.
4b. **Given** the registered semantic rules, **When** the descriptor is generated, **Then** each rule's
   declared repairability appears against the field that rule targets — and a rule that declares
   nothing is rejected rather than assumed repairable.
5. **Given** the descriptor, **When** a caller asks for the value the frontend reads from the example
   audio cue's master volume, or the example DMX cue's channel map, **Then** it can be answered from
   the descriptor alone.
6. **Given** the repository after this item, **When** `create_script` is searched for, **Then** it is
   gone and the descriptor is what serves shape-and-default questions in its place. Its output is
   **not** required to be byte-identical to what `create_script` produced.
7. **Given** the settings schema, **When** its reference instance is produced, **Then** the descriptor
   generates it, and the schema's header no longer asserts a hand-maintenance obligation.
8. **Given** the descriptor's emitted structure, **When** ITEM E is later implemented against it,
   **Then** it is consumed as landed code with a fixed shape — the structure is a named hand-off
   interface, not a negotiable detail.

---

### User Story 5 - A corrupt document can no longer enter the runtime silently (Priority: P1, Phase 2)

An operator opens a show whose document has drifted out of semantic validity. Today it loads, and
the problem surfaces later as inexplicable behaviour somewhere downstream. After this story it is
detected at the boundary, and what happens next depends on *why* the document failed — not on
whether anyone remembered to validate.

**Why this priority**: it is the deliberate reversal of a principle that has held since 004, and the
umbrella under which the other two Phase 2 stories are outcomes rather than special cases.

**Independent Test**: load a document with a known semantic violation through the public show surface
and through each configuration accessor, and assert the violation is detected in every one of them —
where before it was detected in none.

**Acceptance Scenarios**:

1. **Given** a show document that violates a semantic rule, **When** it is loaded, **Then** the
   violation is detected — it is no longer accepted silently.
2. **Given** a configuration document in any of the six domains, **When** it is read through its
   public accessor, **Then** both structural and semantic validation run.
3. **Given** a document that is fully valid, **When** it is loaded, **Then** it loads unchanged, with
   no report, no backup and no conversion.
4. **Given** the reversal, **When** the specification and the load surface's own documentation are
   read, **Then** both state it explicitly as a decision, with the principle it reverses named —
   it does not read as an oversight.
5. **Given** the four configuration schemas that carry no semantic rules today, **When** semantic
   validation runs against them, **Then** it runs and finds nothing, and that fact is recorded rather
   than presented as new enforcement.

---

### User Story 6 - A document already on disk survives the wire change (Priority: P1, Phase 2)

An operator upgrades an installation. Every `script.xml` in their library was written before ITEM A
and carries the old duration shape. Opening one converts it transparently in memory, leaving the file
untouched; converting a whole library on disk is the same logic run from a tool, which backs each
document up before rewriting it.

**Why this priority**: without it ITEM A is unshippable. A change that invalidates every show document
on every installation is a data-loss event unless the conversion ships in the same feature.

**Independent Test**: take the retained pre-change corpus — real old-shape documents, not synthetic
fixtures — load each one and assert it converts to the new shape in memory with its file untouched;
then run the standalone tool over copies of the same files and assert it produces the same result
idempotently, with a recoverable backup per rewritten document.

**Acceptance Scenarios**:

1. **Given** a document whose version marker precedes the current version, **When** it is loaded,
   **Then** it is converted transparently in memory and the caller receives a valid object.
2. **Given** that same load, **When** the filesystem is inspected, **Then** the document on disk is
   unchanged — a load-triggered conversion is in-memory only — and the caller's report says the
   document was converted.
2a. **Given** an old document on read-only media, **When** it is loaded, **Then** it converts and loads
   successfully. It does not fail for want of a backup it never needed.
3. **Given** a directory of old-shape documents, **When** the standalone conversion tool runs over it
   without any application running, **Then** every document is converted and rewritten, each preceded
   by a timestamped backup whose restoration reproduces the original bytes exactly, and the result
   matches what loading each one would have produced.
3a. **Given** one document in that directory whose backup cannot be written, **When** the tool runs,
   **Then** that document is skipped and reported, the remaining documents are still converted, and no
   document is ever rewritten without a backup.
4. **Given** an already-converted document, **When** the conversion runs again, **Then** the bytes are
   unchanged — conversion is idempotent.
5. **Given** a converted document, **When** it is validated against the current schemas, **Then** it
   validates, and its duration values equal the originals to the millisecond.
6. **Given** any document written by this library after this feature, **When** it is inspected,
   **Then** its root element carries an explicit version attribute — one systemic mechanism, not a
   per-change structural tell inferred from which elements happen to be present.
7. **Given** every document in the corpus as it exists before this feature, **When** each is validated
   against its updated schema, **Then** all still validate without the attribute present: declaring it
   optional invalidates nothing on disk.
8. **Given** ITEM A's change to the show schema, **When** configuration documents of the other five
   schemas are loaded, **Then** none is treated as old and none is converted — versions move per
   schema, not in lockstep.

---

### User Story 7 - A corrupt-but-current document is repaired and reported, not rejected (Priority: P1, Phase 2)

An operator opens a document that is current-version and semantically invalid — the common case, and
the one the versioning machinery does not help. It loads. The offending field is recovered to a
default, and the caller receives a structured account of what was changed, precise enough to show the
operator. The library itself tells nobody: it has no UI channel and does not acquire one.

**Why this priority**: without this outcome the reversal in Story 5 makes corrupt documents unloadable
— and every first-party tool that repairs a corrupt document is itself a consumer of the load path.
A rule that made corrupt documents unreadable would disable the tools that fix them.

**Independent Test**: load a current-version document with a repairable semantic violation, assert it
loads, assert the offending field holds the descriptor's default, and assert the returned report names
the document, the field, the prior value and the substituted value.

**Acceptance Scenarios**:

1. **Given** a current-version document with a repairable semantic violation, **When** it is loaded,
   **Then** loading succeeds and the offending field holds the value the descriptor declares as its
   default.
2. **Given** that load, **When** the caller inspects the result, **Then** a structured repair report is
   available naming which document, which field, what was there, what replaced it, and whether the
   file on disk now differs from what was loaded.
3. **Given** the repair report's type, **When** a caller writes code to catch or inspect it, **Then**
   the type is importable from the library's public error surface — a repair the caller cannot name is
   one it cannot surface.
4. **Given** a document whose violation is in a field the descriptor classifies unrepairable — a
   reference to an object that is no longer present, say — **When** it is loaded, **Then** it raises,
   with a diagnostic naming the document and the field. It is not silently defaulted into looking
   valid.
5. **Given** any repair, **When** the substituted value's origin is traced, **Then** it came from the
   schema-derived descriptor — there is no hand-written per-field fallback table anywhere, and neither
   is the repairable/unrepairable decision itself hand-listed.
6. **Given** the library after this story, **When** it is searched for a notification, messaging or
   socket channel, **Then** none was added: the report is returned to the caller and the caller
   decides what to do with it.

---

### Edge Cases

- **A media duration that is absent, empty, or the string `"None"`.** The promoted element must handle
  the shapes the corpus actually contains, not only well-formed timecodes. The six pre-existing
  elements' current behaviour for the same shapes is the reference.
- **A document that is both old-version and semantically invalid.** Which outcome wins? Conversion
  runs first — a document cannot be judged semantically against rules for a version it is not yet in.
  If it is still invalid after conversion, the repair path applies to the converted form.
- **A document with no version marker at all** — that is, every document written before this feature.
  Absence of the marker is itself the oldest version, not a malformed document.
- **A version marker *newer* than the running library.** A document written by a future release is not
  convertible by an older reader; it is not an old document and it is not repairable.
- **A read-only or full filesystem when an old document is loaded.** Resolved by FR-041a: the load path
  converts in memory and needs no backup, so it succeeds; only a path that rewrites the file requires
  one, and there a backup failure is fatal for that document.
- **Concurrent access during the standalone tool's backup-and-rewrite.** Two processes converting the
  same document must not interleave into a half-converted file or two competing backups of different
  content. The load path is exempt by FR-041a — it writes nothing.
- **Repeated repairs of the same document.** Loading, repairing and saving, then loading again must not
  produce a second repair report for a field already repaired — the save records the operator-confirmed
  state, and re-reading it must find nothing to fix.
- **A repaired document saved without the operator having seen the report.** FR-041c's overwrite is safe
  only because the report was surfaced first. A caller that discards the report and saves anyway
  destroys the corrupt original unreviewed; the library cannot prevent this, so the migration guide must
  make the obligation explicit where 009 wires the report to the UI.
- **A restricted enumeration whose facets and the corresponding Python-side truth disagree.** The
  descriptor reads the schema; if the two disagree, that disagreement becomes visible for the first
  time and must be resolved rather than papered over. **This has a live instance**: `ActionType` offers
  `fade_in`/`fade_out` to `FadeCueType` while the `fade_action_type` rule forbids them there — resolved
  by FR-029a, and the reason FR-029b audits every other enumeration for the same shape of defect.
- **An enumeration value that is live in a consumer but semantically wrong.** `fade_in` and `fade_out`
  are dispatched by `cuems-engine` today as aliases for play and stop. "Unused" and "should not exist"
  are different findings; FR-029b's audit must record which one it found, per value.
- **A complex type reachable from no element** (the condition that made the settings timecode pair
  dead). The descriptor covers every declared type; how it presents an unreachable one must be
  deliberate.
- **A network map with zero nodes, or with two nodes claiming the controller role.** Merge, adopt and
  the controller-always-adopted rule must behave as the daemon does today, including in these states.
- **A `QName` defined incompatibly in two schemas.** All six share one target namespace with no
  imports between them; `CTimecodeType` was defined twice, incompatibly, until this feature deletes
  one. Any machinery that walks the namespace across schemas — the descriptor especially — must not
  assume a name resolves to one type.

---

## Requirements *(mandatory)*

### ITEM A — Timecode typing and canonical form *(Phase 1)*

- **FR-001**: Every element in every schema that carries a time value MUST be typed
  `cms:CTimecodeType`. After this feature the count of such elements is **seven** and the count of
  time-carrying elements typed otherwise is **zero**.
- **FR-002**: `script.xsd`'s `Media.duration` MUST be promoted from `cms:TimecodeType` to
  `cms:CTimecodeType`, and MUST store a `CTimecode` object populated by the same shared coercion
  helper the other six elements use.
- **FR-003**: The XML wire for a media duration MUST change from `<duration>TC</duration>` to
  `<duration><CTimecode>TC</CTimecode></duration>`, and the JSON wire from `"duration": "TC"` to
  `"duration": {"CTimecode": "TC"}`. This is deliberate. **No "the wire is unaffected" check may be
  written**; the field is bound to a passthrough projection today, so no such version of this change
  ever existed (E4).
- **FR-004**: The media-duration setter's three-branch type dispatch MUST be removed, collapsing to the
  shared helper.
- **FR-005**: The string branch of the media-duration semantic rule MUST be removed once it is
  unreachable through the setter.
- **FR-006**: The `TimecodeType` → string-passthrough adapter binding MUST be **verified before
  removal**: it may still resolve for the inner `<CTimecode>` child, whose lexical type it remains. The
  verification result MUST be recorded — removed with evidence it was dead, or retained with evidence
  it still resolves. Removing it unverified is not acceptable; leaving it unexamined is not either.
- **FR-007**: `settings.xsd`'s `CTimecodeType` and `TimecodeType` MUST be deleted, together with the
  Python model class that exists only to bind them. The coherence check that motivated that class MUST
  still pass afterwards **without an exception list**.
- **FR-007a**: `script.xsd`'s **fade-profile surface MUST be deleted**: the types `FadeProfileType`,
  `FadeProfilesWrapperType` and `FadeParameterType`, and the `fade_profiles` element on both
  `AudioCueType` and `VideoCueType`. With them go the model classes `FadeProfile` and
  `FadeFunctionParameter`, their registry bindings, `MediaCue`'s `fade_profiles` property and
  `get_fade_profile` accessor, the `AudioCue`/`VideoCue` declared defaults, and the five registered
  semantic rules `fade_profile_type`, `fade_profile_mode`, `fade_profile_parameters`,
  `fade_profile_parameter_value` and `fade_profile_caps`. The coherence check MUST still pass
  afterwards without an exception list.
- **FR-007b**: The justification for FR-007a MUST be recorded as **distinct from FR-007's**, because it
  is weaker and rests on different evidence. `settings.xsd`'s timecode pair is *unreachable from any
  element*; the fade-profile surface **is** reachable, from two cue types, and is removed because it is
  **consumed by nothing outside this repository** — measured as zero references to `fade_profile`,
  `FadeProfile` or `function_id` across `cuems-engine`, `cuems-editor` and `cuems-frontend` — and
  because the repository owner confirms no project document depends on it. A future reader MUST be able
  to tell which of the two arguments was used, since only one of them generalises.
- **FR-007c**: The surface MUST be **deleted rather than renamed**, and the reason recorded: the
  replacement concept (see the Envelope planning document) cannot use the current field set. A
  `FadeProfile` carries `type`, `mode`, `function_id` and `parameters` but neither `duration` nor
  `target_value`, so it cannot produce the `FadeCue` the replacement is meant to expand into; and
  `mode`/`function_id` duplicates `FadeCurveType`'s vocabulary for the same question. Renaming would
  ship a known-wrong shape under a better name and force a second migration later, on documents that
  would by then hold data. Deleting lets the replacement arrive as a **new type**, which the schema
  evolution convention already sanctions as the non-breaking path.
- **FR-008**: `script.xsd`'s `TimecodeType` MUST survive. It is the lexical type of the inner
  `<CTimecode>` element and already carries the canonical pattern.
- **FR-009**: The canonical timecode form MUST be `HH:MM:SS.mmm` everywhere after this feature; no
  surviving pattern, default or example may express the frame-based `HH:MM:SS:FF` form.
- **FR-010**: The golden corpus MUST be re-cut **once**, as a single reviewed diff that is part of this
  decision rather than a consequence of it. Every changed line MUST be attributable to FR-003.
- **FR-011**: The pre-change golden and corpus files MUST be **retained** under an old-version fixture
  path. They are the only first-party collection of real old-shape documents in existence and they are
  ITEM E's conversion fixtures. Deleting them is prohibited.
- **FR-012**: This feature's `.xsd` edits MUST be recorded as D3's second through fifth exceptions, each
  scoped to the file and change it names: `settings.xsd`'s dead-type deletion (FR-007, ITEM A),
  `script.xsd`'s `Media.duration` promotion (FR-002, ITEM A), the version-marker attribute on all six
  root types (FR-048a, ITEM E), and `script.xsd`'s `ActionType` narrowing (FR-029a, ITEM D). Three land
  in Phase 1 and one in Phase 2. **Two of the four invalidate documents on disk** — the duration
  promotion and the `ActionType` narrowing — and both are granted only because ITEM E's conversion
  carries them; that conditionality MUST be recorded with the exceptions, not separately from them.

### ITEM B — Configuration write paths *(Phase 1)*

- **FR-013**: The `settings`, `project_settings` and `project_mappings` configuration objects MUST each
  gain a working save operation, symmetric with the network map's — the only config write path that
  exists today.
- **FR-014**: The configuration façade MUST expose a save accessor for each of those three domains,
  symmetric with the existing network-map save accessor.
- **FR-015**: For each of the three domains, a document MUST survive load → save → load with an equal
  object and a byte-identical document, measured against the input normalised to the writer's output
  form.
- **FR-016**: A routine save MUST NOT write a backup. Backups are a **schema-upgrade** artifact, not a
  general write-path behaviour (FR-041b): a configuration object saved in the ordinary course — an
  operator changing a setting, a node writing an adoption — overwrites its file directly. FR-017's
  all-or-nothing guarantee is what protects that write; a copy of every prior state is not.
- **FR-017**: A save that fails MUST leave the destination holding either the complete prior content or
  the complete new content, never a partial document.
- **FR-018**: The save operation's name and signature MUST be fixed in this feature's data model as a
  **named hand-off interface**. Phase 2 is implemented against it as landed code; if it is still
  negotiable when Phase 1 merges, the gate has bought nothing.

### ITEM C — Network-map configuration object *(Phase 1)*

- **FR-019**: The network-map configuration object MUST gain, in this repository: merge of discovered
  nodes, adopt, unadopt, refresh, controller-always-adopted, missing-adopted check, and a change
  signature — mirroring the shape the configuration façade already has for the other five schemas.
- **FR-020**: That logic MUST NOT require importing from, or executing any code in, the daemon
  repository that hosts it today.
- **FR-021**: Equivalence with today's behaviour MUST be **measured, not asserted**: characterization
  tests capturing the daemon's current behaviour for merge, change signature, adopt/unadopt and
  controller-always-adopted MUST be written **before** the port and MUST pass against the new object.
- **FR-022**: The new object MUST be a valid target for the dispatch chain that carries an operator's
  adopt/unadopt from the settings UI through the engine to the map. That chain works today; every
  operation it performs MUST have an equivalent method here.
- **FR-023**: This feature MUST NOT execute the daemon's full atomization. It MUST instead deliver the
  **target-design basis** for it: the responsibility catalog, which responsibilities are single-class
  candidates, and why.
- **FR-024**: That basis MUST account for the fact that the responsibility being moved has a **live UI
  at the end of its dispatch chain** and cannot be designed as if headless, and for the wire
  entanglement whereby a network-map edit reaches the UI inside a project-mappings payload.
- **FR-025**: The daemon's broken cleanup path — which reads an attribute that is never assigned
  anywhere in the class — MUST be resolved: either fixed in place as a permitted consumer edit, or
  recorded in the migration guide with the prescribed change for feature 009 to apply. Leaving it
  unrecorded is not acceptable.
- **FR-026**: Every consumer-visible aspect of this item MUST appear in the migration guide at
  call-site granularity, ready for feature 009 to execute against.

### ITEM D — Schema-derived descriptor *(Phase 1)*

- **FR-027**: A schema descriptor MUST exist covering **all six** schemas, derived by walking the parsed
  schemas rather than by inspecting the runtime object model.
- **FR-028**: Per complex type, the descriptor MUST emit each field's name, schema type, and cardinality
  (required, repeated).
- **FR-029**: Where a field's type is a restricted enumeration, the descriptor MUST emit its legal
  values, **read from the schema's own enumeration facets** — not from the hand-written Python
  enumerations that carry those vocabularies today.
- **FR-029a**: `script.xsd`'s `ActionType` enumeration MUST have `fade_in` and `fade_out` **deleted**.
  They were superseded by `fade_action` when `FadeCue` was introduced (feature 003) and are incoherent
  in two independent ways today: the registered `fade_action_type` rule forbids them on a `FadeCue`
  while the schema offers them to it, and a plain `ActionCue` carrying one requests a fade while
  declaring none of `curve_type`, `duration` or `target_value`. This is D3's fifth exception (FR-012)
  and, like the third, it invalidates documents on disk — granted on the condition that ITEM E's
  conversion carries it (FR-051a).
- **FR-029b**: Every restricted enumeration in all six schemas MUST be **audited** for values that
  nothing in the system honours, and the audit's result MUST be recorded — values removed with the
  evidence they were dead, or retained with the evidence they are live. The descriptor is the first
  machinery that reads enumeration facets and republishes them to consumers (FR-029), so a value left
  in a facet is a value offered to the cue-creation UI. Auditing them once, here, is what stops the
  descriptor from propagating dead vocabulary through the machinery built to end drift.
- **FR-029c**: **FR-029a and FR-007a are two decisions, and MUST be implemented and reviewed as two.**
  Both remove something spelled "fade", in the same schema, in the same feature — but they rest on
  different evidence and land in different items and phases. FR-029a removes two `xs:enumeration`
  values from `ActionType` because `fade_action` superseded them; FR-007a removes the fade-profile
  types and elements because nothing outside this repository consumes them. Neither is a reason for
  the other.
  The concrete trap: `FadeProfile.type` takes `'in'`/`'out'` and `MediaCue.get_fade_profile` also
  accepts `'fade_in'`/`'fade_out'` as aliases for those directions — the same two strings FR-029a
  deletes from a **different enumeration in a different type**. **FR-029a is the removal of two
  enumeration values, not a textual removal of two strings.** A search-and-delete over `fade_in`/
  `fade_out` would corrupt the fade-profile surface rather than delete it cleanly, and would do so
  in ITEM D while FR-007a's deliberate removal lives in ITEM A.
  Consequently: **if FR-007a is ever descoped, FR-029a MUST still leave the fade-profile surface
  intact and working** — the two are independently revertible, which is the test of whether they were
  kept separate.
- **FR-030**: The descriptor MUST emit each field's **model-layer default value**. Defaults are not
  optional: two independent consumers need values rather than shape — ITEM E's repair path, which has no
  other source of truth, and the frontend template call sites that read concrete values today.
- **FR-031**: A field with no default MUST be distinguishable from a field whose default is empty or
  null. Absence MUST be explicit.
- **FR-031a**: The descriptor MUST emit, per field, a **repairability classification** stating whether
  substituting that field's default would *restore* a valid state or *change meaning*. This is the
  attribute ITEM E consults to choose between D21's second and third outcomes (FR-043, FR-044). Two
  constraints on it: **no field may be left unclassified** — an unclassified field is a descriptor
  defect, not a permissive default; and a field with no default (FR-031) MUST classify as unrepairable,
  since there is nothing to recover it to.
- **FR-031b**: The classification's source MUST be the **registered semantic-rule surface**: each
  registered T2 rule declares whether its own violation is repairable, and the descriptor reads that
  declaration and exposes it against the field the rule targets. A field that no rule targets cannot be
  flagged as violating anything, so it classifies on default presence alone (FR-031a). Three
  consequences the plan must carry:
  - The maintained surface is **the rules, not the fields** — 15 declarations today, rather than an
    annotation on every field across six schemas. An annotation nobody maintains is precisely the drift
    this descriptor exists to end, so the smaller surface is the point, not a convenience.
  - Adding a semantic rule later MUST require declaring its repairability. A rule that does not declare
    is a defect, not a rule that silently defaults to repairable.
  - Reading the rule surface does **not** breach FR-027's independence from the runtime object model.
    Semantic rules are where violations are *defined*, not where objects are *constructed*; structure,
    types, cardinality, enumerations and defaults still come from the parsed schemas.
- **FR-032**: Whether the existing field-shape structure is **extended** to carry enumerations and
  defaults, or a new structure is built **alongside** it, is an implementation choice — but the choice
  and its rationale MUST be recorded. Either is acceptable; an unrecorded one is not.
- **FR-033**: `create_script` MUST be deleted and its role served by the descriptor. Its output is **not**
  required to stay byte-identical, and its faulty ordering — validate, then blank the ids, so the object
  served would fail its own check — MUST NOT be carried forward.
- **FR-034**: The descriptor MUST be able to generate the settings reference instance, and once it can,
  the settings schema's header MUST stop asserting a hand-maintenance obligation for that file.
- **FR-035**: The descriptor's emitted structure — including defaults **and the repairability
  classification** — MUST be fixed in this feature's data model as a **named hand-off interface**, for
  the same reason as FR-018. FR-031a in particular is a Phase 1 deliverable that Phase 2 consumes as
  landed code; if it is still negotiable when Phase 1 merges, ITEM E has no boundary between its second
  and third outcomes.
- **FR-036**: This feature MUST NOT perform the frontend or editor cutover. The handoff MUST be recorded
  in the migration guide at per-call-site granularity — including the two call sites that read concrete
  values out of the current template — as 007 did.

### ITEM E — Validate on load, versioning, and repair *(Phase 2)*

- **FR-037**: The public show load surface and **every** configuration accessor MUST run full validation
  — structural (T1) **and** semantic (T2) — across all six schemas.
- **FR-038**: FR-037 **reverses** the standing principle that reading never becomes stricter (recorded as
  006's FR-026 and standing rule 8, asserted independently in 004, 005 and 006). The reversal MUST be
  recorded explicitly in this specification and at the load surface itself. It MUST NOT read as an
  oversight. The reversal binds **semantic** validation only; structural compatibility is untouched.
- **FR-039**: The specification and the plan MUST state plainly that semantic rule coverage today is
  the show schema plus exactly one project-mappings rule, and that `settings`, `project_settings`,
  `network_map` and `outputs` carry **zero** semantic rules. "Semantic validation across all six
  schemas" is therefore mostly plumbing in four of them. This feature does **not** add new semantic
  rules. Without this statement the measured cost gets attributed to enforcement that is not happening.
- **FR-040**: Load failure MUST have **three** outcomes, determined by document state, not two.
- **FR-041**: **Old** — a document whose version marker precedes the current version MUST be converted
  transparently in memory. The caller receives a valid object, and the conversion MUST be carried in the
  same structured report FR-046 defines, so a silent conversion is not possible.
- **FR-041a**: The backup obligation attaches to **persisting a schema upgrade**, and to nothing else. A
  load-triggered conversion does not write the document back, so it MUST NOT require a backup and MUST
  NOT fail because one could not be written — a read-only or full filesystem must not make a readable
  document unloadable.
  *This scopes D21's "timestamped backup written first", which as worded attached the backup to a
  conversion described in the same clause as in-memory. Scoping it to persistence is a refinement made
  deliberately here, recorded rather than silently applied; the guarantee is unchanged wherever a file
  is actually rewritten by an upgrade.*
- **FR-041b**: A backup MUST be written **only** when a document is rewritten because its format version
  changed — that is, by the conversion tool (FR-042). Three paths that write documents MUST NOT write
  backups: a routine configuration save (FR-016), a show-document save, and **a save of a document that
  was repaired on load**. Upgrade backups are naturally bounded — at most one per document per schema
  version — so no pruning policy is needed and none is specified.
- **FR-041c**: A repaired document MUST be saved by **overwriting**, with no backup. The operator is the
  validator: the repair report (FR-046) tells them exactly what was changed, they confirm the result is
  correct, and the save records that confirmed state. Keeping a copy of the corrupt prior state serves
  nothing once the correction has been reviewed.
  *The tradeoff, stated rather than buried: saving a repaired document destroys the corrupt original.
  That is deliberate and rests on FR-046 being genuinely informative — the report is what makes the
  overwrite safe, which is a second reason (beyond 009's UI forwarding) that it is public and
  structured rather than a log line.*
- **FR-042**: The same conversion logic MUST also ship as a standalone tool for batch, offline and
  post-install use, over a directory of documents, with no application running. It MUST be idempotent and
  MUST be the **only** implementation — the conversion is not built twice. Because it persists, it MUST
  write a timestamped backup per document before rewriting it, and MUST treat a backup failure as fatal
  **for that document** — skipping it and continuing with the rest, reporting the skip, rather than
  aborting the batch or rewriting unprotected.
- **FR-043**: **Current but semantically invalid, in a field the descriptor classifies repairable** —
  the offending field MUST be recovered to its descriptor default, the repair carried in a structured
  report, and loading MUST continue.
- **FR-044**: **Unrepairable** — loading MUST raise, with a diagnostic naming the document and the
  field. A field is unrepairable when the descriptor classifies it so (FR-031a) — notably when
  substituting its default would change meaning rather than restore a valid state, or when it has no
  default at all. The choice between FR-043 and FR-044 MUST be read from the descriptor; it MUST NOT
  be decided by a hand-written list of field names in the load path.
- **FR-045**: Every recovered default MUST come from ITEM D's descriptor. Hand-written per-field fallback
  tables are prohibited — they would recreate exactly the drift the descriptor exists to end.
- **FR-046**: The repair report MUST be a **public** type on the library's error surface, on 006's
  precedent that an exception the caller cannot name is one it cannot catch. From the report alone a
  caller MUST be able to answer: which document, which field, what was there, what replaced it, and
  whether the file on disk now differs from what was loaded.
- **FR-047**: The library MUST NOT acquire a notification, messaging or UI channel. It produces the
  report; feature 009 forwards it to the UI.
- **FR-048**: An **explicit, systemic** document-version marker MUST be designed and built — the
  mechanism rule 4 of the schema-evolution convention called for and which has never been built. It MUST
  NOT be another bespoke per-change structural tell like 007's element-presence check.
- **FR-048a**: The marker MUST be an **optional attribute on each schema's root type**, declared in all
  six schemas. It MUST be optional, so that adding it invalidates no document currently on disk. This is
  D3's fourth relaxation and its decision record is this specification's Clarifications section.
- **FR-048b**: Versioning MUST be **per schema**: each schema carries its own version sequence, and a
  change to one schema MUST NOT age documents of the other five. A single ecosystem-wide counter is
  rejected — ITEM A is a `script.xsd` change, and a shared counter would mark four untouched domains
  stale and force conversions that convert nothing.
- **FR-049**: The marker MUST be readable from a document **before** that document has been judged valid
  against the current schemas — a document of an old version does not validate against them by
  definition. Reading it MUST NOT depend on parser behaviour that the read path does not already rely
  on; this is why a processing instruction was rejected.
- **FR-050**: A document with no marker MUST be treated as the oldest known version, not as malformed.
  Every document written before this feature is in that state.
- **FR-051**: The marker's **first real client** MUST be ITEM A's media-duration conversion, exercised
  against the retained pre-change corpus (FR-011) rather than against a synthetic fixture. A marker that
  has never carried a real migration is not validated.
- **FR-051a**: The marker's **second** real client MUST be ITEM D's `ActionType` narrowing (FR-029a):
  a document carrying `<action_type>fade_in</action_type>` converts to `play`, and `fade_out` to
  `stop`. The mapping is **behaviour-preserving**, not a reinterpretation — it is precisely what
  `cuems-engine`'s handlers already do, so a converted show runs identically and the cue's name simply
  begins matching its behaviour. Promotion to a real `FadeCue` is explicitly **not** the conversion: it
  would have to invent `curve_type`, `duration` and `target_value`, and would change how converted
  shows behave.
- **FR-051c**: The marker's **third** client MUST be FR-007a's fade-profile deletion: a document
  carrying `<fade_profiles>` has those elements **dropped** by the conversion. Dropping data is
  normally prohibited, and this is the recorded exception — the elements carry no meaning any consumer
  reads (FR-007b), and retaining them would fail validation against a schema that no longer declares
  them. The conversion MUST report every dropped element through the same structured report (FR-046),
  so a document silently losing content is not possible.
- **FR-051b**: Having **three** independent conversions (FR-051, FR-051a, FR-051c) in the one schema
  whose version they all move, the version marker MUST be shown to carry **all three at one version
  step** — one `script` version increment, three transformations. A mechanism that needs a version per
  change is a per-change tell wearing a version number, which FR-048 prohibits. Three is materially
  better evidence than one: it is the difference between a mechanism that works and a mechanism shown
  to compose.
- **FR-051d**: A version step whose conversion is the **identity** MUST be supported. This is not a
  degenerate case to tolerate — it is the expected shape of every purely additive change, which the
  schema-evolution convention's rule 1 makes the normal way schemas grow. An additive change needs no
  transformation in the old-document direction (every existing document stays valid), but it still
  needs a version step so that a **new** document meeting an **older** library produces FR-052's
  "written by a newer version" diagnostic rather than a bare "unexpected element" structural failure,
  since no schema declares a wildcard that would let an old reader tolerate a new element.
  Consequently the machinery MUST NOT assume every version step carries a transformation, MUST NOT
  write a backup for a step that changes nothing, and MUST NOT emit a repair report entry for one.
  This feature's own three transformations all sit at a single step and so do not exercise this path;
  it MUST therefore be covered by its own test rather than left to the first feature that needs it.
- **FR-052**: A document whose marker is **newer** than the running library MUST raise a distinguishable
  diagnostic. It is neither old nor repairable.
- **FR-053**: Every document this library writes after this feature MUST carry the marker.

### Cross-cutting

- **FR-053b**: The migration guide MUST record, at call-site granularity, the consumer work FR-029a
  creates in `cuems-engine`: `_handle_fade_in` and `_handle_fade_out` in `cues/ActionHandler.py`, their
  two entries in the dispatch table, and the tests that exercise them all become unreachable once no
  document can carry those action types. Deleting them is **009's**, not this feature's — but the
  entry MUST also record that `_handle_fade_out`'s noted zombie-process defect (it bumps the generation
  counter without disarming) disappears with the handler rather than needing a separate fix, so the
  defect is not tracked twice or fixed in code about to be deleted.
- **FR-053c**: The migration guide MUST record FR-007a's consumer impact as **none measured** — zero
  references across the three consumer repositories — and MUST say so as a *measurement with a date and
  a method*, not as an assurance. It is the entire basis for deleting a reachable schema surface, and a
  future reader needs to be able to re-run it rather than trust it.
- **FR-053a**: The migration guide MUST record, for feature 009, that surfacing the repair report to the
  operator is a **precondition** of saving a repaired document, not a nicety — FR-041c's overwrite
  destroys the corrupt original, and the report is what makes that safe.
- **FR-054**: Feature 009's migration guide MUST carry an entry for every item with consumer impact, at
  the call-site granularity the audit establishes — including the show engine's construction of a
  timecode from a media duration, the editor's raw-dict fixups and its parser call sites, the duration
  repair tool, the frontend's template call sites, and the daemon's dispatch path.
- **FR-055**: This feature MUST NOT ship independently. The release gate 007 established extends through
  it: nothing in the ecosystem releases until feature 009 lands, despite this feature touching no
  consumer repository directly.
- **FR-056**: Phase 1 (ITEMs A–D) MUST be merged and green before any Phase 2 (ITEM E) work starts. No
  Phase 2 task may be marked parallel-safe with a Phase 1 task.
- **FR-057**: Every ITEM A–D acceptance criterion MUST be judgeable with no part of ITEM E in the tree.
  Any criterion that requires validate-on-load, versioning or repair belongs to Phase 2.
- **FR-UX-001**: Every diagnostic, report field and tool output added by this feature MUST follow the
  naming, formatting and message conventions the surrounding modules already use. The repair report and
  the conversion tool are new user-facing surfaces and MUST be consistent with the existing error
  surface rather than inventing a second vocabulary.
- **FR-PERF-001**: The cost of FR-037's strictness MUST be **measured** against feature 007's baseline
  (2393 passed / 94 skipped / 2 xfailed in 59.33 s = **24.79 ms per test**, measured 2026-08-24) — not
  006's, and not assumed acceptable because a requirement says so. The strictness is intentional despite
  its cost, but the cost must be a number. Load-time cost MUST be measured separately for a show document
  and for each configuration domain, by the established method (median of five warm runs against a named
  fixture), and the pre-feature figures MUST be re-measured on this branch rather than carried over from
  006's, which predate 007.
- **FR-PERF-002**: Three budgets bind, set before implementation per Principle IV:
  - **Show-document load: ≤ 200% of its pre-feature figure** (that is, at most a doubling), **and
    ≤ 50 ms absolute** for the largest show document in the corpus. The ratio grants that semantic
    validation is genuinely new work on the read path; the absolute cap stops the ratio from excusing a
    path that scales badly on large scripts.
  - **Configuration-domain load: ≤ 110% of its pre-feature figure**, the same budget 007 used. Three of
    the four configuration domains have **zero** semantic rules and the fourth has one (FR-039), so they
    gain almost nothing to run — a larger regression there indicates plumbing overhead, not enforcement.
  - **Suite: ≤ 110% of 24.79 ms per test.**
  Exceeding any budget MUST be either mitigated or explicitly approved with its rationale recorded in the
  plan's complexity tracking. It MUST NOT be silently accepted, and it MUST NOT be restated as passing.

---

### Key Entities

- **Timecode value**: a point or span in time. After this feature it has exactly one schema type
  (`cms:CTimecodeType`), one in-memory representation (a `CTimecode` object), one canonical lexical form
  (`HH:MM:SS.mmm`), and one wire shape in both XML and JSON. Seven elements carry one.
- **Configuration object**: the in-memory form of one configuration document. There are **four**
  configuration domains — `settings`, `project_settings`, `project_mappings`, `network_map` — out of
  six schemas; `script` is the show domain and `outputs` is a show schema, not a configuration
  document. After this feature all four can be written; before it, one could.
- **Network map object**: the configuration object for the cluster's node topology, which after this
  feature owns its own domain logic — merge, adopt, unadopt, refresh, controller-always-adopted,
  missing-adopted check, change signature — rather than having it reimplemented on a daemon class in
  another repository.
- **Schema descriptor**: a derived, read-only account of what documents of each type may contain — per
  field: name, schema type, cardinality, legal values where the type is a restricted enumeration, the
  model-layer default **value**, and a **repairability classification**. Covers all six schemas.
  Replaces two hand-maintained example instances and is the single source of truth both for repair
  defaults and for the boundary between a repaired document and a rejected one.
- **Repairability classification**: per field, whether substituting its default restores a valid state
  or changes meaning. It is what makes D21's second and third outcomes distinguishable without a
  hand-written list of field names, and it is the one Phase 1 deliverable whose consumer is entirely
  in Phase 2.
- **Document version marker**: an explicit, systemic statement of which version of the document format a
  file was written against, carried as an **optional attribute on the document's root element** and
  versioned **per schema**. Readable before validation. Absent means oldest — which is what every
  document written before this feature is. Its first real client is the media-duration conversion, so
  after this feature `script` documents are at version 2 and the other five schemas remain at their
  first version until something changes them.
- **Repair report**: a public, structured account of what a load changed and why — which document, which
  field, prior value, substituted value, and whether the on-disk file now differs. The library's only
  channel for saying "this loaded, but not as written."
- **Old-version corpus**: the retained pre-change golden and corpus files. The only first-party
  collection of real old-shape documents that exists, and the conversion path's fixtures.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Phase 1 — judgeable with no part of ITEM E present**

- **SC-001**: Exactly **seven** elements across all six schemas carry a time value, all typed
  `cms:CTimecodeType`; the count of time-carrying elements stored as strings is **zero** — counted, not
  reviewed.
- **SC-002**: Every one of the seven yields the same object type from load and the same shape on both
  wires, asserted by a test that treats the promoted element and the six pre-existing ones identically.
- **SC-003**: The golden re-cut is a single commit whose diff is 100% attributable to the duration shape
  change, and the pre-change files remain present under a retained fixture path — counted before and
  after.
- **SC-004**: Zero occurrences of the frame-based `HH:MM:SS:FF` timecode form remain in any schema,
  default, model class or example. The settings schema's dead timecode pair and its Python binding are
  gone; the show schema's `TimecodeType` is present.
- **SC-005**: The dead code the promotion exposes is gone, not orphaned: the setter's type dispatch and
  the semantic rule's string branch are removed, and the adapter binding's fate is recorded with the
  verification evidence behind it.
- **SC-006**: All four configuration domains with a write path save and reload to an equal object and a
  byte-identical document across the whole corpus — up from one domain today.
- **SC-007**: A save that is interrupted never leaves a truncated document — the destination holds the
  complete prior or the complete new content in 100% of injected-failure attempts. Zero backups are
  produced by routine saves, counted across the whole corpus round-trip.
- **SC-008**: 100% of the daemon's ported behaviours — merge, change signature, adopt, unadopt,
  controller-always-adopted, missing-adopted — produce outcomes identical to the daemon's current ones
  under the characterization tests, which were written before the port and fail against an empty
  implementation.
- **SC-009**: The network-map object has zero imports from, and zero runtime dependencies on, the daemon
  repository.
- **SC-010**: The descriptor covers 6 of 6 schemas, and for every complex type its emitted field set
  equals the schema's content model exactly — the same equality the existing coherence check asserts for
  the object model.
- **SC-011**: 100% of restricted-enumeration fields carry their legal values, and the values equal the
  schema's facets exactly. 100% of fields with a model-layer default carry that default's value; fields
  without one are explicitly marked as such.
- **SC-011a**: 100% of fields across all six schemas carry a repairability classification — the count of
  unclassified fields is zero — and every field with no default is classified unrepairable.
- **SC-011b**: 100% of registered semantic rules declare their repairability; the count of rules that do
  not is zero, and a rule added without a declaration is rejected by test rather than defaulting.
- **SC-012a**: `script.xsd`'s `ActionType` enumerates 12 values, not 14: `fade_in` and `fade_out` are
  absent, `fade_action` is present, and the descriptor publishes exactly the 12. Zero schema
  enumerations anywhere in the six schemas offer a value the system does not honour, per FR-029b's
  audit — recorded with evidence per value, not asserted.
- **SC-012b**: A purpose-built fixture document carrying `fade_in` and `fade_out` action cues exists
  and converts to `play` and `stop`. It must be constructed rather than found: the corpus contains
  only `fade_action` and `play`, so nothing on hand proves this conversion.
- **SC-012c**: The two fade removals are **independently revertible**, demonstrated rather than
  asserted: with FR-007a reverted, FR-029a alone still applies cleanly and the fade-profile surface
  remains bound, validated by all five rules, and byte-identical in the goldens. This is the test that
  they were kept as two decisions rather than one search-and-replace.
- **SC-012**: `create_script` and the hand-maintained settings reference instance are both gone, and the
  descriptor answers every question they were consulted for — including the two frontend call sites that
  read concrete values, each demonstrated answerable from the descriptor alone.
- **SC-013**: The two hand-off interfaces — the config save operation and the descriptor's emitted
  structure with defaults **and repairability** — are named and shape-fixed in the data model before
  Phase 1 merges.
- **SC-014**: Every Phase 1 acceptance criterion is demonstrated green on a tree containing no part of
  ITEM E.

**Phase 2**

- **SC-015**: Semantic validation runs on 6 of 6 schemas from the show load surface and from every
  configuration accessor — up from zero call sites today.
- **SC-016**: All three load outcomes are exercised by tests: an old document converts in memory and
  reports, a corrupt-but-current document repairs to a descriptor default and reports, and an
  unrepairable document raises. Each fails before its implementation and passes after.
- **SC-016a**: An old document on read-only media loads successfully, and its file on disk is
  byte-unchanged afterwards — measured, not argued from the code path.
- **SC-016b**: Every document the standalone upgrade tool rewrites has a recoverable backup; restoring it
  reproduces the pre-conversion bytes exactly, in 100% of cases. The count of documents rewritten
  without a backup is zero, including in a run where one document's backup fails.
- **SC-016c**: Backups are produced by the schema-upgrade path and by nothing else — the count of
  backups written by routine saves, show-document saves and repaired-document saves is **zero**,
  counted across the full test corpus rather than argued from the call graph.
- **SC-016d**: One `script` version step carries **all three** of this feature's transformations — the
  duration reshape, the action-type remap and the fade-profile drop — on a single fixture containing
  all three. Three changes, one version increment, one conversion pass.
- **SC-016e**: Every element dropped by the fade-profile conversion appears in the structured report;
  the count of silently discarded elements is **zero**. Dropping data is permitted here only because
  it is reported.
- **SC-016f**: A version step with an identity conversion is exercised by test: the document loads, its
  bytes on disk are unchanged, no backup is written and no repair is reported — while a document
  marked *newer* than the library still raises FR-052's distinguishable diagnostic. This proves the
  machinery supports additive-only evolution, which none of this feature's own three transformations
  exercises.
- **SC-017**: Every document in the retained pre-change corpus converts, validates against the current
  schemas afterwards, and preserves its duration values to the millisecond — measured over the whole
  corpus, not a sample.
- **SC-018**: Conversion is idempotent: converting twice produces the same bytes as converting once, for
  100% of the corpus.
- **SC-019**: The conversion exists in exactly **one** implementation, shared by the load path and the
  standalone tool — counted, not reviewed.
- **SC-020**: Zero hand-written per-field default fallbacks exist and zero hand-written lists of
  unrepairable field names exist; 100% of recovered values and 100% of repairable/unrepairable decisions
  are traceable to the descriptor.
- **SC-020a**: A document violating a field classified repairable loads with a report, and a document
  violating a field classified unrepairable raises — both demonstrated on the same load path, so the
  boundary is exercised rather than assumed.
- **SC-021**: The repair report is importable from the public error surface and answers all five required
  questions for every repair the tests produce.
- **SC-022**: The library gained no notification, messaging or socket channel — asserted against its
  dependency and public-surface snapshot.
- **SC-023**: 100% of documents written after this feature carry the version marker on their root
  element, and a marker-less document is treated as oldest rather than malformed.
- **SC-023a**: Adding the marker attribute to the six schemas invalidates **zero** documents in the
  corpus — every pre-change document still validates structurally against its updated schema without
  the attribute present, proven across the whole corpus rather than argued from the attribute being
  optional.
- **SC-023b**: A change to one schema's version leaves the other five schemas' documents at their
  existing version — demonstrated by ITEM A, which moves `script` and must move nothing else.
- **SC-024**: All three FR-PERF-002 budgets are met and reported as numbers, not as assurances: the
  per-test suite figure within 110% of 24.79 ms; show-document load within 200% of its re-measured
  pre-feature figure **and** under 50 ms for the corpus's largest show document; each configuration
  domain's load within 110% of its re-measured pre-feature figure. A regression beyond budget is either
  mitigated or explicitly approved with its rationale recorded — never silently accepted, and never
  restated as passing.
- **SC-024a**: The pre-feature load figures the budgets are measured against are re-measured on this
  branch, by the established method, and recorded before the strictness lands — not carried over from
  006's baseline, which predates 007.

**Both phases**

- **SC-025**: 100% of items with consumer impact have a migration-guide entry at call-site granularity,
  and the count of unaccounted impacted call sites is zero.
- **SC-QUALITY-001**: No new lint or type warnings; every public symbol added carries the rationale
  documentation the surrounding modules already carry.
- **SC-TEST-001**: Every requirement with observable behaviour has a test that fails before its
  implementation and passes after — including the characterization tests, which must be demonstrated
  failing against an empty implementation before the port.

---

## Assumptions

1. **`Media.duration`'s promotion is granted on the condition that ITEM E carries it.** The schema
   exception (D18b) and the conversion path (D20/D21) are one decision. If ITEM E's conversion does not
   land, ITEM A has shipped a change that invalidates every show document on every installation with no
   path forward — which is why the phase gate is not a release boundary.
2. **The six pre-existing `CTimecodeType` elements need no work.** All six already route through the
   shared coercion helper and already store `CTimecode` objects (E2). The requirement is the seventh.
   Anything found otherwise while implementing is a discovery, not an expectation.
3. **No consumer repository is edited by this feature.** All five items are buildable inside
   `cuems-utils` — closer in shape to features 004–006 than to 007. D16 permits a consumer edit if
   implementation surfaces a case that needs one; it does not mandate any, and FR-025's daemon defect is
   the only candidate identified in advance.
4. **The daemon's current behaviour is the equivalence reference, read but not edited.** Characterization
   tests are written against `CuemsNodeConf`'s behaviour as it stands on its working branch. The actual
   swap — the daemon consuming the new object — is feature 009's.
5. **Feature 009 is a hard successor.** Two of this feature's changes (the duration type and wire, the
   load-strictness reversal) are incompatible with what consumers assume today, so nothing ships until
   009 lands (D27). This feature's job is to make 009 executable, not to execute it.
6. **`create_script`'s output does not need to stay byte-identical**, and its faulty logic does not need
   to be carried forward (D25). This removes the additive-shipping constraint an earlier draft imposed on
   the descriptor and is the reason `create_script` is deleted rather than kept alongside.
7. **The frontend's template surface is small and bounded** — about seven call sites across two files —
   and at least two of them read concrete values rather than shape. That is why FR-030 makes defaults
   mandatory and why a shape-only descriptor would leave 009 with nothing to migrate onto.
8. **This feature adds no new semantic rules.** Four of six schemas have zero today and will have zero
   after. FR-037 makes semantic validation *run* everywhere; it does not make it *find* anything new in
   those four.
9. **The standalone conversion tool is the single rewriter of `<duration>` across project documents.**
   Feature 009 folds the editor's duration-repair tool's second pass into it rather than maintaining a
   second XML rewriter; that tool's ffprobe/database half stays editor-local. 008 owns only the library
   side that makes this viable (E21).
10. **All six schemas share one target namespace with no imports between them**, so a QName can be — and
    `CTimecodeType` currently is — incompatibly defined twice. Nothing composes them today. This is a
    hygiene invariant to preserve, not an accident to rely on, and it constrains the descriptor, which is
    the first machinery to walk the namespace across all six schemas at once.
11. **Commits are GPG-signed**, per repository convention.

---

## Dependencies

- **Features 004, 005, 006 and 007 are landed.** This feature builds on the schema-derived engine and its
  field-shape structures (004), the unified construction path and coercion table (005), the public object
  API and the `cuemsutils.errors` module the repair report joins (006), and the node model, typed
  `network_map` decode and `CuemsNetworkMapType.save()` (007).
- **Feature 007's `baseline.md`** — the current performance baseline (24.79 ms/test, 2026-08-24). 006's
  figures are superseded and MUST NOT be used.
- **`specs/planning/schema-evolution-convention.md`** — rule 4 is what FR-048 finally builds; 007's three
  precedents (renaming, constraining, deleting) are the patterns FR-041's conversion follows.
- **The retained pre-change corpus (FR-011)** is a dependency of Phase 2, produced by Phase 1. This is the
  clearest instance of why the phases are ordered rather than parallel.
- **`cuems-nodeconf`'s `CuemsNodeConf`** — read as the behavioural reference for ITEM C, not edited.
- **`cuems-frontend`'s settings component and the engine's dispatch path** — the live UI and dispatch chain
  ITEM C's API must remain a valid target for. Neither is edited here.
- **Feature 009** — a hard successor. It executes every migration-guide entry this feature writes.

## Out of Scope

- **The daemon's full atomization.** Nine of its ten responsibilities stay where they are. This feature
  delivers the target-design **basis** for splitting them (FR-023) so it can become its own dedicated
  `cuems-nodeconf` feature; it does not perform the split.
- **The frontend and editor cutover.** Retiring the template-as-a-concrete-instance, porting the config
  editing UI onto descriptor-driven forms, and disentangling the network-map/project-mappings payload are
  feature 009's (D26). This feature records the handoff at call-site granularity.
- **The duration-repair tool's own migration.** Moving it off the deprecated parser, dropping its private
  timecode regex and folding its second pass into the conversion tool are 009's (E21). This feature owns
  only the library side that makes them viable.
- **Consumer repository edits not strictly required to prove an item works.** D16 permits them; it does
  not mandate them, and this feature does not seek them out.
- **New semantic validation rules.** FR-037 makes semantic validation run across all six schemas; writing
  rules for the four that have none is not this feature's work (Assumption 8).
- **Deleting `cuems-engine`'s `fade_in`/`fade_out` handlers.** FR-029a makes them unreachable; removing
  them, their dispatch entries and their tests is **009's** (FR-053b). This feature closes the door;
  it does not clear the room behind it.
- **Designing or building the Envelope replacement.** FR-007a removes the fade-profile surface; it does
  **not** design what replaces it. That work — including the two gaps that made deletion the right call
  (no `duration`/`target_value`; `mode`/`function_id` duplicating `FadeCurveType`) and the question of
  where an envelope expands into fade cues — is captured in
  `specs/planning/envelope-feature.md` and belongs to its own later feature.
- **Any `.xsd` change beyond the four named exceptions** (FR-012). `project_settings.xsd`,
  `project_mappings.xsd` and `outputs.xsd` receive **only** the optional version-marker attribute and
  nothing else; `settings.xsd` and `script.xsd` receive that plus the one change each is named for. The
  schema items D3 deferred (X1–X13) stay deferred.
- **The show object model beyond the promoted duration.** The cue model, its construction path and the
  editor's `project_load` payload contract are otherwise untouched — with the one deliberate exception
  that the media duration's JSON shape changes (FR-003), which is itself a migration-guide entry.
