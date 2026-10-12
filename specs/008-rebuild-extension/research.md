# Phase 0 research — feature 008

Measured against the live tree on `008-rebuild-extension`, 2026-08-28. Every decision below
resolves something the spec left as mechanism or that the audit (E1–E26) flagged as undesigned.

---

## R1 — Where the version marker lives, and why it must be excluded from derivation

**Decision.** One **optional, unqualified attribute** on each schema's root element type:
`doc_version`, `type="xs:positiveInteger"`, `use="optional"`. Six declarations, one per schema.
It is emitted by the writer in `mapper.build_document` beside `xsi:schemaLocation`, and it is
**explicitly excluded from `spec.derive`'s attribute derivation and from every wire projection.**

**Rationale.** Three facts constrain this and together leave one option:

1. **No schema declares `anyAttribute` or a root wildcard.** The only attribute declarations across
   all six schemas are `universe_num` and `id` on the DMX types. An undeclared attribute therefore
   fails T1 — the marker must be *declared*, which is why it is D3's fourth exception.
2. **No schema sets `attributeFormDefault`**, so it defaults to `unqualified`: a locally declared
   attribute appears as bare `doc_version="2"` with no prefix. Nothing in the writer or the corpus
   has to learn a new namespace.
3. **The root types are anonymous and local** (`CuemsProject`, `CuemsNetworkMap`, `CuemsOutputs`,
   `CuemsProjectMappings`, `CuemsProjectSettings`, `CuemsSettings`). Adding an attribute is a
   contained edit inside each root's own `xs:complexType`, reaching no shared type.

**The exclusion is the load-bearing part, and it is not optional.** `spec._derive_attributes`
(spec.py:203) turns every declared attribute into a `FieldSpec` with `kind=ATTRIBUTE`, and
`TypeSpec.attributes` feeds the coherence check that compares a model class's declared field set
against its schema type. Two consequences if the marker is derived like any other attribute:

- **`network_map` would gain a domain field it does not have.** Its root path is bound to
  `CuemsNetworkMapType` itself (not `GENERIC`), so `doc_version` would become a declared field of a
  model class, would need a `DECLARED_DEFAULTS` entry, and would appear in that object's `to_wire`
  — a new key in a payload `cuems-engine` reads.
- **It would repeat `schemaLocation`'s history.** That attribute leaks into the decoded dict today
  and is handled as undescribed content in three places (mapper.py:150, :309; spec.py:118), and
  feature 006 had to explicitly drop it from the wire dict. Adding a second document-level attribute
  through the same unmanaged path would re-create a problem already solved once.

So the marker is a **document property, not a domain field**: written by `build_document`, read by a
pre-validation probe (R2), and invisible to the object model. The exclusion lives in one named
constant beside `SCHEMA_INSTANCE_URI` so that "attributes the model does not own" is a list of two
with a reason, not a special case buried in a conditional.

**Versioned per schema** (FR-048b): each schema carries its own sequence. A `script.xsd` change must
not age `network_map` documents.

**The write side has a blast radius, and it is scheduled rather than discovered.** `build_document` is
the single funnel every writer in this library goes through, so the moment the marker is emitted, every
golden cut earlier in the feature and every config round-trip fixture gains a root attribute it did not
have. That is not a reason to place the marker elsewhere — it follows from the marker being written at
all — but it is a reason it cannot be treated as a self-contained Phase 2 change. The full account, with
what each affected artifact is and where it is discharged, is **data-model §1**; the work is task T102a
and FR-010's third recorded golden event.

**Alternatives rejected.** *Dedicated child element* — enters the content model, where required is
breaking and optional still shifts ordering, and would behave differently per schema because
`CuemsScript`'s root is `xs:all` while the others are `xs:sequence`. *Processing instruction* — needs
no `.xsd` edit at all, but stdlib `ElementTree` discards PIs unless a non-default parser target is
configured and the read path runs through `xmlschema`; writable easily, readable only fragilely.
*Single ecosystem-wide counter* — would age four untouched domains the moment ITEM A lands.

---

## R2 — Reading the marker before the document has been validated

**Decision.** A standalone probe that parses with stdlib `ElementTree` and reads `root.attrib` —
no schema, no `xmlschema`, no model construction. Absent attribute → version 1 (the oldest).

**Rationale.** FR-049 requires the marker be readable *before* the document is judged valid, because
an old document does not validate against the current schemas by definition — which is the whole
situation the marker exists to detect. Any probe that runs validation first is circular. Root
attributes are available from the first parse event, so this costs one parse of the file's head and
nothing else. It also means a document too corrupt to validate can still report which version it
claims, which is what makes the difference between D21's three outcomes decidable.

