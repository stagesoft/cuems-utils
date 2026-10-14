<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Data model — the consumer-gate closure

**Phase 1** · 2026-10-13 · derived from [spec.md](spec.md) and [research.md](research.md)

This feature introduces **no new schema type and no new document**. What it changes is the shape of
three *derived* values, the state of one loaded document, one index field's write path, and one
exception's payload. Each section below gives the entity, the fields that move, the invariants that
must hold afterwards, and — where there is one — the state transition.

---

## 1. Configuration write target

Not a stored entity: a **resolved path**, owned by this library because the convention
`library_path/projects/<uname>/<file>` is this library's.

| Field | Meaning |
|---|---|
| directory | `config_dir` for the node level, `library_path/projects/<uname>` for the project level |
| file name | caller-supplied |
| existence requirement | **new** — whether a missing file is an error |

**States**, and the one that is new:

| Existence requirement | File present | File absent |
|---|---|---|
| required (today, and the default) | path returned | `FileNotFoundError` |
| **tolerated (new)** | path returned | **path returned** |

**Invariants**
1. The requirement defaults to *required*, so no existing caller changes behaviour (FR-002).
2. It is **keyword-only**: no positional call site can acquire tolerance by accident (FR-003).
3. Resolving a tolerated target creates nothing — no file, no directory, no side effect (FR-005).
4. A target whose **parent directory** is absent still fails at write time. That is a separate and
   correct matter and is explicitly not fixed (edge case, measured).

---

## 2. Project settings document — a loaded-state change

`CuemsProjectSettingsType`, already an existing root model. Nothing about the *type* changes; what
changes is what the manager holds when the file is absent.

**State transitions for the manager's held document**

| Event | Today | After this feature |
|---|---|---|
| `load_project_config` begins | document ← `None` | unchanged |
| project `settings.xml` present, loads | document ← decoded root | unchanged |
| project `settings.xml` **absent** | document stays `None`; logs *"Keeping default settings"* | **document ← empty `CuemsProjectSettingsType()`** |
| never loaded (no `load_project_config`) | attribute absent/`None` | **unchanged — stays the "not loaded" state** |

**Invariants**
1. "No file" and "never loaded" remain **distinct** states with distinct outcomes (FR-015a). This is
   the invariant the whole decision rests on: collapsing them would make a programming error
   indistinguishable from an ordinary first-run state.
2. The empty document is **schema-valid and saveable**. Measured: `setting` is `minOccurs="0"`, and
   an empty instance saves to a valid 1-element document.
3. Its projection is `{}` — the repeated field is omitted when empty, which is the projection's
   existing rule for an optional empty field, not a new one.
4. The public read reaches it through the **same** projection body as every other section; the
   section resolver already does `getattr(self, section)`, so a property of the right name is the
   whole mechanism (FR-011).
5. The property answers with the **document object**, never a raw `dict` (FR-010) — and invariant 4
   is the reason it cannot be otherwise: the resolver calls `to_wire()` on whatever `getattr` finds,
   so a dict would raise instead of projecting. The standing object-surface contract (feature 006,
   FR-014) asserts the same thing from the other side for every inventoried accessor.

**Consequence worth stating as a model fact**: once the absent-file state holds a document, a
project's **first** save becomes possible as soon as §1's tolerated target exists. G1 and G2 are one
journey (research R6).

---

## 3. Type instance — the derived entity that changes shape

`TypeDescriptor.instance`: a constructible exemplar of one complex type, derived from the schema and
the model's defaults. It is **derived, cached, and served over a websocket**, which is why three of
its invariants are about what it must *not* contain.

### Shape, before and after

| Aspect | Today | After |
|---|---|---|
| repeated complex field | `{"child": [ {...} ]}` | `[ {"child": {...}} ]` — as the wire nests it |
| document-body type | no wrapper | the body wrapper the wire carries |
| root with a single anonymous child | `{"Child": null}` | `{"Child": { …expanded… }}` |
| scalar with no model default | `null` | a **seed** satisfying the field's declared type and facets |
| optional field | present, `null` | present, seeded (so the projection does not omit it) |
| callable default | `null` | **`null` — unchanged** |

### Invariants

1. **Wire-shaped by construction, not by transformation.** The instance is produced by populating a
   value and projecting it through the same encoder `to_wire()` uses. There is no second
   implementation of the wrapping or nesting rules (research R2; the spirit of FR-011 extended to
   the descriptor).
2. **Saveable.** Every root instance, and every nested type instance a consumer names, passes this
   library's own write path unmodified (FR-023, FR-024).
3. **Complete.** Every declared non-wildcard field appears. Achieved by populating optional fields
   too, so the projection's omit-if-optional-and-empty rule has nothing to omit (research R3,
   decision 3). This is the one deliberate divergence from the projection of a real sparse object,
   and it is in the direction of being more useful.
4. **A callable default is never invoked** (FR-027). `derive` is cached, so calling a
   fresh-identifier generator once would freeze one value and hand it to every later caller. The
   callable stays visible on the field.
