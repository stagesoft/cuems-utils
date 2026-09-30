<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Data model — feature 012, uuid4 convergence

**Phase 1 output.** Entities, their fields, the validation rules that bind them, and the state
transitions the re-mint moves through. Derived from [spec.md](spec.md)'s Key Entities and
requirements, and from [research.md](research.md)'s measurements.

---

## 1. The converged identity

### 1.1 The three declarations that move

| Schema | Element | Today | After | Version step |
|---|---|---|---|---|
| `network_map.xsd` | `node_list/node/uuid` (`cms:UuidType`) | any version, either case | retyped to `cms:NodeUuidType`, the **admitted** set (§1.2); the schema's own `UuidType` declaration is **deleted** (FR-020c) | 1 → 2 |
| `project_mappings.xsd` | `NodeMappingType/uuid` (`xs:string`) | any text | `cms:NodeUuidType` | 1 → 2 |
| `settings.xsd` | `NodeConfType/uuid` (`cms:NonEmptyString`) | any non-empty text | `cms:NodeUuidType`, replacing `cms:NonEmptyString` | 2 → 3 |

All three spell the node identity as **one type name**, so no schema carries a union expression of
its own. What that does *not* buy is a single declaration: **none of the six schemas includes or
imports another** — they only share a target namespace — so each of the three declares its own copy
of the three named types. `NonEmptyString`, declared identically in four schemas, is the precedent.

**So the anti-drift guarantee is a test, not a schema mechanism.** The three names are recorded in
`tests/contract/test_schema_name_overlap.py`'s `KNOWN_IDENTICAL_DUPLICATES` (FR-021d), whose drift
test fails the moment one copy gains a facet the others lack. That is the whole guard, and it is
worth naming precisely: an earlier draft of this section claimed the three schemas "reference the
same pair of definitions, so the convergence cannot re-diverge", which is not true of schemas that
reference nothing. The convergence cannot re-diverge because a test says so.

### 1.1a Why the network map's `UuidType` is deleted rather than edited

`UuidType` is declared in `network_map.xsd` **and** `script.xsd`, and the overlap ratchet allows a
twice-declared name exactly two states:

| Recorded as | The test's demand |
|---|---|
| identical duplicate | the declarations' content must **match** |
| divergent, with a verdict | the declarations must **still differ** |

After the narrowing, the network map's node identity admits the sentinel and the show script's
`UuidType` — which types cue and media `id`, not a node identity — must not, by FR-021. The two can
therefore never match, so the divergence entry could never be removed and FR-025's completion marker
would be unreachable. Retyping the element to `cms:NodeUuidType` and deleting the network map's
`UuidType` leaves the name declared **once**, so it stops overlapping, a third test
(`test_the_allowlist_has_no_stale_entries`) then *requires* the entry's removal, and the convergence
completes for the reason it claims to.

**Not moving**, and each for a stated reason:

- `script.xsd`'s `UuidType` — already exactly the converged pattern. It types cue and media `id`,
  not a node identity; its three `node_uuid` elements are commented out.
- `project_mappings.xsd`'s `MappedToType/uuid` — inside a complex type no element references
  (M-k). Out of scope by FR-020b, handed to feature 014.
- `output_name` — stays `NameStringType`. The compound `<identity>_<output>` form is unchanged
  (Out of scope), which is exactly why a stale prefix stays schema-valid and why FR-009 uses
  literal substitution.

### 1.2 The shape — two definitions, and the union of them

**The word "converged" means uuid4 and only uuid4**, here and in every requirement. The sentinel
is *admitted*, never *converged*. The set a schema accepts is the **admitted** set. Keeping the
two words apart is load-bearing: §6.1's decode table and the published coercion rule both turn on
the sentinel not being converged.

```
converged ::= [0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}   (length 36)
sentinel  ::= "00000000-0000-0000-0000-000000000000"
admitted  ::= converged | sentinel
```

The three names, in the schemas:

| Name | Is | Declared in |
|---|---|---|
| `cms:ConvergedUuidType` | the converged pattern, length-pinned at 36 | network_map, project_mappings, settings |
| `cms:NotProvisionedUuidType` | the sentinel, as an enumeration of one value | the same three |
| `cms:NodeUuidType` | the **union** of the two — the only one any element names | the same three |

Only the union is referenced by an element; the two halves exist to be nameable, testable and
removable on their own (FR-021c). All three are recorded as identical duplicates (FR-021d, §1.1).

In the library the same split is the identity type plus the published sentinel constant. The
sentinel is admitted **by union, not by loosening** (assumption 1): no other nil-like value
becomes valid. It is a documented placeholder, not an identity — FR-021's second sentence.

### 1.3 Classification

Every identity the check reports falls in exactly one class. The classes are the vocabulary for
FR-002, the check's exit status (FR-004) and the operator's decision.

| Class | Meaning | Operator action |
|---|---|---|
| `converged` | uuid4, lowercase | none |
| `not-converged` | a well-formed uuid of another version, or upper case | run the re-mint |
| `not-provisioned` | the sentinel | run the identity tool; the node was never provisioned |
| `unrecognised` | not a uuid at all, or unreadable | inspect by hand |

