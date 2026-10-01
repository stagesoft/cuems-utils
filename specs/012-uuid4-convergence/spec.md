<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature Specification: uuid4 convergence

**Feature Branch**: `012-uuid4-convergence`
**Created**: 2026-09-29
**Status**: Draft
**Input**: User description: "Start feature 012 as stated in `specs/planning/etc-cuems-first-install-execution.md` and the audit file `specs/planning/etc-cuems-first-install.md`. Also take into account `../cuems-engine/specs/008-cuems-utils-migration/upstream-reports/PROMPT-012-clarify.md`"

---

## Why this feature exists

A node's identity is one value that lands in at least seven places across three documents, a
service record and every project in the library. Today the ecosystem does not agree on what that
value *is*: one schema accepts any uuid version in either case, another requires uuid4 lowercase,
two declare it as bare text, and a fourth calls it a non-empty string. Both audited production
controllers carry a **uuid1**; one node carries a **uuid5**. None is a uuid4.

Decision §9 of the planning document settled the target on 2026-09-23 — **uuid4 everywhere** — and
then established why it could not be built yet: tightening the schema invalidates every node
identity in the field, and the repair is a cluster-wide, cross-document re-identification that the
per-document conversion machinery cannot perform. That repair tool is `cuems-init-node`, which
landed with feature 011 on 2026-09-28. The blocker is gone; this feature is the convergence itself.

**What this feature is not**: it is not a document conversion (§10.8). It is a re-identification
that spans every node and every project, is ordered against service lifecycle, and must survive a
partial failure. The conversion machinery's role here is to **detect and report**, never to repair.

---

## Clarifications

### Session 2026-09-29

- Q: What is the performance budget measured against, given the library size cannot currently be measured on hardware? → A: A throughput budget — time per megabyte scanned and rewritten, independent of node count — plus a named fixture with a wall-clock ceiling for the acceptance test. The throughput figure additionally becomes operator-facing: before the re-mint runs, it reports an estimated duration derived from the measured throughput, the library's actual size and the node count, so the operator knows what they are committing to before a stop-the-world operation on a live installation.
- Q: What happens when two nodes share one identity, and how does a colliding uuid4 arise once the re-mint works? → A: The re-mint aborts before writing, naming both rows and every script referencing the token. Beyond that, the three routes that *produce* a collision after the migration are closed: identity uniqueness becomes a registered validation rule so a colliding map is refused at read time; the explicit-identity option is checked against the map; the substitution table is built on the controller rather than minted per node; and a preserved identity whose recorded MAC does not match this hardware is refused, which closes disk cloning. The last amends feature 011's D13 and is recorded against it.
- Q: How far does the narrowing reach across the project-mappings schema's two free-text identity declarations? → A: The node mapping's identity converges (admitting the sentinel, since the fresh-install document carries it). The second declaration sits inside a complex type no element references — measured dead — and is recorded and handed to feature 014's project-mappings reshape rather than migrated here.
- Q: Does the node's own identity, in the configuration document, gain a type so the library delivers it as the identity type? → A: Yes — a settings-specific type admitting uuid4 or the not-provisioned sentinel. A provisioned node's identity decodes to the identity type; the sentinel decodes to the published sentinel constant. The consumer census across every sibling repository becomes a blocking task, not a follow-up.
- Q: Where does the read-only detection live — absorb feature 010's conversion check-mode tasks, depend on them, extend the existing identity check, or build a new entry point? → A: Extend the existing identity check. Document *versions* and identity *shapes* are different questions; feature 010's check mode stays feature 010's, and this feature acquires no dependency on it.

---

### Session 2026-09-30 — resolved by the `/speckit.analyze` pass

The analysis pass found one constitution violation, three contradictions and two ambiguities.
All six are settled here and applied to the requirements, the plan and the tasks.

- Q: The performance budget was defined in *shape* only — "a stated tolerance", "its
  per-megabyte budget", "a named fixture" — with no value anywhere, so no test could fail.
  → A: **500 MB/s** throughput floor, **1%** agreement between the two node counts, and fixture
  **`remint_200`** (200 projects, ~4 MB) at **≤ 2.0 s**. The ceiling is explicitly provisional and
  may be adjusted **downward** after measurement; the other two are not. See FR-PERF-001.
  **The 1% figure was superseded the same day** by session 2026-09-30b: the fixture runs in
  milliseconds, where 1% is below timing noise, so the agreement bound became a ratio (≤ 1.10×) at
  named node counts. Left standing here rather than rewritten, because what the first pass decided
  is part of the record.
- Q: FR-022a forbids a registered conversion; FR-023 required "the registered conversion" to
  detect and report. Which holds? → A: FR-022a. FR-023 is restated as a requirement on the
  **version step**, with detection and reporting produced in the validation error path (FR-024).
  No conversion is registered for any of the three steps.
- Q: The re-mint is specified as cluster-wide, but every reach path is a local filesystem path.
  How does a non-controller node's configuration get rewritten? → A: the two reaches have
  different scopes. **Configuration documents are per node** — every node, controller or not,
  rewrites its own from the table the controller built and distributed. **The library is
  controller-authoritative** — rewritten once, on the controller, reaching the nodes by the
  existing project-sharing machinery on project load. A node never re-mints its own library
  replica. See FR-011a. This also resolves the refusal that would otherwise have rejected the
  distributed table on arrival (FR-019c).
- Q: Does the library reach actually earn its place — do files outside the configuration
  directory really carry node identities? → A: **Yes, measured** (M-o). Both forms are present:
  a bare identity in each project's mappings, and an identity embedded in compound output names
  in each project's script. The reach is required, not precautionary.
- Q: "Converged" was being used for two different sets — uuid4 alone in the classification, and
  uuid4 ∪ sentinel in the schema pattern — while FR-021b and the published coercion rule turn on
  the difference. → A: *converged* means uuid4 lowercase, always. The set a schema accepts is the
  **admitted** set. The admitted set is expressed as a union of two separately named definitions,
  one per half, in the schemas and in the library's identity type alike (FR-021c).
- Q: Which "sentinel constant" does FR-031 publish, given that two exist — the nil-uuid value and
  the human-readable status string? → A: the **nil-uuid value**. The status string is already
  public and answers a different question. See FR-031.

### Session 2026-09-30b — resolved by the second `/speckit.analyze` pass

The first pass's own output was re-analysed the same day. It had closed the budget's magnitude and
the distribution question, and left eleven items — two of them blocking. All are settled here.

- Q: FR-025 made "the `UuidType` divergence entry leaves the allowlist" the completion marker, but
  the overlap ratchet admits a twice-declared name only as a *recorded identical duplicate* (content
  compared) or a *recorded divergent* one (difference required). The network map's declaration
  becomes converged ∪ sentinel while the show script's stays converged-only, and FR-021 forbids
  giving the script's the sentinel — so the two can never be made identical and the entry can never
  leave. → A: **rename and delete**. The network map's node identity is retyped to the new named
  union and the network map's own `UuidType` declaration is **deleted**, so the name is declared in
  one schema only, no longer overlaps, and a *different* test then requires the stale entry's
  removal. See FR-020c and FR-025.
- Q: The three new names live in three schemas. Does anything keep the copies in step? → A: **No,
  and the claim that something did was wrong.** None of the six schemas includes or imports another,
  so a shared type is declared once per file — `NonEmptyString`'s four-way duplication is the
  precedent. The copies must be recorded as identical duplicates, and the allowlist's drift test is
  the only guard. See FR-021d; data-model §1.1 corrected.
- Q: FR-001 requires the *check* to work on documents the tightened definition refuses. Nothing said
  it of the **re-mint**, whose whole purpose after the narrowing is repairing documents that are now
  invalid — and whose collision abort must read a map FR-019a's new rule refuses. → A: stated as
  FR-006a: stdlib XML only on every pre-write path, with FR-017's post-write validation the one
  deliberate exception.
- Q: The estimate was pinned to the 500 MB/s **floor** while SC-PERF-003 requires it within ±25% of
  actual. An implementation beating the floor by 2× fails the tolerance by construction. → A: the
  estimate divides by a throughput the **survey measures on that machine**, falling back to the
  floor only when the survey is too small to time — and saying so when it does. See FR-PERF-003.
