<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Research — feature 012, uuid4 convergence

**Phase 0 output.** Every item below was resolved by measurement against
`012-uuid4-convergence` at `2a88a7c` on **2026-09-29**, not by reading the planning documents.
Where a measurement contradicts the spec or the planning documents, the contradiction is stated
and the correction recorded (FR-037).

Format per item: **Decision** / **Rationale** / **Alternatives considered**.

---

## R1 — `settings.xml` cannot deliver the identity type by flipping a flag

**Measured**: [`registry.py:359`](../../src/cuemsutils/xml/registry.py#L359) —
`SchemaRegistry(schema_name, runs_adapter_table=schema_name == "network_map")`. The adapter table
is a **per-schema** opt-in and `network_map` is the only configuration schema that has it, by
feature 007's research R1. Feature 007 proved by golden comparison (its SC-010a) that the other
four decode every scalar as text.

**Decision**: meet FR-021b with a **per-field** adapter opt-in, not by turning
`runs_adapter_table` on for `settings`. The registry gains a way to say "this one field runs its
declared adapter" and the settings registry names exactly one field: the node's own identity.

**Rationale**: flipping the schema-level flag would re-decode *every* scalar in `settings.xml` at
once — ports to `int`, unit floats to `float`, and so on. That is a behaviour change across the
whole configuration surface, invisible in this feature's tests, and it would break feature 007's
recorded guarantee that four schemas are untouched. FR-021b asks for one field to change type;
the mechanism should have the same blast radius as the requirement.

**Alternatives considered**:

- *Flip `runs_adapter_table` for `settings`* — rejected: blast radius far exceeds the requirement,
  and it silently retires a property feature 007 measured and pinned.
- *Convert in `ConfigManager.node_uuid`'s property rather than in decoding* — rejected: it would
  make the accessor and the underlying `node_conf["uuid"]` dict entry disagree, which is the
  two-types-for-one-value defect (M-a) reproduced one layer down.
- *Leave it as text and convert in every consumer* — this is the spec's rejected option B.

---

## R2 — the uniqueness rule has a mechanism already, and two precedents

**Measured**: [`validators.py:193`](../../src/cuemsutils/xml/validators.py#L193) —
`register(name, applies_to, *, repairable, document_scoped=False)`, consumed at `:410`. Two rules
already use `document_scoped=True`: `target_resolves` (`repairable=True`) and
`action_target_resolves` (`repairable=False`). Both need the whole document to decide, which is
exactly the shape of a cross-row uniqueness check.

**Decision**: register node-identity uniqueness as a `document_scoped=True`, `repairable=False`
rule on the network map's node type. Model it on `action_target_resolves`, which is the closest
precedent in both scope and repairability.

**Rationale**: `repairable=False` is forced by the domain, not chosen for convenience — the
library cannot know which of two colliding rows is the real node, so there is no defensible
default to repair *to*. Feature 008 established that an unrepairable T2 violation raises
`ValidationError`, which is the behaviour FR-019a wants.

**Alternatives considered**:

- *`xs:unique` in the schema* — rejected. It would work, but it puts the diagnosis in
  `xmlschema`'s words rather than ours, and FR-024 requires an error naming the repair tool. The
  T2 tier is where this project already puts rules that need an actionable message. Recorded as a
  genuine alternative rather than dismissed: it is the more conventional XSD answer.
- *Check only in the tool* — rejected by FR-019a, which exists because the collision is currently
  invisible to every consumer.

---

## R3 — the script filename is **not discoverable from configuration**

**Measured**, and this contradicts both FR-012's wording and §10.5:

- `script_file_name` does **not** appear in `settings.xsd`, in `cuemsutils.config.settings`, or in
  any document this library reads. It is an **editor-internal settings-dict key**:
  `cuems-editor/src/cuemseditor/cli.py:41` sets `'script.xml'`, `CuemsProjectManager.py:38`
  documents `'cue_script.xml'`, and `CuemsDBProject.py:212` reads it from a dict the editor builds.
- `cuems-engine` hardcodes `"script.xml"` (`BaseEngine.py:492`).
- `library_path` **is** configuration — `settings.xsd:34`, read by
  [`ConfigBase.library_path`](../../src/cuemsutils/tools/ConfigBase.py#L178).

**Decision**: discover scripts by **root element**, not by filename. For each project directory
under the library, read each candidate file's root element with stdlib XML and treat it as a
script if the root names the script schema's root. The filename becomes irrelevant.

**Rationale**: FR-012's *intent* is that a library configured the other way is not silently
skipped. Reading configuration cannot satisfy that intent, because the value is not in any
configuration this library can see — a tool that "discovered" it would be reading the editor's
private dict, which it has no access to. Root-element identification satisfies the intent
strictly more completely: it finds a script under *any* filename, including one neither repo
uses. It also closes §10.7's "the configured `script_file_name` on each machine" without needing
the hardware that has been unreachable since 2026-09-23.

**Consequence for the spec**: FR-012 said "MUST discover the configured script filename rather
than assuming a constant", which assumed a configuration value that does not exist. **Reworded
2026-09-30** to its intent — "MUST NOT assume a script filename; scripts are identified by root
element" — and the measurement recorded as M-n. The acceptance scenario (US2 scenario 8) passed
as written before the rewording and still does.

**Alternatives considered**:

- *Add `script_file_name` to `settings.xsd`* — rejected for this feature: it is a schema change
  serving one tool, on a schema already taking a version step for a different reason, and the
  editor would still not read it. A candidate for feature 014, not here.
- *Try both known names* — rejected: it is the hardcoding FR-012 forbids, with two constants
  instead of one.
- *Rewrite every `.xml` in a project directory* — rejected: it would touch documents this feature
  has no mandate over, and §10.7 explicitly leaves open whether other files embed output names.
  Root-element identification answers that question per file instead of assuming it.

---

## R4 — the consumer census, measured

FR-032 makes this a **blocking precondition** of the own-identity type change. Measured across
every sibling checkout on 2026-09-29:

| Repository | Reads `node_uuid` / `node_conf["uuid"]`? | Risk under a changed type |
|---|---|---|
| `cuems-engine` | **Yes**, many sites — `BaseEngine.py` (`node_conf["uuid"]`, `.node_uuid`, `.node_uuid == SENTINEL`), `NodeEngine.py` (`:204` comparison, `:337` f-string, `:675` f-string, `:714` comparison), `ControllerEngine.py:281` set membership, `players/DmxPlayer.py` | **None measured.** Every site is equality, `f`-string, set membership or hashing — all covered by the identity type's `__eq__`, `__str__` and `__hash__`. rc7 additionally routes egress through `id_str` |
| `cuems-power-bridge` | **Yes**, one site — `network_map.py:295`, `own_uuid = str(cm.node_uuid)` | **None.** Already converts explicitly |
| `cuems-nodeconf` | **No** | — |
| `cuems-editor` | **No.** Its `node_uuid` occurrences are websocket handler parameters from the frontend, not library reads | — |
| `cuems-common` | **No** | — |
| `cuems-frontend` | **No** — it is TypeScript and consumes JSON over the wire | — |

**Decision**: the type change is safe against every measured site. The census is nonetheless
carried as a task, not closed here: this is a grep-shaped measurement, and FR-032 asks for a
recorded result per repository, which the task produces as an artifact.

**One site worth naming even though it is not a library read**:
`cuems-editor/src/cuemseditor/CuemsWsUser.py:407` does
`if not node_uuid or not isinstance(node_uuid, str)`. The identity type is **not** a `str`
subclass, so this would reject one. It is fed from the websocket, so it is out of reach today —
but it is the exact shape of the silent failure the census exists to find, and it is a reason not
to let the identity type leak into wire payloads.

---

## R5 — the version step needs **no** registered conversion

**Measured**: [`versioning.py:78-91`](../../src/cuemsutils/xml/versioning.py#L78-L91) — the
`Conversion` docstring states that the identity step is represented by the **absence** of a
registry entry, and that "no conversion" and "a conversion that happens to do nothing" must not
be confusable. `convert()` at `:129` treats a missing entry as an identity step and records it as
such.

**Decision**: register **no** conversion for any of the three steps. The version increments; the
document is untouched; the tightened pattern then rejects a non-converged identity at T1, and
FR-024's actionable message is produced in the **validation error path**, not in a conversion.

**The three steps, and a correction to the clarification record**: `network_map` 1→2,
`project_mappings` 1→2 and `settings` **2→3**. The clarification pass's Q3 answer called this a
"two-schema migration", counting only the two schemas whose *identity declarations* Q3 was about.
Q2's answer types the node's own identity in `settings.xsd`, and every deployed configuration
document carries a uuid1, so that schema is invalidated and takes a step too. The two answers were
taken separately and their combined effect went unstated until this phase traced it; the spec is
corrected at FR-022 and at Q3's entry.

**Rationale**: this is what FR-023 asks for — detect and report, never repair — expressed in the
machinery's own vocabulary. Registering a do-nothing `Conversion` to carry a description would
violate the documented invariant and make a future reader unable to tell a deliberate identity
step from a transformation that lost its body.

**Consequence for the spec**: FR-022 has been corrected to require the version step alone, and
FR-022a states that no conversion is registered. **FR-023 was corrected 2026-09-30** by the
analysis pass, which found it still requiring "the registered conversion" to detect and report —
a direct contradiction of FR-022a, and an unimplementable requirement, since the artifact it
named is one this feature deliberately does not create. It is now a requirement on the **version
step**, with detection and reporting produced in the validation error path (FR-024).

**Alternatives considered**:

- *A registered `Conversion` whose `apply` returns `[]`* — rejected by the machinery's own
  documented invariant.
- *Repair in the conversion by minting a new identity per document* — rejected, and this is the
  single most important rejection in the feature: a per-document mint gives `settings.xml` and
  `network_map.xml` different answers for the same node, which is §9.4's measured failure
  (`Node with uuid … not found`).

---

## R6 — clone detection has its inputs already

**Measured**: [`init_node.py:314-338`](../../src/cuemsutils/tools/init_node.py#L314-L338).
`_resolve_identity` already calls `_derive_mac(sysfs)` in its `else` branch, and already holds
`previous["mac"]` from the stored document. The comparison FR-019d needs is between two values
the function has in scope; nothing new must be discovered.

The branch that produces the defect is explicit:

```python
elif real_before and previous.get("mac") and previous["mac"] != SENTINEL_MAC and not args.force_new_identity:
    mac = previous["mac"]
```

The stored MAC is preferred over the hardware's, so a clone never consults its own hardware.

**Decision**: derive the hardware MAC unconditionally, compare it with the stored one, and refuse
a preserved identity when they differ — pointing at `--force-new-identity`. Refuse rather than
re-mint silently: a MAC can also differ because a NIC was replaced on the *same* node, where
preserving identity is correct and re-minting would cost an adoption.

**Rationale**: refusing distinguishes the two cases by asking the one party that can tell them
apart. Silently re-minting would turn a NIC replacement into a lost node identity, which §9.5
establishes is now permanent.

**Alternatives considered**:

- *Re-mint automatically on MAC mismatch* — rejected: indistinguishable from a NIC swap.
- *Compare against the network map instead of the hardware* — rejected: on a freshly cloned node
  the map is the clone's copy and agrees with itself.

**Cost**: deriving the MAC unconditionally adds one sysfs read to every run, including
`postinst`'s. Measured as negligible, but it must not be able to *fail* the run — `_derive_mac`
returning `None` is already a `Refusal` in the mint path and must stay a non-event in the
preserve path.

---

## R7 — `trash/` does mirror `projects/`, and that is code, not hardware

**Measured**: [`ConfigBase.py:154-155`](../../src/cuemsutils/tools/ConfigBase.py#L154-L155) —
`trash = [path.join('trash', i) for i in dirs]`, where `dirs` already contains `projects`. The
hierarchy is created by the library itself.

**Decision**: the re-mint's reach is
`<library_path>/projects/*/` **and** `<library_path>/trash/projects/*/`, derived from
`library_path` in `settings.xml`. Assumption 2 stands, now on evidence.

**Rationale**: §10.7 lists "whether `trash/` mirrors `projects/`" as unconfirmed-on-hardware. It
is confirmed *in code* — the library creates both — which is stronger than one machine's layout.

**Remaining genuinely unconfirmed from §10.7**: whether any project carries its own
`mappings.xml` versus relying on `default_mappings.xml`, and whether any *other* file in a project
directory embeds an output name. R3's root-element discovery makes the second one moot for
scripts; the first is handled by treating `mappings.xml` as optional per project.

---

## R8 — measuring throughput so that a per-node pass is visible

**Decision**: measure megabytes-scanned-per-second over a generated fixture library at **two node
counts** (a small and a large substitution table) over the *same* library bytes. Budget the
throughput figure; assert the wall-clock ceiling on the named fixture; and require the two node
counts to produce throughput within a stated tolerance of each other. **The values were
supplied 2026-09-30** by the analysis pass, which found R8 had specified the budget's shape and
never its magnitude: >= 500 MB/s, the two node counts agreeing within 1%, and the named fixture
`remint_200` (200 projects, ~4 MB) at <= 2.0 s — the last provisional and adjustable downward
only. See FR-PERF-001.

**Rationale**: SC-PERF-001's whole point is catching an implementation that loops files per node.
A single wall-clock number on one fixture cannot see that. Two node counts over identical bytes
turn the defect into a divergence between two measurements, which is a test, not a judgement.

**Fixture scale, grounded**: the largest corpus script is ~24 KB and the whole corpus is 504 KB.
A 200-project library is therefore single-digit megabytes, so the operation is I/O-trivial in
absolute terms — which is exactly why the budget must be shaped to catch algorithmic regression
rather than to police absolute time.

**For FR-PERF-003's operator estimate**: the estimate is
`measured throughput × measured library bytes`, with the node count entering only through the
substitution pass count if the implementation has one. SC-PERF-003's tolerance is what keeps the
estimate honest.

---

## R9 — the check's reach, and what it may assume

**Decision**: the check reads `library_path` from `settings.xml` to find the library, and degrades
to configuration-only when `settings.xml` is absent, unreadable, or carries no library path —
reporting that it did so (FR-005).

**Rationale**: the check must work on a node whose documents the library would refuse, which is
when an operator runs it. It therefore reads with stdlib XML throughout, as
`identity_check` already does, and never routes through the validating load path.

---

## R10 — what stays unresolved, and why it does not block

| Item | Status |
|---|---|
| §10.7 live library layout on the two production machines | **Unresolved** — unreachable since 2026-09-23. Mitigated: R3 and R7 answer the two layout questions from code instead |
| Whether every project carries its own `mappings.xml` | **Unresolved** — handled by treating it as optional per project rather than by knowing the answer |
| The full per-repository census artifact (FR-032) | **Deferred to a task** — the measurement is done (R4); the recorded artifact is not |
| The recorded amendment to feature 011's D13 | **Deferred to a task** — it edits another feature's landed decision record and must be a deliberate, separate act |

None of these blocks design. The two that would have — the script filename and the `trash/`
layout — were resolved from code, which is the better source.


---

## Addendum, 2026-09-30 — resolved during the `/speckit.analyze` pass

R11 and R12 were measured after Phase 0, when the analysis pass asked how a rewritten library
reaches a node that did not rewrite it, and whether the library reach was load-bearing at all.
Both were answered from code in the sibling tree, on the same terms as R1–R10.

## R11 — the library is replicated from the controller, and a length-preserving rewrite is nearly invisible to it

**Measured**, in `cuems-engine`:

- `tools/CuemsDeploy.py:102` — a node syncs from
  `rsync://cuems_library_rsync@<controller ip>/cuems`. `NodeEngine.py:98` constructs it; the
  controller is the source, every other node a replica.
- `tools/CuemsDeploy.py:231` — the command is `rsync -rt --delete --delete-delay …`. **No `-c`,
  no `--checksum`.** rsync's default quick check is *size plus modification time*.

**Decision**: the re-mint rewrites the library **once, on the controller**, and relies on this
replication to carry it. Each node rewrites only its own configuration documents, from the
distributed table. No distribution machinery is added by this feature.

**Rationale**: the machinery exists, is already the path every other library change takes, and is
already ordered against project load. Adding a second one would put two authorities on the same
files.

**The property this inherits, and it is a trap**: the substitution replaces 36 characters with 36
characters, so **every rewritten file is exactly the size it was**. Under `-rt` with no checksum,
the modification time is the *only* thing that tells rsync the file changed. A rewrite that
preserved modification times — an easy, well-intentioned thing to add — would leave every node's
replica stale indefinitely, with no error at any layer; the failure would surface much later as
an output resolving to nothing. Writing through a temporary plus `os.replace` gives a fresh time
and satisfies it. Pinned as FR-011b and tested, rather than left as a property that happens to
hold.

**Alternatives considered**:

- *Have every node re-mint its own library replica* — rejected: N nodes independently rewriting
  replicas of one authoritative tree, with `--delete` replication running against them. The
  controller's copy is the only one that means anything.
- *Add `-c` to the deploy* — rejected as out of scope and the wrong repository: it would slow
  every project load for every future change to fix one migration's blind spot.
- *Touch each rewritten file explicitly* — unnecessary; `os.replace` already does it. Recorded
  because the temptation is to add it, and the real requirement is the opposite — **do not**
  restore times.

## R12 — the library reach is required, not precautionary

**Measured**: node identities are present outside the configuration directory in **both** forms
this feature must handle.

- Bare: `project_mappings.xsd:45`, `NodeMappingType/uuid` — carried by each project's
  `mappings.xml` as well as by `/etc/cuems/default_mappings.xml`.
- Embedded: the corpus carries `<output_name>0367f391-ebf4-48b2-9f26-000000000001_0</output_name>`
  and three siblings — the compound `<identity>_<output>` form, in a script.

**Decision**: FR-011's reach into the library stands as required work. Recorded as M-o.

**Rationale**: the analysis pass asked whether files outside `/etc/cuems` genuinely need
re-minting before committing to the largest part of the feature. They do, and the embedded form
is why literal substitution is the instrument — a structural rewrite would update the mappings
and leave every script's output prefix stale and schema-valid.
