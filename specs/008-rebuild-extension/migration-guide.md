# Migration guide — feature 008

Consumer-impact entries, at call-site granularity, per FR-054. This is 009's
hand-off document — built up through the feature rather than written at the
end, per the tasks that reference it.

---

## ITEM A — timecode typing and the fade-profile deletion

### FR-007b/FR-007c — the fade-profile surface is deleted, not renamed (T022)

**Measurement (FR-007b), so a future reader can re-run it rather than trust
it.** Checked 2026-08-28 against the three sibling repositories on disk
(`cuems-engine`, `cuems-editor`, `cuems-nodeconf`) with:

```bash
grep -rn "fade_profile\|FadeProfile\|function_id" \
  /disk/Projects/StageLab/cuems-engine/src \
  /disk/Projects/StageLab/cuems-editor/src \
  /disk/Projects/StageLab/cuems-nodeconf
```

Zero references in any of the three. The surface was live *inside*
`cuemsutils` (five registered T2 rules, two model classes, a registry
binding) and dead everywhere else — never consumed externally, never
implemented end to end.

**Delete-rather-than-rename reasoning (FR-007c).** A `FadeProfile` carries
neither `duration` nor `target_value`, so it cannot expand into the `FadeCue`
its eventual replacement concept needs, and its `mode`/`function_id` fields
duplicate `FadeCurveType`. Renaming it (`FadeProfile` → `Envelope`, the
option considered in session (c) of `spec.md`'s Clarifications) would ship a
shape already known to be wrong under a better name, forcing a second
migration once real documents held data in it. Deletion lets the eventual
replacement arrive later as a genuinely new type — the schema-evolution
convention's non-breaking path (`specs/planning/schema-evolution-convention.md`).
Design inputs for that future work are preserved in
`specs/planning/envelope-feature.md`.

### FR-053b — cuems-engine's now-unreachable fade-action handlers

`_handle_fade_in`/`_handle_fade_out` in
`cuems-engine/src/cuemsengine/cues/ActionHandler.py:516-553` and their
`SUPPORTED_CUE_ACTIONS`/`_ACTION_HANDLERS` entries (lines 30-45, 775-787)
become dead code once no schema-valid document can carry `fade_in`/`fade_out`
(FR-029a, ITEM D). Both were already stub implementations — `fade_in` logs
"treated as play (fade envelope not yet implemented)" and dispatches exactly
`_handle_play`'s body; `fade_out` logs "treated as stop" and carries a
recorded zombie-process defect (bumps `_go_generation` without calling
`disarm()`, so player processes are not cleaned up) that disappears with the
handler. 009 (or a `cuems-engine`-side cleanup) should delete both handlers,
their two dispatch-table entries, and the two `SUPPORTED_CUE_ACTIONS` members.

### FR-002/FR-003 — `Media.duration`'s wire shape changes

Every consumer that reads or writes a media cue's duration as a bare string
must move to the wrapped form:

- **`cuems-engine`**: `CTimecode(cue.media.duration)` call sites now receive
  a `CTimecode` object directly (the getter contract changed from `str` to
  `CTimecode`, FR-004) — `CTimecode(a_ctimecode)` already round-trips
  (`CTimecode.__init__` accepts a `CTimecode`), so these call sites keep
  working but the wrapping is now redundant and can be simplified when
  touched.
- **`cuems-editor`**: any raw-dict fixup or parser call site that reads
  `media["duration"]` as a plain string now receives
  `{"CTimecode": "HH:MM:SS.mmm"}` on both the XML and JSON wire forms — there
  was never a version of this change that left the wire alone (research
  "Resolved without research", E4).
- **`repair_durations.py`** (wherever it lives in the consuming repo): any
  pass that rewrites `<duration>` text in place needs to target the new
  `<duration><CTimecode>...</CTimecode></duration>` shape.

### FR-041/FR-041a (forward reference) — documents on disk carrying the old shape

D3's second recorded exception: this promotion invalidates every real
`script.xml` still on disk with a bare `<duration>` element, including the
two frozen `tests/data/corpus/legacy/` snapshots in this repository (see
`tests/contract/test_legacy_compatibility.py`,
`tests/contract/test_accept_reject_parity.py`). The exception is granted
**only** because ITEM E's conversion registry (`script` 1→2, FR-051) exists
to carry such documents forward again — see `tests/data/corpus/pre-008/` for
the retained originals that conversion is built and tested against. **Until
Phase 2 lands**, any production `script.xml` written before this feature will
fail to load; 009 must sequence the `.deb` rollout so ITEM E's conversion (or
the standalone `cuems-convert-documents` tool) reaches nodes no later than
this schema change does.