- Q: The two node counts had to agree "within 1%" on a fixture that runs in milliseconds, which is
  below timing noise, and the counts were never named. → A: **2 and 10 nodes**, and the bound is a
  **ratio** — the slower run's time ≤ 1.10× the faster's. A per-node pass makes it 5×, so the bound
  still catches the defect it exists to catch. See FR-PERF-001 and SC-PERF-001.
- Q: "The recorded baseline" named none of the three that exist, and feature 008's `network_map` row
  is recorded there as exceeded-or-marginal (10.14–10.49 ms against a 10.20 ms budget) — so a test
  asserting its budget fails for a reason predating this feature. → A: feature 008's baseline, named
  by path; the show-document row compared to its budget, the `network_map` row to its measured band.
  See FR-PERF-002 and SC-PERF-002.
- Q: FR-017 and SC-002 assert a full load succeeds on **every** node, but the configuration reach is
  per node and the verification runs only where it runs. What demonstrates the cluster? → A: a
  per-node **completion record** and a roll-call counted against the map's rows. See FR-017a,
  SC-002b, FR-036c.
- Q: How does the substitution table actually reach a node? "Distributed" named no step. → A: the
  operator copies it; this feature adds no transport, and the copy is a numbered step in the guide.
  See FR-007 and FR-034.
- Q: A cluster arriving with a pre-existing collision is stopped by FR-019 (the re-mint aborts) and
  by FR-019a (the map stops loading after the narrowing), and released by neither. → A: a manual
  resolution procedure in the guide, run **before** the re-mint while the map still loads. See
  FR-036b.
- Q: FR-019a turns a read that succeeds today into a `ValidationError` for every consumer, and the
  blocking census covered only the accessor's return type. → A: the census covers both changes, two
  results per repository. See FR-032a.
- Q: US5 declared an Independent Test and Phase 7 was six writing tasks with nothing that checks the
  guide — against the constitution's "testing work and verification steps per story". → A: a
  verification task was added; see tasks.md Phase 7.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An operator learns whether a machine needs re-minting (Priority: P1)

An operator running a CUEMS installation wants to know, before touching anything, whether the
node identities on a machine are already uuid4 or whether the migration applies to them. They run
a read-only check that reports every identity it finds, by document and by path, says which ones
are not uuid4, and changes nothing on disk.

**Why this priority**: it is the half of §9.4's division of labour that carries no risk, it is the
precondition for an operator deciding to run anything else, and it is independently valuable on a
cluster that turns out to need no migration at all. It is also the only part of this feature that
is safe to ship to a field machine before the repair tool's reach has been confirmed on hardware
(§10.7).

**Independent Test**: point the check at a directory tree containing documents with a uuid1, a
uuid5, a uuid4 and the not-provisioned sentinel; confirm the report names each one with its
document and path and classifies it correctly, that the exit status distinguishes "migration
needed" from "already converged", and that every file's bytes and modification time are unchanged
afterwards.

**Acceptance Scenarios**:

1. **Given** a machine whose configuration document and network map carry a uuid1 node identity,
   **When** the operator runs the check, **Then** the report names both documents, the path within
   each, the offending value and the reason it is not uuid4, and exits with a status meaning
   "migration needed".
2. **Given** a machine whose identities are already uuid4, **When** the operator runs the check,
   **Then** the report says so and exits with a status meaning "nothing to do".
3. **Given** a freshly installed, never-provisioned node whose identity is the sentinel,
   **When** the operator runs the check, **Then** the sentinel is reported as *not provisioned*
   and distinguished from a stale non-uuid4 identity, because the two need different actions.
4. **Given** any of the above, **When** the check completes, **Then** no file has been created,
   modified, moved or deleted.

---

### User Story 2 - An operator re-mints a cluster's identities, completely (Priority: P2)

An operator with a cluster whose identities are not uuid4 runs the re-mint. Every node gets a new
uuid4, minted once on the controller, and every place that node's old identity was written —
including the places where it is embedded inside a longer string — is updated in the same pass.
Afterwards the cluster loads, adoption state is intact, and re-running the tool changes nothing.

**Why this priority**: this is the repair. Without it the narrowing in US3 cannot land, and it is
the single largest body of work in the feature because it must reach beyond the three documents
the node identity tool owns today into the project library.

**Independent Test**: build a fixture cluster — three documents plus a project library containing
projects whose scripts carry compound `<uuid>_<output_id>` output names — run the re-mint, and
verify by exhaustive search that no old identity token survives anywhere, that every touched
document still validates, that adoption state per node is unchanged, and that a second run
rewrites nothing.

**Acceptance Scenarios**:

1. **Given** a cluster whose nodes carry non-uuid4 identities, **When** the re-mint runs on the
   controller, **Then** a substitution table mapping each old identity to exactly one new uuid4 is
   persisted **before** any file is written.
2. **Given** that table, **When** the re-mint is interrupted after some files are written and then
   re-run, **Then** it resumes from the persisted table and does **not** mint a second new identity
   for a node it has already half-rewritten.
3. **Given** a project script containing `<output_name>` values of the form `<old-uuid>_<output>`,
   **When** the re-mint runs, **Then** those values carry the new identity and the rest of each
   value is unchanged — the compound occurrences are covered, not only the elements named `uuid`.
4. **Given** a node already carrying a valid uuid4, **When** the re-mint runs, **Then** that node's
   identity is left alone and no file mentioning only that node is rewritten.
5. **Given** a completed re-mint, **When** an exhaustive search for every old identity is performed
   over the configuration directory and the whole library, **Then** it returns nothing.
6. **Given** a completed re-mint, **When** the re-mint is run a second time, **Then** it reports
   that there is nothing to substitute and no file's bytes change.
7. **Given** a completed re-mint, **When** each node is loaded in full, **Then** the load succeeds
   and each node's adopted and online state is exactly what it was before.
8. **Given** a project library whose script filename is configured to something other than the
   common default, **When** the re-mint runs, **Then** those scripts are found and rewritten —
   the filename is discovered, never assumed.
9. **Given** a library of known size and a known node count, **When** the operator starts the
   re-mint, **Then** it reports an estimated duration before writing anything, and asks for
   confirmation.
10. **Given** two nodes sharing one identity, **When** the re-mint runs, **Then** it aborts before
   writing anything, names both rows with their recorded hardware addresses and every script that
   references the shared token, and no file is modified.
11. **Given** a node whose stored identity records a hardware address that is not this machine's,
   **When** the identity tool runs, **Then** it refuses to preserve that identity and offers to
   re-mint, rather than silently adopting a cloned node's identity.
12. **Given** the table the controller built, **When** a node that is not the controller runs the
   re-mint with it, **Then** that node rewrites **its own** configuration documents from the
   table and does **not** rewrite its replica of the project library, and **When** it runs
   without a table, **Then** it refuses rather than minting one of its own.
13. **Given** a completed run on any node, **When** it finishes, **Then** it leaves a completion
   record naming the table it ran from, the paths it rewrote and its own verification result, so
   the operator can hold one record per row in the map and see that no node was missed.
14. **Given** a library file rewritten on the controller, **When** its modification time is
   compared with the one it had before, **Then** it is later — the file is the same size as
   before, so the modification time is what makes the rewrite visible to the replication that
   carries it to the nodes.

---

### User Story 3 - The schema refuses a non-uuid4 node identity (Priority: P3)

Once identities in the field can be repaired, the schema stops accepting the shapes that caused
the divergence. A document carrying a uuid1, a uuid5 or an upper-case uuid is rejected at read
time with a message that names the offending value and points at the repair tool. A document
written before the tightening is recognised by its version marker as an **identity step** — the
version increments, the document is untouched — and is then judged by the tightened definition like
any other, so it is rejected with the actionable message rather than reported as malformed.

**Why this priority**: it is the feature's completion marker, and it is deliberately last. Landing
it before US1 and US2 exist would invalidate both production maps with nothing able to repair them
— the "shipping a brick" outcome §9.3 exists to prevent. Its value is preventive: it is what stops
the divergence from returning.

