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

### T069 — every `create_script` consumer, before anything is deleted

18 entries, checked by `grep -rl "create_script\b" src/ tests/ templates/` on
2026-09-02. **Fifteen are live references** — deleting the function without
moving them first turns the suite red in fifteen files. **Three are prose**
(a docstring, a comment, a provenance note) — they redden nothing, but
T079's check is counted rather than reviewed, so they fail it just the same.

**Six direct callers** (import and call `create_script()` themselves):

- `tests/test_cuelist.py`
- `tests/test_xml.py`
- `tests/test_fade_cue.py`
- `tests/integration/test_mediacue_fade_roundtrip.py`
- `tests/integration/test_create_script_completeness.py`
- `tests/unit/test_id_clearing.py`

**Four golden assertions** (compare a produced document against
`generated/create_script.xml`/`.reader.json`):

- `tests/integration/test_d14_chain.py:109`
- `tests/contract/test_byte_identity_xml.py:53,60`
- `tests/contract/test_byte_identity_dict.py:64`
- `tests/contract/test_dmx_failure_path.py:135`

**Two support modules** (the shared harness every one of the above actually
routes through):

- `tests/support/capture_goldens.py` — `build_generated_script()`,
  `_make_template_writable()`, `_capture_generated()`
- `tests/support/invalid_scripts.py` — `build_generated_script()`'s base

**Two manifest/inventory entries**:

- `tests/contract/test_corpus_coverage.py:116` — the slug set
- `tests/golden/MANIFEST.sha256:29-30` and `tests/golden/outcomes.json` —
  the `generated/create_script` entries

**Three prose-only references** (no executable dependency, but counted by
T079's check):

- `tests/integration/test_construction_parity.py:9` — module docstring
- `tests/unit/test_script_equality.py:38` — comment
- `tests/data/corpus/PROVENANCE.md:38` — provenance note

### What replaced it (T070)

`cuemsutils.xml.descriptor.generate_script_example()` — one `CuemsScript`
carrying one instance of every concrete cue type. Structural completeness
(*which* cue types appear) is read off the registry's
`CueListContentsType` binding rather than hand-listed, so a schema addition
is caught by `descriptor._assert_every_choice_member_has_a_builder` at
generation time instead of silently missing. Each cue's *content* (a media
file, an output's geometry, a DMX channel) is not schema-derivable and stays
a small, explicit, hand-authored builder per type — see
`descriptor._script_cue_builders`.

**Output is not byte-identical to `create_script()`'s** (FR-033, sanctioned):
fresh uuid4s throughout, `name`/`description` differ, and — the one
deliberate behavioural difference — **there is no id-blanking step**.
`create_script()` validated a fully-populated script and then cleared the
script id, cue-list id and every direct cue's id on the way out, which is
exactly the ordering defect FR-033 names (the returned, blanked object is
not the one that was validated). The new generator has nothing to undo that
defect *for* — `capture_goldens._make_template_writable`, which existed only
to restamp what `create_script` blanked, is deleted with it (T072). A
"blank template for the UI to fill in" is a 009/frontend-integration
concern now, not something this repository's example-document builder
re-implements.

`generate_settings_example()` (T078) replaces `templates/settings.xml`
the same way: field *names* are read off `settings.xsd` via
`spec.derive()`, so an added or removed field is caught at generation time;
field *values* come from a small explicit table
(`descriptor._SETTINGS_EXAMPLE_VALUES`) transcribed from the retired
template's illustrative content.

### T081 — frontend template call sites (FR-036), enumerated rather than estimated

Checked 2026-09-02 against `/disk/Projects/StageLab/cuems-frontend` on disk. Three files
consume `ProjectsService.projectTemplate()` (the Angular service that used to be populated
from this repository's `initial_template` payload, `create_script()`'s output); only two
call sites read **concrete values** out of it rather than just checking presence/shape:

- **`src/app/components/projects/project-edit/sequence/sequence.component.ts:688`** —
  `newCue.master_vol = template?.['CuemsScript']?.['CueList']?.['contents']?.find((item:
  any) => item.AudioCue)?.AudioCue?.master_vol || 20`. The fallback (`20`) already diverges
  from the schema's own default (`100`, `AudioCueType.master_vol` — SC-012's descriptor
  answer), which is worth 009 noticing independently of this migration: reading
  `SchemaDescriptor().describe(TypeKey("script","AudioCueType"))`'s `master_vol` field
  default replaces both the template walk *and* silently fixes the fallback's drift from the
  schema.
- **`src/app/components/projects/project-edit/sequence/sequence.component.ts:726-727`** —
  walks `template['CuemsScript']['CueList']['contents']`, finds the entry carrying `DmxCue`,
  and reads `DmxCue.DmxScene.DmxUniverse.dmx_channels` (unwrapping each `{DmxChannel:
  {...}}` entry) to seed the new cue's initial channel list. The descriptor's answer for
  `DmxUniverseType.dmx_channels`'s default is `None` (T057) — an empty starting list, not a
  channel to copy — so 009's port is a **behaviour choice**, not a mechanical substitution:
  either keep this component's own hard-coded `[{channel: 1, value: 0}]` fallback as the
  sole source, or decide a real seed value belongs in `descriptor._SETTINGS_EXAMPLE_VALUES`-
  style table for the show schema too. Recorded here rather than resolved, since the
  decision is 009's to make against the live UI, not this feature's.
- **`src/app/services/projects/handlers/project-create.handler.ts`** and
  **`src/app/components/projects/project-edit/project-edit.component.ts:141`** — both consume
  `projectTemplate()` (clone/existence checks) but read no concrete field values from it;
  no descriptor migration is needed at these two call sites beyond whatever 009 does to the
  service's own population source.

**`cuems-engine`'s now-unreachable fade-action handlers** (FR-053b, restated here at
call-site granularity per T081's instruction): `_handle_fade_in` (`ActionHandler.py:516`)
and `_handle_fade_out` (`ActionHandler.py:542`), their `_ACTION_HANDLERS` entries
(`ActionHandler.py:784-785`) and their `SUPPORTED_CUE_ACTIONS` members (`:30`) become dead
code once `fade_in`/`fade_out` (FR-029a, T066) can no longer appear in a schema-valid
document. `_handle_fade_out`'s recorded zombie-process defect (bumps `_go_generation`
without calling `disarm()`) disappears with the handler rather than needing its own fix.

---

## ITEM E — strict reading, versioning, repair

*(FR-053a's precondition — surfacing the repair report before saving a
repaired document — will be recorded here once ITEM E lands.)*
