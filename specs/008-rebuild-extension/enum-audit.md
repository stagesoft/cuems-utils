# Enumeration audit — feature 008 (T004a)

Every restricted enumeration (`xs:enumeration` facets on an `xs:simpleType`) across all six bundled
schemas, with a per-value verdict and the consumer-repository evidence behind it. Consumer repositories
checked: `cuems-engine`, `cuems-editor`, `cuems-nodeconf`, `cuems-common` (siblings on disk at
`/disk/Projects/StageLab/`). Date: 2026-08-28.

**Verdict is `RETAIN` or `REMOVE`.** `REMOVE` means this feature's schema edit deletes the value;
`RETAIN` means the value stays declared in the schema this feature ships, whether or not a consumer
currently dispatches it — evidence of no consumer honouring a value is not, by itself, licence to delete
it. Only the values the spec's clarification sessions named as in scope (`fade_in`/`fade_out`,
FR-029a) are `REMOVE`. T059 asserts the descriptor's published facets equal the `RETAIN` set, per
schema.

---

## `script.xsd`

### `ActionType` (`script.xsd:235-251`)

| Value | Verdict | Evidence |
|---|---|---|
| `play` | RETAIN | `ActionHandler._ACTION_HANDLERS["play"]` — dispatched |
| `pause` | RETAIN | `_ACTION_HANDLERS["pause"]` — dispatched |
| `stop` | RETAIN | `_ACTION_HANDLERS["stop"]` — dispatched |
| `load` | RETAIN | No entry in `SUPPORTED_CUE_ACTIONS`/`_ACTION_HANDLERS` (`cuems-engine/src/cuemsengine/cues/ActionHandler.py:30-45,775-787`) — an `ActionCue` carrying this value fails the dispatch guard at line 244. Not honoured today, but not named by this feature's spec/clarifications as in scope for removal; recorded for a future feature rather than acted on here |
| `unload` | RETAIN | Same as `load` — no dispatch entry |
| `enable` | RETAIN | `_ACTION_HANDLERS["enable"]` — dispatched |
| `disable` | RETAIN | `_ACTION_HANDLERS["disable"]` — dispatched |
| `fade_in` | **REMOVE** | `_handle_fade_in` (`ActionHandler.py:516-536`): `Logger.info("fade_in treated as play (fade envelope not yet implemented)")` — a never-implemented stub, identical to `play`. Superseded by `fade_action` since feature 003 (spec.md clarification session (c)). Schema/rule contradiction found in the same session: `ActionType` offers this value to `FadeCueType` while the `fade_action_type` T2 rule forbids it there — a live contradiction, not a hypothetical one |
| `fade_out` | **REMOVE** | `_handle_fade_out` (`ActionHandler.py:542-553`): `Logger.info("fade_out treated as stop (fade envelope not yet implemented)")`, plus a recorded zombie-process defect (bumps `_go_generation` without calling `disarm()`) that disappears with the handler (FR-053b). Same supersession and contradiction as `fade_in` |
| `fade_action` | RETAIN | `_ACTION_HANDLERS["fade_action"]` — dispatched, extensively tested (`cuems-engine/tests/test_fade_action_handler.py`) |
| `wait` | RETAIN | No dispatch entry found. Not in scope for removal (see `load`) |
| `go_to` | RETAIN | `_ACTION_HANDLERS["go_to"]` — dispatched |
| `pause_project` | RETAIN | No dispatch entry found in `ActionHandler.py`; project-level pause is a different code path (`ControllerEngine`/`NodeEngine` status machinery, not `ActionCue` dispatch). Not in scope for removal |
| `resume_project` | RETAIN | Same as `pause_project` |

**Post-feature count: 12** (14 − `fade_in` − `fade_out`), matching T058/SC-012a.

### `FadeCurveType` (`script.xsd:254-259`)

| Value | Verdict | Evidence |
|---|---|---|
| `linear`, `exponential`, `logarithmic`, `sigmoid` | RETAIN | `ActionHandler._handle_fade_action` reads `fade_cue.curve_type` and forwards it opaquely as a string to `GradientClient.add_arg(curve_type, ...)` (`ActionHandler.py:727-744`, `GradientClient.py:45-59`) — the shape is interpreted by `gradient-motion-engine`, outside these four repositories' source, so per-value dispatch cannot be confirmed by grep; the pass-through itself is live for all four values |