**Independent Test**: validate a corpus document carrying each non-uuid4 shape against the
tightened schema and confirm rejection with an actionable message; validate a uuid4 document and
the pristine not-provisioned document and confirm both are accepted; confirm the version marker
moves, that a pre-tightening document is recognised as an identity step rather than reported as
malformed, and that no conversion is registered for any of the three steps.

**Acceptance Scenarios**:

1. **Given** a document carrying a uuid1 node identity, **When** it is read, **Then** it is
   rejected, and the error names the document, the path, the value, and the tool that repairs it.
2. **Given** a document carrying an upper-case but otherwise valid uuid4, **When** it is read,
   **Then** it is rejected — case is part of the converged definition.
3. **Given** the pristine document set a fresh package installation produces, whose identity is the
   not-provisioned sentinel, **When** it is validated, **Then** it is accepted. The sentinel is not
   a uuid4 and must remain valid, or a freshly installed node cannot load.
4. **Given** the package build's own generation step, **When** it generates and validates the three
   default documents, **Then** it succeeds — the tightening must not break the build that produces
   the documents the tightening applies to.
5. **Given** a document written before the tightening, **When** it is read, **Then** its version
   marker is recognised as an **identity step** — no conversion is registered for it (FR-022a) —
   and the document is judged by the tightened definition: a converged identity loads, and a
   non-converged one is rejected with FR-024's actionable message. It is never reported as an
   unknown or malformed document.

---

### User Story 4 - A consumer receives one type for one kind of value (Priority: P4)

A consumer of this library reading a node identity gets the same type every time, whichever
document it came from, and has the tools to handle it without copying the library's internal
decoding rules into its own code.

**Why this priority**: it is a library-surface change with no operator-visible behaviour of its
own, but it closes the defect class a consumer measured and reported (`cuems-engine`, 2026-09-29):
the library hands out an identity type that varies by source document, and the leniency rule that
decides which is internal, so at least one consumer has mirrored it by hand.

**Independent Test**: read the same node identity through every public accessor the library
offers and confirm the returned type is the same in each case; confirm the published coercion
behaviour matches what the library itself does; confirm a collection of identities can be sorted
without error.

**Acceptance Scenarios**:

1. **Given** a provisioned node's identity read from the configuration and the same identity read
   from the network map, **When** both are returned through the public accessors, **Then** they
   compare equal and have the same type.
2. **Given** a node that is not provisioned, **When** its identity is read through any public
   accessor, **Then** every accessor yields the published sentinel constant, so one check tells a
   consumer the node is unprovisioned before it attempts a full load.
3. **Given** a collection of node identities, **When** a consumer sorts them, **Then** the sort
   succeeds rather than failing on an unordered type.
4. **Given** a consumer that needs to recognise the not-provisioned sentinel before attempting a
   full load, **When** it looks for the constant to compare against, **Then** that constant is
   declared public surface with a stated name.

---

### User Story 5 - An operator is not surprised by what the migration costs (Priority: P5)

An operator reading the migration guide before a venue installation learns the three things about
this change that are not visible from its outputs: that a re-imaged node no longer regenerates its
old identity and must be re-adopted; that backups taken before the re-mint contain stale
identities and restoring one reintroduces the defect; and which other components must be upgraded
in the same step.

**Why this priority**: none of it is code, and all of it is the difference between a planned
migration and an incident. §9.5 states the reimage property explicitly so it is "lost knowingly".

**Independent Test**: the guide is checked against this specification's requirements — every
stated loss, hazard and precondition appears, and every version and component it names is verified
against the actual trees rather than asserted.

**Acceptance Scenarios**:

1. **Given** the migration guide, **When** an operator reads the preconditions, **Then** it names
   every component that must be stopped before the re-mint and every component whose version is
   coupled to it.
2. **Given** the migration guide, **When** an operator reads it, **Then** it states that re-imaging
   a node after this change produces a new identity requiring re-adoption, and that pre-migration
   backups and conversion backups are **not** rewritten and must not be restored afterwards.
3. **Given** the migration guide, **When** an operator finishes a re-mint, **Then** it gives a
   verification procedure that measures success rather than inferring it from the absence of
   errors — including the roll-call: one completion record per node in the map, counted against the
   map's rows, rather than the controller's run exiting cleanly.
4. **Given** a cluster that arrives at the migration with two nodes already sharing an identity,
   **When** the operator reads the guide, **Then** it gives the manual resolution procedure to run
   **before** the re-mint, while the map still loads — because the re-mint aborts on a collision, the
   library refuses to guess which row is the real node, and after the narrowing that map does not
   load at all.
5. **Given** the migration guide, **When** an operator reads the procedure, **Then** the step that
   copies the substitution table from the controller to each remaining node is numbered among the
   others, and the guide says that a node invoked without it refuses by design.

---

### Edge Cases

- **The not-provisioned sentinel is not a uuid4.** A fresh installation writes the nil uuid as its
  identity placeholder. The tightened definition must admit it, or the package's own build-time
  generation fails and every freshly installed node becomes unloadable. Measured, not hypothetical
  — see M-f.
- **An identity embedded in a compound string stays valid when stale.** Output names are declared
  as free-form names, so a script carrying a superseded identity prefix passes validation and fails
  later as an output that resolves to nothing. This is the trap that makes a structural rewrite the
  wrong instrument (§10.2).
- **A node whose identity is already uuid4, in a cluster where others are not.** It must be left
  untouched, and the pass must still be a single coherent operation.
- **A re-mint interrupted between two files.** The substitution table is the only record linking
  old identity to new; losing it strands a half-rewritten cluster.
- **Two nodes sharing an identity.** Not a legacy artifact the migration clears: it is reachable
  *after* a correct migration, by four measured routes (M-l). The audited controllers share a
  cloned prefix with differing hardware suffixes, so an exact collision is plausible rather than
  measured in the field — but the route that produces one is how venues provision nodes.
- **A node restored from a disk image taken after provisioning.** It carries the original's
  identity *and* the original's recorded hardware address, so it believes it is the original node
  entirely and the hardware address is no longer a discriminator between them.
- **An identity set explicitly to a value another node already holds.** Accepted today: only its
  shape is checked.
- **A project restored from the deleted-projects area after the re-mint**, reintroducing stale
  identities into a live library.
- **A rewritten library file that replication declines to transfer.** The substitution changes no
  file's size, and the replication in use compares size and modification time. A rewrite that
  preserved modification times would leave every node's replica stale, permanently and silently —
  the failure would surface as an output resolving to nothing, far from its cause (M-o).
- **Upper case.** One schema accepts either case today; the converged definition is lowercase only,
  so a mixed-case but otherwise well-formed uuid4 becomes invalid and needs the same repair path as
  a uuid1.
- **A document the check finds that no component writes** — a stray backup, an editor scratch file.
  The check reports; it must not be read as an instruction to rewrite a file nothing owns.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Detection and reporting

- **FR-001**: The read-only check that already reports this node's identity across its known
  locations MUST be extended to report every node identity it finds across the configuration
  documents **and the project library**, naming the document and the path within it for each
  occurrence. It MUST remain usable on a node whose documents the tightened definition would
  refuse, since that is exactly when an operator runs it.
- **FR-001a**: The check MUST NOT acquire a dependency on the conversion tool's own check mode.
  Reporting a document's *version* and classifying an identity's *shape* are separate questions,
  and the conversion tool's check mode belongs to a different feature that has not delivered it.
  This is satisfied **by design** rather than by a dedicated test: the check reads with stdlib XML
  only and never routes through the validating load path, which the no-write and invalid-document
  tests already exercise. Reversing it — routing any part of the check through the conversion
  machinery — MUST carry a stated justification in the plan, because it would couple a read-only
  diagnostic to a feature that has not delivered.
- **FR-002**: The check MUST classify each identity as converged (uuid4, lowercase), not converged
  (any other well-formed uuid), not provisioned (the sentinel), or unrecognised, and MUST report
  the four classes distinguishably.
- **FR-003**: The check MUST write nothing — no file created, modified, moved or deleted, and no
  backup taken.
- **FR-004**: The check's exit status MUST distinguish "already converged", "migration needed" and
  "could not determine", so it is usable from a script without parsing its output.
