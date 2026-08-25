# Feature Specification: Node model migration — the model comes home to its schema

**Feature Branch**: `007-node-model-migration`
**Created**: 2026-08-21
**Status**: Clarified 2026-08-24 — 5 questions answered; **scope enlarged by decision**: the
schema is edited, `node_type` becomes `node_role` with a real enumeration, and `cuems-common`
joins the feature. Ready for `/speckit.plan`.
**Input**: Bring the node object model and its serializers into `cuemsutils` from
`cuems-nodeconf`. `cuems-utils` already owns `network_map.xsd`, the `NetworkMap` reader and
`ConfigManager`'s network-map integration; only the object model and serializers live in the
other repository, which is why that repository injects classes into this package's module
globals to make serialization work, and why a type-coercion bug fixed here stayed open there.

**Planning context** (authoritative, read before planning):
`specs/planning/xml-rebuild/xml-rebuild-01-audit.md` (findings F1–F24, schema audit X1–X17),
`specs/planning/xml-rebuild/xml-rebuild-02-node-model-ownership.md` (**this feature's charter** — §§4, 7, 9),
`specs/planning/xml-rebuild/xml-rebuild-03-design-inputs.md` (Q11/Q14 rationale),
`specs/planning/xml-rebuild/xml-rebuild-04-object-model.md` (construction paths, measured divergence),
`specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md` (editor↔UI payload contract),
`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §§3.4, 5, 10, 12 (the target design),
`specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md` §6 (this feature's place in the sequence),
`specs/004-xml-serialization-core/migration-map.md` §3 (**the FR-026d break this feature repairs**).

This is feature 4 of 5 in the XML rebuild. It covers phase 6 of the target design (§13) and is
the **intake** feature: it moves ~200 lines of model and serializer code across a repository
boundary and closes the one breaking change feature 004 declared. Feature 008 (consumer
migration) follows and is out of scope here — but is now a **hard successor**, not a follow-up
(FR-030c).

**Settled decisions** (from the planning phase — not reopened by this spec): D1, D2, D5, D9,
D11, D12, D13, D14, D15, Q11→(c), Q14→(i).

**D3 is deliberately relaxed, once.** "Wire-compatible with every XML on disk; no `.xsd` edits"
continues to bind the other five schemas. For `network_map.xsd` it is lifted by explicit
decision recorded in Clarifications: the schema is the sole source of truth, this lands as a
strong rebuild, and the `node_type` → `node_role` rename with a real `NodeRoleType` enumeration
is the migration `cuems-common/CLAUDE.md` already had scheduled. The incoming instruction
"DO NOT CHANGE the node_type wire format" is **superseded** by that decision.

---

## Why this feature exists

Six defects trace to one cause: the node model is maintained in a repository that does not own
its schema (Part 2a §3).

| | |
|---|---|
| **Schema** `network_map.xsd` | `cuems-utils` |
| **Read path** `NetworkMap`, `get_node`, `get_nodes_by_adoption` | `cuems-utils` |
| **Config integration** `load_network_map`, `network_map`, `node_network_map` | `cuems-utils` |
| **Object model** `node`, `node_list`, `NodeType` | **`cuems-nodeconf`** |
| **Serializers** `nodeXmlBuilder`, `node_listXmlBuilder`, `nodeParser`, `node_listParser` | **`cuems-nodeconf`** |
| **Dead landing site** `CuemsNodeDictXmlBuilder` | `cuems-utils`, referenced by nobody |

The consequences are measured, not hypothetical:

- **The model has drifted from its own schema.** `network_map.xsd` declares `role_id`, `alias`
  and `hostname`; the `cuems-nodeconf` `node` class declares none of them, so they survive only
  as untyped dict keys.
- **A type-coercion bug fixed here stayed open there** (F7): `nodeParser` re-implements the
  generic parse loop and drops the `key=` argument that carries string-typed-key protection.
  Fixed in `cuems-nodeconf` `4b6844e` / `0a3ce37` — as a copy, not as an inheritance.
- **`NodeType` is defined twice inside `cuems-nodeconf`** (`CuemsNode.py`, `AvahiTool.py`),
  and neither definition is the schema's — the schema types `node_type` as `NonEmptyString`
  and constrains nothing.
- **Node serialization is broken today.** Feature 004 replaced the implicit `globals()` handler
  lookup with an explicit registry; `cuems-nodeconf` registers its handlers by writing into
  those module globals, so as of the 004 release the assignments still execute and their effect
  is simply gone. Nothing raises and nothing logs. This is FR-026d, declared and pinned by 004,
  **with this feature named as the carrier of the fix**.

This feature is not a refactor with a cleanup attached. It is the repair of a declared break,
and the model migration is how the repair is made durable.

---

## Clarifications

### Session 2026-08-24 (b) — cross-artifact analysis remediation

`/speckit.analyze` raised 16 findings, 1 critical. All are remediated; the six that changed what
gets built are recorded here because each was a decision, not a correction of wording.

- Q: The round trip cannot differ from the corpus "in exactly two ways" — the writer emits no
  indentation and rewrites `xsi:schemaLocation` to the bare filename, while the corpus maps are
  indented and carry two different absolute forms. → A: **Normalise the corpus** to the writer's
  output form first, as a separate reviewable step, and measure the FR-010 diff against the
  normalised documents (FR-010b). This is the treatment the show corpus already received.
- Q: Is `cuemsutils.config` public, given FR-007 demanded a public import path while D15 names
  only `CuemsScript` and `ConfigManager`/`ConfigBase`? → A: **`config/` stays internal.** The
  ported classes land in a new `cuemsutils/tools/NodeList.py`, beside the public configuration
  façade (FR-002b, FR-007). The schema-bound containers stay in `config/` because the registry
  and the coherence check need them there, and because `config/` importing `tools/` would be an
  import cycle rather than a preference.
- Q: What does the conversion do with a role value it does not recognise — FR-014 rejects it at
  validation while the conversion was specified to leave it alone? → A: **Refuse the file as a
  whole**, write nothing, and name the node and value in a diagnostic (FR-011h). A
  half-converted map is a document no requirement describes.
- Q: Nothing required a backup before rewriting operator data in place. → A: **A timestamped
  backup is required**, with a documented restore procedure (FR-011i, SC-011).
- Q: The release gate is documentation only, and `dpkg` may upgrade `cuems-utils` first. → A:
  **Enforce it with versioned package dependencies** (FR-030d, SC-012).
- Q: Is schema item X9 resolved or re-deferred? → A: **Resolved** — `PutType` is deleted from
  `network_map.xsd` with its model class and registry binding (FR-029).

### Session 2026-08-24 (a)

- Q: What does `node_list` denote in `cuemsutils`, given feature 006 landed a class of that
  name bound to the schema's `NodeDictType` while `cuems-nodeconf`'s `node_list` is a MAC-keyed
  working set? → A: Option A — `node_list` stays the schema container; the MAC-keyed working
  set lands under a distinct name in the same configuration domain, carrying the role
  selections. `cuems-nodeconf`'s consumers of both types are reformatted to match, and
  `CuemsNode.py` moves into `cuemsutils` in full, exposed as a configuration-like object for
  `cuems-nodeconf` to consume.
- Q: Does the settled constraint "no `.xsd` edits, wire-compatible with every XML on disk"
  (D3) still bind this feature? → A: **Relaxed for `network_map.xsd` only.** The schema is the
  sole source of truth and this lands as a strong rebuild, so any label or parameter name in
  that schema may be rewritten and the byte-identity requirement is lifted for network-map
  documents. D3 continues to bind the other five schemas unchanged.
- Q: What replaces `node_type`? → A: The element is renamed **`node_role`**, typed
  **`cms:NodeRoleType`**, and `NodeRoleType` is added to `network_map.xsd` as a real
  enumeration — retiring the `NonEmptyString` typing that let the `NodeType.<name>` spelling
  become permanent by accident. This supersedes the incoming instruction that the `node_type`
  wire format must not change: the format change is now **in scope and required**.
- Q: What values does `NodeRoleType` enumerate? → A: Option B — `controller`, `node`,
  `firstrun`. This completes the controller/node standardization `cuems-common/CLAUDE.md`
  already declares (which names `<node_type>NodeType.master|slave</node_type>` as pending
  "serialized enum, XSD migration" — the migration this feature performs), and aligns the role
  vocabulary with `role_id`'s existing `controller` / `nodeNN` values. `master`/`slave` are
  **not** accepted as synonyms in the enum.
- Q: How do the `network_map.xml` documents already on disk migrate? → A: Option A — **hard
  cutover**. The schema declares `node_role` only, with no transitional acceptance of the old
  element, and `cuems-common`'s package upgrade runs a one-shot idempotent conversion of
  `/etc/cuems/network_map.xml` before any component reads it. The library does not accept what
  the schema rejects, and no dual-spelling state exists in any release.
- Q: What types does a node object hold in memory? → A: Option A — **fully typed, for
  `network_map` only**: the role is an enum member, `adopted`/`online` are `bool`, `uuid` is a
  `Uuid`, all converted at the document boundary. This is a declared single-schema exception to
  feature 006's "config decoding runs no adapters" rule, made now because the consumers of
  those values are being migrated for the rename regardless, and because the schema already
  types `adopted`/`online` as `BoolType` — D2 makes `bool` the derived answer. The other four
  config schemas keep 006's behaviour untouched.
- Q: Which repositories does this feature edit? → A: Option C — `cuems-utils`,
  `cuems-nodeconf` and `cuems-common`. The atomic unit is the schema and everything that writes
  or ships it: the schema itself, `cuems-common`'s mirrored copy plus the upgrade conversion
  and its three controller-selecting tools, and `cuems-nodeconf` as the sole writer.
  `cuems-engine` and `cuems-editor` are readers and migrate in feature 008. **No release ships
  between 007 and 008.**

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The node model lives where its schema lives (Priority: P1)

A maintainer adding a field to `network_map.xsd` finds the Python model for that schema in the
same repository, declares the field once, and a coherence check tells them if the two ever
disagree again. A consumer reading a network map gets node objects with declared fields — not
raw nested dicts whose keys are whatever the document happened to contain.

**Why this priority**: every other story depends on the model existing here. It is also the
story that closes the measured drift: the three identity fields the schema declares and the
current model omits.

**Independent Test**: load each of the three corpus `network_map.xml` documents and assert the
result is composed of node objects whose declared field set equals the schema's — including
`role_id`, `alias` and `hostname` — with the same values the pre-feature goldens recorded.

**Acceptance Scenarios**:

1. **Given** a `network_map.xml` containing two nodes, **When** it is loaded through the public
   configuration surface, **Then** each node is a declared-field model object, not a plain dict.
2. **Given** a node element carrying `role_id`, `alias` and `hostname`, **When** it is loaded,
   **Then** those three values are reachable as declared fields of the node object.
3. **Given** a node element that omits all three identity fields, **When** it is loaded, **Then**
   the object carries no keys for them — it does not materialise three empty strings.
4. **Given** the node model and `network_map.xsd`, **When** the coherence check runs, **Then**
   the declared field set and the schema's content model are equal as sets.
5. **Given** a loaded network map, **When** a caller asks for a node by UUID, **Then** it
   receives a node object and an unambiguous error if no such node exists.

---

### User Story 2 - Node serialization works again, through the one engine (Priority: P1)

`cuems-nodeconf` writes `network_map.xml` on every adoption, every discovery pass and every
node-type election. Since the 004 release that write silently stops going through the node
handlers. This story makes reading **and writing** a network map a first-party capability of
`cuemsutils`, served by the same schema-derived engine that serves show documents — which is
what makes the repair permanent rather than re-injected.

**Why this priority**: it is the declared break. Without it, the migration moves code but leaves
the ecosystem's node persistence broken.

**Independent Test**: take each corpus `network_map.xml`, load it to objects, write it back, and
compare bytes; assert no module-globals injection is required anywhere in the chain.

**Acceptance Scenarios**:

1. **Given** a corpus `network_map.xml`, **When** it is loaded to objects and written back
   without modification, **Then** the output differs from the input only by the `node_role`
   rename and the role-value mapping, and in no other byte.
2. **Given** a node whose role is the controller, **When** the map is written, **Then** the
   document contains `<node_role>controller</node_role>` and no `<node_type>` element.
3. **Given** a written map, **When** it is validated against the updated `network_map.xsd`,
   **Then** a role value outside `controller` / `node` / `firstrun` is rejected by the schema —
   the constraint the previous `NonEmptyString` typing never applied.
4. **Given** the library's own read and write path for network maps, **When** the whole corpus
   is exercised, **Then** no deprecation warning is emitted and no handler class is looked up
   through a module namespace.
5. **Given** a written network map, **When** it is validated against `network_map.xsd`,
   **Then** it validates — including for a node named `none` and a `role_id` of `n`.

---

### User Story 3 - A deployed node survives the rename (Priority: P1)

An operator upgrades a running installation. Their `/etc/cuems/network_map.xml` — which records
which machine is the controller, which nodes are adopted, and the operator-assigned aliases —
was written before the rename and is invalid against the new schema. The upgrade converts it in
place, before anything reads it, and the cluster comes back with its topology intact.

**Why this priority**: the rename is unshippable without it. A schema change that invalidates
every file on every deployed node is a data-loss event unless the conversion is part of the
same release, and the conversion is what makes the hard cutover a decision rather than a risk.

**Independent Test**: take a pre-rename `network_map.xml`, run the conversion, validate the
result against the updated schema, run the conversion again and assert the bytes are unchanged.

**Acceptance Scenarios**:

1. **Given** a `network_map.xml` carrying `<node_type>NodeType.master</node_type>`, **When** the
   upgrade conversion runs, **Then** the file carries `<node_role>controller</node_role>`, every
   other field is untouched, and it validates against the updated schema.
2. **Given** a document that spells the value bare (`master`), **When** the conversion runs,
   **Then** it converts equally — both legacy spellings are handled.
3. **Given** an already-converted file, **When** the conversion runs again, **Then** the bytes
   are unchanged and the upgrade succeeds.
4. **Given** no `/etc/cuems/network_map.xml` at all, **When** the conversion runs, **Then** the
   upgrade succeeds without error.
5. **Given** a converted map, **When** the controller-selecting tools run, **Then** chrony
   source selection and log collection resolve the controller's IP as before.
6. **Given** a legacy document that never passed through the conversion, **When** a component
   reads it, **Then** it fails with a message naming the migration — not with a generic
   structural complaint.

---

### User Story 4 - The coercion guard becomes first-party (Priority: P2)

A node named `none`, a `role_id` of `n`, an `alias` of `off`, a `hostname` of `007` — all are
values an operator can legitimately enter, and all were being type-guessed into `None`, `False`,
`False` and `7`. The first three validate against the schema, so they wrote to disk and silently
replaced operator data; the fourth produced `<name/>` and a hard validation failure on write.
The guard exists in `cuems-nodeconf` as a copy of a fix made here. This story makes it a
property of the library that owns the schema.

**Why this priority**: it is a data-integrity guarantee with an existing 106-case test, and it is
the concrete evidence that the split was costing correctness.

**Independent Test**: run the ported regression suite against the library's own node read path;
it must pass without importing anything from `cuems-nodeconf`.

**Acceptance Scenarios**:

1. **Given** a node field the schema types as text and a value drawn from the boolean/null
   vocabulary (`none`, `n`, `y`, `off`, `on`, `no`, `yes`, `true`, `false`, `0`, `1`, `007`,
   `42`, `null`), **When** the node is read, **Then** the value is unchanged and still text.
2. **Given** a node named `none`, **When** the map is written, **Then** `<name>none</name>` is
   emitted and the document validates.
3. **Given** `role_id="n"`, `alias="off"` and `hostname="007"`, **When** the node is read and
   written back, **Then** all three survive verbatim.

---

### User Story 5 - `cuems-nodeconf` stops owning a model it cannot maintain (Priority: P2)

`cuems-nodeconf` deletes its node model and its serializers, imports them from `cuemsutils`, and
stops writing into another package's module namespace. What remains there is what belongs
there: discovery, adoption and orchestration.

**Why this priority**: the migration is only complete when the source copy is gone. Two copies of
a model is the state this feature exists to end, and leaving the old one in place would recreate
the drift within one release.

**Independent Test**: in the `cuems-nodeconf` working branch, `NodeXmlBuilders.py` and
`CuemsNode.py` are absent, no assignment into a `cuemsutils` module namespace exists anywhere,
and the repository's own suite is green against the new `cuemsutils`.

**Acceptance Scenarios**:

1. **Given** the `cuems-nodeconf` working branch, **When** the sources are searched for
   assignments into a `cuemsutils` module namespace, **Then** there are none.
2. **Given** `cuems-nodeconf`'s adoption flow, **When** a node is adopted and the map written,
   **Then** the resulting document is schema-valid and carries the adopted node's new state.
3. **Given** `cuems-nodeconf`'s enum usages, **When** the sources are searched for a node-type
   enum definition, **Then** exactly zero are defined locally and all usages resolve to the
   `cuemsutils` definition.
4. **Given** `cuemsutils`, **When** it is searched for a public means of registering an external
   builder or parser class, **Then** none exists and none is added.

---

### User Story 6 - Adopted-node selection stops mutating its input (Priority: P3)

`cuems-engine` avoids the library's own `get_nodes_by_adoption` and re-implements the selection
inline, with a comment saying why: the library function rewrites `adopted` and `online` inside
the caller's data as a side effect of answering a question. This story gives it a non-mutating
answer to reach for.

**Why this priority**: it is a small, self-contained correctness improvement, it is named in the
target design's consumer-migration table, and this is the feature that owns the node collection
it operates on. It delivers value on its own but nothing else depends on it.

**Independent Test**: call the replacement on a loaded network map, then assert the map's values
are unchanged by the call while the returned selection is correct.

**Acceptance Scenarios**:

1. **Given** a loaded network map, **When** adopted and unadopted nodes are selected, **Then**
   the map's own node values are identical before and after the call.
2. **Given** a map where `adopted` is recorded as text, **When** the selection runs, **Then**
   nodes are partitioned correctly without the stored values being rewritten.
3. **Given** the existing mutating function, **When** this feature ships, **Then** it still
   behaves as it does today or is retired with a stated migration — its removal is not silent.

---

### Edge Cases

- **A role value the enumeration does not contain.** Previously `NonEmptyString` accepted
  anything and `cuems-nodeconf` logged and silently demoted to slave. After FR-011 this is a
  schema error, and the silent demotion must not survive the migration.
- **A legacy document reaching a converted system.** Both `NodeType.master` and bare `master`
  exist in the wild. Neither validates after the cutover; both must be handled by conversion
  (FR-011d), and the failure a system sees if conversion did not run must name the migration.
- **A document that arrives without ever passing through the upgrade.** An operator-restored
  backup, an image built before the release, or a node re-joining after a long absence.
- **A node missing a field `cuems-nodeconf` treats as required.** The write path there raises if
  `uuid`, `mac`, `name`, the role or `ip` is `None`; the schema's own cardinality is the
  authority in `cuemsutils`, and the two must be reconciled explicitly rather than by accident.
- **An empty `<node_list/>`.** A first-run controller writes a map with no nodes yet.
- **Duplicate MAC or duplicate UUID across nodes.** The schema forbids neither. Node identity is
  keyed on UUID in the adoption model and on MAC in the discovery collection.
- **The `schemaLocation` attribute at the document root.** Present in every corpus network map, in
  **two different forms** (`/etc/cuems/network_map.xsd` and `https://stagelab.coop/cuems/network_map.xsd`),
  retained as an undeclared key by the config decode path — and rewritten to the bare filename by
  the writer (feature 006's F24 fix). It is one of the two reasons the corpus needs normalising
  before a round-trip diff means anything (FR-010b).
- **Corpus documents stored in a form the writer does not produce.** The network maps are
  4-space indented; the writer emits no indentation. The show corpus was normalised to the
  writer's output form when its byte-identity contract was established; the network maps never
  were, because no config write path existed until this feature.
- **`PutType` in `network_map.xsd`.** Declared, referenced by no element, bound to a model class
  by feature 006. Schema item X9 — **resolved** in this feature, since this schema is being
  edited (FR-029).
- **A conversion that meets a role value it does not recognise.** Neither convertible nor safely
  left alone: converting it would invent data, leaving it produces a file the schema rejects
  (FR-011h).
- **A `cuems-nodeconf` node discovered but never persisted.** The Avahi listener constructs node
  objects for hosts that may never reach a file; the migrated model must be constructible
  directly, not only by decoding a document.

---

## Requirements *(mandatory)*

### Ownership and the model itself

- **FR-001**: `NodeType` — the `master`/`slave`/`firstrun` vocabulary — MUST have exactly one
  definition, and it MUST live in `cuemsutils`'s configuration domain. The two definitions in
  `cuems-nodeconf` MUST be removed and all their usages resolved to the migrated one.
- **FR-002**: Two distinct collection types MUST exist in `cuemsutils`'s configuration domain,
  under distinct names: `node_list` keeps the meaning feature 006 gave it — the schema's
  `NodeDictType`, the document's ordered list of `<node>` children — and the MAC-keyed working
  set that `cuems-nodeconf` calls `node_list` today lands under its own name, carrying the role
  selections. Neither name may be applied to both shapes.
- **FR-002a**: The whole of `cuems-nodeconf`'s `CuemsNode.py` MUST move into `cuemsutils` and be
  exposed for `cuems-nodeconf` to consume. `cuems-nodeconf`'s own consumers of `node` and the node
  collection are reformatted to the migrated shapes rather than being preserved by compatibility
  aliases; the `CuemsNode`/`CuemsNodeDict` backwards-compatibility aliases MUST NOT be carried
  across.
- **FR-002b**: The ported classes MUST land in a **new module `cuemsutils/tools/NodeList.py`**,
  beside `ConfigBase` and `ConfigManager` — the public configuration façade under D15. The
  schema-bound containers stay in `cuemsutils/config/`, which the registry and the coherence
  check require and which stays **internal** (FR-007). `tools/NodeList.py` imports from `config/`
  and never the reverse: `xml/registry.py` imports `config/` and `tools/ConfigManager.py` imports
  `xml/`, so the opposite direction is an import cycle, not a preference.
- **FR-003**: The `node` model MUST declare the three identity fields `role_id`, `alias` and
  `hostname` that `network_map.xsd` declares and the current `cuems-nodeconf` model omits.
- **FR-004**: A node model object MUST be constructible directly from field values, not only by
  decoding a document, because discovery constructs nodes that are never persisted.
- **FR-005**: The node models MUST be declared-field model objects of the same kind as every
  other model in the package — same base, same declared-field mechanism, same projection to a
  wire dictionary — so that no consumer has to treat a node as a special case.
- **FR-006**: A coherence check MUST assert set equality between the node model's declared field
  set and `network_map.xsd`'s content model, so this class of drift cannot recur unnoticed.
- **FR-007**: `cuemsutils.config` MUST stay **internal** — it exports nothing publicly and joins
  `cuemsutils.xml` on the internal side of Q14→(i). The one public node import path is
  `cuemsutils.tools.NodeList`, which MUST be stable and MUST be named in the migration guide's
  consumer section (FR-027a). A consumer that reaches into `cuemsutils.config` is using an
  internal module, and the guide MUST say so.
- **FR-007a**: The public API snapshot golden MUST be updated to record the surface this feature
  adds — `tools/NodeList.py`'s exports and `ConfigManager.save_network_map` — with a recorded
  justification and an enumerated diff, following the ceremony feature 006 established for the
  only two goldens it modified. Adding public surface without updating that snapshot is a suite
  failure, not an oversight.

### Serialization

- **FR-008**: Reading a network map MUST go through the same schema-derived engine as every
  other document type. No separate parse loop for nodes may remain.
- **FR-009**: Writing a network map MUST be a first-party capability of `cuemsutils`, served by
  the same schema-derived engine. Today no working configuration write path exists here, and
  `cuems-nodeconf` cannot write a valid map without one.
- **FR-010**: Byte-identity is **relaxed for network-map documents only**, and replaced by a
  *declared transformation* measured against the **normalised** corpus (FR-010b): loading a
  normalised corpus `network_map.xml` and writing it back unmodified MUST produce output that
  differs from the input in exactly two ways — the `<node_type>` element is spelled
  `<node_role>`, and its value is mapped to the new enumeration. Every other byte MUST be
  unchanged, and the diff MUST be asserted as that exact set rather than waived.
- **FR-010b**: The corpus network maps MUST first be **normalised to the writer's output form** —
  no indentation, and `xsi:schemaLocation` carrying the bare schema filename — because they are
  stored in a form the writer does not produce and never were normalised, no config write path
  having existed before this feature. The show corpus received exactly this treatment when its
  byte-identity contract was established. Normalisation MUST be a separate, reviewable step whose
  diff is recorded before the rename lands, so the two transformations are never conflated:
  without it "differs in exactly two ways" is unachievable, and the failure would surface only
  after the schema, model and write path were all built.
- **FR-010a**: D3's byte-identity requirement continues to bind the other five schemas
  unchanged. No `.xsd` other than `network_map.xsd` is edited, and no show or settings document
  changes by a single byte.
- **FR-011**: `network_map.xsd` MUST rename the `<node_type>` element to **`<node_role>`** and
  type it **`cms:NodeRoleType`**, a new `xs:simpleType` enumerating exactly `controller`,
  `node` and `firstrun`. The `NonEmptyString` typing that allowed any text — and so let the
  `NodeType.<name>` spelling become permanent unnoticed — MUST be gone.
- **FR-011a**: A node object MUST hold **typed** values in memory: the role as an enum member,
  `adopted` and `online` as booleans, `uuid` as the library's UUID type. Conversion happens at
  the document boundary through an explicitly declared rule per field, never as a side effect
  of which string conversion the serializer happens to call. The schema's enumeration is the
  authority on accepted role values; the model MUST NOT accept one the schema rejects.
- **FR-011a-i**: This typing is a **declared exception scoped to `network_map`**, and it MUST
  be recorded as such where feature 006 recorded the opposite rule. The other four
  configuration schemas keep decoding without adapters, and their recorded goldens MUST NOT
  change by a single value.
- **FR-011b**: The mirrored copy of `network_map.xsd` shipped by `cuems-common` at
  `/etc/cuems/network_map.xsd` MUST be updated in the same coordinated release. A node running
  the old mirrored schema against a new document, or the reverse, MUST NOT be a supported
  intermediate state — it MUST be named as a release-ordering constraint.
- **FR-011c**: The migration of documents already on disk is a **hard cutover**. No release
  accepts both spellings: the schema declares `node_role` only, and neither the schema nor the
  library tolerates `<node_type>` in any form. A legacy document MUST fail validation with a
  message that names the migration, not with a generic structural complaint.
- **FR-011d**: A one-shot, **idempotent** conversion of `/etc/cuems/network_map.xml` MUST run
  during package upgrade, before any component reads the file, and MUST be owned by
  `cuems-common` — the package that owns `/etc/cuems/`, ships the default map and mirrors the
  schema. It MUST be implemented with the standard library only, because tools installed under
  `/usr/bin` cannot import `cuemsutils` (the shared-venv rule). Running it twice MUST be a
  no-op; running it on an already-converted or absent file MUST NOT fail the upgrade.
  **Its ordering relative to the services that read the map at startup is feature 008's** — see
  FR-011d-ii.
- **FR-011d-i**: The conversion MUST emit **positive evidence that it ran and what it did** — how
  many nodes were converted, and where the FR-011i backup was written — not only diagnostics on the
  exceptional paths. Silence on success is indistinguishable from never having run, and an operator
  debugging a cluster months later has no other way to tell "this file was already in the new
  format" from "the conversion never reached this node". Each of the four outcomes — converted,
  already converted, absent, refused — MUST be distinguishable from the others in that record.
- **FR-011d-ii**: The ordering of the conversion **relative to the systemd services that read the
  map at startup** is **deferred to feature 008** as part of the consumer migration, and MUST be
  recorded in the migration guide as deferred rather than settled here. Both the conversion and
  `dh_installsystemd`'s service restart run in `postinst`, so their relative order decides whether
  a service reads the converted file or the old one — but the services that do the reading are
  `cuems-engine`'s and `cuems-editor`'s, which this feature does not edit (FR-030). Settling it
  here would fix an ordering against consumers that have not yet migrated. Feature 008 owns it
  because it owns those readers.
- **FR-011e**: The conversion MUST be exercised against every corpus network map and against an
  already-converted document, with the resulting file validated against the updated schema.
- **FR-011h**: A role value the conversion does not recognise MUST cause it to **refuse the file
  as a whole**: nothing is written, the file is left byte-identical, and a diagnostic names the
  document, the node and the unrecognised value alongside the accepted ones. It MUST NOT convert
  the recognised nodes and leave the rest — a half-converted map is a document no requirement
  describes. The upgrade still succeeds (FR-011d), and the node then meets FR-011c's
  migration-naming failure at read, which is the loud outcome intended. This resolves the
  otherwise-undefined state where the conversion accepts a file the schema rejects.
- **FR-011h-i**: The operator's path out of a refused file MUST be specified rather than left to
  be inferred. Reading a map the conversion refused MUST **raise the corresponding named error** —
  not a generic structural complaint — carrying the document, the node, the offending value, the
  accepted values and the remedy: edit the value to an accepted one and re-run the conversion.
  Where the offending value is a **recognisable legacy form** that the conversion would otherwise
  have mapped, a **deprecation notice** MUST be emitted naming the replacement, so a value that is
  merely old is distinguishable from one that is meaningless. A diagnostic that names the problem
  without naming the action is half a diagnostic.
- **FR-011i**: The conversion MUST write a **timestamped backup** of `/etc/cuems/network_map.xml`
  beside the original before modifying it, and the restore procedure MUST be documented where an
  operator will look. That file is the only record of node aliases and adoption state on a
  cluster; rewriting it in place with no recoverable prior version is a data-loss risk that no
  other requirement covers. Backups MUST NOT accumulate without bound — the requirement is a
  recoverable prior version, not a history. **Downgrade is not supported and MUST be stated as
  unsupported**: installing a pre-rename `cuems-common` or `cuems-utils` over a converted file
  leaves a document the older schema rejects, and the restore procedure this requirement mandates
  is the only path back. No automatic reverse conversion is provided — a downgrade is an operator
  action that restores the backup.
- **FR-011f**: The three `cuems-common` tools that XPath on `node[node_type='NodeType.master']`
  — `cuems-write-chrony-source`, `cuems-log-collector-url` and `cuems-logs` — MUST be updated
  to the new element and vocabulary in the same coordinated release. They select the controller
  for chrony time sync and log collection, so a stale expression degrades silently rather than
  failing loudly.
- **FR-011g**: `cuems-engine`'s `CONTROLLER_NETWORK_FLAG = "NodeType.master"` and its two
  comparison sites, and `cuems-editor`'s node field list, MUST be accounted for in the
  migration guide with their new values. Those two repositories are not edited here (FR-030).
  The guide MUST additionally record **`cuems-common`'s Avahi discovery surface** as feature 008
  work — the `node_type` TXT record in `etc/avahi/services/cuems.service` and
  `usr/share/cuems/cuems.service.{master,slave,firstrun}`, and the retired vocabulary in the last
  three **filenames** — with the `debian/install` and template-resolution consequences of renaming
  them. That repository *is* edited here, so this entry exists to state what is deliberately left
  for 008 rather than overlooked, and it is what SC-004a's exclusion points at.
- **FR-012**: Node values that the schema types as text MUST never be type-guessed on read. The
  guarded set is stated from `network_map.xsd`: `name`, `ip`, `mac`, `role_id`, `alias`,
  `hostname`. The role field leaves the guarded set because the schema now enumerates it — the
  guard is no longer the mechanism protecting it.
- **FR-013**: The written document MUST validate against the updated `network_map.xsd` for
  every value the regression corpus exercises, including a node named `none`.
- **FR-014**: A role value the schema's enumeration does not contain MUST be rejected at
  validation with a message naming the field and the accepted values. This *replaces* the
  previous tolerate-and-default behaviour: `cuems-nodeconf` logs and falls back to slave today
  precisely because `NonEmptyString` let anything through, and that fallback MUST NOT be
  carried across — an unknown role is now a schema error, not a silent demotion.
- **FR-015**: The write path MUST NOT mutate the objects it is given. `cuems-nodeconf` currently
  builds a separate serialization copy precisely because in-place conversion broke later enum
  comparisons; that workaround must become unnecessary rather than being carried across.

### The declared break, and the machinery it leaves behind

- **FR-016**: Feature 004's FR-026d breaking change MUST be closed: node handler classes are
  bound in the registry like every other type, and `cuems-nodeconf` no longer injects anything
  into `cuemsutils` module namespaces.
- **FR-017**: `cuemsutils` MUST NOT gain a public registration API for external builder or
  parser classes. After this feature no external registrant exists, and the registration
  mechanism 004 removed is not reinstated in any form.
- **FR-018**: Every **orphaned node artefact** MUST be gone. An orphaned node artefact is defined
  as: a symbol, module or test whose subject is the node model or its serialization, which after
  this feature has no caller inside its own repository and no consumer outside it. The two known
  instances are `CuemsNodeDictXmlBuilder` and `cuems-nodeconf`'s `test_xml_roundtrip.py`;
  `CuemsNodeDictParser` was already removed by feature 006 and its absence must stay asserted.
  The definition is stated so the requirement can be *searched against* rather than satisfied by
  the two names it happens to list — a search MUST be run and its result recorded. The search MUST
  cover the **duplicate-named legacy modules** that survive in `cuemsutils/xml/`
  (`Settings.py`/`settings.py`, `XmlReaderWriter.py`/`xml_reader_writer.py`,
  `CMLCuemsConverter.py`/`converter.py`, `Parsers.py`, `XmlBuilder.py`), whose node-facing content
  is otherwise unstated: the recorded result MUST say which of them hold node content and which
  hold none, so "we looked" is distinguishable from "we did not think to look".
- **FR-019**: The contract test that pins the 004 break MUST be updated to assert the repaired
  state rather than deleted, so the record of what was broken and when it was fixed survives.
- **FR-020**: A search of `cuemsutils` and `cuems-nodeconf` for assignments into another
  package's module namespace MUST return nothing, and that MUST be asserted by a test rather
  than checked by hand.

### Consumers of the network map inside this repository

- **FR-021**: `NetworkMap` and `ConfigManager`'s network-map accessors MUST return node objects
  (D12), and the node lookup by UUID MUST return a node object.
- **FR-022**: A non-mutating selection of adopted versus unadopted nodes MUST be available.
  `cuems-engine` works around the existing mutating function today; the replacement is what
  feature 008 migrates it to.
- **FR-023**: Every value read out of `ConfigManager.network_map` whose name or type changes MUST
  be enumerated against its consumer call site — the renamed role field, the three retyped
  fields, and any change to the `{"node": {...}}` wrapper feature 006 recorded as load-bearing.
  Nothing changes incidentally: a change absent from that table is a defect, not an improvement.
  The table lives in the migration guide, whose contents FR-027a enumerates.

### Testing and evidence

- **FR-024**: The 106-case node-field coercion regression test MUST be ported from
  `cuems-nodeconf` and MUST run against `cuemsutils`'s own read path, stating its field list from
  the schema rather than importing it from the implementation. Its assertions that
  `adopted`/`online` decode to booleans and `uuid` to a `Uuid` carry across **unchanged**, since
  FR-011a makes them true here. Its `node_type` cases become `node_role` cases, and the guarded
  text fields are `name`, `ip`, `mac`, `role_id`, `alias`, `hostname` — `node_role` leaves the
  guarded set because the schema now enumerates it.
- **FR-025**: A full-chain test MUST cover `xml → object → json → object → xml` for network maps
  (D14), asserting the `node_role` element name and its enumerated value at both ends.
- **FR-026**: The pre-feature behaviour of every corpus network map MUST be captured before any
  code changes and compared against after, so the FR-010 transformation is a measurement and
  not a claim. The corpus network maps and their recorded goldens MUST be regenerated as part
  of this feature, with the regeneration shown as a reviewable diff whose every line is either
  the rename or the value mapping.
- **FR-027**: Every node symbol moved MUST be accounted for: a table of source symbol → new home
  → status (moved, replaced, deleted) → **the requirement that authorises it**, with nothing
  unaccounted for. The source set is the symbol inventory taken before any edit, so "complete" is
  measurable against a denominator rather than asserted. The authorising-requirement column is what
  makes each row traceable to a decision rather than to the plan alone: a symbol whose movement no
  requirement authorises is a finding, not a row.
- **FR-027a**: The migration guide's required contents MUST be enumerated in **one** place, and
  the requirements that feed it MUST reference that enumeration rather than each restating an
  obligation. The guide MUST contain: the moved-symbol table (FR-027); the public import path
  and the internal-module warning (FR-007); the changed names and types against their consumer
  call sites (FR-023); what **feature 008** must change — `cuems-engine`, `cuems-editor` and
  `cuems-common`'s Avahi discovery surface (FR-028, FR-011g); the release-ordering gate, at node
  *and* cluster scope (FR-030c); the restore procedure and the unsupported downgrade (FR-011i);
  SC-004a's named exclusion list; and the deliberate non-migrations, each with its reason.
- **FR-028**: The guide MUST record what `cuems-engine` and `cuems-editor` must change in feature
  008 as a consequence of nodes becoming objects and the role field being renamed, verified
  against the live call sites rather than transcribed from the planning documents.
- **FR-029**: Schema item X9 is **resolved, not re-deferred**: `PutType` is unreferenced by any
  element in `network_map.xsd` and MUST be deleted from the schema, together with its model class
  and its registry binding. It is distinct from `project_mappings.xsd`'s `PutType`, which is
  untouched. The schema evolution convention MUST also be updated: it records only the "added
  element is optional and carries a model-layer default" rule, and this feature performs
  *renaming*, *constraining* and *deleting* changes it does not cover — each precedent written
  down with the migration pattern it used.

### Cross-repository delivery

- **FR-030**: This feature edits **three** repositories: `cuems-utils`, `cuems-nodeconf` and
  `cuems-common`. `cuems-engine` and `cuems-editor` are not edited here; their reader migration
  is feature 008's, and this feature writes their guide entries.
- **FR-030a**: `cuems-nodeconf` modifications MUST land on a new branch created from
  `feat/nodeconf-reenable` at commit `0a3ce37ab8dd33501c4817fa57fd8e390732967d`, never on
  `main` directly and never by amending that branch. Merging it to `main` is not this feature's
  exit; the exit is a branch that is complete, green and documented.
- **FR-030a-i**: The `cuems-nodeconf` caller inventory (FR-027's denominator) is scoped to
  **`cuemsnodeconf/` — the package directory — deliberately, and the repository root and `tests/`
  are excluded by decision, not by oversight.** That code is partially implemented and nowhere near
  the integration maturity of the other repositories, so inventorying it would measure completeness
  against a moving target. The consequence is stated rather than implied: **the migrated node
  standard and its full testing live in `cuems-utils` exclusively.** `cuems-nodeconf` keeps no node
  model tests of its own — this is why T066 and T078 delete rather than relocate, and why the
  106-case regression suite ports upstream instead of being duplicated. A node-model test added to
  `cuems-nodeconf` after this feature is a regression against this requirement.
- **FR-030a-ii**: Callers that **continue to resolve but become semantically wrong** are a named
  class and MUST be accounted for separately from callers that stop resolving. A caller that stops
  resolving fails loudly at import or attribute access; one in this class keeps running and returns
  the wrong answer. The known members are the `node_type` normalisation in
  `CuemsNodeConf.read_network_map` (normalising a spelling that no longer exists), the role enum
  comparisons that would compare against a retired vocabulary, and `cuems-engine`'s
  `CONTROLLER_NETWORK_FLAG` string comparison. The migration guide MUST list this class explicitly,
  and the inventory MUST be searched for it rather than relying on a failing import to surface it —
  nothing fails when this class is missed.
- **FR-030b**: `cuems-common` modifications MUST land on a new branch created from `rc_1` at
  commit `0be3506f22de6ea2dd6d20fbd211febe7b26c710`, stated to the same precision as FR-030a's
  `cuems-nodeconf` branch point so both are checkable at review rather than one being exact and
  the other being "their own branch". The branch MUST cover the
  mirrored `etc/cuems/network_map.xsd`, the shipped default `etc/cuems/network_map.xml`, the
  upgrade conversion (FR-011d), the three tools (FR-011f), and the documentation that states
  the field contract — `docs/node-identity-contract.md`, `CLAUDE.md` and `README.md` all
  currently document `node_type` and the `NodeType.master` spelling as the contract.
- **FR-030c**: No release of any of the three repositories may ship before feature 008 lands
  the reader migration. The hard cutover has no partially-deployed state that works, and the
  release ordering MUST be stated in the migration guide as a gate, not as advice. The gate MUST
  also cover the **cluster**, not only the node: FR-030d enforces package ordering *within* one
  machine, but a staged rollout that upgrades the controller and leaves a node behind produces two
  machines whose maps disagree on the vocabulary. The guide MUST state whether a staged rollout is
  supported and, if it is not, say that the cluster upgrades as a unit — a per-node guarantee is
  not a per-cluster one, and nothing else in this feature says so.
- **FR-030d**: The ordering MUST additionally be **enforced by versioned package dependencies**
  between the `.deb` packages, not by documentation alone. On a single node `dpkg` is free to
  upgrade `cuems-utils` before `cuems-common`, which produces exactly the partially-deployed
  state FR-030c forbids: a migrated schema and an unconverted file. A gate that only a human can
  observe is not a gate.
- **FR-031**: `cuems-nodeconf`'s remaining use of deprecated read/write entry points MUST be
  migrated to the current public surface as part of its branch work, since the file is being
  edited anyway and the deprecated names are removed in the next release.
- **FR-032**: Avahi discovery, adoption logic and systemd orchestration MUST remain in
  `cuems-nodeconf`. This feature moves what a node *is* and how it is *stored*, nothing about how
  nodes are *found* or *adopted*. The boundary MUST be **checked, not asserted**: the migrated
  surface is searched for discovery, adoption and orchestration symbols and the result recorded,
  so "nothing came across that should not have" is a measurement.
- **FR-033**: The editor↔UI `project_load` payload MUST be shown to be untouched by this feature.
  It is the hard constraint carried from planning Part 2d — the payload is transmitted verbatim
  to the Angular UI — and it is stated here as a numbered requirement because this feature
  *verifies* it, and a verification with no requirement behind it has nothing to trace to. Show
  documents are outside this feature's scope, so the expected evidence is that their goldens are
  byte-identical.
- **FR-UX-001**: Error messages raised on the node path MUST name the document, the node and the
  field at fault, matching the message conventions already used by the configuration accessors —
  a schema failure while loading a network map must be as legible as one while loading settings.
- **FR-PERF-001**: Loading a network map MUST be measured before and after, and MUST NOT regress
  by more than 10% against the pre-feature measurement on the same corpus and machine. The
  package-level per-test suite figure (~27 ms/test, feature 006 baseline) MUST NOT regress by
  more than 10%. Both figures are recorded in this feature's `baseline.md`.

### Key Entities

- **Node**: one machine's identity and state in the CUEMS cluster. Persisted fields: `uuid`
  (stable primary key), `mac`, `name`, `node_role`, `ip`, `adopted`, `online`, and the identity
  trio `role_id`, `alias`, `hostname`. Some fields are live facts (`online`) and some are
  operator data (`alias`); the model does not distinguish them. In memory the role is an enum
  member, `adopted`/`online` are booleans and `uuid` is a UUID (FR-011a).
- **Node role** (formerly referred to as "node type"): the closed vocabulary `controller`,
  `node`, `firstrun`, enumerated by `network_map.xsd` as `NodeRoleType` and enforced by
  validation. It replaces the unconstrained `node_type` element whose `NodeType.<name>` values
  originated in a serialization accident. It is a mutable projection of node identity; `uuid`
  remains the primary key.
- **Node collection**: the set of nodes in a map, in two distinct shapes under two distinct
  names — the document's ordered list of `<node>` children (`node_list`, the schema's
  `NodeDictType`), and the MAC-keyed working set carrying the role selections, which migrates
  in from `cuems-nodeconf` under its own name (FR-002).
- **Network map document**: the root of `network_map.xml`; what `ConfigManager.network_map`
  holds, what `cuems-nodeconf` rewrites on every adoption, and what `cuems-engine` reads adopted
  UUIDs and the controller IP from.
- **Node handlers**: the read and write behaviour for the two node types — currently four classes
  in `cuems-nodeconf` injected into this package's module namespaces, after this feature two
  registry bindings like every other type.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero node model or node serializer code remains in `cuems-nodeconf`: the two source
  files are deleted and every symbol they exported resolves to `cuemsutils`.
- **SC-002**: Zero assignments into another package's module namespace exist across both
  repositories, asserted by test.
- **SC-003**: All three corpus network maps round-trip through the public read and write path
  with a diff of exactly the FR-010 transformation — the element rename and the value mapping —
  and zero other differing bytes.
- **SC-004**: `<node_role>` carries an enumerated value for 100% of nodes and `<node_type>`
  appears in zero written documents, proven by round-trip against the corpus.
- **SC-004a**: Zero occurrences of `node_type` or the `NodeType.` prefix remain across the three
  edited repositories' code, schemas, shipped files and documentation — counted, not reviewed.
  **The count excludes the Avahi discovery surface**, which Assumption 10 scopes out of this
  feature and assigns to feature 008: `cuems-common`'s `etc/avahi/services/cuems.service` and
  `usr/share/cuems/cuems.service.{master,slave,firstrun}`. That exclusion is a named file list, not
  a tolerance — the count is exact over everything else, and the excluded files are enumerated in
  the migration guide as feature 008's work (FR-011g). Without this exemption the criterion
  contradicts Assumption 10 and cannot be met.
- **SC-004b**: A legacy `network_map.xml` converts idempotently: converting twice produces the
  same bytes as converting once, and the result validates against the updated schema.
- **SC-005**: All 106 ported coercion cases pass against `cuemsutils`'s own read path, with no
  import from `cuems-nodeconf`.
- **SC-006**: The node model's declared field set equals `network_map.xsd`'s content model
  exactly — 10 fields, including the three identity fields that are absent today.
- **SC-007**: 100% of moved symbols appear in the migration table with a resolved status; the
  count of unaccounted symbols is zero.
- **SC-008**: `cuems-nodeconf`'s own test suite is green against the migrated `cuemsutils`, with
  a node adoption writing a schema-valid map end to end.
- **SC-009**: Loading a network map does not regress by more than 10% against the pre-feature
  measurement; the suite's per-test figure does not regress by more than 10%.
- **SC-010**: No consumer-visible value read from `ConfigManager.network_map` changes name or
  type without appearing in the migration guide — measured by comparing the recorded
  configuration goldens before and after, not by review.
- **SC-010a**: The four configuration schemas other than `network_map` show zero golden changes,
  and the show-document goldens are byte-identical — the schema edit does not leak, and the
  `project_load` payload is therefore untouched (FR-033).
- **SC-011**: A converted `/etc/cuems/network_map.xml` has a recoverable prior version, and
  restoring it reproduces the pre-conversion bytes exactly.
- **SC-012**: Installing the three packages in any order on one node cannot produce a migrated
  schema beside an unconverted map — enforced by package metadata, demonstrated by attempting the
  out-of-order upgrade.
- **SC-013**: Zero discovery, adoption or orchestration symbols appear in the migrated surface,
  counted against the pre-migration inventory (FR-032).
- **SC-014**: The public API snapshot records exactly the surface this feature adds and nothing
  more, with the diff enumerated (FR-007a).
- **SC-QUALITY-001**: No new lint or type warnings; every public symbol added carries the
  rationale documentation the surrounding modules already carry.
- **SC-TEST-001**: Every requirement with observable behaviour has a test that fails before its
  implementation and passes after, including the FR-026d repair — which must be demonstrated
  failing on the pre-feature state.

---

## Assumptions

1. **The `cuems-nodeconf` working branch is the source of truth for the code being moved.**
   `CuemsNode.py` (~110 lines) and `NodeXmlBuilders.py` (~90 lines) are read from
   `feat/nodeconf-reenable`, which already carries the F7 coercion fix. `main` predates it and is
   not the input.
2. **The starting point is known broken, by design.** On `feat/nodeconf-reenable` node
   serialization does not work against `cuemsutils` ≥ the 004 release. Verifying that break is
   the first step of the work, not an unexpected finding.
3. **`network_map.xsd` is edited, and it is the only schema that is.** D3's no-schema-edits
   constraint is lifted for this one file by explicit decision (Clarifications). The renaming,
   constraining change it undergoes is a new precedent for the schema evolution convention,
   which today covers only additive change.
4. **The network-map write path is new public surface in this feature.** Configuration documents
   have never had a working write path here — the previous generic builder was deleted in feature
   006 as unreachable — so FR-009 adds capability rather than restoring it. It is expected to sit
   on the configuration façade, alongside the accessors, matching how show documents are saved.
5. **Decoding a document yields the list shape**; the MAC-keyed working set is built by a caller
   and is never what a document decodes to.
6. **`cuems-engine` and `cuems-editor` are not edited in this feature.** Their migration is
   feature 008's; this feature writes their guide entries and the release gate that keeps them
   from meeting a converted document before they are ready.
7. **All three repositories' commits are GPG-signed**, per the repository convention.
8. **The existing mutating `get_nodes_by_adoption` stays available** until feature 008 migrates
   its caller, so this feature adds an alternative rather than breaking a working consumer.
9. **The role vocabulary maps to today's values as** `master` → `controller`, `slave` → `node`,
   `firstrun` → `firstrun`. `firstrun` keeps its name because it names a lifecycle state, not a
   cluster role, and nothing in the controller/node standardization displaces it.
10. **`cuems-common`'s Avahi service templates are a separate surface, and they change in feature
    008.** They carry a `node_type` TXT record used by discovery, not by the XML document.
    Discovery is out of scope here (FR-032), so this feature **inventories them and does not edit
    them** — but they are *not* permanently exempt: they carry the retired vocabulary and must
    follow it. Four files are affected — `etc/avahi/services/cuems.service` and
    `usr/share/cuems/cuems.service.{master,slave,firstrun}` — and in the last three the retired
    vocabulary is in the **filename** as well as the contents, so the change reaches
    `debian/install` and anything that resolves a template by name. They are recorded as feature
    008's work (FR-011g) and excluded from SC-004a's count. If the inventory shows any of them
    reads the XML document, it falls under FR-011f and is changed here instead.

---

## Dependencies

- Features 004, 005 and 006 are landed. This feature builds on the schema-derived engine, the
  unified construction path, the configuration model classes feature 006 created as containers,
  and the registry.
- `cuems-nodeconf` `feat/nodeconf-reenable` at `0a3ce37` — the branch point and the code source.
- Feature 004's `migration-map.md` §3 — the specification of what FR-026d broke.
- Feature 006's `config/network_map.py` — the container classes this feature fills in, and the
  boundary comment that reserves this work for feature 007.
- `cuems-common` — owns `/etc/cuems/`, the mirrored schema, the shipped default map, the field
  contract documentation and the three controller-selecting tools. Edited by this feature.
- **Feature 008 is a hard successor, not a follow-up.** The hard cutover leaves no working
  partially-deployed state, so 008 must land before anything ships (FR-030c).

## Out of Scope

- **Avahi/mDNS discovery, adoption logic, role election, systemd orchestration, the
  config-serving protocol** — these stay in `cuems-nodeconf` (FR-032).
- **The `node_type` TXT record in the Avahi service templates** — a discovery surface, not the
  XML document. Inventoried here, **changed in feature 008** (Assumption 10, FR-011g). Four files,
  three of which also carry the retired vocabulary in their filenames. Out of scope for this
  feature is not the same as exempt, which is why they are named rather than waved at.
- **Editing `cuems-engine` or `cuems-editor`** — feature 008 (FR-030).
- **The five other `.xsd` files.** Only `network_map.xsd` is edited; D3 binds the rest
  unchanged (FR-010a).
- **The show-document surface.** `CuemsScript` and the cue model are untouched.
- **Backwards compatibility for `<node_type>`.** No release accepts both spellings, by decision
  (FR-011c). Documents on disk are converted, not tolerated.