**Alternative rejected.** Reading it out of the decoded dict, which requires the decode this probe
exists to precede.

---

## R3 — Descriptor: built alongside `FieldSpec`, not by extending it

**Decision.** A **new module** with its own dataclasses, which **reuses `spec.derive()`** for
structure rather than re-walking the XSD, and adds what `derive` does not carry: enumeration values,
model-layer default values, and the repairability classification.

**Rationale (FR-032 requires this choice be recorded with its reason).** Three arguments, one of
them decisive:

- **`FieldSpec` is on the hot path and the descriptor is not.** `derive` is `lru_cache`d and consulted
  during every object construction and every encode; the descriptor is consulted when generating a
  template or repairing a field. Widening the cached structure would grow every entry with data the
  decode path never reads.
- **The concerns are different.** `FieldSpec` answers *what shape is this document* — the question D2
  makes the schema authoritative for. The descriptor answers *what may a user put here, and what does
  it default to* — which is partly schema (`xs:enumeration`), partly model (`DECLARED_DEFAULTS`), and
  partly rule surface (repairability). Two of its three sources are not the schema at all, so it is
  not a natural extension of a schema-derived structure.
- **`FieldSpec` is frozen and its field set is asserted by tests.** Extending it edits a structure
  three features already depend on; building alongside touches nothing.

**Reuse, not duplication.** The descriptor calls `derive(TypeKey(...))` for names, types, cardinality
and order. It never re-implements the walk — which is what keeps D2 true, and what stops the two from
drifting.

---

## R4 — Reading `xs:enumeration` values from the parsed schema

**Decision.** Read the facet off the resolved simple type through `xmlschema`'s validator API, from
the schema objects the registry has already loaded (`documents.schema_object`). No reparse, and no
reading of the hand-written Python `Enum` classes.

**Rationale.** FR-029 requires the legal values come from the schema's own facets, because the
hand-written enums and the facets can disagree — and this feature found a live case where the schema
and a semantic rule disagree about `ActionType` (FR-029a). Reading facets is what makes that class of
disagreement visible instead of invisible. Sharing the registry's loaded schema objects is what keeps
the descriptor's cost off the load path.

**Note for implementation.** All six schemas share one `targetNamespace` with no imports between
them, and a QName can be — and `CTimecodeType` currently is — incompatibly defined twice. The
descriptor is the first machinery to walk all six at once, so it must resolve types **per schema**,
never by bare QName. `TypeKey` already carries the schema name for exactly this reason.

---

## R5 — Where model-layer defaults come from

**Decision.** From the bound model class's accumulated `declared_defaults()`, reached through the
registry binding for the type. The existing `Unset` sentinel already distinguishes "no default" from
"defaults to `None`", so FR-031's requirement that absence be explicit needs no new convention.

**Rationale.** `DECLARED_DEFAULTS` is already the one place a default is written, accumulated along
the class chain by `CuemsDict.declared_defaults`. Any second source would be the drift the descriptor
exists to end. Types bound to `GENERIC` have no model class and therefore no defaults — that is a
real answer, recorded as such, not a gap.

---

## R6 — `save()` for the three config domains, and what "atomic" means

**Decision.** Symmetric with `CuemsNetworkMapType.save()`: validate T1 via `iter_schema_errors`, then
`documents.build_tree` → `write_tree`. Write to a temporary file in the destination's directory and
`os.replace` onto the target, which is atomic within a filesystem.

**Rationale.** `save_network_map` (ConfigManager.py:246) is the only config write path that exists and
its docstring already claims atomicity; making the other three match is FR-013's symmetry requirement
answered by copying a landed pattern rather than inventing one. `os.replace` gives FR-017's
all-or-nothing guarantee without a lock: a reader sees either the whole old file or the whole new one.

**What changed from an earlier draft of the spec.** Routine saves write **no backup** (FR-016). The
backup obligation attaches to persisting a *schema upgrade* only (FR-041b). `os.replace` is therefore
carrying the whole safety story for ordinary writes, which is why it is a requirement and not a
detail.

---

## R7 — The network-map object's shape, and what is characterizable

**Decision.** The behaviours land on `NodeIndex` as **pure methods over the index plus an explicit
argument**, with `CuemsNetworkMapType` orchestrating read/merge/write. Discovery input is passed in,
never reached for.