- **FR-005**: The check MUST report a document it cannot read or does not recognise rather than
  failing the whole run, and MUST continue to the remaining documents.

#### The re-mint

- **FR-006**: The system MUST mint every new identity through this library's existing identity
  minter, which produces uuid4 and refuses any other shape, so a minted value cannot be one the
  tightened definition will reject.
- **FR-006a**: The re-mint MUST remain usable on documents the tightened definition refuses, for the
  same reason FR-001 states it of the check and for two further ones of its own. After the narrowing
  lands, every deployed non-converged document **is** invalid, and repairing them is the re-mint's
  entire purpose; and FR-019's collision abort must read a network map that FR-019a's new rule
  refuses at read time in order to name the two rows. Every path that reads a possibly-invalid
  document — the survey, the collision check and the substitution itself — MUST therefore read with
  stdlib XML only and MUST NOT route through the validating load path. The one exception is the
  **post-write** verification of FR-017, which validates on purpose and runs only after the
  rewrite has made validation possible.
- **FR-007**: The substitution table mapping each old identity to exactly one new identity MUST be
  built once, on the controller, and MUST be persisted before any file is written. Every node that
  rewrites its own configuration documents MUST do so from **that** table, never from one it
  minted itself. **How the table travels MUST be stated, not implied**: the operator copies the
  persisted table from the controller to each node and names it on that node's invocation. This
  feature adds no transport of its own — the table is one small file and the migration is already
  an attended, stop-the-world procedure — but the copy is a step in the procedure and the
  migration guide MUST carry it (FR-034).
- **FR-008**: A re-mint re-run after an interruption MUST resume from the persisted table and MUST
  NOT mint a second identity for a node already partly rewritten.
- **FR-009**: The re-mint MUST replace identities by literal substitution of the whole 36-character
  token across whole files, so that bare and embedded occurrences are covered in one pass, and MUST
  leave every other byte of each file unchanged.
- **FR-010**: The substitution table MUST be built from node identities only, so a replacement
  cannot land on an unrelated value that happens to be a uuid.
- **FR-011**: The re-mint MUST reach, in addition to the three configuration documents it covers
  today, every project's mappings and every project's script within the configured library,
  including the deleted-projects area. Both are measured, not assumed: a project's mappings carry
  a bare node identity, and a project's script carries it embedded in compound output names.
- **FR-011a**: The re-mint's two reaches have **different scopes**, and the system MUST treat them
  as such. The configuration documents under the configuration directory are **per node** — every
  node rewrites its own, controller or not, from the distributed table (FR-007). The project
  library is **controller-authoritative**: it is rewritten once, on the controller, and reaches
  the nodes by the ecosystem's existing project-sharing machinery, which replicates it from the
  controller on project load. A node MUST NOT re-mint its own replica of the library.
- **FR-011b**: A rewritten library file MUST NOT carry its pre-rewrite modification time. The
  substitution is length-preserving — 36 characters become 36 characters — so a replicated copy is
  **byte-identical in size** to the stale one, and the replication machinery's default quick check
  compares size and modification time only. Preserving the modification time would leave every
  node's replica stale indefinitely, with no error anywhere. Writing through a temporary and an
  atomic replace satisfies this; explicitly restoring times MUST NOT be added.
- **FR-012**: The re-mint MUST NOT assume a script filename. A run that assumes the wrong name
  skips a library silently and completely, which is the failure mode this requirement exists to
  prevent. Scripts MUST be identified by their **content** — the document's root element — because
  the filename is not recorded in any document this library reads (M-n): it is an editor-internal
  key, and the two sibling components that use it disagree on its value. Identification by content
  satisfies the intent strictly more completely than reading a configured name would, since it
  finds a script under any filename, including one no component uses today.
- **FR-013**: The re-mint MUST be idempotent: a second run over a converged cluster MUST substitute
  nothing and MUST change no file's bytes.
- **FR-014**: A node already carrying a valid uuid4 MUST be left unchanged by the re-mint.
- **FR-015**: The re-mint MUST NOT rewrite backup files of any kind. The operator-facing half of
  this — that restoring a pre-migration backup reintroduces a stale identity — is a documentation
  obligation and is stated once, in the Documentation block, as FR-033a.
- **FR-016**: After a re-mint, an exhaustive search for every old identity over the configuration
  directory and the whole library MUST return nothing; the system MUST provide this as a
  verification step rather than leaving it to the operator to invent.
- **FR-017**: After a re-mint, every touched document MUST validate against its schema, and a full
  load MUST succeed on each node.
- **FR-017a**: Because the configuration reach is per node (FR-011a), each node's run MUST leave a
  **completion record** naming the table it ran from, the paths it rewrote and the result of its own
  FR-016/FR-017 verification. The operator MUST be able to assemble those records into a roll-call
  covering every node in the map, because that is the only thing that distinguishes "the cluster is
  converged" from "every node I happened to run it on is converged". A node absent from the
  roll-call is the failure FR-036's detector catches far downstream and much later.
- **FR-018**: After a re-mint, each node's adoption and online state MUST be exactly what it was
  before — only the identity moves.
- **FR-019**: Where two nodes are found to share an identity, the re-mint MUST abort before writing
  anything, naming both rows with their recorded hardware addresses and every project script that
  references the shared token. It MUST NOT assign both the same new identity, and MUST NOT split
  them into two: the shared token is the *only* record of which node an output belongs to, so a
  split would silently reassign one node's entire output set to the other — schema-valid, and
  failing later as an output that resolves to nothing.
- **FR-019a**: The system MUST make a colliding identity visible outside the tool. Node-identity
  uniqueness within a network map MUST become a registered validation rule, classified as **not
  repairable** — the library cannot know which of two rows is the real node.
- **FR-019b**: An identity supplied explicitly to the node identity tool MUST be checked against the
  network map, not only for shape. Today only its shape is validated, so an operator can set a
  collision and be told the run succeeded.
- **FR-019c**: The build-once-on-the-controller rule is FR-007's and is not restated here. What
  this requirement adds is the **refusal that enforces it**: a node that is not the controller MUST
  refuse to build a table of its own, and MUST accept a table the controller built and handed to it.
  The existing tool mints locally, per node, which §10.3 warns gives the controller's map and the
  node's own configuration different answers. The refusal is therefore on *minting without being
  the controller*, never on *using a table another node built* — which is the table's whole
  purpose.
- **FR-019d**: A preserved identity whose recorded hardware address does not match the hardware the
  tool is running on MUST be refused, with re-minting offered. This closes disk cloning — the route
  by which a venue provisions nodes, and the one that reproduces a collision after a correct
  migration. It **amends feature 011's D13** from "mint if and only if there is none" to "if and
  only if there is none, **or** the identity on disk was minted for different hardware", and that
  amendment MUST be recorded against feature 011 rather than made silently.

#### The converged definition

**Vocabulary, fixed here because the two senses were being used interchangeably.** *Converged*
means **uuid4, lowercase, exactly 36 characters** — and nothing else, in every requirement, every
classification and every published rule below. The not-provisioned sentinel is **not** converged;
it is a documented placeholder that the schemas additionally *admit*. The set a schema accepts is
therefore the **admitted** set — converged ∪ sentinel — and the two words are never
interchangeable. The distinction is load-bearing: FR-021b turns on the sentinel *not* being
converged, and so does the published coercion rule (FR-030).

- **FR-020**: The node identity definition in the network map MUST narrow to the admitted set built
  on the project's converged definition: uuid4, lowercase, exactly 36 characters.
- **FR-020c**: The narrowing MUST be carried by **retyping** the network map's node identity to the
  new node-identity type of FR-021c and **deleting** the network map's own `UuidType` declaration,
  rather than by editing that declaration in place. Stated as a requirement because the obvious
  route is blocked and the blockage is mechanical, not aesthetic. `UuidType` is declared in both the
  network map and the show-script schema, and the project's overlap ratchet admits exactly two
  states for a name declared twice: recorded as an **identical** duplicate, which the test enforces
  by comparing the declarations' content, or recorded as a **divergent** one, which the test
  enforces by requiring them to still differ. The show script's `UuidType` types cue and media
  identifiers, so FR-021's "admitted for node identities and nowhere else" forbids giving it the
  sentinel — the two declarations therefore can never be made identical, and editing the network
  map's in place would leave the divergence permanently unresolvable. Deleting it instead leaves
  `UuidType` declared in one schema only, so the name no longer overlaps at all, which is the state
  FR-025's completion marker actually requires.
