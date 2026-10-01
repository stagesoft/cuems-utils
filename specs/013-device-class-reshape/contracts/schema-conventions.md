<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — authoring a class-conditional element

**Feature**: `013-device-class-reshape` | **Binds**: every schema under `src/cuemsutils/xml/schemas/`
**Enforced by**: `tests/contract/test_class_conditional_convention.py` (new)

This is the convention that lets the library derive the class→type map from the schema instead of
declaring it a second time in Python (research R3). It exists because SC-002 requires a new hardware
class with special fields to cost **one** declaration, in **one** schema. A Python-side table would be
the second.

---

## The five rules

1. **The discriminator is an attribute named `class`**, `use="required"`, type `cms:NonEmptyString`,
   declared on the element's unconditional base type. Spelled `class` because that is the form proven
   to validate under the pinned `xmlschema==3.4.3` on 2026-09-23.
2. **Every conditional test is exactly `@class='VALUE'`** — single quotes, no whitespace variation
   beyond what the test normalises, one value per alternative. Anything else is a convention
   violation and fails the contract test rather than being interpreted.
3. **The last `xs:alternative` is unconditional** and names the fallback type. An element with no
   fallback would make an unknown class a validation failure, which FR-002 and assumption A2 forbid:
   the vocabulary is open, and an unrecognised class validates, decodes and is *reported*.
4. **The element lives in a container type that holds nothing else.** A type may not mix single
   element children with a repeated one — the converter's content assembler discards the single ones
   (research R2, `converter.py:144-148`). `DevicesType`, `PlayersType`, `DefaultsType` are this
   feature's three; `OutputsType` and `RegionsType` are the pre-existing precedent.
5. **The container asserts class uniqueness**:
   `<xs:assert test="count(X) = count(distinct-values(X/@class))"/>` (FR-013). Schema-level rather
   than a load-path rule, because `cuems-editor` validates against the XSD directly and a T2 rule
   would not hold where the documents are written.

---

## What a new hardware class costs

| The class needs | Cost |
|---|---|
| no special fields | **nothing.** It is a `class` value the fallback type already accepts. No schema, no model, no constant, no test, no registry entry. |
| special fields | **one** `xs:alternative` line, plus the type it names, in **one** schema. |

Anything beyond that is a defect in this convention, not a cost of the class.

---

## What the library is not allowed to do

- Declare a tuple, list, set or enum of device-class names anywhere in `src/cuemsutils/`
  (FR-010, SC-003, asserted by a source-level ratchet).
- Map a class value to a type by name-mangling (`"video"` → `VideoDeviceType`).
  `registry.py`'s own docstring records what that cost last time: thirteen bindings missed silently.
- Name a Python `@property` after the discriminator. `class` is a keyword; it is a dict **key**, and
  an accessor that needs a name is spelled `device_class` (research R4).

---

## Same-commit obligations for any edit under this contract

| Artifact | Why |
|---|---|
| `CURRENT_SCHEMA_HASHES` (`tests/contract/test_schema_scope.py:65`) | the hash and the schema move together — that pairing is the mechanism |
| `KNOWN_IDENTICAL_DUPLICATES` (`tests/contract/test_schema_name_overlap.py:80`) | any type name this feature declares in more than one schema |
| `KNOWN_DIVERGENT_DECLARATIONS` (`:105`) | **stays empty.** It reached empty as feature 012's completion marker |
| `spec._derive_attributes`' docstring (`spec.py:227-235`) | it states a count of declared attributes that `class` falsifies |

**Not touched by anything under this contract**: `CURRENT_VERSION`, the conversion registry, and
`DELIBERATE_IDENTITY_STEPS`. This feature takes no version step (FR-020, SC-006).
