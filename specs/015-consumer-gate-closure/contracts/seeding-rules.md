<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — instance seeding rules

**Phase 1** · 2026-10-13 · the closed rule set that makes a type instance saveable (FR-025, FR-026b,
FR-028), derived in [research.md](../research.md) R3.

**What a seed is**: a value for one field, computed from that field's **resolved simple type** —
never from the field's name. A seed is used only where the bound model class leaves the field unset,
so every value the model already supplies stays exactly where it is.

**Precedence**

| 1 | the bound model class's declared default, if any |
| 2 | the seed below |

**What a seed is not**: it is not a `FieldDescriptor.default`, and it does not enter the
repairability classification. That separation is the gate's load-bearing invariant — see
[public-surface.md](public-surface.md) C3.

---

## The rules, in order. First match wins.

| # | Condition on the resolved simple type | Seed |
|---|---|---|
| 1 | has `xs:enumeration` facets | the **first declared** value |
| 2 | is a union | the enumerated member's first value if any member is an enumeration; else apply rules 3–7 to the first member |
| 3 | numeric with `minInclusive` | that bound |
| 4 | numeric with `minExclusive` **and** `maxInclusive` | the `maxInclusive` |
| 5 | numeric with only `maxInclusive` | `0` |
| 6 | length-bounded string, **no** pattern | `""` if `minLength` is 0, else one character |
| 7 | pattern-restricted string | the declared seed for that type — the table below |
| 8 | an XSD built-in | the table below |

**Rule 4's reasoning, because it is the only non-obvious one**: "the smallest valid value" is not
expressible for an exclusive float bound, so the inclusive bound at the other end is used. For the
two types this reaches — a scale factor and a region dimension — `1.0` is also the semantically
right seed.

**Rule 2 has an ordering dependency** on S2 landing first. Before the union narrowing, a union's
merged member enumerations are reported *as* the type's enumeration, so rule 1 fires and returns the
right value for the wrong reason — and the test meant to pin rule 2 would pass vacuously.

---

## Built-ins in use (7, measured across all six schemas)

| Type | Sites | Seed | Note |
|---|---|---|---|
| `boolean` | 32 | `False` | |
| `string` | 24 | `""` | |
| `positiveInteger` | 7 | **`1`** | the one built-in where `0` would **not** validate |
| `nonNegativeInteger` | 6 | `0` | |
| `integer` | 4 | `0` | |
| `float` | 4 | `0.0` | |
| `byte` | 1 | `0` | |

## Rule 7 — the pattern table (5 entries)

A regular expression cannot be inverted, and no runtime dependency generates a matching string. This
is the irreducible residue, keyed by **type**, not by field.

| Type | Pattern | Seed |
|---|---|---|
| `UuidType` (script) | `[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}` | `00000000-0000-4000-8000-000000000000` |
| `TargetType` | `(uuid-shaped)\|()`, `minLength 0` | `""` — the pattern admits empty |
| `Md5Type` | `[a-f0-9]{32}` | thirty-two `0` characters |
| `TimecodeType` | `[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}` | `00:00:00.000` |
| `NonEmptyString` (declared in 4 schemas, identical facets) | `.*[^\s].*`, `minLength 1` | one non-space character |

**Two contract tests guard this table**, in the shape this repository already uses for closed tables
(`seed_values.py`'s four rules; `_assert_every_choice_member_has_a_builder`):

1. **Completeness** — every pattern-restricted simple type reachable from any instance in the six
   schemas has an entry. A sixth pattern added to any schema **fails** rather than silently seeding
   nothing.
2. **Validity** — every entry validates against its own declared type. A table entry that does not
   match its pattern is the one failure mode that would otherwise surface as an unsaveable instance
   in a consumer.

---

## Named types this resolves, by rule (30, measured)

| Rule | Types |
|---|---|
| 1 — enumeration | `PostGoType`→`pause`, `ActionType`→`play`, `FadeCurveType`→`linear`, `PortDirectionType`→`input` |
| 2 — union | `NodeUuidType`→the NOT PROVISIONED sentinel (3 schemas), `AutoOrIntLatencyMsType`→`auto` (settings) |
| 3 — `minInclusive` | `PercentType`→`0`, `ChannelNumberType`→`0`, `ChannelValueType`→`0`, `UnitFloat`→`0.0`, `NonPrivilegedPort`→`1024`, `LoopType`→`-1`, `DateType`→`2020-01-01T00:00:00` |
| 4 — `minExclusive` + `maxInclusive` | `PositiveUnitFloat`→`1.0` |
| 5 — only `maxInclusive` | `IntLatencyMsType`→`0` |
| 6 — length-bounded, no pattern | `DescriptionStringType`→`""`, `NameStringType`→one character |
| 7 — pattern | the five above |

**The sentinel is the semantically right seed for an unprovisioned identity**, so rule 2 happens to
be correct twice — once structurally and once in meaning.

**`LoopType`'s `minInclusive` is `-1`**, so rule 3 seeds `-1`. The model's declared default is `1`
and takes precedence, so no instance is affected today; the rule is stated for the case where a
model binding is absent.

---

## Completeness claim, stated so it can be checked

**25 of the 30 named types are derived from facets alone; the 7 built-ins are table-seeded.**
(⚠ This said "and all 7 built-ins are derived from facets alone", which is not what rule 8 does —
rule 8 *is* a seven-entry per-type table. The distinction matters only because FR-028's prohibition
is about tables, so the one claim worth stating precisely is which seeds come from a table: twelve
of them, five by rule 7 and seven by rule 8.) The remaining five
are rule 7's table. FR-028's prohibition is on a *per-field* table of fallbacks and on per-type
special cases; a five-entry table keyed by type, with a completeness test, is neither — and it is the
same answer this repository already reached twice for the same shape of problem.