- **FR-020a**: The node identity declared as free text in the project mappings MUST narrow to the
  same converged definition, since it names the same nodes as the network map and diverging there
  would reproduce the defect this feature exists to close.
- **FR-020b**: The project mappings' *second* free-text identity declaration — the one inside a
  complex type that no element references (M-k) — is **out of scope**. It is recorded as measured
  dead schema and handed to the feature that reshapes this schema. This feature MUST NOT delete it:
  removing it carries a model class and a registry binding with it, which is unrelated work to ride
  along on a field re-identification.
- **FR-021**: The definition applied to a node identity MUST admit the not-provisioned sentinel
  **in addition to** the converged shape, because a freshly installed node carries it and the
  package's own build-time document generation validates what it produces. The sentinel MUST NOT
  be admitted as a generally valid identity anywhere it is not the documented placeholder — it is
  admitted for node identities and nowhere else, and it never becomes *converged* by being
  admitted.
- **FR-021a**: The node's own identity, in the configuration document, MUST be typed rather than
  left as free text: uuid4 **or** the not-provisioned sentinel, and nothing else. A uuid1 or uuid5
  written there MUST be refused, as it already is in the network map.
- **FR-021b**: A provisioned node's own identity — a *converged* value — MUST decode to the same
  identity type the network map yields; the sentinel, which is admitted but not converged, MUST
  decode to the published sentinel constant (FR-031) and to nothing else. The decoded type therefore varies only between "provisioned" and "not provisioned", and a
  consumer needs exactly one documented check to tell them apart.
- **FR-021c**: The admitted set MUST be expressed as a **union of two separately named
  definitions** — one for the converged shape, one for the sentinel — rather than as a single
  widened pattern, in the schemas and in the library's own identity type alike. Each half is then
  nameable, testable and removable on its own, and a reader can see that the sentinel is a
  placeholder admitted by exception rather than a shape the converged definition happens to allow.
  This is assumption 1 made structural: admitted by union, not by loosening. The union itself MUST
  also be named, so that all three schemas spell the node identity as one type name rather than
  three copies of a union expression, and so that FR-020c's retyping has something to point at.
- **FR-021d**: The three names FR-021c introduces MUST be recorded as **identical duplicates** in
  the project's overlap allowlist, in the same change that introduces them. Stated because the
  structural fact behind it is easy to get wrong: the six schemas share one target namespace but
  **none of them includes or imports another**, so a type used by three schemas is declared three
  times, once per file. Nothing in the schema layer keeps the three copies in step — the guard is
  the allowlist's own drift test, which fails the moment one copy gains a facet the others lack.
  A new name declared twice and left unrecorded fails the ratchet at the commit that introduces it,
  which is the ratchet working; recording it is how the convergence avoids re-diverging one level
  down, and no claim that the three schemas "reference the same definition" may stand in its place.
- **FR-022**: The narrowing MUST be carried as a file-format migration under the project's schema
  evolution convention: a document-version step for **each of the three** schemas whose definition
  moves — the network map, the project mappings and the settings. The settings schema moves
  because FR-021a types the node's own identity and deployed configuration documents carry a
  uuid1.
- **FR-022a**: No *registered* conversion accompanies these steps. The conversion machinery
  represents an identity step as the **absence** of a registry entry and forbids a do-nothing
  conversion, and the repair is cross-document and out-of-band by design (FR-023). The version
  increments; the document is untouched; the tightened pattern then rejects a non-converged
  identity, with FR-024's actionable message produced in the validation error path.
- **FR-023**: The version step MUST detect and report a non-converged identity and MUST NOT
  attempt to repair one, because the repair is cross-document and a per-document conversion cannot
  perform it safely. The detection and the report are produced in the **validation error path**
  (FR-024), not by a conversion: FR-022a establishes that no conversion is registered for these
  steps, so there is no conversion here to carry them. Stated as a requirement on the step rather
  than on a conversion because the earlier wording named an artifact this feature deliberately
  does not create.
- **FR-024**: A document rejected for a non-converged identity MUST produce an error naming the
  document, the path, the offending value, and the tool that repairs it.
- **FR-025**: The completion marker for the convergence is that the recorded divergence between the
  two identity definitions leaves the duplication allowlist **because the name no longer overlaps**
  — FR-020c's deletion, not a re-converging of two declarations that FR-021 forbids re-converging.
  The entry and the schema change MUST move in the same change, in both directions: while the entry
  is listed, its own test requires the divergence to still exist, and once the name is declared in
  one schema only, a different test requires the now-stale entry to be removed. Either half alone
  fails.
- **FR-026**: Every schema whose content changes MUST have its pinned content hash updated in the
  same commit, with the reason in the commit message. The same commit MUST carry FR-021d's
  allowlist entries and FR-025's removal, for the same reason: each is a pin that the schema edit
  invalidates, and a pin left behind is a test asserting something that is no longer true.
- **FR-027**: Negative fixtures affected by the tightening MUST be re-checked for *which* error
  they now raise, not merely that they still fail.

#### The library surface consumers see

- **FR-028**: On a **provisioned** node, a node identity returned through the library's public
  accessors MUST have the same type regardless of which document it was read from. On a node that
  is not provisioned, every accessor MUST instead yield the published sentinel constant — the one
  documented exception, and the same exception from every accessor.
- **FR-029**: A collection of node identities MUST be sortable without error.
- **FR-030**: The rule by which a raw value becomes an identity — converged value becomes the
  identity type, other non-empty values are passed through unchanged, an empty value becomes
  nothing — MUST be available to consumers as public surface, so a consumer does not have to
  reimplement the library's leniency by hand. If this is declined, the reason MUST be recorded so
  the existing consumer copy is an accepted duplication rather than undocumented drift.
- **FR-031**: The not-provisioned sentinel constant MUST be declared public surface with a stated
  name, so a consumer can recognise an unprovisioned node before attempting a full load. **Which
  constant this is, stated because two answer to the name**: it is the nil-uuid *value* a node
  carries as its identity placeholder, not the human-readable *status string* the identity report
  prints for it. The status string is already public; the value is what a consumer compares an
  identity against, and it is the one this requirement is about. If both end up published, each
  MUST carry documentation saying which question it answers.
- **FR-032**: The change of the own-identity accessor's return type (FR-021b) MUST be **preceded**
  by a census of every consumer that reads it, covering every sibling repository by name, with the
  result recorded per repository. This is a blocking precondition of the change, not a follow-up:
  one consumer is measured and the rest are not, and a changed type where a string was is silent
  wherever anything slices, sorts or concatenates it.
- **FR-032a**: The same census MUST also cover FR-019a's new refusal, because that is the feature's
  **second** change to what a consumer receives and the only one that turns a successful read into
  an exception. A network map carrying two rows with one identity loads today — `NodeIndex.merge`
  collapses the duplicate silently (M-l) — and raises `ValidationError` for every reader afterwards.
  Each sibling repository MUST therefore be recorded twice over: what it does with the own-identity
  accessor's type, and what it does when a map read raises. Both are recorded in the one census
  artifact, and both are blocking for the same reason — the failure is silent in the first case and
  loud in the wrong place in the second.

#### Documentation

- **FR-033**: The migration guide MUST state that a re-imaged node no longer regenerates its former
  identity and must be re-adopted.
- **FR-033a**: The migration guide MUST state that backups are not rewritten (FR-015) and that
  restoring a pre-migration or conversion backup after the re-mint reintroduces a stale identity.
  This is the operator-facing half of FR-015, stated here rather than there so the hazard has one
  home.
- **FR-034**: The migration guide MUST name the components that must be stopped before a re-mint,
  including the one that writes the network map and could otherwise reintroduce an old identity
  mid-pass. It MUST also carry the **table copy** as a numbered step (FR-007): where the controller
  leaves the persisted table, how the operator gets it onto each remaining node, and that a node
  invoked without it refuses by design rather than by accident.
