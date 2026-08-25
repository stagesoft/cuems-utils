# `negative/` — parity cases, not compatibility obligations

**Feature**: `004-xml-serialization-core` | **Task**: T006b

Every document in this directory is **rejected** by the library today. They are vendored so
that the refactor keeps rejecting them, for the same reason and with the same exception
type — nothing more.

## Why this distinction matters

`legacy/` and `negative/` look alike from the outside: both hold old documents recovered
from history. They carry opposite obligations.

| | `legacy/` | `negative/` |
|---|---|---|
| Loads today | ✅ | ❌ |
| Obligation | **must keep loading** (FR-035a) | must keep **failing the same way** (FR-015) |
| If it changes | compatibility regression | parity regression |
| In scope to fix | — | **no** |

Treating a `negative/` document as a compatibility obligation would mean making the library
accept it — which is a schema change (FR-023 forbids `.xsd` edits here) and a behaviour
change (FR-015 forbids that too). **Out of scope per FR-035a.**

## The documents

### `settings_bad_dmx_auto.xml`

Deliberately malformed, authored in this repository as a negative fixture. A DMX field
carries the literal `auto` where the schema requires `xs:nonNegativeInteger`.

```
XMLSchemaDecodeError: failed validating 'auto' with XsdAtomicBuiltin(name='xs:nonNegativeInteger')
```

Unlike the other two, this one was always meant to fail. It is the reason
`tests/contract/test_accept_reject_parity.py` has a case that cannot be confused with an
accident.

### `settings-utils-v0.1.0rc2.xml` and `settings-utils-v0.1.0rc7.xml` — **X13**

Recovered from this repository's own release tags. Both were valid when they shipped. Both
are rejected now:

```
Reason: Unexpected child with tag 'videoplayer' at position 13. Tag 'gradient_osc_port' expected.
```

`gradient_osc_port` was added to `NodeConfType` **without** `minOccurs="0"`, so it is
required. Every settings file written before it existed became invalid the moment the
schema landed — including files this project itself shipped in two releases.

This is **X13** in the audit's deferred series. It is recorded, not fixed:

- fixing it means editing `settings.xsd`, which FR-023 forbids in this feature;
- the fix is a one-attribute change (`minOccurs="0"`), but it changes what the library
  **accepts**, which is a behaviour change (FR-015);
- it is scheduled under the schema-evolution convention adopted in feature 006 — see
  `specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md` §5.1 and §9 rules 7–8, whose whole
  point is that a new required element is a breaking schema change and must be added
  optional-with-default instead.

Two shipped releases are the evidence that the convention is worth having. That is why
these files are in the corpus rather than in a footnote: X13 is currently a paragraph, and
after 006 it becomes a `legacy/` entry that must load.
