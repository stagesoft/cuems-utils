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
| `network_map.xsd` | `node_list/node/uuid` (`cms:UuidType`) | any version, either case | uuid4 lowercase **or** sentinel | 1 → 2 |
| `project_mappings.xsd` | `NodeMappingType/uuid` (`xs:string`) | any text | uuid4 lowercase **or** sentinel | 1 → 2 |
| `settings.xsd` | `NodeConfType/uuid` (`cms:NonEmptyString`) | any non-empty text | uuid4 lowercase **or** sentinel | 2 → 3 |

**Not moving**, and each for a stated reason:

- `script.xsd`'s `UuidType` — already exactly the converged pattern. It types cue and media `id`,
  not a node identity; its three `node_uuid` elements are commented out.
- `project_mappings.xsd`'s `MappedToType/uuid` — inside a complex type no element references
  (M-k). Out of scope by FR-020b, handed to feature 014.
- `output_name` — stays `NameStringType`. The compound `<identity>_<output>` form is unchanged
  (Out of scope), which is exactly why a stale prefix stays schema-valid and why FR-009 uses
  literal substitution.

### 1.2 The shape

```
converged  ::= uuid4-lowercase | sentinel
uuid4-lowercase ::= [0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}   (length 36)
sentinel        ::= "00000000-0000-0000-0000-000000000000"
```

The sentinel is admitted **by union, not by loosening** (assumption 1): no other nil-like value
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

### 2.2 Resume

`applied` is what makes the operation resumable (FR-008). On re-run the table is loaded, not
rebuilt; files in `applied` are skipped; minting does not happen again. A run that finds a table
whose `controller` is not this node refuses — the table is distributed, not regenerated per node.

---

## 3. Identity report

What the read-only check produces (FR-001). Data only, never `None` in place of an empty report
— the convention feature 008 set for `LoadReport`.

| Field | Type |
|---|---|
| `locations` | list of occurrences |
| `verdict` | `converged` / `migration-needed` / `undetermined` |
| `exit_code` | 0 / 1 / 2 |
| `fix` | the command to run, or empty |

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
survey ──► build table ──► persist ──► [abort if collision] ──► estimate ──► confirm
                                                                               │
                              ┌────────────────────────────────────────────────┘
                              ▼
        per file: read ─► substitute ─► temp ─► os.replace ─► append to applied
                              │
                              └──► verify: zero old tokens, all documents valid, loads succeed
```

The collision check runs **after** the survey and **before** any write, so an abort costs
nothing. The estimate is produced from the survey's measured byte count and the throughput
budget, and presented with the confirmation (FR-PERF-003).

---

## 6. Library surface

| Symbol | Kind | Requirement |
|---|---|---|
| the identity type, gaining a total ordering | existing, extended | FR-029 |
| the coercion rule, published outside `cuemsutils.xml` | new | FR-030 |
| the sentinel constant, declared public | existing, exposed | FR-031 |
| the own-identity accessor's return type | changed | FR-021b, gated on FR-032 |

### 6.1 The decoded type, by state

| Node state | Own identity accessor | Map identity |
|---|---|---|
| provisioned | identity type | identity type |
| not provisioned | the sentinel constant (a string) | the sentinel constant |

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