**Rationale.** `CuemsNodeConf.network_map` is a **MAC-keyed dict of node dicts** — `merge_discovered_nodes`
matches by UUID but iterates a MAC-keyed map, and `set_master_always_adopted` iterates `.items()` as
`(mac, node)`. `NodeIndex` is already the MAC-keyed working set feature 007 created for exactly this
role, so the shape matches and no translation layer is needed.

What blocks direct porting is that four of the methods read `self.listener.nodes` — live discovery
state — rather than taking it as an argument. Parameterising that is what turns them into functions
of their inputs, and therefore into things E23's characterization tests can pin:

| Behaviour | Today | Ported shape |
|---|---|---|
| `merge_discovered_nodes` | reads `self.listener.nodes` | `merge(discovered)` |
| `check_missing_adopted_nodes` | reads `self.listener.nodes` | `missing_adopted(discovered)` |
| `set_master_always_adopted` | pure over the map | pure |
| `adopt_node` / `unadopt_node` | pure over the map | pure |
| `_map_signature` | pure over the map | pure |
| `refresh_network_map` | orchestrates the five above, writes if changed | orchestration on `CuemsNetworkMapType` |

**Note.** `write_network_map` filters on `required_fields = ['uuid','mac','name','node_role','ip']`.
Whether that filter is behaviour to preserve or an artifact of the old write path is a question the
characterization tests answer rather than assume.

---

## R8 — How a semantic rule declares repairability

**Decision.** Extend `validators.register(name, applies_to)` with a **required keyword-only**
`repairable: bool`. No default value.

**Rationale.** FR-031b requires that a rule which does not declare its repairability be a defect
rather than silently repairable. A required keyword makes that a `TypeError` at import time — the
earliest possible failure, and one that cannot be forgotten in review. `Rule` already carries
`(name, applies_to, fn)`, so this is one field, and the closed `RULES` list that the coherence test
already reads becomes the descriptor's source for the classification (R3).

**Alternative rejected.** A separate mapping from rule name to repairability — a second structure to
keep in step with the first, which is the drift this feature is removing elsewhere.

---

## R9 — Version steps that transform nothing

**Decision.** The conversion registry maps a version step to an **optional** transformation. A step
with none is valid: the version increments, the document is untouched, no backup is written and no
repair is reported.

**Rationale.** FR-051d. Purely additive schema growth — the normal case under the schema-evolution
convention's rule 1 — needs no transformation in the old-document direction, because every existing
document stays valid. It still needs a version step so that a *new* document meeting an *older*
library produces FR-052's "written by a newer version" diagnostic instead of a bare unexpected-element
failure, since no schema declares a wildcard that would let an old reader tolerate a new element.
None of this feature's own three transformations exercises this path, so it needs its own test
(SC-016f) rather than being left to the first feature that relies on it.

---

## R10 — Performance measurement method

**Decision.** Median of five warm runs against a named fixture, in a fresh process per measurement —
the method 006 and 007 both used, so the figures are comparable. Pre-feature figures are
**re-measured on this branch** before the strictness lands (SC-024a); 006's numbers are superseded and
007's `baseline.md` supplies only the suite figure.

**What gets measured, against FR-PERF-002's three budgets:** show-document load (≤ 200% and ≤ 50 ms
absolute for the corpus's largest show document), each configuration domain's load (≤ 110%), and the
suite's per-test figure (≤ 110% of 24.79 ms).

**The show fixture is named here, not left to the measurer**:
`tests/data/corpus/cuems-engine/projects/complex_test/script.xml` — **24,183 bytes**, the corpus's
largest show document, confirmed loadable (median 11.76 ms, indicative, Python 3.13, 2026-08-28).

---

## T068 — FR-029c's independence claim, measured

**Claim under test.** The `ActionType` narrowing (FR-029a, deleting `fade_in`/`fade_out`, T066) is a
**separate decision** from the `fade_profiles` deletion (FR-007a, T018–T021) — the two share the word
"fade" because both were early, competing approaches to the same eventual envelope concept, not because
one depends on the other.