### Frontend template call sites (FR-036) — carried forward to ITEM D

Enumerated in ITEM D's section below (T081) rather than here, since they
concern `create_script`'s retirement, not the duration promotion.

---

## ITEM C — the network-map object moves in from `cuems-nodeconf`

**This ships with no first-party caller.** `NodeIndex.merge`/`adopt`/`unadopt`/
`set_controller_always_adopted`/`missing_adopted`/`signature` and
`CuemsNetworkMapType.refresh` (`data-model.md` §5) exist in this repository now,
characterized against `CuemsNodeConf`'s current behaviour, but nothing calls
them yet. 009 is where `cuems-nodeconf` actually adopts this object and
deletes its own copies.

### T050 — prescribed fix, `cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:579-583`

```python
def cleanup(self):
    try:
        os.remove(os.path.join(CUEMS_CONF_PATH, self.cm.show_lock_file))
    except FileNotFoundError:
        pass
```

`self.cm` is never assigned anywhere in the class — every call to `cleanup()` raises
`AttributeError` before the `try` block's own exception handling ever gets a chance
(the `except FileNotFoundError` does not catch `AttributeError`). Not fixed here (D16:
this feature does not edit consumer repositories). **Prescribed fix**: assign
`self.cm = ConfigManager(...)` in `__init__` (matching how every other daemon reads
`show_lock_file`) — or, more directly, since `CuemsNodeConf` already carries
`self.map_path` = `os.path.join(CUEMS_CONF_PATH, MAP_FILE)`, read
`show_lock_file` off a `ConfigManager` instance constructed the same way. 009 should
land this alongside the `NodeIndex` adoption, since both touch `CuemsNodeConf.__init__`.

### T052 — call-site entries for the adopt/unadopt dispatch chain

Per `data-model.md` §5's table:

- `cuemsnodeconf/CuemsNodeConf.py:113-144` (`engine_callback`) — `self.adopt_node(node_uuid)`
  and `self.unadopt_node(node_uuid)` (each returning a `{'OK': ..., 'error'?: ...}` dict) are
  replaced by `self.network_map.adopt(node_uuid)` / `.unadopt(node_uuid)` (each returning
  `bool`). The RPC response shape (`{'OK': bool, 'error'?: str}`) is `engine_callback`'s own
  concern, not `NodeIndex`'s — 009's port needs to reconstruct the error message
  (`"Node {uuid} not found"` / `"node is offline"` / `"Cannot unadopt master node"`) from the
  `False` return and which check failed, since the ported methods no longer carry that string.
- `cuemsnodeconf/CuemsNodeConf.py:440` (`merge_discovered_nodes`), `:490`
  (`set_master_always_adopted`), `:501` (`check_missing_adopted_nodes`) — replaced by
  `CuemsNetworkMapType.refresh(discovered, path)`, called from `refresh_network_map`
  (`:229-246`) in place of its current four-step body. `check_missing_adopted_nodes`'s
  logging call is not part of `refresh`'s orchestration (§5) — 009 must call
  `self.network_map.missing_adopted(discovered)` itself if the warning log is to survive
  the port.
- `cuems-frontend/src/app/components/settings/settings.component.ts:119-139`
  (`confirmRemoveNode`/`confirmAddNode`) — unaffected. The chain's *shape*
  (`nodelist_modify` → `{OK: bool}` response) does not change; only what runs on the
  daemon side of it does.

---

## ITEM D — `create_script` retirement and the schema descriptor

*(Recorded incrementally as ITEM D lands — not yet reached in the
implementation sequence as of this entry.)*

---

## ITEM E — strict reading, versioning, repair

*(FR-053a's precondition — surfacing the repair report before saving a
repaired document — will be recorded here once ITEM E lands.)*