- **FR-035**: The migration guide MUST state that the re-mint ships in the same upgrade as the
  consumer version that can handle the resulting identity type, and MUST never run under an older
  one. That version MUST be named in the guide's precondition list.
- **FR-036**: The migration guide MUST include an operator-visible detector of an incomplete
  re-mint: after re-minting, loading each project on the controller and checking the cluster
  warning — a node reported missing under an old identity is a script the re-mint did not reach.
- **FR-036a**: The migration guide MUST state the four measured collision routes (M-l) and which
  of them this feature closes, so an operator learns that cloning a provisioned disk is now
  refused rather than silently duplicating an identity — a change to how venues provision nodes,
  and the one operator-visible consequence of FR-019d.
- **FR-036b**: The migration guide MUST give the operator a procedure for a **pre-existing**
  collision, because without one the migration has a dead end. The re-mint aborts on a shared
  identity (FR-019) and the library cannot resolve it (FR-019a is not repairable), and after the
  narrowing that same map does not load at all — so a cluster that arrives at the migration with a
  collision is stopped by two requirements and released by neither. The procedure MUST be the manual
  one the library refuses to automate: how to decide from the two rows' hardware addresses and the
  scripts naming the shared token which node the outputs belong to, that the other node is treated
  as never provisioned and re-minted by the identity tool, and that this is done **before** the
  re-mint, on a map that still loads.
- **FR-036c**: The migration guide MUST state the **roll-call** FR-017a's records make possible: the
  operator confirms the cluster is converged by holding one completion record per node in the map,
  not by the controller's run finishing without error.
- **FR-037**: Facts the planning documents state that this feature measures to be different MUST be
  recorded as corrections in this specification and then applied to the planning documents, never
  changed silently.
- **FR-038**: The items §10.7 lists as unconfirmed on hardware MUST be confirmed before a first
  real run, and the confirmation recorded.

#### Cross-cutting

- **FR-UX-001**: The check and the re-mint MUST follow the conventions the existing node identity
  tooling already established — the same reporting style, the same confirmation requirement for a
  destructive step, and the same dry-run affordance.
- **FR-PERF-001**: The re-mint's budget is a **throughput** figure — megabytes scanned and
  rewritten per second — that is independent of node count, **plus** a named fixture with a
  wall-clock ceiling for the acceptance test. The throughput shape is required rather than a
  single wall-clock figure because it is what catches an implementation that makes one pass per
  node, turning a linear job into one proportional to nodes times files; a ceiling on one fixture
  hides that. The library's real size is unavailable (§10.7), which is why the budget must not
  depend on knowing it. **The three values**:

  | Budget | Value | Basis |
  |---|---|---|
  | Throughput floor | **500 MB/s** scanned and rewritten | the operation is read, literal substitution, write — no parsing, no reserialisation. Below this the implementation is doing something other than the operation |
  | Agreement between the two node counts — **2 and 10**, the ends of the cluster range | the slower measurement's time over the faster one's is **≤ 1.10×** | a per-node repeated pass multiplies the work by five between these two counts, so it cannot hide inside 1.10×. Stated as a **ratio**, not a percentage: the fixture's absolute time is a few milliseconds, where a 1% tolerance is below ordinary timing noise and would have measured the machine's jitter rather than the implementation. 2 and 10 are named because the tolerance is meaningless without knowing what it separates |
  | Named fixture ceiling | **`remint_200`** — 200 projects, ~4 MB — completes in **≤ 2.0 s** | an initial estimate from the floor plus process overhead, **explicitly provisional**: it MAY be adjusted once measured, in one direction only — downward, toward the measured figure — and never raised to accommodate an implementation |

  The ceiling is the one figure stated as an estimate rather than a requirement, and it is marked
  as such so that adjusting it later is a recorded decision rather than a silent relaxation. The
  throughput floor and the 1.10× agreement are **not** provisional: they are what the tests are for.
- **FR-PERF-002**: The read path MUST be measured against feature 008's recorded baseline —
  `specs/008-rebuild-extension/baseline.md`, the load-timing table, named exactly because three
  later baselines exist and "the recorded baseline" does not pick one. Two rows are compared
  differently, and the difference is not a convenience: the show-document row is compared against
  its **budget**, while the `network_map` configuration row is compared against its **measured
  band** of 10.14–10.49 ms, because that row is recorded there as exceeded-or-marginal against its
  own 10.20 ms budget. Comparing it to the budget would assert a threshold the baseline itself does
  not meet, and a test that fails for a reason predating the feature tells a reader nothing about
  the feature. Budgets are recorded as measured, including when they are exceeded.
- **FR-PERF-003**: Before the re-mint writes anything, it MUST report an **estimated duration** to
  the operator: the surveyed byte volume divided by a throughput the run **measures on the machine
  it is running on**, not by the FR-PERF-001 floor. The distinction is what makes the estimate meet
  SC-PERF-003's tolerance rather than miss it by construction — 500 MB/s is a *floor*, so an
  implementation that beats it by 2× would report an estimate twice the actual duration and still be
  a correct implementation. The measurement MUST come from the survey itself, which already reads
  every byte the apply pass will read: the survey records its own elapsed time and bytes read, and
  that observed rate is what the estimate divides by. Where the survey is too small to time
  meaningfully, the run MUST fall back to the FR-PERF-001 floor and MUST say that it did, so a
  pessimistic estimate is never passed off as a measured one. The re-mint is a stop-the-world
  operation on a live installation — services stopped, no shows running — so the operator must be
  able to decide whether the window is long enough before committing, not discover it midway. The
  estimate MUST be presented alongside the confirmation FR-UX-001 requires for a destructive step.

### Key Entities

- **Node identity** — the one value that identifies a node across the cluster. Appears bare in
  three configuration documents and each project's mappings, embedded within compound output names
  in each project's script, and in the node's service record. Converged form: uuid4, lowercase, 36
  characters.
- **Substitution table** — the mapping from each node's old identity to its new one, built once on
  the controller and persisted before any write. The only record linking the two; its loss strands
  a partly-rewritten cluster.
- **Not-provisioned sentinel** — the nil-uuid placeholder a fresh installation writes as its
  identity. Coherent but actionable: not a stale identity, and not a converged one.
- **Identity report** — what the read-only check produces: every occurrence, by document and path,
  with its classification.
- **Completion record** — what each node's run leaves behind: the table it ran from, the paths it
  rewrote, its own verification result. One per node; the set of them is the roll-call that answers
  "is the cluster converged?" rather than "did my run finish?".
- **Version step** — what the schema evolution convention requires for a change that invalidates
  documents already on disk. Here it is an **identity** step in all three schemas: the version
  increments and **no conversion is registered**, because the machinery represents an identity step
  as the absence of a registry entry and the repair is cross-document and out-of-band by design
  (FR-022a, FR-023).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a cluster whose identities were not converged, after the migration an exhaustive
  search for every pre-migration identity over the configuration directory and the entire project
  library returns **zero** occurrences.
- **SC-002**: Every document touched by the migration validates against its schema afterwards, and
  a full load succeeds on **every** node in the cluster — each node's own configuration documents
  having been rewritten locally from the distributed table, and the library having been rewritten
  once on the controller (FR-011a).
- **SC-002b**: "Every node" is demonstrated rather than assumed: the operator holds **one completion
  record per node in the network map**, each naming the table it ran from and its own verification
  result, and the count of records equals the count of rows (FR-017a). A cluster with a node missing
  from the roll-call is reported as incomplete, not as converged.
- **SC-002a**: After the library is rewritten on the controller, every rewritten file's
  modification time is later than it was before, so the replication machinery's size-and-time
  quick check transfers it. Verified by comparison, not assumed — the substitution preserves file
  size exactly, so the modification time is the **only** thing that makes the change visible to
  replication (FR-011b).
- **SC-003**: Adoption and online state is identical for **every** node before and after the
  migration.
- **SC-004**: Running the migration a second time over the same cluster changes **zero** bytes in
  **zero** files.
- **SC-005**: The read-only check, run over a tree of mixed identity shapes, classifies **100%** of
  occurrences correctly and modifies **zero** files.