**Method.** A scratch `git worktree`, checked out at `7013489` (the tip before any Phase 1 commit —
confirmed by inspection that this repository's actual commit graph interleaves the "setup" commit
*after* ITEM A, not before, so the naive "parent of the setup commit" checkout would already have
carried ITEM A's fade-profile deletion; `7013489` is the true pre-Phase-1 state). T066's `ActionType`
edit alone was applied on top — nothing from T018–T021. Run against the worktree's own `src/` via
`PYTHONPATH`, since the pyenv environment's editable install otherwise shadows it with the main
checkout (the CLAUDE.md-documented venv gotcha, encountered here in miniature).

**Result, 2026-09-02.** With `fade_in`/`fade_out` deleted and `FadeProfileType`/`FadeProfilesWrapperType`/
`FadeParameterType`/`FadeProfile.py`/the five `fade_profile_*` T2 rules all still present and unmodified:

- `tests/unit/test_mediacue_fade_profile.py`, `tests/integration/test_mediacue_fade_roundtrip.py`,
  `tests/contract/test_fade_rules_corpus.py`, `tests/contract/test_mediacue_fade_schema_contract.py`,
  `tests/integration/test_mediacue_fade_performance.py` and `tests/unit/test_t2_registry.py` — **96
  passed**, 0 failed. The fade-profile surface stays bound and validated by all five of its rules with
  no part of FR-007a applied.
- `tests/data/corpus/pre-008/cuems-utils/fade_showcase.xml` (the one corpus document carrying
  `fade_profiles`) round-trips through `CuemsScript.load`/`.save` **byte-identical** to the pre-008
  original in this configuration.

**Conclusion.** FR-029c's independence claim holds on measured evidence, not just by inspection of the
diff. The scratch branch and worktree were discarded after the run (SC-012c); nothing here is carried
into the working tree.
Pinning it is part of the method, because the fixture determines whether the absolute cap can bind at
all: on `fade_showcase.xml` (2,649 B, 3.48 ms) the 50 ms cap sits 14× away and is unreachable, which
would satisfy FR-PERF-002 on paper while measuring nothing. `quickstart.md` named `fade_showcase.xml`
until 2026-08-28; it is not the largest and the substitution was not deliberate.

**Excluded**: the two 24,067-byte `tests/data/corpus/legacy/` documents, which feature 005 recorded as
deliberately rejected at `VideoCueOutput.__init__` → `_classify_output_name`. They are nearly the same
size and would otherwise look like the obvious choice.

**Rationale.** The strictness in FR-037 is intentional despite its cost, but the cost must be a
number, and a number is only meaningful against a baseline measured the same way on the same tree.
Carrying 006's figures forward would compare different suites.

---

## Resolved without research

- **Whether `Media.duration`'s wire changes** — E4 settles it: the field is bound to `_String()`,
  whose `to_wire` returns the object unchanged, so storing a `CTimecode` under the old type would put
  an unserialisable object in the payload. There was never a version of this change that left the
  wire alone.
- **Whether the `"TimecodeType": _String()` binding can be removed** — FR-006 requires this be
  *verified* rather than assumed, because `TimecodeType` survives as the lexical type of the inner
  `<CTimecode>` element (script.xsd:167) and may still resolve there. The verification is a task, not
  a research question.

  **Verified dead, and removed (T016).** `Mapper._decode_field` consults the adapter for a field's
  *own* `xsd_type` **before** considering whether that type has a child to recurse into
  (`mapper.py:154-163`, comment: "treating 'has a child type' as 'recurse into it' leaves every
  timecode as a bare `{'CTimecode': '...'}` dict instead of a `CTimecode` object"). So a field typed
  `CTimecodeType` resolves `ADAPTERS["CTimecodeType"]` (`_CTimecodeAdapter`) and that adapter consumes
  the whole `{"CTimecode": "..."}` subtree in one call — it never recurses into the inner `<CTimecode>`
  element as a separate field, so `ADAPTERS["TimecodeType"]` is never looked up through that path.
  `coercion._resolve` (`coercion.py:135-145`) is the only other adapter-resolution call site, and it
  only iterates the fields of a class **bound to a real model** via the registry; `CTimecodeType` is
  bound `GENERIC` (no model class), so `_resolve` is never invoked for it either. Confirmed
  empirically: walking `derive()` for every complex type across all six schemas finds exactly two
  fields whose `xsd_type` is `"TimecodeType"` — `script.CTimecodeType.CTimecode` and
  `settings.CTimecodeType.CTimecode` — and both belong to complex types with no bound model class, so
  neither reaches an adapter lookup. Before this feature, the **one** live use was `Media.duration`'s
  own field type (bare `cms:TimecodeType`, not wrapped) — T013 promotes exactly that field to
  `CTimecodeType`, which is what removes the last path that ever reached this entry. Removed from
  `ADAPTERS` in `xml/adapters.py`.
- **`create_script()`'s fate** — D25: superseded, output need not stay byte-identical.