5. **Serialisable.** Nothing non-serialisable enters it (FR-030) — it is served to a UI.
6. **The per-field `default` fact and every field's repairability classification are unchanged**
   (FR-026a). This is the load-bearing invariant of the whole gate: the classification's first rule
   is *no default means unrepairable*, and the load path **repairs** a repairable violation where it
   **raises** on an unrepairable one. Seeding an instance must not move 64 fields across 19 types
   from "the document is refused" to "the document loads with a fabricated value".
7. Cycles stay bounded by branch, as today — a type reached twice down two different branches
   expands both times; a revisit on the same branch does not.

### The seed, as a derived value

A seed is a function of the field's **resolved simple type**, never of the field's name. Seven
ordered rules over facets, plus a five-entry table for the irreducible pattern case — the full
contract is [contracts/seeding-rules.md](contracts/seeding-rules.md).

| Precedence | Source |
|---|---|
| 1 | the bound model class's declared default, if any (today's behaviour) |
| 2 | the seed derived from the declared type |

So the seed only ever fills what the model leaves unset, which keeps today's values exactly where
they are and bounds the change to the 64 measured fields plus the optional ones.

---

## 4. Field description — one fact narrows

`FieldDescriptor`, unchanged in structure. One of its six facts changes meaning in one case.

| Field | Change |
|---|---|
| `enum_values` | reported **only** when every member of a union type is an enumeration |

**Invariants**
1. A union all of whose members are enumerations keeps reporting their merged values (FR-068) — the
   narrowing is conditional, not a removal.
2. A union with at least one non-enumerated member reports **no** closed choice set (FR-066).
3. Every other descriptor fact for the affected fields is unchanged (FR-029).

**The five affected sites**, measured — note the second type is numeric, which the planning document
did not record:

| Schema | Type | Field | Reported today | Actually valid |
|---|---|---|---|---|
| `network_map` | `NodeType` | `uuid` | the NOT PROVISIONED sentinel, alone | any uuid4, plus that sentinel |
| `settings` | `NodeConfType` | `uuid` | same | same |
| `project_mappings` | `NodeMappingType` | `uuid` | same | same |
| `settings` | `AudioPlayerType` | `output_latency_ms` | `auto`, alone | `auto`, **or 0–500** |
| `settings` | `VideoPlayerType` | `output_latency_ms` | same | same |

⚠ **Ordering dependency**: this narrowing must land **before** the instance's union seeding rule, or
that rule's test passes vacuously (plan, *Implementation sequencing*).

---

## 5. Node index entry — one field gains a write path

A node's row in the network map, held **by reference** so that a mutation is already visible in the
document about to be serialised.

| Field | Owner | Writable by a consumer after this feature |
|---|---|---|
| `alias` | **operator (UI)** | **yes — the only one** |
| `role_id`, `hostname` | the per-node daemon | no |
| `uuid`, `mac` | identity | no |
| `ip`, `online`, `adopted`, `name` | discovery | no |

**State transitions for `alias`**

| From | Event | To | Reported |
|---|---|---|---|
| absent | set a valid label | present | success |
| present | set a different valid label | updated | success |
| present | set the same label | unchanged | success, and the index signature does not move |
| present | clear | **key removed** | success |
| any | set an invalid label (empty or blank) | **unchanged** | raises, **before** anything is touched |
| — | set on an unknown identity | nothing | failure reported, nothing mutated |

**Invariants**
1. **Validate before mutating** (FR-036). Measured: an in-place empty label makes the save fail
   *after* the index changed, and the daemon's pending-write retry then fails on that row until
   restart. This is the invariant with an operational incident behind it.
2. **Mutate in place** (FR-039). Rebinding a copy is a breaking change, not a tidy-up: callers hold
   these node objects through more than one reference, which is what makes a concurrent adopt
   unlosable in a daemon that takes no lock.
3. Clearing **removes the key**, because the element is optional (FR-037).
4. Liveness is **not** a precondition — an offline node and the controller are both labellable
   (FR-043), unlike adoption.
5. A discovery merge does not clear a label (FR-044), pinned by test rather than argued from the
   merge's implementation.
6. The index signature already includes `alias`, so the write-if-changed path needs no change
   (FR-041, verified).

---

## 6. Identity collision — prose becomes data, in two layers

Two or more map rows carrying one node identity, with the hardware addresses that distinguish them.

| Layer | Type | Carries | Why here |
|---|---|---|---|
| **internal**, raised by the rule | a `ValueError` subclass | the collisions, as data | stays a `ValueError`, so every existing path and the pinned raw verdicts are unchanged |
| **public**, raised by the accessor | `ValidationError` subclass | the same data **plus the file path**, and a populated violation | the accessor is where the file path exists, and where contract C2 already places the posture |

| Field | Content |
|---|---|
| collisions | each colliding identity with the hardware addresses carrying it |
| file | the document's path — present only on the public layer |
| violation | located as `(identity, "uuid")` — the pair form the violation type already documents as addressable without parsing a string |
| message | **unchanged**, including its remedy sentence and the command it names |

