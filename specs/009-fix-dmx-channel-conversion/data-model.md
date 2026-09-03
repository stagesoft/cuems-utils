# Phase 1 Data Model: DMX channel conversion error

This feature adds no new persisted or wire entity — no `.xsd` change (confirmed in spec.md), no
new field on `DmxChannel` or `DmxUniverse`. The only new "entity" is an in-memory exception type.
Documented here per the plan template's requirement, for completeness rather than because the
domain model actually grew.

## `DmxChannelDecodeError` (new, `src/cuemsutils/errors.py`)

An exception, not a data record — but its shape is a contract other code depends on (FR-002,
FR-006), so it is specified precisely.

| Attribute | Type | Notes |
|---|---|---|
| `universe` | `DmxUniverse` | The object `set_dmx_channels` was populating when the failure occurred. May be a partially-constructed instance (`universe_num` may or may not be set yet, depending on construction order — see Invariants). |
| `index` | `int` | Zero-based position of the failing entry within the input list passed to `set_dmx_channels` (after the non-list → `[x]` wrapping already performed today). |
| `entry` | `object` | The raw, unconverted failing entry itself. Stored for programmatic inspection (a caller catching the error can look at what it was), but **never rendered into the message** — only `type(entry).__name__` appears there (Decision 2, research.md). |
| message (via `str(exc)`) | `str` | `"DMX channel entry at index {index} in universe {universe_num!r} could not be converted to a DmxChannel (entry: {type(entry).__name__})."` — `universe_num` read defensively (see Invariants); falls back to a placeholder if unavailable. |
| `__cause__` | `KeyError \| TypeError` | The original per-entry conversion failure, preserved via `raise ... from exc` — never discarded (mirrors `DmxSceneWriteError`'s precedent, `test_the_original_failure_is_preserved_as_the_cause`). |

### Invariants

- **Never constructed with a successfully-converted entry.** `DmxChannelDecodeError` is raised
  exactly once per failing `set_dmx_channels` call, at the first entry that raises `KeyError` or
  `TypeError` during conversion (Decision 3: first-failure, not collect-all).
- **Reading `universe_num` off `universe` must not itself raise.** `DmxUniverse.__init__` calls
  `self.setter(init_dict)` before `_fill_declared_defaults()`
  (`src/cuemsutils/cues/DmxCue.py:342-345`), so at the moment `set_dmx_channels` runs,
  `universe_num` may already be set (if `universe_num` was ordered before `dmx_channels` in the
  input dict) or may not yet exist as a key at all. The error's message-building code MUST guard
  this the same way `DmxSceneWriteError.__init__` guards reading `scene.get("id")`
  (`mapper.py:927-932`, a `try`/`except Exception` around the defensive read only — not around the
  error's own construction) — falling back to a placeholder (e.g. `"<universe_num unknown>"`)
  rather than letting a broken universe fail to even name itself.
- **`dmx_channels` is left unset (or at its prior value) on the `universe` object when this error
  raises** — FR-003: no mix of converted and raw entries is ever stored. Concretely: `channel_list`
  accumulates every resolved entry (already-`DmxChannel` instances appended as-is, raw dicts
  converted and appended) in a single unified pass and is only assigned to `dmx_channels` once,
  after the loop completes without failure — never assigned partially, and the raw fallback
  assignment (`super().__setitem__('dmx_channels', channels)` in today's `except` branch), along
  with today's separate per-iteration reassignment in the already-`DmxChannel` branch, are both
  deleted — there is exactly one assignment point in the new code, not a fallback preserved for
  some cases (see research.md Decision 3, revised).
- **A raw dict never reaches `dmx_channels`, even transiently, even in a batch mixing
  already-`DmxChannel` instances with still-raw-but-valid entries** (FR-004a). The two-branch
  original design reassigned `dmx_channels` independently per branch per iteration, so a mixed
  batch's outcome depended on which branch's iteration ran last — silently dropping the other
  kind of entry. The unified loop removes this: one entry, one resolution (append as-is or
  convert-then-append), one shared accumulator, one assignment.

## Existing entities, unchanged

- **`DmxChannel`** (`src/cuemsutils/cues/DmxCue.py:428`) — `channel: int`, `value: int`. No field,
  constructor signature, or behavior change. Still constructed the same way
  (`DmxChannel(r['DmxChannel'])`) on the success path.
- **`DmxUniverse`** (`src/cuemsutils/cues/DmxCue.py`) — `universe_num: int`,
  `dmx_channels: list[DmxChannel] | None`. Only `set_dmx_channels`'s failure-path body changes;
  `get_dmx_channels`, `get_universe_num`/`set_universe_num`, and the success path of
  `set_dmx_channels` are unchanged (FR-004, FR-008).

## State transitions

None — this is a stateless conversion routine (input list → stored list, or exception). No
multi-step lifecycle is introduced.