- **SC-006**: A migration interrupted at any point and re-run produces exactly one new identity per
  node — no node ends with two successive new identities.
- **SC-007**: Every non-converged identity shape found on the audited production machines — uuid1
  and uuid5 — is rejected by the tightened definition, and the pristine freshly-installed document
  set is accepted.
- **SC-008**: The package's build-time document generation succeeds under the tightened definition.
- **SC-009**: `UuidType` is declared in **one** schema, the divergence entry is gone from the
  duplication allowlist, and the three new node-identity type names are recorded there as identical
  duplicates instead (FR-020c, FR-021d, FR-025). All three overlap tests pass together: no
  unrecorded name is declared twice, no recorded name has diverged, and no recorded name is stale.
- **SC-010**: On a provisioned node, a node identity read through **every** public accessor returns
  the same type, and a collection of them sorts without error. On a node that is not provisioned,
  **every** accessor returns the published sentinel constant.
- **SC-011**: The consumer census covers **every** sibling repository by name, with **two** results
  recorded per repository — what it does with the own-identity accessor's changed return type, and
  what it does when a network-map read raises for a colliding identity (FR-032, FR-032a) — and is
  complete **before** either change lands.
- **SC-012**: A network map carrying two rows with one identity is refused at read time by the
  registered rule, and reported as not repairable.
- **SC-013**: Each of the four measured collision routes (M-l) is closed or explicitly refused:
  a cloned identity is refused, an explicit identity colliding with the map is refused, a
  re-mint over an existing collision aborts without writing, and the substitution table is built
  on the controller.
- **SC-PERF-001**: The re-mint's measured throughput is **at least 500 MB/s**, and the named
  fixture `remint_200` completes within **2.0 s** (provisional per FR-PERF-001). Throughput is
  measured at **2 and 10** nodes over the same library bytes, and the slower run's elapsed time is
  **≤ 1.10×** the faster run's — a ratio rather than a percentage, because the fixture runs in
  milliseconds and a 1% tolerance would have measured machine jitter. A per-node repeated pass makes
  the 10-node run about five times the 2-node run, so it cannot pass this bound.
- **SC-PERF-002**: Measured on feature 008's method against
  `specs/008-rebuild-extension/baseline.md`: the show-document load stays within its recorded
  **budget**, and the `network_map` configuration load stays within its recorded **measured band**
  of 10.14–10.49 ms — that row's budget is recorded there as exceeded-or-marginal, so the band is
  what a regression is measured against (FR-PERF-002).
- **SC-PERF-003**: The duration the re-mint estimates before starting is within **±25%** of the
  duration it actually takes, measured on the named fixture at both node counts — achievable
  because the estimate divides by the throughput the survey measured on that machine, not by the
  FR-PERF-001 floor, which an implementation is expected to beat. The tolerance is
  wide on purpose: the estimate exists so an operator can judge whether a maintenance window is
  long enough, which is a question about minutes, not milliseconds — and a tight tolerance on a
  sub-second fixture would measure process startup rather than the operation. An estimate the
  operator cannot trust is worse than none.
- **SC-QUALITY-001**: No new lint or type warnings are introduced, and every schema whose content
  changes has its pinned hash updated in the same commit.
- **SC-TEST-001**: Every behaviour change has a test that fails before the implementation and
  passes after it; the suite's per-test timing stays within the recorded budget; and every negative
  fixture affected by the tightening is verified to raise the error it is meant to raise.

---

## Measured since the planning documents

Recorded here and then applied to the planning documents (FR-037), never changed silently. All
measured 2026-09-29 against `feat/xml-refactor` at `2a88a7c`.

| # | Finding | Corrects |
|---|---|---|
| **M-f** | The pristine `network_map.xml` a fresh installation receives carries the **nil uuid** in `node_list/node/uuid` — generated from the sentinel identity and validated at package build time. Narrowing `UuidType` to `script.xsd`'s pattern verbatim would make the package's own generation step fail, and every freshly installed node unloadable | §9.2, which describes the narrowing as `network_map.xsd` adopting `script.xsd`'s definition with no exception stated |
| **M-g** | The node identity is declared **four** ways, not two: `network_map.xsd` `cms:UuidType` (any version, either case); `settings.xsd` `cms:NonEmptyString`; `project_mappings.xsd` bare `xs:string` in **two** places (`NodeMappingType/uuid` and `MappedToType/uuid`). `script.xsd`'s `UuidType` types cue and media `id`, not a node identity — its three `node_uuid` elements are commented out | §9.2's two-column table and the brief's "narrow `network_map.xsd`'s `UuidType`", both of which frame the convergence as a two-site question |
| **M-h** | `cuems-convert-documents` has **no argument parsing at all** — every argument is treated as a document path. A `--check` flag passed today would be read as a filename | the brief's "`cuems-convert-documents --check` gaining detect-and-report", which reads as an extension of an existing mode |
| **M-i** | `network_map` and `project_mappings` are both at document version **1**; `script`, `settings` and `hardware_outputs` are at **2**. Whichever schemas this feature narrows take their first version step here | — (states the starting point rather than correcting a claim) |
| **M-l** | A colliding identity is **reachable after a correct migration**, by four routes: (R1) a disk image taken after provisioning — `_resolve_identity` preserves both the stored identity *and* the stored hardware address, so a clone never consults its own hardware; (R2) the explicit-identity option validates shape only and is never checked against the map; (R3) restoring a backup or copying the configuration onto another node; (R4) the substitution table keys on the old value, so two nodes already sharing one receive one new one. **Nothing detects the result**: no `xs:unique` on any node identity (the only two in the six schemas are DMX universe and channel numbers), no registered validation rule, `NodeIndex.merge` collapses duplicates through a dict comprehension, and `ensure` returning false makes the tool adopt the colliding row as its own | §9.5 and the briefs, which treat non-uuid4 identities as the problem and uniqueness as a property the convergence delivers |
| **M-m** | The node identity tool **mints locally, per node** — `_resolve_identity` calls the minter on the node itself. §10.3 requires the table built "once, on the controller, and distributed", warning that per-node minting gives the controller's map and the node's own configuration different answers. So FR-007 is new work, not a property the existing tool already has | the readiness re-measure, which reads as though only the tool's *reach* were missing |
| **M-k** | `project_mappings.xsd`'s `MappedToType` — the second of M-g's two free-text identity declarations — is declared but **referenced by no element**. The live `mapped_to` elements (`:75`, `:116`) are bare `xs:string` carrying JACK port names such as `system:playback_1`, so `MappedToType/uuid` is never instantiated by any document. It nonetheless has a model class and a registry binding, and no sibling repository mentions it. Same shape as `PutType`/X9, which feature 007 deleted | M-g's "two places", which counts two identity declarations where only one is reachable |
| **M-n** | The script filename is recorded in **no document this library reads**. It is an editor-internal settings-dict key, and the two components that use it disagree: the editor's CLI sets `script.xml` while its project manager documents `cue_script.xml`, and the engine hardcodes `script.xml`. A tool cannot "discover the configured filename" because there is no configuration carrying it — scripts must be identified by root element instead (research R3) | FR-012's original wording, "MUST discover the configured script filename", which assumed a configuration value exists. Reworded 2026-09-30 to its intent |
| **M-o** | Files outside the configuration directory **do** carry node identities, in both forms, so the library reach is required rather than precautionary: each project's mappings carry a bare identity (`NodeMappingType/uuid`), and each project's script carries one embedded in compound output names (corpus: `0367f391-…-000000000001_0`). Separately, the library reaches the nodes by rsync **from the controller** on project load, with `-rt` and no checksum flag — so the quick check is size plus modification time. The substitution is length-preserving, which makes the modification time the **only** signal that a rewritten file differs (FR-011b) | the assumption that the re-mint's reach into the library was a matter of thoroughness, and the absence of any statement about how a rewritten library reaches the nodes |
| **M-j** | The consumer's four questions arrived as an upstream report from `cuems-engine` feature 008 dated 2026-09-29, measured against this repository at `996617f`. They are input to the clarification pass, not decisions | the planning documents, which predate the report and do not mention it |
| **M-p** | The overlap ratchet (`tests/contract/test_schema_name_overlap.py`) leaves **one** way to resolve `UuidType`: four tests together admit a twice-declared name only as a recorded *identical* duplicate (bodies must match, whitespace-normalised) or a recorded *divergent* one (bodies must still differ), and require a name that stops overlapping to leave the file. And **none of the six schemas imports or includes another** — they share only a target namespace, so a shared type is declared once per file, `NonEmptyString`'s four-way duplication being the precedent | the allowlist's own recorded verdict, written 2026-09-23 before M-f: "script's is the surviving definition and network_map's narrows to **match**". With the sentinel exception it can never match, so the narrowing must be a rename-and-delete (FR-020c) and the three new names must be recorded as identical duplicates (FR-021d). The verdict text is removed by the same commit, so the correction lands where the claim lived |
| **M-q** | Feature 008's baseline records the `network_map` configuration-load row as **exceeded-or-marginal**, not passing: three trials of five runs gave medians 9.984 / 10.486 / 10.214 ms against a 10.20 ms budget, with the mechanism identified and no mitigation applied in that pass | FR-PERF-002's original "the existing recorded baseline", which named none of the three baselines that exist and, for this row, would have asserted a budget the baseline itself does not meet. The show-document row is compared to its budget; this row is compared to its measured band |

