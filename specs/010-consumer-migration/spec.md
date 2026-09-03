# Feature Specification: Consumer migration — one public API, six repositories, one release

**Feature Branch**: `010-consumer-migration`
**Created**: 2026-09-03
**Status**: Draft — no open questions. Q1 (dev-fixture counting), Q2 (per-type constructible
instance) and Q3 (batch-conversion trigger) all answered 2026-09-03; see Clarifications. Ready
for `/speckit.clarify`.
**Input**: Define and execute the consumer migration to the new public API, coordinated as a
single version bump across the CUEMS ecosystem. Feature 007's migration guide is the input
inventory; feature 008's is the second.

**Planning context** (authoritative, read before planning):
`specs/planning/xml-rebuild/xml-rebuild-01-audit.md` (findings F1–F23, schema audit X1–X12),
`specs/planning/xml-rebuild/xml-rebuild-02-node-model-ownership.md`,
`specs/planning/xml-rebuild/xml-rebuild-03-design-inputs.md` (design constraints, Q11/Q14 rationale),
`specs/planning/xml-rebuild/xml-rebuild-04-object-model.md` (construction paths, measured divergence),
`specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md` (editor↔UI payload contract),
`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` (**the target design** — §12 is the
per-repository table),
`specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md` §8 (this feature's cross-repo shape
and decision record) and §10 (standing rules),
`specs/planning/xml-rebuild/xml-rebuild-08-extension-audit.md` (feature 008 evidence E1–E26 —
read its revision table first),
`specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md` (**this feature's charter** —
evidence C1–C12, measured 2026-09-03 *after* 008 landed; it corrects and extends §8),
`specs/planning/xml-rebuild/010-consumer-prompts/` (the runnable per-repository flows derived
from this spec — seven files, one per repository),
`specs/007-node-model-migration/migration-guide.md` and
`specs/008-rebuild-extension/migration-guide.md` (the two input inventories).

This is feature 6 of 6 in the XML rebuild and the last one. It is a **hard successor** to 007 and
008, not a follow-up: 007 renamed `<node_type>` to `<node_role>` as a hard cutover with no
dual-spelling state, and 008 changed `Media.duration`'s type *and* wire shape and made reading
strict — both without editing any consumer. **Nothing in the ecosystem ships until this feature
lands** (007 FR-030c/FR-030d, extended through 008 by D27).

**Settled decisions** (from the planning phase — not reopened by this spec): D1, D2, D3, D5, D9,
D11, D12, D13, D14, D15, D16, D17, D18, D18b, D19, D20, D21, D22, D23, D24, D25, D26, D27, D28,
D29, D30, D31, D32, D33, D34, D35, D36, Q11→(c), Q14→(i). The full text is in
`xml-rebuild-07-speckit-prompts.md` §2.

**Scope shape.** Seven repositories run seven spec-kit flows against one release: `cuems-utils`
(this repository — three library obligations, D16), `cuems-engine`, `cuems-editor`,
`cuems-common`, `cuems-nodeconf`, `cuems-frontend`, `cuems-wsclient`. This document is the
cross-repo contract, the exit criteria and the decision record; the per-repository prompt files
are its execution. Where the two disagree, this document is authoritative.

**Two decisions this feature is executing rather than making** — restated because both are
routinely misremembered:

- **The UI payload constraint is an enumerated delta, not unconditional byte-identity** (C3).
  `cuems-editor`'s `project_load` payload is transmitted verbatim to the Angular UI and stays
  byte-identical to today's **except** for exactly two already-landed, deliberate changes:
  (a) `schemaLocation` is absent — 006's `to_wire()` drops it; (b) `Media.duration` is
  `{"CTimecode": "HH:MM:SS.mmm"}` rather than a bare string — 008's D17/D18b. Every other key,
  the ordering, and the **string** boolean form are unchanged; the UI's
  `enabled === true || enabled === 'True'` dual-read still holds and is still written back as a
  string. `doc_version` is **not** a third change: it is excluded from every wire projection and
  the frontend never sees it. The unconditional wording that stood before 2026-09-03 contradicts
  two of this rebuild's own decisions and MUST NOT be restated.
- **The node model lives in `cuemsutils` exclusively** (007 FR-030a-i). No consumer
  re-implements or re-tests it. A node-model test appearing in a consumer repository during this
  migration is a regression, not coverage.

**The dangerous caller class.** 007 FR-030a-ii distinguishes callers that **stop resolving**
(loud, at import) from callers that **keep resolving and become wrong** (silent, and the suite
stays green). The second class is what this feature searches for; a green suite is not evidence
it is empty. `cuems-wsclient`'s node filter (C1) is the purest instance found so far, and it was
found by reading, not by a failure.

---

## Clarifications

### Session 2026-09-03

