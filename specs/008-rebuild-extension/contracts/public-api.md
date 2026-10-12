# Contract — public surface added by feature 008

`cuemsutils` is a library, so its contract is its importable surface. D15 fixes the public objects as
`CuemsScript` (show) and `ConfigManager`/`ConfigBase` (config); Q14 keeps `xml/` internal
(`cuemsutils.xml.__all__ == []`); 006 established `cuemsutils.errors` as the one exception, because a
caller must be able to name what it catches.

Everything below is **additive**. No public symbol is removed, and the two removals this feature makes
(`create_script`, the fade-profile classes) were never public.

---

## 1. `cuemsutils.errors` — new public types

```python
from cuemsutils.errors import LoadReport, Outcome, RepairRecord, ConversionRecord
```

| Symbol | Contract |
|---|---|
| `LoadReport` | What a load did beyond returning an object. Answers: which document, which fields were repaired, what replaced what, which conversions ran, whether the on-disk file is now stale |
| `Outcome` | `CLEAN` \| `CONVERTED` \| `REPAIRED` |
| `RepairRecord` | `field_path`, `previous_value`, `substituted_value`, `rule_name` |
| `ConversionRecord` | `from_version`, `to_version`, `description`, `dropped_elements` |

**Guarantees.**

- A clean load produces a report with `outcome == CLEAN` and empty tuples — **never `None`**. A caller
  never branches on presence before reading.
- Every repair and every dropped element appears. Silent repair and silent data loss are both
  impossible by contract (SC-016e, SC-020a).
- These are **data**, not exceptions. Only the unrepairable outcome raises, and it raises
  `ValidationError` — an existing public type, so no caller learns a new one to catch.

**Non-guarantee, stated because it constrains 009.** The library never delivers a report anywhere. It
returns it. `cuemsutils` has no UI channel and does not acquire one (FR-047).

---

## 2. `CuemsScript` — load becomes strict, and reports

```python
CuemsScript.load(path) -> CuemsScript                  # unchanged signature
CuemsScript.load_with_report(path) -> tuple[CuemsScript, LoadReport]
```

**Behaviour change, and it is a deliberate reversal** (FR-037, FR-038). `load` runs full validation —
T1 **and** T2 — where it previously ran T1 only on the principle that reading never becomes stricter.
**Five document states, three of which are FR-040's load-failure outcomes** (converted, repaired,
raised); the other two are the clean load and the newer-than-library refusal:

| State | Result |
|---|---|
| Valid | Loads. `CLEAN` |
| Version precedes current | Converts in memory, loads. `CONVERTED`. **File on disk untouched** |
| Current, invalid, field repairable | Repairs to the descriptor default, loads. `REPAIRED` |
| Current, invalid, field unrepairable | Raises `ValidationError` |
| Version newer than the library | Raises `ValidationError`, distinguishable (FR-052) |

`load` keeps its signature so existing callers compile; they simply lose access to the report.
`load_with_report` is how a caller that intends to surface repairs gets them. **A caller that saves a
repaired document without having read the report destroys the corrupt original unreviewed** — the
library cannot prevent this, which is why it is a migration-guide obligation (FR-053a).

---

## 3. `ConfigManager` — write paths for the three remaining domains

```python
save_settings(path=None) -> None
save_project_settings(project_uname, path=None) -> None
save_project_mappings(project_uname, path=None) -> None
```

Symmetric with the landed `save_network_map`. Validate T1, then write atomically via temp file plus
`os.replace`. Raise `SchemaError` on structural violation, writing nothing. **No backup** — that
belongs to schema upgrades alone (FR-016).

Every accessor on `ConfigManager`/`ConfigBase` also becomes strict per §2's table.

---

## 4. `cuemsutils.tools.NodeList` — the network-map object

```python
NodeIndex.merge(discovered) -> None
NodeIndex.adopt(node_uuid) -> bool
NodeIndex.unadopt(node_uuid) -> bool
NodeIndex.set_controller_always_adopted() -> None
NodeIndex.missing_adopted(discovered) -> tuple[...]
NodeIndex.signature() -> str
CuemsNetworkMapType.refresh(discovered) -> bool
```

**Contract with its future caller.** This ships with no first-party caller — `cuems-nodeconf` adopts it
in 009 — so the contract is pinned by characterization tests taken from that repository's **current**
behaviour before any port (FR-021, E23). The chain it must remain valid for is
`settings.component.ts` → `nodelist_modify` → `engine_callback` → adopt/unadopt (FR-022). That chain
works today and must still work after 009 migrates it.

`unadopt` refuses the controller node, returning `False` — preserved because it is current behaviour,
not because it is re-derived.

---

## 5. Conversion tool

A standalone entry point, for batch, offline and post-install use with no application running.

```
cuems-convert-documents <path>...
```

- Converts every document whose version precedes current; leaves current ones untouched.
- **Writes a timestamped backup before rewriting**, and treats a backup failure as fatal **for that
  document only** — skipping it, reporting it, and continuing (FR-042).
- Idempotent: a second run over the same files changes no bytes.
- **The only implementation.** The load path and this tool share one conversion registry; the rewriter
  is not built twice (SC-019). 009 folds `repair_durations.py`'s Pass B into this rather than
  maintaining a second XML rewriter.

---

## 6. What does not change

- **The `project_load` payload stays byte-identical — modulo FR-003's deliberate duration reshape**,
  which is the payload's *only* sanctioned change in this feature (`"duration": "TC"` becomes
  `"duration": {"CTimecode": "TC"}`, and it is a migration-guide entry). Part 2d constrains that nothing
  **else** moves the payload; in particular the version marker is excluded from every wire projection
  precisely so it never reaches it (research R1). Booleans stay strings; the UI's
  `=== true || === 'True'` reading is unaffected. *Stated with the exception because an unqualified
  "stays byte-identical" here would assert the opposite of FR-003.*
- **`cuemsutils.xml.__all__` stays `[]`** (Q14).
- **`cuemsutils.config` exports nothing** — the descriptor is internal machinery; 009 consumes it
  through the public façade, not by importing `config/`.
- **No public symbol is removed.** `create_script` and the fade-profile classes were internal.