The consumer's own measurements (M-a to M-e in the upstream report) are not restated here; they
are cited by the requirements they drive — FR-028 and FR-029 (one type, sortable), FR-030 (the
mirrored coercion rule), FR-031 (the sentinel constant), FR-035 (the coupled consumer version) and
FR-036 (the incomplete-re-mint detector).

---

## Assumptions

Recorded rather than asked, because a reasonable default exists and the planning documents already
argue for it.

1. **The sentinel is admitted by union, not by loosening.** FR-021 is read as "uuid4 **or** the
   documented sentinel", keeping every other value rejected — rather than relaxing the pattern to a
   shape that would admit other nil-like values. Made structural by FR-021c (2026-09-30): the union
   is two separately named definitions, not one widened pattern, and the union itself is named so
   all three schemas spell the node identity as one type name. Its two consequences are requirements
   rather than assumptions, because both are mechanical: the named union is what the network map's
   node identity is **retyped to**, which is what lets its `UuidType` declaration be deleted and the
   divergence resolved at all (FR-020c); and the three names, being declared once per schema in a
   set of schemas that import nothing, must be recorded as identical duplicates (FR-021d).
2. **The deleted-projects area is included** in the re-mint's reach by default (§10.5): a project
   restored from it after the migration would otherwise reintroduce a stale identity. Excluding it
   is defensible only if restoring from there is accepted as requiring a re-run, and that would be a
   decision to record.
3. **The re-mint stays in the existing node identity tool** rather than becoming a second entry
   point: that tool already owns the cross-document write, the preserve-identity rule and the
   forced re-mint, and §9.4 assigns the work to it by name.
4. **Detection extends the existing identity check** (clarified 2026-09-29). §9.4 assigns
   detection to the conversion machinery, written before the identity check existed. That check
   now owns identity across locations, already reports per path without writing, already has the
   exit-status vocabulary FR-004 needs, and already reads without the schema — so it works on the
   documents the tightening will reject. Extending its **reach** to the project library is work
   FR-011 requires for the re-mint anyway, so the two share it. §9.4's assignment is corrected
   accordingly under FR-037.
5. **Sortability is provided by giving the identity type an ordering** consistent with its string
   form, rather than by asking every consumer to convert at each sort site. One change in the
   library removes the failure for every consumer at once; a consumer that already converts is
   unaffected.
6. **The coercion rule is published** (FR-030's first branch), since a consumer has already
   mirrored it by hand and mirroring library leniency is the duplication class this project's own
   flags exist to catch.
7. **The sentinel constant is published** where it already lives, by declaring the module's public
   surface explicitly rather than relocating it.
8. **No library version change.** Schema changes are signalled by the document version marker; the
   library version stays where the coordinated release pins it.
9. **The library reaches the nodes by the machinery that already exists** (2026-09-30). The
   re-mint rewrites the controller's copy; the ecosystem's project deployer replicates it to each
   node on project load, as it does for every other project change. This feature adds no
   distribution mechanism of its own — it inherits one, and states the single property that
   inheritance depends on (FR-011b, the modification time).
10. **Nothing ships from this branch alone.** This feature merges toward the coordinated release
   tag, after which the whole ecosystem moves together.
11. **The frontend needs no change.** Its minting is already uuid4 and its parsing of the compound
    form is version-agnostic — measured 2026-09-23, and nothing in this feature changes the
    compound form's shape.

---

## Dependencies

- **Feature 011 (landed 2026-09-28, local branch)** — hard. The cross-document write, the
  preserve-identity rule and the forced re-mint that this feature extends all arrive with it, and
  the not-provisioned sentinel that FR-021 must admit is its invention.
- **Feature 010's open check-mode tasks** — **not a dependency** (clarified 2026-09-29). Detection
  extends the existing identity check instead, so nothing in this feature waits on them.
- **Feature 011's D13, amended by this feature** (FR-019d). "Mint if and only if there is none"
  becomes "if and only if there is none, or the identity on disk was minted for different
  hardware". The amendment MUST be recorded against feature 011's decision record, not applied
  silently — feature 011 has landed on its own branch and its decision text is the authority a
  later reader will find first.
- **The coordinated release** — the migration cannot be run on a machine whose consumers predate
  the identity type it produces (FR-035).
- **Hardware confirmation of §10.7** before a first real run (FR-038): the live library layout, the
  configured script filename on each machine, whether every project carries its own mappings, and
  whether any other file in a project embeds an output name. Both production machines have been
  unreachable since 2026-09-23.

---

## Out of scope

- Reshaping device classes, and anything that moves the port inventory — features 013 and 014.
- The Avahi service record's own rewrite: it is derived from the node's configuration at every
  start by the node configuration daemon, settled in feature 011.
- A frontend identity-minting endpoint — the condition that would have required it is not met.
- The editor database, media, waveforms and thumbnails: none stores a node identity.
- Changing the compound `<identity>_<output>` form itself.
- Removing the project mappings' unreferenced complex type and the model class and registry binding
  that accompany it (M-k, FR-020b) — feature 014's, which already owns this schema's reshape.

---

## Questions taken in the clarification pass

The decisions that changed what this feature builds and had no defensible default. **None remain
open.** Each is recorded in **Clarifications** above and applied to the requirements it bears on;
they are kept here, struck, so a later reader can see what was in question and where it landed.

- ~~**Q1 — check-mode ownership.**~~ **Answered 2026-09-29**: neither absorbed nor depended upon —
  detection extends the existing identity check. See Clarifications, FR-001, FR-001a and
  assumption 4.

- ~~**Q2 — the node's own identity type.**~~ **Answered 2026-09-29**: yes, a settings-specific type
  admitting uuid4 or the sentinel. See Clarifications, FR-021a, FR-021b, FR-028 and FR-032. This
  was the consumer's own Q1 and, per its hand-over note, the only one it still needed answered.

- ~~**Q3 — the project-mappings declarations.**~~ **Answered 2026-09-29**: the node mapping's
  identity converges (FR-020a); the unreachable one does not and is handed on (FR-020b, M-k).

  **Corrected at plan time (2026-09-29)**: this answer said "a **two-schema** migration". It is a
  **three-schema** one. Q2's answer types the node's own identity in the configuration document
  (FR-021a), and deployed configuration documents carry a uuid1, so that schema is invalidated too
  and takes its own version step. The two clarification answers were taken separately and their
  combined effect was not stated until Phase 1 traced it. The schemas are the network map
  (version 1 → 2), the project mappings (1 → 2) and the settings (2 → 3). None of them needs a
  *registered* conversion — research R5 — because the machinery represents an identity step as the
  absence of a registry entry, and the repair is out-of-band by design (FR-023).

The four questions the consumer asked (upstream report, 2026-09-29) map onto these as: its Q1 is
**answered** above (FR-021a, FR-021b) — the one it still needed; its Q2, Q3 and Q4 are answered by
assumptions 6, 5 and 7 and by FR-030, FR-029 and FR-031, confirmed rather than reopened.
