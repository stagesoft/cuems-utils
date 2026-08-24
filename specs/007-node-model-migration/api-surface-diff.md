# API surface diff — feature 007 (T046b, FR-007a, SC-014)

The third permitted golden modification this feature makes (the first two are the four
`network_map` dict goldens, recorded in `golden-changes.md`). `tests/golden/api/public_api.json`
pins the method signatures of `CuemsScript`, `ConfigManager` and `ConfigBase` — the three classes
`tests/contract/test_public_api_surface.py`'s `PUBLIC_CLASSES` snapshots.

## Enumerated diff

One entry added, nothing removed or changed:

```diff
   "ConfigManager": {
     ...
+    "save_network_map": "(self, path: str | None = None) -> None",
     "set_dir_hierarchy": "(self) -> None",
```

**Justification**: `ConfigManager.save_network_map()` is the façade contract C5 requires — the
first-party write path for `network_map` (research R6). It did not exist before this feature;
`network_map` had no writer in the ecosystem (plan.md's phasing table, step 6).

## Not captured by this golden, recorded here instead

`tests/golden/api/public_api.json`'s `PUBLIC_CLASSES` only tracks `CuemsScript`, `ConfigManager`
and `ConfigBase` — it has never snapshotted arbitrary new modules. `cuemsutils.tools.NodeList`
(`NodeRole`, `NodeIndex`, and the re-exported `node`) is this feature's other addition to the
public surface (contract C10) and has no golden mechanism to sit in; its import path is instead
the one `migration-guide.md` names for consumers (FR-027a). `cuemsutils.errors` gained two
message-building functions (`network_map_node_type_message`, `network_map_role_enum_message`) used
internally by `ConfigBase.load_config_document` — neither is in `PUBLIC_ERRORS`, and neither is
part of the four-exception-type public surface `errors.py`'s own docstring describes; they are
implementation detail of one accessor's error posture, not a second public entry point.

## What did not change

`CuemsScript`'s and `ConfigBase`'s snapshotted method sets are byte-identical to the pre-feature
golden — this feature edits `ConfigManager` only.