`not-provisioned` is deliberately **not** a failure: feature 011 established it as the coherent
state of a freshly installed node. It is reported distinguishably because it needs a different
action from `not-converged` (US1 scenario 3).

---

## 2. Substitution table

The only record linking an old identity to its new one. Persisted **before** the first write
(FR-007); its loss strands a partly-rewritten cluster.

| Field | Type | Notes |
|---|---|---|
| `created` | timestamp | when the table was minted |
| `controller` | identity | the node that built it — the table is built once, centrally (FR-019c) |
| `entries` | map old → new | one entry per **distinct** old identity |
| `applied` | list of paths | every file already rewritten, appended as each `os.replace` lands |
| `scope` | `configuration` / `library` / `both` | which reach this run performed — the controller does both, a plain node only its own configuration (FR-011a) |

### 2.1 Invariants

1. **Every `new` is uuid4**, minted through the library's minter, which refuses any other shape
   — so the table cannot contain a value the tightened pattern will reject (FR-006).
2. **Every `new` is distinct.** A minted collision is vanishingly improbable but the table is
   checked rather than trusted, because the failure is silent and permanent.
3. **No `new` appears as an `old`.** A chained substitution would rewrite a node twice.
4. **A node already converged has no entry.** `old == new` is not recorded; the file is not
   rewritten (FR-014).
5. **Keys are built from node identities only** (FR-010), never from cue or media identifiers,
   which bounds where a replacement can land.

### 2.1a Who rewrites what

| Reach | Rewritten by | Reaches the other nodes by |
|---|---|---|
| the configuration documents under the configuration directory | **each node, itself**, from the distributed table | not at all — each node's are its own |
| the project library | **the controller, once** | the existing project-deployer replication, on project load |

A node that is not the controller MUST NOT rewrite its replica of the library, and MUST NOT mint
a table of its own. It refuses in the second case; it accepts a table the controller built, which
is what the table is for (FR-019c).

**The property the replication depends on** (FR-011b): the substitution preserves file size
exactly — 36 characters become 36 characters — and the replication in use compares size and
modification time, with no checksum. The modification time is therefore the *only* signal that a
rewritten file differs. Writing through a temporary and an atomic replace gives a fresh time and
satisfies this; restoring the original times would strand every node's replica silently.

### 2.2 Resume

`applied` is what makes the operation resumable (FR-008). On re-run the table is loaded, not
rebuilt; files in `applied` are skipped; minting does not happen again.

**The refusal on `controller`, stated exactly, because an earlier draft of this section had it
backwards.** A table whose `controller` is not **this node** is the *normal* case on every node but
one — that is what distribution means, and refusing it would refuse the table's whole purpose. The
refusal is on a table whose `controller` is not **the map's controller**: such a table was minted by
something with no authority to mint it. See contracts/cli-remint.md, "Not a refusal".

### 2.2a How the table travels

The operator copies it (FR-007). This feature adds no transport: the table is one small file, the
migration is attended and stop-the-world, and a second distribution mechanism would put two
authorities on the operation's only durable record. The copy is a numbered step in the migration
guide (FR-034), and a node invoked without a table refuses by design rather than by accident.

### 2.3 Completion record

One per node per run (FR-017a), written where the tool already keeps its state. It is what makes
"the cluster is converged" a countable claim rather than an impression.

| Field | Type | Notes |
|---|---|---|
| `node` | identity | the node this record is for — its **new** identity |
| `table` | digest + path | which table this run applied; a record naming a different table is not part of this migration |
| `scope` | `configuration` / `library` / `both` | mirrors the table's `scope` for this run |
| `rewritten` | list of paths | what this node actually changed |
| `verification` | per-check result | FR-016's zero-token search, FR-017's validate-and-load, FR-018's adoption comparison |
| `finished` | timestamp | |

**The roll-call** (FR-036c): the operator holds the records, keys them by `node`, and compares the
set against the network map's rows. Equal sets mean the cluster is converged; a row with no record
is a node the migration did not reach, reported as incomplete rather than inferred to be fine. The
controller's own run exiting cleanly says nothing about the other nodes, which is why this exists.

---

## 3. Identity report

What the read-only check produces (FR-001). Data only, never `None` in place of an empty report
— the convention feature 008 set for `LoadReport`.

| Field | Type |
|---|---|
| `locations` | list of occurrences |
| `verdict` | `ok` / `mismatch` / `migration-needed` / `absent` / `not-provisioned` |
| `exit_code` | 0 / 1 / 2 / 3 |
| `fix` | the command to run, or empty |

The verdict vocabulary **extends** the shipped one rather than replacing it (Principle III): `ok`,
`mismatch`, `absent` and `not-provisioned` are what the tool reports today, and
`migration-needed` is this feature's addition. It is the field that distinguishes the two
meanings now sharing exit class 1 — a mirror disagreeing with the source, and an identity that is
not converged. Existing consumers keying on `mismatch` keep their meaning.

Exit codes and their precedence (3 > 2 > 1) are the shipped tool's, unchanged; only class 1
widens. The four are listed in contracts/cli-check.md.

Each occurrence carries:

| Field | Type | Notes |
|---|---|---|
| `path` | file path | absolute |
| `location` | element path or `output_name` | where within the document |
| `value` | string | the identity as found |
| `classification` | one of §1.3 | |
| `embedded` | bool | true when found inside a compound string rather than as an element's whole value |

`embedded` exists because it is the distinction that makes a structural rewrite wrong (§10.2),
and an operator reading the report should be able to see how much of the work is invisible to a
naive tool.

---

## 4. Node row — the collision case

A network map's rows are keyed by MAC and matched by identity ("practice 5: match by uuid, key by
MAC"). That asymmetry is what makes a collision *representable*: two rows can carry one identity.

### 4.1 The rule

| | |
|---|---|
| Name | node identity uniqueness |
| Scope | `document_scoped=True` — needs every row to decide |
| Repairable | **`False`** — the library cannot know which row is the real node |
| Raises | `ValidationError`, naming both rows with their MACs |

Modelled on `action_target_resolves`, the closest existing precedent in both scope and
repairability (R2).

### 4.2 Why the re-mint aborts rather than resolving

Splitting a shared identity is safe in the configuration documents — the MAC discriminates — and
**unsafe in the library**, where the compound `<identity>_<output>` prefix is the only record of
which node an output belongs to. No discriminator exists there, so a split would silently
reassign one node's entire output set. The re-mint therefore aborts (FR-019), naming both rows
and every script referencing the shared token.

---

## 5. State transitions

### 5.1 A node's identity

```
        ┌──────────────────┐
        │ not-provisioned  │  fresh install; sentinel
        └────────┬─────────┘
                 │ identity tool mints
                 ▼
        ┌──────────────────┐        re-mint          ┌──────────────────┐
        │    converged     │◄────────────────────────│  not-converged   │
        └────────┬─────────┘                         └──────────────────┘
                 │                                            ▲
                 │ disk image restored onto other hardware    │ deployed uuid1/uuid5
                 ▼                                            │
        ┌──────────────────┐                                  │
        │ cloned (refused) │──── operator re-mints ───────────┘
        └──────────────────┘      or confirms NIC swap
```

`cloned` is the state FR-019d adds: stored identity present, stored MAC not this hardware's. It
is refused rather than resolved, because it is indistinguishable from a NIC replacement on the
same node — where preserving identity is correct and re-minting would cost an adoption (R6).

### 5.2 The re-mint

```
survey ──► [abort if collision] ──► build table ──► persist ──► estimate ──► confirm
                                                                               │
                              ┌────────────────────────────────────────────────┘
                              ▼
        per file: read ─► substitute ─► temp ─► os.replace ─► append to applied
                              │
                              └──► verify: zero old tokens, all documents valid, loads succeed
                              │
                              └──► write the completion record (§2.3)
```

The collision check runs **after** the survey and **before the table is built**, which is earlier
than "before any write" and is the order contracts/cli-remint.md states: an abort then costs
nothing at all, not even a minted identity.

Everything up to the verify step reads with **stdlib XML only** (FR-006a) — the survey and the
collision check both run on documents the tightened definition refuses, which after the narrowing is
every document they exist to repair. The verify step is the one place validation is wanted, and it
runs only after the rewrite has made validation possible.

The estimate divides the survey's measured byte count by **the throughput the survey itself
observed** on this machine — its own elapsed time over its own bytes read — not by FR-PERF-001's
floor, which an implementation is expected to beat and which would therefore make every estimate
pessimistic by exactly that margin (FR-PERF-003). Where the survey is too small to time
meaningfully the run falls back to the floor and says so. The estimate is presented with the
confirmation.

---

## 6. Library surface

| Symbol | Kind | Requirement |
|---|---|---|
| the identity type, gaining a total ordering | existing, extended | FR-029 |
| the coercion rule, published outside `cuemsutils.xml` | new | FR-030 |
| the sentinel constant, declared public | existing, exposed | FR-031 |
| the own-identity accessor's return type | changed | FR-021b, gated on FR-032 |

### 6.1 The decoded type, by state

| Node state | Value on disk | Own identity accessor | Map identity |
|---|---|---|---|
| provisioned | converged | identity type | identity type |
| not provisioned | sentinel (admitted, **not** converged) | the published sentinel constant, a plain string | the same constant |

The published coercion rule (contracts/library-surface.md §2) reads "a **converged** value becomes
the identity type" in exactly the §1.2 sense, so the sentinel falls through its second branch and
stays a string. That is the intended result, not an exception to the rule.

The type varies only between provisioned and not, and identically from every accessor — the one
documented exception in FR-028, and the reason a consumer needs exactly one check (M-d).

### 6.2 Ordering

The identity type gains a total ordering consistent with its string form. It already defines
`__eq__` and `__hash__` against both itself and `str`, so ordering completes the set rather than
introducing a new comparison semantics. This removes the sort failure for every consumer at once
(M-b), including the ones that have not been fixed.

**Not added**: slicing, `len`, or `split`. Those would invite consumers to treat an identity as a
string in ways that the compound-form parsing already handles elsewhere, and the census (R4)
found no site that needs them.