Three questions were open at drafting. Each changed scope rather than wording, and two were left
open deliberately by the consumer audit (`xml-rebuild-09-consumer-audit.md`, "What this document
does not settle"). All three are answered.

- **Q1 — Does the ecosystem-wide count reach non-shipped `dev/` code?**
  → **Answered: shipped sources only; the known `dev/` occurrences join the enumerated exempt
  set.** This continues 007's precedent, which counted shipped sources. The four files are named
  rather than covered by a category — `cuems-engine`'s `dev/network_map.xml`,
  `dev/test_xml_files/network_map.xml` and `dev/CuemsEngine_old.py`, and `cuems-nodeconf`'s
  `test_run_nodeconfig.py`. The consequence is accepted and stated: a stale scratch fixture
  survives the migration, so the exempt set has to say *why* each entry is exempt — "not shipped"
  is a different reason from "this code exists to detect the retired spelling", and conflating
  them is how the next sweep loses the distinction. Governs FR-070–FR-073.
- **Q2 — Does the descriptor gain a constructible empty instance per complex type?**
  → **Answered: yes.** The descriptor emits, per complex type, a constructible empty instance
  alongside its five existing facts. This is **new library capability inside a feature that
  otherwise adds none**, and it is recorded as a deliberate exception rather than absorbed: it
  enlarges `cuems-utils`' own share, and it is the only descriptor change this feature sanctions.
  The alternatives were a hand-authored seed in the UI (which leaves a hand-maintained shape that
  can drift from the schema — the exact failure the template cutover exists to end) and cloning
  from a generated example (which works only while the example happens to contain one of every
  cue type). A per-type instance is reusable beyond the one call site that forced the question.
  Governs FR-022a, FR-026 and FR-086.
- **Q3 — Where does the batch document conversion run?**
  → **Answered: an explicit operator command.** Converting a project library is unlike converting
  one configuration file: it is long-running, it is user data, and on a controller it changes what
  is deployed to every node (C11). An operator-triggered run gives progress, a chosen moment and
  no surprise inside a package upgrade. The cost is accepted and stated: an upgrade can leave a
  library unconverted until someone acts, so the library's convert-on-read path — not the batch
  command — is what guarantees an unconverted document still opens. Governs FR-095, and leaves
  FR-094's configuration-document ordering (which stays in `postinst`) as a separate question with
  a separate answer.

A second pass (`/speckit.clarify`, same day) found three further gaps — all of them consumer-side
behaviour that features 007 and 008 deliberately delegated here and that the first draft carried
only as an obligation to "surface" or "verify", without saying what the consumer does:

- Q: When a load repairs a field in a current-version document, does `cuems-editor` write the
  repaired document back to disk? → A: **Never as a side effect of load.** The report is
  surfaced, the file on disk is left as it was, and the repaired form reaches disk only through
  an ordinary user-initiated save. A load stays a read. The accepted cost is that an unsaved
  document is repaired identically on every open and reports the same repair each time; the
  report's own "the file on disk is now stale" flag is what makes that state legible rather than
  confusing. Governs FR-048a–FR-048c.
- Q: What does `cuems-editor` do when a document is unrepairable and the strict load raises
  (D21's third outcome)? → A: **A structured failure message on the same channel as the repair
  report**, naming the document and the failing field. The project stays listed, the session
  survives, and only that one document refuses to open. The rejected alternatives are recorded
  because one of them is tempting: a lenient read-only fallback would preserve today's behaviour
  for corrupt files, but it reintroduces the permissive path 008 deliberately removed and makes a
  second reader for documents the strict path rejects. Governs FR-049–FR-049c.
- Q: What is the rollback plan for this cutover, given that converted documents outlive a package
  downgrade? → A: **Two procedures with an explicit boundary at the conversion.** Before the
  operator runs the batch conversion, rollback is a package downgrade and nothing else — the
  documents are still version 1 and the previous library reads them. After it, rollback also
  requires restoring documents from the conversion backups. Q3's operator-triggered conversion is
  what creates that window, and naming it gives the operator a reason to let an upgrade prove
  itself before converting. A reverse converter was rejected: 008's registry is forward-only by
  construction, and the dropped fade-profile block is not reversible in any case. Governs
  FR-100–FR-104.
- Q: `cuems-frontend` has no packaging and so cannot carry a release-gate edge. How is UI/editor
  compatibility guaranteed across this cutover? → A: **A runtime payload-version handshake.** The
  editor advertises a payload version when a client connects; a UI that does not understand it
  refuses and says so, rather than rendering a wrapped duration as an object. This is the only
  mechanical guard available where packaging cannot reach — the frontend has no `debian/`
  directory — and it catches the cached-browser-bundle case that "they deploy together" does not.
  The cost is accepted: new protocol surface in the two repositories already carrying the most
  work in this feature. Governs FR-105–FR-108.
- Q: What document-library scale should the batch conversion be designed and verified against?
  → A: **Hundreds of show documents per library.** Progress reporting and resumability after an
  interruption are both required; batching and a throughput budget are not. A stage-show library
  is a working set rather than an archive, so this is the scale the tool is built and measured
  for, and SC-017's convert-and-count-every-document verification stays feasible on a real one.
  Governs FR-095c and FR-095d, and sizes the "what does a mid-conversion library look like"
  requirement FR-095 already carried. Governs SC-017b.

A third pass (checklist review, same day) closed two findings `release-readiness.md` raised against
the spec's own text — CHK002 and CHK003, both cases where a requirement could be satisfied by doing
the wrong thing:

- Q: "Byte-identical to today's" has no pinned baseline — after the migration, "today" is gone.
  What is the comparison against? → A: **this repository's golden corpus** (`tests/golden/`), not a
  payload captured at migration time. The goldens were deliberately re-cut during this rebuild
  (D29) and already carry `doc_version="2"` and the wrapped duration, so they *are* the behaviour
  consumers must produce rather than a record of what preceded it — verified 2026-09-03. A fresh
  capture would pin the wrong side of a change made on purpose, and would be unreviewed where the
  goldens are reviewed, versioned and checksummed. **And the payload is not the interface**:
  consumers implement object-to-object, with the projection produced once at the UI edge, because
  the Angular client is the one consumer that cannot hold an object. Governs FR-013a, FR-013b.
- Q: FR-043 never required the editor's raw-dict fixups to keep **catching** what they caught, so it
  was satisfiable by deleting them. Where do they belong? → A: **split by responsibility**, on the
  test of whether a fixup needs anything beyond the document. Dangling-reference nulling needs only
  the document, so it becomes a **library** semantic rule — repairable, reported — and the editor's
  copy is deleted rather than ported. Duration-from-database needs the editor's database, which the
  library has no access to and must not gain, so it **stays in the editor** as an object-level
  operation. Both must still detect what they detect today, measured against the cases the current
  implementation catches. Recorded because the split is not what "make the fixups the library's
  responsibility" reads like at first: one of the two cannot move. Governs FR-043–FR-043d.

---

## User Scenarios & Testing *(mandatory)*

Ten stories, one per coherent slice of the migration. The dependency edges between them are
stated in each story's **Depends on** line and are structural, not advisory — FR-090 makes the
ordering enforceable.

### User Story 1 — A coordinated shutdown stops cutting power to nodes nobody asked to stop (Priority: P1)

An operator triggers a coordinated cluster shutdown through the websocket power bridge. Today the
bridge resolves **zero** nodes, SSHes nowhere, skips its reachability poll outright, and then arms
the relay that cuts mains power — to machines that were never asked to shut down, logging
`"0 nodes to power off: (none)"` at INFO. After this story it resolves the adopted nodes again,
asks them to shut down, polls them, and only then cuts power.

**Why this priority**: it is the only *live safety defect* in the ecosystem, it has been live
since 007 landed, and no test could have caught it — `cuems-wsclient` has no `tests/` directory
at all while its packaging fully configures one. It is also the cheapest flow here and depends on
nothing.

**Independent Test**: run the bridge's shutdown path against a network map containing adopted
nodes and assert the resolved target list is non-empty and matches the adopted set; the same test
MUST fail against the pre-migration string comparison.

**Depends on**: nothing.

**Acceptance Scenarios**:

1. **Given** a `network_map.xml` in the current (`<node_role>`) vocabulary containing two adopted
   non-controller nodes, **When** the bridge resolves its shutdown targets, **Then** both nodes
   are returned.
2. **Given** the same map, **When** the shutdown sequence runs, **Then** the reachability poll
   executes (it is not skipped for an empty list) and the relay is armed only after it.
3. **Given** the pre-migration comparison against the retired string, **When** the same test runs,
   **Then** it fails — proving the test discriminates rather than passing either way.
4. **Given** the migrated repository, **When** its sources are searched, **Then** no private
   network-map reader remains: the map is read through the library's public path.

---

### User Story 2 — The editor process starts against the current library (Priority: P1)

The editor imports a module the library deleted, so it raises `ImportError` at module import and
the process does not start. Nothing else in that repository can be exercised until this is fixed.

**Why this priority**: it is a hard blocker, not a symptom. Every other `cuems-editor` obligation
in this feature is untestable until the process runs, and "the suite is green" says nothing about
a repository whose entry point does not import.

**Independent Test**: import the websocket server module and start the process; it must reach its
listening state without raising.

**Depends on**: nothing (the identifier it needs already exists on a public path).

**Acceptance Scenarios**:

1. **Given** the current library, **When** the editor's websocket server module is imported,
   **Then** no `ImportError` is raised.
2. **Given** the migrated import, **When** the editor's UUID-minting call sites are inspected,
   **Then** all of them source that helper from the same public path the repository already uses
   at its four other sites — the identifier is not re-implemented locally.
3. **Given** the editor starts, **When** a client connects, **Then** the connection completes —
   establishing the baseline that the rest of the editor work is measured against.

---

### User Story 3 — The schema descriptor has a public path (Priority: P1)

A consumer that needs to build a form or a new show object from the schema can reach the
descriptor through the library's documented public surface, for all six schemas, without
importing internal machinery.

**Why this priority**: it is the precondition of Stories 6 and 8 — the editor cannot serve what it
cannot import, and the frontend cannot render forms from a descriptor that has no path. It is
also the story that ends an existing, unrecorded violation: `cuems-nodeconf` imports internal
`xml/` modules today and no feature has ever called that out. It carries the feature's **one**
sanctioned descriptor addition (FR-022a, a constructible instance per complex type), which is
why this story is library work rather than a re-export.

**Independent Test**: for each of the six schemas, obtain the descriptor through the public path
and assert it equals the one the internal path produces; assert the internal package still
exports nothing.

**Depends on**: nothing. **Blocks**: Stories 6 and 8.

**Acceptance Scenarios**:

1. **Given** the public configuration façade, **When** a caller asks for the descriptor of any one
   of the six schemas including the show schema, **Then** it receives one, and for every complex
   type it answers: field name, XSD type, cardinality, the legal value list where the type is a
   restricted enumeration, and the model-layer default.
2. **Given** the same façade, **When** a caller asks for a generated example document,
   **Then** the example generators are reachable from that same public path.
2a. **Given** any complex type in any of the six schemas, **When** a caller asks the descriptor
   for a seed object of that type, **Then** it receives a constructible empty instance carrying
   that type's declared defaults, and that instance validates against its own schema.
3. **Given** the migrated library, **When** the internal XML package's export list is inspected,
   **Then** it is still empty — this story strengthens the internal/public boundary rather than
   weakening it.
4. **Given** the two internal imports `cuems-nodeconf` makes today, **When** the migration guide
   is consulted, **Then** each has a named public equivalent — and where one already exists, the
   guide names it rather than the library adding a synonym.

---

### User Story 4 — The engine reads roles, scripts and durations through the public API (Priority: P2)

The show engine loads scripts through the public show object, compares node roles as typed values
rather than strings, and partitions nodes by adoption without mutating the map it was handed.

**Why this priority**: the engine is where a silently-wrong role comparison decides which machine
is the controller. Three of its call sites are in the "keeps resolving but becomes wrong" class.

**Independent Test**: run the engine's controller-selection and node-partition paths against a
current-vocabulary map and assert the correct node is selected and the input map is unmodified;
each test MUST fail against the retired string constant.

**Depends on**: nothing.

**Acceptance Scenarios**:

1. **Given** a current-vocabulary network map, **When** the engine selects the controller,
   **Then** it selects by typed role, and the same test fails against the retired string.
2. **Given** a map with adopted and unadopted nodes, **When** the engine partitions them,
   **Then** it uses the non-mutating partition and the caller's map is unchanged afterwards.
3. **Given** a show document, **When** the engine loads it, **Then** it loads through the public
   show object rather than a reader/parser pair, and a media duration arrives as a timecode object
   without the engine re-wrapping a string.
4. **Given** the engine's action dispatch, **When** it is inspected, **Then** the handlers,
   dispatch entries and supported-action members left unreachable by 008's enumeration narrowing
   are gone rather than resolving to nothing.

---

### User Story 5 — A published node and a listening node still find each other (Priority: P2)

Node discovery advertises and reads the role vocabulary. The advertised key, the three service
templates in each of the two repositories that own them, the template **filenames**, the packaging
entries that place them, the publisher and the listener all move together.

**Why this priority**: discovery failure is how a cluster loses its topology, and this key cannot
be half-renamed — a listener reading the new key against a publisher writing the old one discovers
nothing. Two repositories own it, and no earlier plan assigned the larger half.

**Independent Test**: run a publisher and a listener from the migrated repositories against each
other and assert the node is discovered with its role; assert no half-renamed combination is
shippable.

**Depends on**: nothing. **Merges simultaneously with**: nothing else — Stories 5 and 7 touch the
same repository and their merges are coordinated.

**Acceptance Scenarios**:

1. **Given** a node published by the migrated publisher, **When** the migrated listener observes
   it, **Then** the node is discovered and its role is read from the new key.
2. **Given** the migrated repositories, **When** the service templates are located, **Then** they
   are found by their new filenames, and the packaging entries that install them point at those
   names.
3. **Given** the listener, **When** its sources are inspected, **Then** the old-key translation
   table is gone rather than retained unused.
4. **Given** the source comments that defer this work to a closed feature, **When** the migration
   completes, **Then** those comments name this feature or are removed.

---

### User Story 6 — The editor serves shows and configuration through the public API (Priority: P2)

The editor loads and saves shows through the public show object, serves the UI its payload through
the public wire projection, serves the schema descriptor over its websocket, and forwards the
library's repair report so a repaired document is never repaired silently.

**Why this priority**: the editor is the ecosystem's only writer of show documents and the only
channel between the library and the UI. It carries five parser call sites, four raw-dict fixups
that predate a now-strict read path, and the repair report's only route to a human.

**Independent Test**: save a project through the editor and reload it; assert the payload matches
today's except for the two enumerated deltas, and assert a document requiring repair produces a
report the client receives.

**Depends on**: Stories 2 and 3.

**Acceptance Scenarios**:

1. **Given** a project saved by the editor, **When** it is loaded and served to the UI, **Then**
   the payload equals today's except that `schemaLocation` is absent and the media duration is
   wrapped — and nothing else moved, including key order and the string boolean form.
2. **Given** the editor's five show-parsing call sites, **When** they are inspected, **Then** all
   five use the public show object, and none constructs a parser or reader/writer directly.
3. **Given** the raw-dict fixups the editor performs before parsing, **When** they are reviewed
   against the library's repair path, **Then** each is either a sanctioned pre-validation step, a
   real object-level operation, or removed because the library now performs it — and none
   duplicates a repair the library already makes.
4. **Given** a document the library repairs on load, **When** the editor serves it, **Then** the
   client receives the repair report as a message, naming what was repaired and to what.
4a. **Given** that same repaired document, **When** the load completes, **Then** the file on disk
   is byte-identical to what it was before the load, and the report says the loaded form and the
   stored form differ.
4b. **Given** the user then saves that project, **When** the save completes, **Then** the repaired
   form is on disk and a subsequent load reports no repair.
4c. **Given** a project whose document is unrepairable, **When** a user opens it, **Then** they
   receive a message naming the document and the failing field, the project list is unaffected,
   and every other project still opens.
5. **Given** the duration-repair tool, **When** it runs, **Then** it still reads the deliberately
   corrupt documents it exists to repair — verified, not assumed — its document-rewriting pass is
   the library's conversion tool rather than a second rewriter, and its media-probing pass stays
   in the editor.
6. **Given** the editor's node field list and network-map reads, **When** they are inspected,
   **Then** they consume the typed role, the boolean adoption/online flags and the typed
   identifier rather than strings.

---

### User Story 7 — The node daemon delegates its network-map logic to the library (Priority: P2)

The configuration daemon adopts, unadopts, merges, refreshes, signs and writes the network map by
calling the library's network-map object rather than its own ad hoc equivalents.

**Why this priority**: 008 built and characterized that object precisely so this swap could be
*measured* rather than argued. The daemon's dispatch has a live UI at the far end of it, so
equivalence is a user-visible property, not an internal one.

**Independent Test**: run 008's characterization tests, ported from this daemon, against the
daemon's post-swap behaviour; the swap is done when they pass unchanged.

**Depends on**: Story 3 (for the two internal imports' public replacements).

**Acceptance Scenarios**:

1. **Given** 008's characterization tests, **When** they run against the migrated daemon,
   **Then** they pass without being edited to accommodate the new API.
2. **Given** an adopt request arriving through the daemon's dispatch, **When** it is handled,
   **Then** the map is updated through the library object and the UI at the far end still reflects
   the change.
3. **Given** the daemon's sources, **When** they are inspected, **Then** the relocated timing
   helper is imported from its current path rather than the warning shim, the two internal
   library imports are gone, and the dead reference in the cleanup path is fixed or removed.
4. **Given** the node model, **When** the daemon is searched, **Then** it neither re-implements
   nor re-tests it — 007 already deleted it here and this feature confirms rather than repeats.

---

### User Story 8 — The UI builds shows and edits configuration from the schema (Priority: P3)

The UI stops cloning a concrete example document to make new objects and reads the schema
descriptor instead; the configuration screens that already exist are ported onto a schema-driven
form renderer with their behaviour preserved; a media duration renders as a duration again.

**Why this priority**: it is the largest single port in the feature and the last user-visible one,
and it is a **port, not a greenfield build** — a network-map editing screen is in daily use and
mixer screens read the mappings payload today. Getting that backwards is how working behaviour
disappears in a rewrite.

**Independent Test**: the characterization tests written **before** the port still pass after it.

**Depends on**: Stories 3 and 6. **Preceded by**: its own characterization tests (D35).

**Acceptance Scenarios**:

1. **Given** the three files this port rewrites, **When** the port begins, **Then** each already
   has characterization tests pinning today's behaviour — including the adopt/unadopt cycle, the
   template reads, and the stored-template round trip.
2. **Given** the migrated UI, **When** a new project or cue is created, **Then** its values come
   from the schema's declared defaults, the drifted local fallback that disagreed with the schema
   is gone, and a new cue's output structure comes from the descriptor's constructible instance
   rather than a cloned example or a hand-authored seed.
3. **Given** a cue with a media duration, **When** the show view renders it, **Then** a duration
   is shown rather than an object placeholder — using the same unwrapping the fade fields already
   use.
4. **Given** the configuration screens, **When** they are used after the port, **Then** adopt and
   unadopt still work end to end, the mixer screens still read their mappings, and a network-map
   edit no longer arrives inside a mappings payload.
5. **Given** the new per-domain messages, **When** they are compared to the existing pair,
   **Then** they generalise the serve-plus-mutate pattern that already exists rather than
   introducing an unrelated one.
6. **Given** a repaired document, **When** the UI receives the report, **Then** it renders it.
7. **Given** the mappings response type, **When** it is inspected, **Then** the required field
   nothing reads is gone.
8. **Given** a UI bundle older than the editor it connects to, **When** it connects, **Then** it
   refuses and says so — it does not render a wrapped duration as an object placeholder.

---

### User Story 9 — An operator upgrades a cluster and it comes back whole (Priority: P3)

An operator upgrades a controller and at least one node. Packages refuse combinations that cannot
work; the document library converts with its backups retained; services read the converted map,
not the old one; and the cluster returns with its topology intact.

**Why this priority**: this is where the release gate stops being prose. Today exactly one edge of
it is mechanically enforced, one repository declares two floors that disagree with each other, and
the mechanical demonstration 007 wrote has never been run because no releasable package existed.

**Independent Test**: install an out-of-order package combination in a sandbox and observe the
package manager refuse it; then upgrade a controller and a node and confirm topology.

**Depends on**: all of Stories 1–8 being merged.

**Acceptance Scenarios**:

1. **Given** an unmigrated consumer and a library that has moved past it, **When** the combination
   is installed, **Then** the package manager refuses it — and the refusal is demonstrated, not
   asserted.
2. **Given** the repository whose two declared floors disagree, **When** they are compared after
   this feature, **Then** they agree.
3. **Given** a node whose configuration document is converted during upgrade, **When** its
   services start, **Then** they read the converted document — the ordering between conversion and
   service restart is decided and recorded, not inherited.
4. **Given** a controller whose document library has been converted, **When** it deploys a show to
   a node, **Then** either the node can read it or the rollout order prevents the combination —
   and the constraint is stated in the rollout plan rather than discovered at show-load time.
5. **Given** a real document library, **When** an operator runs the conversion command, **Then**
   every document is converted — counted, not sampled — each has a retained backup, and the
   operator can see progress while it works.
5a. **Given** a library whose operator has not yet run that command, **When** a show in it is
   opened, **Then** it opens: the library's convert-on-read path carries it, which is why
   deferring the batch run to an operator is safe rather than merely convenient.
6. **Given** a cluster upgraded controller-first and node-first, **When** each comes back,
   **Then** the safe order is the one the rollout plan names and the unsafe one is prevented or
   documented.
7. **Given** an upgraded cluster whose operator has **not** run the conversion, **When** a defect
   forces a rollback, **Then** downgrading the packages is sufficient and no document is touched.
8. **Given** an upgraded cluster whose operator **has** run the conversion, **When** the same
   rollback is needed, **Then** the retained backups restore the library, and the operator can
   determine which of the two cases they are in without inspecting documents by hand.

---

### User Story 10 — The deprecated surface comes out and the guide records what moved (Priority: P3)

Once every consumer is off the old paths, the library deletes them, moves to the release its own
warnings have been promising, and hands over a guide that maps every removed or changed entry
point to its replacement.

**Why this priority**: it is last by dependency and must be — running it early breaks six
repositories at once. It is also the step that physically closes the release gate.

**Independent Test**: count live imports of every deprecated path across all six consumer
repositories on disk and show the count is zero; then delete and run the suite.

**Depends on**: Stories 1–9, all merged.

**Acceptance Scenarios**:

1. **Given** the six consumer repositories on disk, **When** their imports of every deprecated
   library path are counted, **Then** the count is zero — measured, because "the flows are merged"
   is a different claim and the difference is a broken daemon.
2. **Given** that measured zero, **When** the deprecated surface is deleted, **Then** the shim
   modules, the aliases and the deprecated-symbol sites are all gone and the suite is green.
3. **Given** the contract tests that pin the shims' behaviour, **When** they are retired,
   **Then** the spec and guide say so explicitly — a contract test deleted alongside the contract
   it guards is correct here and reads as vanishing coverage if unstated.
4. **Given** the library version after this feature, **When** it is compared to the removal
   release every deprecation warning has named, **Then** they match — or the divergence is
   recorded, because every warning emitted since feature 006 said otherwise.
5. **Given** the migration guide, **When** a reader consults it, **Then** every removed or changed
   entry point maps to its replacement with a before/after example, the sixth consumer repository
   is listed, the ecosystem-wide count carries its enumerated exempt set, and one section states
   which obligation landed in which repository.

---

### Edge Cases

- **A repository is migrated but its own tests never exercised the migrated path.**
  `cuems-wsclient` has no test directory; `cuems-frontend` has five test files across 112 sources
  and none covering the three this feature rewrites. A green suite in either says nothing, which
  is why Stories 1 and 8 require a test that fails against the pre-migration behaviour.
- **A caller keeps resolving and returns the wrong answer.** The whole FR-030a-ii class. Search
  against 007's and 008's inventories; do not wait for a red suite.
- **A document is repaired and nobody is told.** The library deliberately has no notification
  channel. If the editor does not forward the report, or the UI does not render it, the
  three-outcome design silently degrades to one outcome.
- **The same repair is reported on every open.** Under FR-048a a repaired document is not written
  back, so opening it again repairs it again and reports it again. This is correct, and the UI
  must not de-duplicate it into silence — the repetition *is* the signal that the document is
  still unsaved.
- **A project that opened yesterday refuses to open today.** 008's strictness reversal makes this
  reachable for the first time. It is correct behaviour, it is new, and an operator meets it with
  no prior warning unless the guide says so (FR-049c).
- **The duration-repair tool cannot read the documents it exists to repair.** Its purpose is
  loading deliberately corrupt files under a read path that is now strict. Verify, do not assume.
- **A half-renamed discovery vocabulary is shipped.** A publisher and a listener disagreeing on
  the advertised key discover nothing, and the failure is silent at the daemon level.
- **A converted controller deploys to an unconverted node.** Fails at show-load time, not upgrade
  time, and no package manager mediates it.
- **The count reaches zero by deleting a working diagnostic.** Detection and conversion code has
  to name what it detects. The exempt set is enumerated for exactly this reason.
- **The batch conversion is interrupted mid-library.** What an operator sees, what state the
  library is in, and whether the backups are sufficient to resume — and, since the rollback
  boundary is "has this library been converted", what a **partially** converted library answers.
  FR-095c makes resuming a requirement rather than an accident: re-running must finish the
  remainder without re-converting or double-backing-up what already moved.
- **A defect is found after the backups have been reclaimed.** FR-102's retention window is the
  whole protection; if it is shorter than the window in which defects surface, the post-conversion
  rollback procedure cannot be performed at all.
- **A browser holds a cached UI bundle across the upgrade.** The only way a UI can lag an editor
  that serves it, and the reason FR-105 is a runtime check rather than a deployment convention.
- **Two repositories in the discovery cutover merge at different times.** Their specs are separate
  because the repositories are; their merges are not.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Cross-cutting

- **FR-001**: The migration MUST be executed as **one coordinated version bump across seven
  repositories**: `cuems-utils`, `cuems-engine`, `cuems-editor`, `cuems-common`,
  `cuems-nodeconf`, `cuems-frontend` and `cuems-wsclient`. No repository releases independently
  (D27).
- **FR-002**: Every consumer-repository modification this feature makes MUST be described in this
  repository's migration guide (D16), so one document answers what changed where.
- **FR-003**: The node model MUST NOT be re-implemented or re-tested in any consumer repository
  (007 FR-030a-i). A node-model test appearing in a consumer repository is a defect of this
  migration, not coverage it added.
- **FR-004**: Callers in the "keeps resolving but becomes semantically wrong" class MUST be found
  by **searching against 007's and 008's inventories**, not by waiting for a failing suite, and
  each one MUST acquire a test that **fails against the pre-migration value**.
- **FR-005**: The three stale documents that are this feature's own inputs MUST be corrected:
  this repository's project instructions (which describe a sibling repository's node-identity
  work as not started when it has been on a branch since 2026-08-24), `cuems-common`'s project
  instructions (which assign a role-constant migration to a closed feature number), and the two
  `cuems-nodeconf` source comments deferring the discovery-key change to that same closed feature.

#### The UI payload contract

- **FR-010**: The editor's project-load payload MUST remain byte-identical to today's **except**
  for exactly two changes: `schemaLocation` absent, and the media duration carried as a wrapped
  timecode rather than a bare string.
- **FR-011**: Every other key, the key ordering, and the **string** boolean form MUST be
  unchanged. The UI's dual boolean read stays valid and continues to write the string form back.
- **FR-012**: The document-version marker MUST NOT appear in the payload. It is a document
  property, excluded from every wire projection.
- **FR-013**: Payload equality MUST be verified against the **two-delta** statement above, not
  against unconditional byte-identity — which has not held since 008 landed.
- **FR-013a**: The baseline for that comparison is this repository's **golden corpus**
  (`tests/golden/`), not a payload captured at migration time. The goldens were deliberately re-cut
  during this rebuild (D29, and 008's three recorded golden events), so they already carry
  `doc_version="2"` and the wrapped duration — they *are* the behaviour consumers must produce, not
  a record of what preceded it. Capturing a fresh "today's payload" fixture would pin the wrong
  side of a change this rebuild made on purpose, and would be unreviewed where the goldens are
  reviewed, versioned and checksummed.
- **FR-013b**: Consumers MUST implement against **objects, not payloads**. The wire projection is a
  **boundary** artifact, produced once at the UI edge, because the Angular client is the one
  consumer that cannot hold an object. No consumer may manipulate the payload dict internally to
  achieve an object-level result — that is the raw-dict habit D12 exists to end, and FR-043 removes
  its last instance. Payload byte-equality is therefore a **migration-period** check against
  FR-013a's goldens, not the interface consumers are built on.

#### `cuems-utils` — the library's own three obligations (D16)

- **FR-020**: The public configuration façade MUST expose the schema descriptor for **all six**
  schemas, the show schema included.
- **FR-021**: This widening of a configuration-domain object's role to cover the show schema MUST
  be stated in the spec and next to the code, with its reason: the alternative is two public paths
  for one mechanism, and the component that serves configuration forms is the same one that serves
  the show template. A reader who finds a show descriptor on a configuration object must find the
  reason beside it.
- **FR-022**: The published descriptor MUST answer, per complex type: field name, XSD type,
  cardinality, the legal value list where the type is a restricted enumeration, and the
  model-layer default — the same five facts the internal descriptor already produces. This
  feature **publishes** that surface; it does not redesign it.
- **FR-022a**: The descriptor MUST additionally emit, per complex type, a **constructible empty
  instance** — a well-formed object of that type carrying its declared defaults, suitable as the
  seed for a new object. This is the one descriptor capability this feature adds, answering Q2.
  It exists because a nested object is not a field default: a consumer creating a new cue needs
  the *shape* of that cue's output, which no combination of the five per-field facts supplies.
- **FR-022b**: FR-022a MUST be recorded as a **deliberate exception to FR-026**, in the spec and
  beside the code, and MUST NOT be generalised into further descriptor growth. It enlarges this
  repository's own share of the feature; that enlargement is stated rather than discovered.
- **FR-023**: The example generators MUST be reachable from the same public path, since retiring
  the concrete-instance template is what the editor and the UI do with them.
- **FR-024**: The internal XML package's export list MUST stay empty. Nothing in this feature
  weakens the internal/public boundary.
- **FR-025**: Each of the two internal library imports `cuems-nodeconf` makes today MUST have a
  **named, tested public equivalent**. Where a public equivalent already exists, the guide names
  it rather than the library adding a synonym — the deliverable is a stated migration target per
  import, not necessarily new code.
- **FR-026**: The library MUST NOT grow new descriptor capability in this feature **beyond
  FR-022a's constructible instance**, which Q2 sanctions explicitly. Any further gap a consumer
  discovers is **recorded**, not quietly absorbed — the rule this feature follows is that
  descriptor growth is a decision with a name on it, not a side effect of a consumer's need.
- **FR-027**: Apart from FR-022a's addition, the library MUST NOT change what the descriptor
  computes for any existing fact — the five per-field facts are published as they are, not
  recomputed — and MUST NOT change any of the six schemas. FR-022a **adds** an emitted fact; it
  MUST NOT alter, reinterpret or re-derive the five that already exist.
- **FR-028**: The public accessor's **name** is part of the deliverable, not an implementation
  detail: it is the name five other repositories will import for years.
- **FR-029**: The deprecated surface MUST be removed only after a **measured** count of live
  imports across all six consumer repositories on disk returns zero. "The consumer flows are
  merged" is a different claim.
- **FR-029a**: Removal MUST cover all five shim modules, the aliases in the XML package's
  namespace, and every remaining deprecated-symbol site.
- **FR-029b**: The contract tests pinning the shims MUST be retired **deliberately**, with the
  spec and guide stating what replaces them and why deleting them is correct here.
- **FR-029c**: The library version MUST move to the removal release its warnings have named since
  feature 006 — or the divergence MUST be recorded, because otherwise every one of those warnings
  was wrong.
- **FR-029d**: Before deleting either, the two similarly-named parser symbols MUST be
  distinguished: one is a retired alias, the other is a delegating façade contractually required
  to stay silent. They are different symbols.

#### `cuems-engine`

- **FR-030**: The engine MUST obtain show documents through the public show object rather than a
  reader/parser pair.
- **FR-031**: The controller-role constant and both of its comparison sites MUST compare typed
  roles, not the retired string.
- **FR-032**: The online-state comparison against a string MUST follow the same retyping.
- **FR-033**: The engine MUST adopt the library's **non-mutating** adoption partition in place of
  its inline workaround for the mutating accessor, and the caller's map MUST be unchanged after
  the call.
- **FR-034**: The engine MUST consume the media duration as a timecode object, without
  re-wrapping a string.
- **FR-035**: The action handlers, dispatch entries and supported-action members left unreachable
  by 008's enumeration narrowing MUST be removed, not left resolving.
- **FR-036**: The engine's show-distribution path MUST be treated as a **rollout-ordering input**,
  not a code change: a converted controller pushes converted documents to every node it deploys to.

#### `cuems-editor`

- **FR-040**: The editor MUST start against the current library. The import of the deleted
  template module MUST be resolved **first**, before any other editor work, and the identifier it
  also imported MUST be re-sourced from the public helper path this repository already uses at
  four other sites.
- **FR-041**: All **five** show-parsing call sites MUST move onto the public show object — the
  four in the project store plus the fifth in the duration-repair tool, which the first audit pass
  missed.
- **FR-042**: The project load path MUST return the public wire projection, subject to FR-010.
- **FR-043**: The raw-dict fixups performed before parsing MUST be **split by responsibility**,
  not ported wholesale. The dividing question is whether the fixup needs anything beyond the
  document itself: a repair the document alone determines belongs to the library, which owns
  repair (D21); a correction requiring the editor's database belongs to the editor, which owns the
  database. Neither may remain a dict edit ahead of a now-strict read.
- **FR-043a**: **Dangling-reference nulling moves into the library** as a registered semantic rule
  — every `target` and `action_target` MUST resolve to a cue present in the same document, and a
  reference that does not MUST be **repairable**, cleared to the field's default and named in the
  load report. It needs only the document, so under FR-043's rule it is the library's. The editor's
  implementation is **deleted, not ported**; two implementations of one repair is how they drift.
- **FR-043b**: **Duration-from-database correction stays in the editor.** It overwrites a cue's
  media duration from the project database, and the library has no database and MUST NOT gain one.
  It MUST become an **object-level operation** on the loaded show object rather than a dict walk,
  and MUST run at a point the strict read path sanctions.
- **FR-043c**: Whichever side owns a fixup, it MUST still **detect what it detected before** —
  dangling targets and action targets, and durations the database disagrees with. Equivalence MUST
  be measured against the cases the editor's implementation catches today, not asserted from the
  new code's shape. Without this, FR-043 is satisfiable by deleting the fixups entirely.
- **FR-043d**: FR-043a changes behaviour for **every** consumer, not only the editor: a show
  document with a dangling reference now loads with that reference cleared and reported, where
  previously only documents passing through the editor were corrected. This MUST be recorded in the
  migration guide as a deliberate widening — the engine could previously dispatch against a
  reference to a cue that does not exist.
- **FR-044**: The duration-repair tool MUST move off the deprecated reader/parser paths and off
  its private timecode regex; its document-rewriting pass MUST be folded into the library's
  conversion tool rather than kept as a second rewriter; and its media-probing pass stays local.
- **FR-045**: That tool MUST still be able to read the deliberately corrupt documents it exists to
  repair. This MUST be **verified** against the library's repair contract, not assumed.
- **FR-046**: The editor's node field list and network-map reads MUST consume the typed role, the
  boolean adoption and online flags, and the typed identifier.
- **FR-047**: The editor MUST serve the schema descriptor over its websocket, and MUST accept
  configuration-domain saves, generalising the existing serve-plus-mutate message pair rather
  than inventing an unrelated one.
- **FR-048**: The editor MUST forward the library's repair report to the client as a message. A
  repair the user never sees is the outcome the three-outcome design exists to prevent, and the
  library cannot do this half itself.
- **FR-048a**: A load that repairs a document MUST NOT write that document back to disk. Loading
  is a read; the repaired form reaches disk only through a save the user initiated for their own
  reasons. 008 sanctioned persisting a repair *conditional on the report being surfaced first*;
  this feature takes the narrower option and records why — rewriting user data as a side effect of
  opening a project is the silent mutation the three-outcome design exists to prevent, and a
  read-only browse must stay read-only.
- **FR-048b**: The repair report MUST carry, and the editor MUST forward, the indication that the
  file on disk no longer matches what was loaded. Under FR-048a that flag is not informational: it
  is the only thing distinguishing "repaired in memory, disk untouched" from "already fixed".
- **FR-048c**: A document repaired on load and not saved MUST be repaired identically on the next
  load and MUST report the same repair again. The repetition is expected behaviour, not a defect
  to suppress, and the UI MUST NOT treat a repeated report as a duplicate to be swallowed.

#### `cuems-wsclient`

- **FR-049**: When a show document is **unrepairable** and the strict load raises, the editor MUST
  report the failure to the client as a **structured message on the same channel as the repair
  report**, naming the document and the field that failed. The two outcomes share a channel
  because they are the same event class from the operator's side — "the library found something
  wrong with this document" — differing only in whether it could continue.
- **FR-049a**: An unrepairable document MUST NOT take down the session or the project list. The
  project stays listed and every other project stays openable; the failure is attached to one
  document, not to the connection.
- **FR-049b**: The editor MUST NOT fall back to a permissive read for a document the strict path
  rejects. A second reader for exactly the documents the first one refuses is the duplication this
  rebuild exists to end, and 008 removed that path deliberately.
- **FR-049c**: The migration guide MUST record that this outcome is **new user-visible behaviour**
  introduced by 008's strictness reversal: a project that opened before this release can refuse to
  open after it. An operator meeting that for the first time needs it documented, not diagnosed.
- **FR-050**: The private network-map reader MUST be **replaced** by the library's public path,
  not re-spelled to the new element name. A second reader for a schema the library owns is the
  duplication this rebuild exists to end.
- **FR-051**: The shutdown fan-out MUST resolve the adopted nodes again, and the fix MUST carry a
  test that fails against the pre-migration comparison.
- **FR-052**: The reachability poll MUST NOT be skipped as a side effect of an empty target list,
  and the power relay MUST NOT be armed against a set of nodes that were never asked to stop.
- **FR-053**: The repository's library dependency MUST become non-optional and correctly bounded
  in both its Python packaging and its system packaging.

#### Node discovery — `cuems-common` and `cuems-nodeconf`, one cutover

- **FR-060**: The advertised discovery key MUST move to the role vocabulary in **both** owning
  repositories as a single coordinated cutover. No half-renamed state ships.
- **FR-061**: The cutover MUST cover: the shared service definition and its three role-specific
  templates in the first repository; the same three templates in the second; the **filenames**
  that carry the retired words; the packaging entries that install them and anything resolving a
  template by name; the publisher; the consumer's two handling blocks; and the old-key translation
  table, which retires with them.
- **FR-062**: A node published by the migrated publisher MUST be discovered by the migrated
  listener, verified end to end across both repositories.
- **FR-063**: Feature 007's deliberate exclusion of these files from its own scope MUST NOT be
  read as an exemption. Out of scope there is in scope here.

#### `cuems-nodeconf` — the network-map object

- **FR-064**: The daemon's ad hoc adopt, unadopt, merge, refresh, signature and write methods MUST
  be replaced by calls into the library's network-map object.
- **FR-065**: Equivalence MUST be **measured** by 008's characterization tests, ported from this
  daemon, passing unchanged against the new API — not asserted by inspection.
- **FR-066**: The dispatch that receives node modifications MUST be migrated against, and the
  configuration screen at the far end of it MUST keep working.
- **FR-067**: The relocated timing helper MUST be imported from its current path rather than the
  warning shim.
- **FR-068**: The dead reference in the cleanup path MUST be fixed or removed while the file is
  open for this work.
- **FR-069**: The daemon's node model and serializers MUST be **confirmed** done from 007, not
  redone. The remaining nine daemon responsibilities are explicitly **out of scope** (D23); this
  feature leaves their target-design basis intact for a later dedicated feature.

#### The ecosystem-wide count

- **FR-070**: Zero occurrences of the retired element name or the retired type prefix MUST remain
  anywhere in the ecosystem, **counted rather than reviewed** — including the four files 007
  excluded from its own count, `cuems-wsclient`'s five, and `cuems-nodeconf`'s thirty.
- **FR-071**: The count MUST carry an **enumerated exempt set**, listed site by site rather than
  described by category. Code whose *purpose* is detecting or converting the retired spelling has
  to contain it, and a criterion that flags such code instructs the reader to delete a working
  migration diagnostic to make a number reach zero.
- **FR-072**: This repository's own sixteen occurrences are exempt in full and MUST survive: the
  role mapping and the unconverted-document diagnostic in the errors module, the three sites in
  the configuration base that wire that diagnostic into the load path, the prose in the
  network-map configuration module, and the schema comment recording 007's change. The sibling
  repository's conversion command and its tests are exempt on the same grounds.
- **FR-073**: The count MUST cover **shipped sources only**, continuing 007's precedent (Q1).
  The four known non-shipped occurrences MUST be named individually in the exempt set —
  `cuems-engine`'s `dev/network_map.xml`, `dev/test_xml_files/network_map.xml` and
  `dev/CuemsEngine_old.py`, and `cuems-nodeconf`'s `test_run_nodeconfig.py` — not covered by a
  `dev/` wildcard.
- **FR-073a**: The exempt set MUST record **why** each entry is exempt, distinguishing the two
  reasons: *not shipped* (FR-073's four files) and *exists to detect or convert the retired
  spelling* (FR-072's sites). They are different exemptions with different lifetimes — the first
  is a stale fixture that could be cleaned up at any time, the second is code that must keep the
  retired spelling forever — and merging them loses that.

#### 008's consumer-impacting changes

- **FR-080**: Every 008 item with consumer impact MUST be verified against **each live call site
  its migration guide named** — the same discipline 007 required of this feature for the role
  rename.
- **FR-081**: The media duration's **type and wire** change MUST be verified at the engine's
  timecode construction, the editor's read and write paths, and the UI's duration display, which
  MUST unwrap the wrapper the way the fade fields already do.
- **FR-082**: The strict read path MUST be verified at every configuration accessor and the show
  load path.
- **FR-083**: The document-version marker's presence MUST be verified on documents this library
  writes, and its absence verified on every wire projection.

#### `cuems-frontend`

- **FR-084**: Characterization tests MUST exist for the three files this port rewrites **before**
  the port begins, covering at minimum the adopt/unadopt cycle, the five template reads including
  the output-structure clone, and the stored-template round trip.
- **FR-085**: The template-cloning surface MUST move off cloning a concrete example instance onto
  the schema descriptor, across **all four** consuming files.
- **FR-086**: The **three** value-reading sites MUST read the schema's declared values: the master
  volume (whose local fallback already disagrees with the schema's own default), the DMX channel
  map, and the per-type output structure — the third of which is not a field default at all and
  MUST consume FR-022a's constructible instance rather than a hand-authored seed or a clone of a
  generated example (Q2).
- **FR-087**: The media-duration display MUST render a duration rather than an object placeholder,
  copying the unwrapping the fade path already performs.
- **FR-088**: The configuration-domain screens MUST be **ported with their logic preserved**, not
  rebuilt: the network-map editing screen and the two mixer screens that read the mappings payload
  keep working through the port.
- **FR-088a**: The entanglement whereby a network-map edit reaches the UI inside a mappings
  payload MUST be untangled as part of that port, and the characterization tests MUST prove the
  untangling preserved behaviour.
- **FR-088b**: The new per-domain messages MUST generalise the existing serve-plus-mutate pair
  rather than modelling on the serve-only template message; and the new views MUST NOT inherit the
  misleading name of the screen that is called after one domain while editing another.
- **FR-088c**: The repair report MUST be rendered.
- **FR-088d**: The required response field nothing reads MUST be deleted.
- **FR-088e**: The dual boolean check's simplification is an **optional follow-up**, not a
  blocker for this feature.

#### Sequencing and the release gate

- **FR-090**: The task ordering MUST make the dependency chain **structural rather than advisory**:
  the descriptor's public path lands before the editor's and UI's descriptor work, and the
  deprecated-surface removal is unrunnable until the measured import count is zero. A task list
  that permits the removal to start early is a task list that can break six repositories at once,
  and that possibility must not exist in the file rather than being avoided by care.
- **FR-091**: The release gate MUST acquire the **four package edges it is missing**. A lower
  bound cannot express "must refuse a library that has moved past me", which is what the gate
  says; only an upper bound or a break relation can.
- **FR-092**: The one repository declaring two disagreeing floors MUST be reconciled.
- **FR-093**: 007's deferred **mechanical demonstration** MUST be run: install an out-of-order
  combination and observe the package manager refuse it. It was deferred here precisely because no
  releasable package existed before this feature.
- **FR-094**: The ordering between the configuration-document conversion and the service restart
  during upgrade MUST be **decided and recorded**, not inherited. 007 deferred it here because the
  services doing the reading are the ones this feature migrates.
- **FR-095**: The show-document conversion MUST run as an **explicit operator command** (Q3), not
  from `postinst` and not at first boot. Unlike the configuration conversion (one file per node),
  it runs over every document in every library, so the plan MUST still state what happens to a
  library mid-conversion, how backups are retained and reclaimed, and what an operator sees while
  it works.
- **FR-095a**: Because FR-095 leaves a library unconverted until an operator acts, the library's
  **convert-on-read** path — not the batch command — is what guarantees an unconverted document
  still opens. This MUST be verified rather than assumed, and stated in the rollout plan as the
  reason an unconverted library is not a broken one.
- **FR-095b**: FR-094's configuration-document ordering and FR-095's show-document trigger MUST be
  kept as **separate decisions with separate answers**. The configuration conversion stays in the
  upgrade path; the show conversion leaves it.
- **FR-095c**: The conversion MUST be designed and verified against a library of **hundreds** of
  show documents. It MUST report progress and MUST be **resumable** after an interruption —
  re-running it over a partly converted library MUST complete the remainder without re-converting,
  double-backing-up or corrupting what already moved.
- **FR-095d**: Batching and a throughput budget are explicitly **not** required at this scale. If a
  real library is found to be an order of magnitude larger, that is a recorded finding for a later
  decision, not a silent redesign during implementation.
- **FR-096**: The show-distribution ordering constraint (FR-036) MUST be stated in the rollout
  plan alongside the upgrade ordering. The reverse order — nodes first — is safe, because the
  library converts older documents in memory on read.
- **FR-097**: The three cutover classes MUST be kept apart in the plan: 007's role rename and
  008's duration and strictness changes are **hard cutovers with no dual state**, so
  "the library releases first with both APIs live" does not apply to them; it applies only to
  006's show-API deprecations.

#### The UI compatibility edge

- **FR-105**: The editor MUST advertise a **payload version** to a client on connect, and the UI
  MUST verify it before rendering. A UI that does not understand the advertised version MUST
  refuse and say so plainly, rather than rendering a payload it cannot interpret.
- **FR-106**: This payload version is **not** the document-version marker and MUST NOT be confused
  with it. The document marker describes a file on disk and is excluded from every wire projection
  (FR-012); this one describes the editor↔UI message contract and appears only on that link.
- **FR-107**: The payload version MUST change when this feature's two enumerated payload deltas
  land (FR-010), because those are exactly the changes a stale UI mis-renders.
- **FR-108**: FR-105 exists because `cuems-frontend` carries no packaging and therefore **cannot**
  hold a release-gate edge — FR-091 covers four packaged consumers and the UI is not among them.
  The spec records that asymmetry rather than leaving the UI as the one unguarded surface, and it
  is the surface a user actually looks at. A cached browser bundle is the concrete failure this
  catches and a deploy-together convention does not.

#### Rollback

- **FR-100**: The rollback plan MUST be **stated**, as two distinct procedures separated by an
  explicit boundary: whether the operator has run the show-document conversion (FR-095).
- **FR-101**: **Before** the conversion, rollback MUST be a package downgrade and nothing else.
  The documents are still at the previous version and the previous library reads them unchanged,
  so no data operation is required or performed.
- **FR-102**: **After** the conversion, rollback MUST additionally restore documents from the
  backups the conversion retained. The plan MUST state how long those backups are retained and
  when they may be reclaimed, because a retention window shorter than the window in which a defect
  is discovered makes FR-102 unperformable.
- **FR-103**: The boundary MUST be **checkable** — an operator must be able to determine whether a
  given library has been converted, without inspecting documents by hand. A rollback procedure
  that begins "if you converted" and offers no way to answer that is not a procedure.
- **FR-104**: A **reverse conversion MUST NOT be built**. 008's conversion registry is forward-only
  by construction; one of its transformations drops a block and is not reversible; and building one
  would be new library capability in a feature that sanctions exactly one (FR-022a). The rejection
  is recorded so it is not re-proposed as an obvious convenience.

#### Documentation

- **FR-UX-001**: The migration guide is this feature's user-experience deliverable
  (Constitution III) and MUST follow the shape 006's, 007's and 008's guides established: every
  removed or changed entry point mapped to its replacement, with before/after examples, at
  call-site granularity, so a consumer flow can be written against it without reading library
  source.
- **FR-UX-002**: The guide MUST list `cuems-wsclient` as a consumer. Its absence from 007's guide,
  008's guide and the cross-repo plan's repository list is why a silently broken shutdown path
  survived two features; the next ecosystem sweep must reach it by construction, not by memory.
- **FR-UX-003**: The guide MUST carry the ecosystem-wide count **with its exempt set enumerated**
  (FR-071/FR-072).
- **FR-UX-004**: The guide MUST state, in one place, which of this feature's obligations landed in
  which repository — seven flows produce seven task lists and no single view of the whole.

#### Performance

- **FR-PERF-001**: This feature MUST define and validate measurable budgets:
  - This repository's suite baseline is **20.73 ms/test** (2573 passed, 96 skipped, 2 xfailed in
    53.34 s, measured 2026-09-03 on `feat/xml-refactor` @ `7a1893f`). Budgets derive from that
    figure — **not** from 008's recorded 22.06 ms/test, nor from the 20.8 ms/test measured earlier
    the same day at `7c5896c` before two commits landed.
  - Publishing the descriptor MUST cost nothing measurable. If the public accessor eagerly builds
    all six descriptors where the internal path built one lazily, that is a **design error**, not
    a budget overrun to accept.
  - Removing the deprecated surface SHOULD make the suite faster (22 contract tests retire). If it
    does not, something else changed and MUST be explained.
  - The engine's project-load time MUST NOT regress **against 008's post-landing figure**, not
    007's — 008 added validation to that path, and measuring against the older baseline charges
    this feature for 008's decision.
  - Network-map load MUST stay within 007's recorded budget.

### Key Entities

- **Node role** — a node's function in the cluster (controller, node, first-run). A typed value in
  the library; a string in every unmigrated consumer, which is what makes the wrong ones silent.
- **Network map document** — the cluster's node inventory: role, adoption state, online state,
  identifier and addressing per node. One per node, owned by the library's schema, read today by
  five separate readers this feature reduces to one.
- **Show document** — a project's cues and structure, carrying a format-version marker. Converted
  in memory on read when older; converted on disk by a standalone command; distributed
  controller-to-node by the engine, which is a third exposure surface.
- **Schema descriptor** — the machine-readable answer to "what fields does this type have, of what
  type, how many, which values are legal, and what is the default", for all six schemas. Replaces
  a cloned concrete example as the source of new objects and of form structure.
- **Repair report** — the structured record of what a load repaired, converted, and whether the
  file on disk is now stale. Produced by the library, forwarded by the editor, rendered by the UI;
  silent if any link is missing.
- **Discovery advertisement** — the key/value pair one daemon publishes and another reads to find
  a node and learn its role. Owned by two repositories; unusable if half-renamed.
- **Package dependency edge** — the declared relation between an installed library and an
  installed consumer. Only one of five is currently expressive enough to enforce the release gate.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A coordinated shutdown resolves **100%** of adopted nodes as targets (currently 0%),
  and no node has its power cut without first being asked to stop and polled for reachability.
- **SC-002**: The editor process starts against the current library — measured as "imports and
  reaches its listening state", the precondition every other editor criterion depends on.
- **SC-003**: The descriptor is reachable from the public surface for **6 of 6** schemas, and for
  each one the public result equals the internal result — verified per schema, not sampled. Every
  complex type across those six schemas yields a constructible empty instance that validates
  against its own schema — 100% of types, counted, not the one type the UI happened to need.
- **SC-004**: The internal XML package still exports nothing after this feature, and the count of
  consumer imports reaching into internal library modules is **zero** (currently two, in one
  repository, unrecorded by any feature until now).
- **SC-005**: A project saved by the editor loads in the engine and renders in the UI unchanged —
  end to end, with the payload differing from today's in exactly **two** enumerated ways and in no
  other key, order or value form.
- **SC-006**: **Zero** occurrences of the retired element name or type prefix remain across the
  ecosystem outside the enumerated exempt set, counted rather than reviewed; and the exempt set is
  enumerated site by site, with this repository's sixteen intact.
- **SC-007**: Every caller in the "keeps resolving but becomes wrong" class carries a test that
  **fails against the pre-migration value** — the count of such callers found and the count of such
  tests added are equal, and both are stated.
- **SC-008**: **100%** of 008's characterization tests for the node daemon's network-map behaviour
  pass unchanged against the library's object after the swap.
- **SC-009**: All **five** show-parsing call sites in the editor are migrated (four in the project
  store, one in the duration-repair tool), and zero direct parser or reader/writer constructions
  remain in that repository.
- **SC-010**: The duration-repair tool still reads **100%** of the corrupt documents it could read
  before, verified against a fixture set rather than assumed, and the ecosystem contains exactly
  **one** document rewriter.
- **SC-005a**: The payload comparison runs against the **golden corpus**, and the goldens used are
  identified by their checksums — zero payload baselines are captured at migration time.
- **SC-005b**: **Zero** consumer code paths manipulate the wire dict to achieve an object-level
  result; the projection appears once, at the UI boundary, in each consumer that has one.
- **SC-010a**: A show document carrying a dangling `target` or `action_target` loads with that
  reference cleared and named in the report — from **every** consumer, not only through the editor
  — and **100%** of the cases the editor's current implementation catches are caught by the
  library's rule, measured case by case.
- **SC-010b**: The editor retains **exactly one** fixup — the database-sourced duration
  correction — and it operates on the loaded object, not on a dict. Zero dangling-reference code
  remains in that repository.
- **SC-011**: A document repaired on load produces a report that reaches the screen — traced
  end to end through library, editor and UI in a single scenario — and the file on disk is
  unchanged by that load, verified byte-for-byte.
- **SC-011a**: All **three** load outcomes are reachable from the UI and distinguishable there:
  a clean load, a repaired load with its report, and an unrepairable document whose failure names
  the document and the field. One unopenable project leaves 100% of the others openable.
- **SC-012**: A publisher and a listener from the two migrated discovery repositories find each
  other, and **zero** half-renamed combinations are shippable — the templates, filenames,
  packaging entries, publisher, consumer and translation table all move in one cutover.
- **SC-013**: The three files the UI port rewrites carry characterization tests written before the
  port, and **100%** of those tests still pass after it. Adopt and unadopt still work end to end,
  and the mixer screens still read their mappings.
- **SC-014**: New objects created in the UI take their values from the schema's declared defaults;
  **zero** local fallbacks disagreeing with a schema default remain among the migrated sites.
- **SC-015**: An out-of-order package combination is **actually refused** by the package manager
  in a demonstration that is run, not described; the release gate's missing edges are present; and
  the repository with two disagreeing floors has one.
- **SC-015a**: A UI older than the editor it connects to is **refused at connect** and says why —
  demonstrated against a deliberately stale bundle, which is the one incompatibility packaging
  cannot express because the UI has no package.
- **SC-016**: A controller-plus-node cluster upgrade comes back with its topology intact — every
  node discovered, adopted state preserved, and a show loadable on each.
- **SC-017**: **Every** document in a real library is converted, counted not sampled, each with a
  retained backup, and the ordering constraints (conversion vs. service restart; controller vs.
  node upgrade; converted controller deploying to an unconverted node) are each decided and
  recorded rather than inherited.
- **SC-017b**: The conversion completes over a library of hundreds of documents, reports progress
  while it runs, and — interrupted partway and re-run — converts exactly the remainder: zero
  documents converted twice, zero backups written twice, zero documents left in a partial state.
- **SC-017a**: Both rollback procedures are **executed**, not only written: a pre-conversion
  rollback restores service by package downgrade alone, and a post-conversion rollback returns the
  library to its pre-conversion state from the retained backups. The retention window is stated as
  a duration.
- **SC-018**: The measured count of live imports of deprecated library paths across all six
  consumer repositories is **zero** before a single deletion, and the deprecated surface is gone
  after: five shim modules, the namespace aliases and every remaining deprecated-symbol site.
- **SC-019**: The library's version equals the removal release its warnings have named since
  feature 006, or the divergence is recorded in the guide.
- **SC-QUALITY-001**: No new lint, type or deprecation warnings are introduced in any of the seven
  repositories, and each consumer pull request carries evidence of its own green suite. A green
  suite is explicitly **not** accepted as evidence for SC-007.
- **SC-TEST-001**: Every behaviour change in every repository carries a test that fails before the
  change and passes after it. For the two repositories with no meaningful coverage today
  (`cuems-wsclient`, which has no test directory at all, and `cuems-frontend`, with 5 test files
  across 112 sources), the tests this feature adds are the first that could detect the defects it
  fixes.
- **SC-PERF-001**: This repository's suite stays within budget derived from **20.73 ms/test**;
  the descriptor's publication costs nothing measurable; the deprecated-surface removal does not
  make the suite slower; the engine's project-load time does not regress against **008's**
  post-landing figure; and network-map load stays within 007's recorded budget. Each is measured
  and recorded, including any that is exceeded — recorded as exceeded rather than restated as
  passing.

---

## Assumptions

1. **This spec is the cross-repo contract; the per-repository prompt files are its execution.**
   Seven spec-kit flows run against it, five of them in repositories that have no spec-kit today
   and acquire it on their first run. Where a prompt file and this document disagree, this
   document is authoritative (its own §8 says so).
2. **`cuems-utils`' own share is three items, not zero** — the public descriptor path, the
   deprecated-surface removal, and the migration guide. The target design's per-repository table
   has no row for this repository; the cross-repo prompt's completion list has three obligations
   for it. Both are true and the second is the operative one. Q2's answer grows the first of the
   three: it is now "publish the descriptor **and add one capability to it**", which is a larger
   claim than "publish what exists" and is stated here so nobody reads FR-022a as a re-export.
   FR-043a enlarges it once more: the library gains a **semantic rule** it did not have, which is
   neither descriptor capability (FR-026) nor a schema change (FR-027), but is new behaviour on the
   validating read path and must be reviewed as such.
3. **Everything else this feature asks of the library already exists** and is confirmed rather
   than rebuilt: the non-mutating adoption partition, the standalone conversion command, the
   public report types, and the strict load path with its three outcomes. Verified on disk
   2026-09-03.
4. **The two repositories in the discovery cutover merge together.** Their specs are separate
   because the repositories are; a half-renamed intermediate state is forbidden (D33), so the
   merges are coordinated rather than sequential.
5. **Story 1 runs first in practice even though nothing depends on it.** It is last by dependency
   and worst by current state: a live path that cuts mains power to nodes it never asked to stop.
6. **The nine remaining node-daemon responsibilities stay out of scope** (D23). This feature
   consumes the network-map object swap only and leaves the atomization basis intact for a later
   dedicated feature.
7. **The UI's dual boolean check stays.** Simplifying it is an optional follow-up (FR-088e); the
   string boolean form on the wire is unchanged by this feature.
8. **Upgrading nodes before controllers is the safe order** for the show-document conversion,
   because the library converts older documents in memory on read. The unsafe order is
   controller-first with un-upgraded nodes still receiving deployments. Q3's answer narrows the
   exposure without removing it: because the batch conversion is operator-triggered, a freshly
   upgraded controller does not convert its library on its own, so the dangerous combination
   arises when the operator runs the conversion — a moment they choose — rather than during an
   unattended upgrade.
9. **`cuems-editor`'s duplicate work is removed rather than kept in parallel.** Where the library
   now performs a repair the editor used to perform as a dict edit, the editor stops doing it —
   two implementations of one repair is how they drift.
10. **A document library holds hundreds of show documents, not tens or thousands.** This is the
    scale the conversion is designed and verified against (FR-095c). It is an assumption about a
    working stage-show library rather than a measurement; FR-095d says what happens if a real one
    proves an order of magnitude larger.
11. **Performance is measured per test, not per suite wall-clock.** The suite has grown across
    005–009; an absolute wall-time budget compares different suites and reads growth as
    regression.

---

## Dependencies

- **Feature 007** (`specs/007-node-model-migration/`) — its migration guide is this feature's
  first input inventory: the moved-symbol table, every changed name and type against its live
  call site, the release gate, and four items deferred here by name (the discovery files, the
  postinst ordering, the mechanical gate demonstration, and the caller class).
- **Feature 008** (`specs/008-rebuild-extension/`) — its migration guide is the second: the
  duration type and wire change, the strict load path, the repair report, the version marker, the
  descriptor, the config save paths, the network-map object and its characterization tests, and
  the standalone conversion command.
- **Feature 006** — the six retired entry points that still resolve and warn, and the wire
  projection that drops `schemaLocation`.
- **`cuems-common`'s unmerged branch** — the schema mirror, shipped-map conversion, postinst
  wiring, versioned dependencies and documentation pass that have been on its local
  `007-node-model-migration` branch since 2026-08-24. Unmerged and unreleased, but landed; this
  feature builds on it rather than redoing it.

## Out of Scope

- The node daemon's remaining nine bundled responsibilities (D23) — a later dedicated feature.
- Any change to the six schemas, and any change to the five facts the descriptor already computes
  (FR-027). FR-022a adds a sixth; it revises none of the five.
- The UI's dual boolean check simplification (FR-088e) — an optional follow-up.
- New descriptor capability beyond FR-022a's constructible instance (FR-026).
- Any node-model re-implementation or re-testing in a consumer repository (FR-003).
- A reverse (v2→v1) document conversion (FR-104).
