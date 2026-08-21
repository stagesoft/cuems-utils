# Note for the frontend team — the two payloads now agree (T085, FR-UX-001)

**Feature**: 006-public-object-api · **Date**: 2026-08-20
**Action required: none.** This is a heads-up, and a handover of one cleanup
that is yours to schedule.

---

## What changed

The Angular UI receives the same document type on two paths, and until this
release they disagreed:

| field | `initial_template` (was) | `project_load` (was) | both (now) |
|---|---|---|---|
| `enabled`, `autoload`, `timecode` | `true` — JSON boolean | `"True"` — string | `"True"` |
| `ui_properties.warning` and friends | `0` — number | `"0"` — string | `"0"` |
| `schemaLocation` | absent | **present** | absent |

Both payloads now come from one projection. `project_load` is **byte-identical**
to what it was, minus the dropped `schemaLocation` key; `initial_template` moved
to match it.

## Why no frontend change is required

Because the UI already handles both forms. The boolean reads are written as:

```ts
cueData.enabled === true || cueData.enabled === 'True'
```

The dual-check absorbs the change on the day it ships. That is why this is a
note and not a coordinated release.

`schemaLocation` is the other half, and it was checked rather than assumed
(`schemalocation-evidence.md`): four repositories contain no reference to it at
all, and `cuems-frontend` has exactly one — a `schemaLocation: string` field in
the `InitialMappingsResponse` interface at
`src/app/services/projects/projects.service.ts:120`. Searching all of `src/` for
`.schemaLocation` returns **the declaration and nothing else**: no component,
service or template reads it. It also describes `initial_mappings`, a payload
this feature does not touch.

## The cleanup that is yours

The dual-check exists because the two payloads disagreed. They no longer do, so
it can go:

```ts
// then
cueData.enabled === true || cueData.enabled === 'True'
// now
cueData.enabled === 'True'
```

**Schedule this when it suits you, and not before `v0.1.0` is deployed
everywhere.** A node still running the previous library version sends
`initial_template` in the old form, so a UI that has dropped the dual-check will
read `true` as not-`'True'` and show every cue as disabled. The dual-check is
harmless indefinitely; removing it early is not.

## Why the booleans are strings at all

`cms:BoolType` is an `xs:string` restricted to the two literals `True` and
`False` — not an `xs:boolean`. The wire form follows the schema, and the UI
writes the string form back on save, so this is a round-trip contract rather
than a serialization detail.

Making them real JSON booleans is a **file-format migration**, not a payload
tweak: it changes every show file on every node. It is recorded as deferred item
**X1** and explicitly out of scope here.

## If something does look wrong

The claim "`project_load` is unchanged" is asserted per corpus document by
`tests/contract/test_wire_byte_identity.py`, against payloads captured before
this feature. A field that moved and is not in the table above is a bug in the
library, not an intended change — please report it with the cue type and field
name rather than working around it.