### `PostGoType` (`script.xsd:512-517`)

| Value | Verdict | Evidence |
|---|---|---|
| `pause` | RETAIN | `CueHandler.py:746`: `cue.post_go in ("pause", "go_at_end")` |
| `go` | RETAIN | `CueHandler.py:371,695,703,821` — the auto-follow chain walk |
| `go_at_end` | RETAIN | `CueHandler.py:211,718,793,807,818,746` |

### `FadeTypeType` (`script.xsd:102-107`) and `FadeModeType` (`script.xsd:109-114`)

| Value | Verdict | Evidence |
|---|---|---|
| `in`, `out` (`FadeTypeType`) | **REMOVE** | Referenced only by `FadeProfileType.type` (`script.xsd:137`), which is deleted whole by FR-007a (T018). Deleting `FadeProfileType` without deleting `FadeTypeType` would leave an orphaned simple type nothing references — deleted alongside it for schema hygiene, though T018's task text names only the three complex types |
| `preset`, `parametric` (`FadeModeType`) | **REMOVE** | Same reasoning — referenced only by `FadeProfileType.mode` (`script.xsd:138`) |

`FadeFunctionIdType` (`script.xsd:116-120`) carries no `xs:enumeration` (an `xs:minLength` pattern only)
and is out of this audit's scope; it is deleted alongside `FadeProfileType` for the same orphaning
reason.

### `BoolType` (`script.xsd:450-455`)

| Value | Verdict | Evidence |
|---|---|---|
| `True`, `False` | RETAIN | Pervasive — every boolean-typed show field |

---

## `settings.xsd`

### `BoolType` (`settings.xsd:119-124`)

| Value | Verdict | Evidence |
|---|---|---|
| `True`, `False` | RETAIN | Pervasive |

### `AutoOrIntLatencyMsType` (`settings.xsd:163-180`)

| Value | Verdict | Evidence |
|---|---|---|
| `auto` | RETAIN | `NodeEngine.py:33-35,511,626` — `isinstance(value, int)` distinguishes an explicit override from `"auto"` (audioplayer default) or absent (DMX has no auto form) |

---

## `network_map.xsd`

### `BoolType` (`network_map.xsd:43-48`)

| Value | Verdict | Evidence |
|---|---|---|
| `True`, `False` | RETAIN | `adopted`/`online`, decoded to Python `bool` via the adapter table (feature 007) |

### `NodeRoleType` (`network_map.xsd:52-57`)

| Value | Verdict | Evidence |
|---|---|---|
| `controller`, `node`, `firstrun` | RETAIN | `cuemsutils.tools.NodeList.NodeRole` — the typed Python enum feature 007 introduced; all three values round-tripped in that feature's coercion regression suite |

---

## `project_mappings.xsd`, `project_settings.xsd`, `outputs.xsd`

No `xs:enumeration` facets in any of the three (only `xs:pattern`/`xs:minLength`/`xs:maxInclusive`
restrictions — `UnitFloat`, `PositiveUnitFloat`, `NonEmptyString`, `NonPrivilegedPort`). Nothing to
audit.

---

## Summary

| Enumeration | Schema | Values | RETAIN | REMOVE |
|---|---|---|---|---|
| `ActionType` | script | 14 | 12 | 2 (`fade_in`, `fade_out`) |
| `FadeCurveType` | script | 4 | 4 | 0 |
| `PostGoType` | script | 3 | 3 | 0 |
| `FadeTypeType` | script | 2 | 0 | 2 (whole type deleted) |
| `FadeModeType` | script | 2 | 0 | 2 (whole type deleted) |
| `BoolType` | script | 2 | 2 | 0 |
| `BoolType` | settings | 2 | 2 | 0 |
| `AutoOrIntLatencyMsType` | settings | 1 | 1 | 0 |
| `BoolType` | network_map | 2 | 2 | 0 |
| `NodeRoleType` | network_map | 3 | 3 | 0 |

**Count of facet values with no verdict recorded**: 0 (T059's assertion).
