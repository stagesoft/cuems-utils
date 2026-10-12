<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the library surface consumers see

Everything here is **public**: a consumer must be able to name it, and nothing in
`cuemsutils.xml` counts, because consumers may not import that package (Q14).

## 0. One word, one meaning

*Converged* means uuid4 lowercase, 36 characters. The not-provisioned sentinel is **admitted** by
the schemas but is never *converged*. Every table below uses the words that way; §2 in particular
is unreadable if they blur.

## 1. The identity type — gains a total ordering

Already defines equality and hashing against both itself and `str`. Ordering completes that set,
consistent with the string form.

| | |
|---|---|
| Before | `sorted()` over identities raises `TypeError` |
| After | sorts, ordering by string form |
| Not added | slicing, `len`, `split` — no measured consumer needs them, and they invite treating an identity as a string |

This removes the failure for every consumer at once, including those not yet fixed (M-b).

## 2. The coercion rule — published

The public face of the library's own decoding leniency:

| Input | Output |
|---|---|
| a **converged** value — uuid4 lowercase, and only that | the identity type |
| any other non-empty string, **including the sentinel** | unchanged, as a string |
| empty | nothing |

"Converged" here is data-model §1.2's sense: uuid4 alone. The sentinel is *admitted* by the
schemas but is not converged, so it falls through the second branch and a consumer receives the
published constant as a plain string — which is what makes one comparison enough to recognise an
unprovisioned node.

Lives in `cuemsutils.tools`, **not** in `cuemsutils.xml`. One consumer has already mirrored this
rule by hand (M-c); publishing it lets that copy be deleted rather than left to drift.

## 3. The sentinel constant — declared public

Declared as public surface where it already lives, rather than relocated (assumption 7). A
consumer compares against it to recognise an unprovisioned node **before** attempting a full
load, which otherwise raises (M-d).

**Which constant**, stated because the tool holds two that answer to the name: the **nil-uuid
value** a node carries as its identity placeholder — not the human-readable status string the
report prints for it, which is already public and answers a different question ("what should this
line of output say?" rather than "is this node provisioned?"). If both remain published, each
carries documentation naming the question it answers.

## 4. The own-identity accessor — changed return type

**Gated on the consumer census (FR-032), which is a blocking precondition, not a follow-up.**

| Node state | Returns |
|---|---|
| provisioned | the identity type |
| not provisioned | the sentinel constant (a string) |

Identical from every accessor, so one check distinguishes the two states.

### Census result (R4, measured 2026-09-29)

| Repository | Reads it | Risk |
|---|---|---|
| `cuems-engine` | yes, many sites | none measured — equality, f-string, set membership, hashing |
| `cuems-power-bridge` | yes, one site | none — already converts explicitly |
| `cuems-nodeconf`, `cuems-editor`, `cuems-common`, `cuems-frontend` | no | — |

### The second column the census must carry (FR-032a)

The accessor's type is not this feature's only change to what a consumer receives. FR-019a makes
node-identity uniqueness a registered, **not repairable** rule, so a network map carrying two rows
with one identity — which loads today, `NodeIndex.merge` collapsing the duplicate silently (M-l) —
raises `ValidationError` for every reader afterwards. That is the feature's only change that turns a
successful read into an exception, and it reaches every repository that reads the map, not just the
two that read the accessor.

Each repository is therefore recorded **twice**: what it does with the changed type, and what it does
when a map read raises. Both are blocking for the same reason and for opposite failure modes — the
first is silent, the second is loud and lands far from its cause.

**One site named although it is not a library read**: the editor's websocket handler rejects a
non-`str` node identity by `isinstance`. Fed from the frontend, so out of reach today — and a
reason not to let the identity type leak into wire payloads.

## 5. What does not change

- The compound `<identity>_<output>` form.
- Wire payloads: an identity projects to its string form, as it does today.
- The library version. Schema changes are signalled by the document version marker.