**Invariants**
1. The internal exception **remains a `ValueError`** (research R4). The rule raises one *because*
   `xmlschema`'s own validation error is also a `ValueError`, so `isinstance` cannot tell a semantic
   from a structural failure — and `tests/golden/outcomes.json` pins the internal reader's raw
   verdicts document by document.
2. The public type is a **`ValidationError` subclass**, so a consumer catching the general case keeps
   catching this one (FR-060a).
3. The message is unchanged, so message-shape recognition keeps answering for any caller still on it
   (FR-063, FR-064).
4. Two distinct collisions in one document are distinguishable without re-parsing text (FR-062).
5a. "Published surface" is **three** places and two are hand-maintained (FR-065c): `__all__`, the
   `PUBLIC_ERRORS` tuple that is asserted equal to it, and the API golden that is **generated from**
   that tuple. Adding to `__all__` alone turns an existing contract test red; re-cutting the golden
   without the tuple omits the class entirely.
5. The new type joins the errors module's published surface and documented hierarchy (FR-065a) — a
   type a consumer cannot import is a type it cannot catch.

⚠ **Why the public type cannot simply be raised by the rule** (the measurement that shaped this):
the accessor's handler orders `except ValidationError: raise` **before** the clause that attaches the
file path. A `ValidationError` subclass raised in the validator would propagate past it and lose the
one field the accessor exists to add.

---

## 7. Version step — the retired counts, in either shape

A registered transformation of a `settings` document from version 1 to version 2, dropping two
derived counts that were required pre-F3.

| Field | Flat location (pre-013) | Reshaped location (post-013) |
|---|---|---|
| `audio_cards` | `Settings/node/audioplayer` | `Settings/node/players/player[@class='audio']` |
| `universes` | `Settings/node/dmxplayer` | `Settings/node/players/player[@class='dmx']` |

**Invariants**
1. The field is dropped **wherever it is found** (FR-051). The tree reaching the converter may or may
   not have been reshaped — on the load path it has not, inside the reshape tool's pre-write
   validation probe it has, and both are legitimate.
2. **Idempotent**: a document with neither field converts to itself (FR-052).
3. Every drop is still named in the load report (FR-057).
4. The tool order is **not** inverted (FR-054): convert-before-reshape dead-ends for `script`
   exactly as reshape-before-convert dead-ends for `settings` today.
5. A flat document **without** the retired counts still migrates cleanly (FR-055) — the eight-day
   window between the two schema changes is a real population.

**Open sub-question the design must answer** (research R7): the current lookup is singular
(`Settings/node`) and addresses only the first node section. Whether a `settings` document may carry
more than one is a schema question; if it may, the converter has a second latent defect of this
family.

---

## 8. Written document — the bytes gain structure

| Property | Status |
|---|---|
| **indented and line-broken** | **new** |
| atomic (temporary + replace in the same directory) | unchanged |
| target file mode preserved | unchanged |
| `cms` prefix registered | unchanged |
| UTF-8 encoding and XML declaration, explicit | unchanged |
| idempotent — a document this library wrote, reloaded and rewritten, is byte-identical | unchanged, and **must be re-proved** |

**Invariants**
1. Indentation never alters an element's text where that text is data (FR-073). Satisfied by the
   stdlib indenter's own contract, verified: mixed content is returned untouched. Exactly **one**
   mixed-content type exists across the six schemas, and it is the one at risk.
2. The five guarantees above are untouched (FR-072) — each has a recorded failure behind it, two of
   them outages.
3. The golden set is re-cut as **one** reviewable change (FR-074): six XML goldens, two API goldens
   (for §1's and §2's signature additions **and §6's new exception type** — `public_api.json` carries
   an `errors` section enumerating every public error class, so S1 moves it too), and the manifest.
   The **24** wire-dict goldens, `generated/example_script.reader.json` and the outcomes record are
   unaffected — a wire dict carries no whitespace. ⚠ Counted on disk 2026-10-13; this said 20, and
   the API goldens were scheduled before the addition in §6 that moves them.
4. The two canonically-authored corpus documents are **re-authored** in the new form (FR-075), so
   their first-cycle byte-identity claim still holds rather than being quietly reclassified.
5. The **three 007 pre-state documents** are re-authored too (FR-075a) — the hand-authored set is
   **five** documents, not two. `tests/contract/test_network_map_roundtrip.py` diffs `save()`'s
   output against them and asserts the diff is exactly two lines, which holds only while the
   document is one line; all three are. ⚠ Added by the second analyze pass: this one is invisible to
   a golden list because it asserts a **line count**, not a hash.
6. A golden moving is a claim about the **generator**, not about the package (FR-041a, FR-065c): the
   API goldens record a hand-maintained `PUBLIC_CLASSES`/`PUBLIC_FUNCTIONS`/`PUBLIC_ERRORS`, so
   §5's `set_alias` and §6's exception type move them only once those lists do.
