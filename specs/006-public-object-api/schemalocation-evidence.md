# Evidence: who reads `schemaLocation` (T038, CHK027, CHK042)

**Feature**: 006-public-object-api · **Searched**: 2026-08-20

FR-011 removes the `{http://www.w3.org/2001/XMLSchema-instance}schemaLocation` key from the
wire dict, and FR-029 narrows the written attribute to the bare schema filename. Both are
safe only if nothing downstream reads either. **A negative result is only evidence if what
was searched is recorded**, so this file records the search rather than the conclusion.

## What was searched

| Repository | Branch | Commit | Path searched |
|---|---|---|---|
| `cuems-engine` | `rc_1` | `afff04a` | whole tree, excluding `.git` |
| `cuems-editor` | `rc1` | `ef74136` | whole tree, excluding `.git` |
| `cuems-nodeconf` | `feat/nodeconf-reenable` | `0a3ce37` | whole tree, excluding `.git` |
| `cuems-common` | `rc_1` | `0be3506` | whole tree, excluding `.git` |
| `cuems-frontend` (Angular) | `main` | `c69dc1c` | `src/`, excluding `node_modules`, `dist` |

Patterns, case-sensitive, over source files (`.xsd` and `.xml` files excluded — those *declare*
the attribute, which is the point, and are not consumers of it):

```
schemaLocation
schema_location
xsi:
```

## Result

**Four of the five repositories: zero hits.** `cuems-engine`, `cuems-editor`,
`cuems-nodeconf` and `cuems-common` contain no reference to the attribute or the key in any
form.

**`cuems-frontend`: one hit**, and it needs stating precisely rather than being counted as a
blocker or waved away.

```
src/app/services/projects/projects.service.ts:120:    schemaLocation: string;
```

Three facts about it, each checked:

1. **It is a type declaration, not a read.** It is a field in the `InitialMappingsResponse`
   TypeScript interface. Searching the whole of `src/` for `.schemaLocation` — the only way
   the value could be consumed — returns **the declaration and nothing else**. No component,
   service or template reads it.
2. **It is on a different payload from the one this feature changes.**
   `InitialMappingsResponse` describes `initial_mappings`, which `cuems-editor` sends from
   `CuemsWsServer.mappings_dict` — the decoded `project_mappings.xml`
   (`CuemsWsServer.py:511`). FR-011 concerns the **script** wire dict returned by
   `CuemsScript.to_wire()`, which reaches the UI as `project_load` and `initial_template`
   (`CuemsWsServer.py:503`). The mappings payload is untouched by US2.
3. **TypeScript's structural typing makes an absent field a compile error only where it is
   constructed.** `projects.service.ts:252` builds an `InitialMappingsResponse` literal; that
   site would fail to compile if the field vanished from the payload *and* the interface. It
   does not, because neither changes here.

## Disposition

FR-011 and D2a stand. The change is **not** blocked, and the assumption is not being quietly
amended: the one positive hit is on a payload outside the change's scope and is never read.

Two things follow, and they are recorded rather than assumed:

- **If the config projection is ever transmitted to the UI** (Contracts §W8's planned
  follow-on, deliberately *not* done in this feature), the `initial_mappings` payload would
  start coming from `encode_wire`, which emits no `schemaLocation`. That interface field would
  then describe a key that is not there. It is unread, so nothing breaks — but the follow-on
  feature owns deleting the declaration, and this paragraph is the note that it exists.
- The search is reproducible: the commands are the three patterns above, run from
  `/disk/Projects/StageLab` against the commits in the table.
