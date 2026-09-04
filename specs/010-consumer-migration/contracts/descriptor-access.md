# Contract — public descriptor access

**Wave 0** | Governs FR-020–FR-028 | Blocks waves 2 and 3

## What this contract is for

Five repositories will import this surface and depend on it for years (FR-028). It is the only new
public door this feature opens, and it is opened *because* the alternative — consumers reaching
into `cuemsutils.xml`, as `cuems-nodeconf` does today — is the erosion Q14 forbids and no feature
had recorded until C4.

## Shape

The descriptor is reached **through the existing public configuration façade** (D34/D15), not
through a new public module. `cuemsutils.xml.__all__` stays `[]` (FR-024).

**Decided 2026-09-04.** The accessor is **`get_schema_descriptor`**, and it takes a **public
enumeration of schema names**, not a string.

```
from cuemsutils.tools.ConfigManager import ConfigManager, <SchemaNameEnum>

ConfigManager(...).get_schema_descriptor(<SchemaNameEnum>.SCRIPT)
```

`get_schema_descriptor` follows `ConfigManager`'s existing split: bare-noun properties for held
state (`network_map`, `mappings`), `get_*` for parameterised lookups (`get_video_output_id`,
`get_audio_output_id`). A descriptor lookup takes an argument, so it is the second kind.

The enum sits **in the same module as the accessor**, so one import gives a consumer both. That is
a deliberate departure from `NodeRole`, which earns its own module (`tools/NodeList.py`) by
carrying a domain vocabulary; this enum is the argument vocabulary of one accessor and nothing
else. Its members are **asserted against the library's schema registry**, never hand-copied — the
same anti-drift contract `NodeRole` holds against `NodeRoleType`'s facets — and the name must not
read as the loaded-schema object that the internal `get_schema` returns.

**Obligations**

| # | Obligation | Requirement |
|---|---|---|
| 1 | Covers **all six** schemas, `script` included | FR-020 |
| 2 | Per complex type, answers six facts | FR-022, FR-022a |
| 3 | Example generators reachable from the same path | FR-023 |
| 4 | Lazy per schema — asking for one builds one | FR-PERF-001, research R8 |
| 5 | The public result **equals** the internal result, per schema | SC-003 |
| 6 | Carries FR-021's rationale beside the code | FR-021 |

**The six facts**, per complex type:

1. field name
2. XSD type
3. cardinality
4. legal values, where the type is a restricted enumeration
5. model-layer default
6. **a constructible empty instance of the type** ← added by this feature (FR-022a)

Facts 1–5 are **published as they are**, not recomputed (FR-027). Fact 6 is the single sanctioned
addition, and it may not alter, reinterpret or re-derive the other five (FR-022b).

## The widening, stated rather than discovered

A configuration-domain object serving the **show** schema's descriptor is surprising on sight. The
reason must live beside the code, not only in this file (FR-021):

> The alternative is two public paths for one mechanism. The component that serves configuration
> forms is the same one that serves the show template, so splitting the surface by domain would
> split it against the consumer rather than with it.

A reader who finds a script descriptor on a configuration object must find that reason next to it,
or file it as a mistake.

## Consumers, and what each needs

| Consumer | Needs | Wave |
|---|---|---|
| `cuems-editor` | serves the descriptor over WS to the UI | 2 |
| `cuems-frontend` | form structure; the three value-reading sites; fact 6 for output structure | 3 |
| `cuems-nodeconf` | a public equivalent for its two internal imports (FR-025) | 2 |

**FR-025 is a documentation obligation as much as a code one**: where a public equivalent already
exists, the guide **names** it rather than the library adding a synonym. The deliverable is a
stated, tested migration target per import — not necessarily new code.

## Verification

- Per-schema equality between public and internal results — **six assertions, not a sample**
  (SC-003).
- Every complex type across the six schemas yields an instance that **validates against its own
  schema** — 100% of types, counted (SC-003).
- Laziness: asking for one schema's descriptor does not construct the other five (R8). This test
  must not be defeated by an equality test that builds all six first.

## Explicitly not in this contract

- New descriptor capability beyond fact 6 (FR-026).
- Any change to the six schemas (FR-027).
- Any weakening of `cuemsutils.xml.__all__` (FR-024).
