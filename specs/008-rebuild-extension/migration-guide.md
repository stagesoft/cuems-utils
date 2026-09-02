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

### FR-053a — surfacing the repair report is a precondition of saving a repaired document

`CuemsScript.load_with_report(path)` returns `(script, report)`; `report.outcome` is
`REPAIRED` when a field was substituted to its descriptor default. **Saving that `script`
overwrites the original on disk with no backup** (FR-041c, `config.base.save_document`'s and
`CuemsScript.save`'s existing atomic-overwrite behaviour — nothing new was built for this,
because the ordinary save path already does the right thing). That overwrite **destroys the
corrupt original**, and the only thing that makes destroying it safe is that a human saw
`report.repairs` first and agreed the substitution is acceptable.

**009's obligation, stated precisely so it is not lost in translation**: wherever the UI (or
any other 009 caller) calls `load_with_report` and then later calls `.save()` on the result,
the repair report **must** have been surfaced to the operator, and the save must not proceed
on a `REPAIRED` (or `CONVERTED`) outcome without that surfacing having happened. This library
cannot enforce the ordering — `load_with_report` and `.save()` are two independent calls, and
nothing stops a caller from doing the second without ever inspecting the first's report — so
the obligation is procedural, recorded here, not a runtime check anywhere in `cuemsutils`.

### FR-037/FR-038 — every consumer of `CuemsScript.load`/config accessors gains new failure modes

`CuemsScript.load(path)` keeps its signature but can now raise `ValidationError` in two new
cases it previously could not:

- an **unrepairable** T2 violation on a current-version document (FR-044) — previously this
  loaded silently and only failed at `save()`;
- a document whose `doc_version` marker is **newer** than this library's (FR-052) —
  previously not a concept that existed at all.

Every call site across `cuems-engine`/`cuems-editor` that calls `CuemsScript.load` and only
catches `SchemaError` (a T1-only expectation, reasonable before this feature) should widen its
catch to `ValidationError` (`SchemaError`'s own base) if it wants to handle **both** failure
kinds the same way, or add a second `except ValidationError` branch if it wants to
distinguish them (`isinstance(exc, SchemaError)` still tells T1 from T2/version at the catch
site). **009's migration task**: audit `cuems-engine`'s show-loading call site(s) — the engine
loads a project's `script.xml` at startup/project-open — for this widened failure surface, and
decide whether an unrepairable violation there should be a startup-abort (current behaviour,
appropriate) or something the operator is prompted about via 009's own UI work.

The same reversal applies to every `ConfigManager`/`ConfigBase` accessor
(`load_network_map`, `load_base_settings`, `load_net_and_node_mappings`,
`load_project_mappings`, `load_project_settings`) — each now runs T2 as well as T1. Measured
consequence: only `project_mappings` carries a registered T2 rule today
(`one_custom_template_per_node`, FR-039), and it is `repairable=False`, so the only new
observable behaviour is that a config document already carrying two custom templates on one
node — which would previously have loaded and been rejected later, at the point something
actually used the offending mapping — now raises `ValidationError` (not `SchemaError`) at
`ConfigManager` construction time. No corpus document exercises this today, so no consumer is
known to be affected; recorded as the honest, narrow scope FR-039 asks for rather than
inflated into a broader warning.

### FR-041/FR-041a — an old `script.xml` on disk now converts in memory rather than failing

This closes the obligation ITEM A's section above opened ("Until Phase 2 lands, any
production `script.xml` written before this feature will fail to load"). As of ITEM E, it no
longer fails: `CuemsScript.load` detects a `doc_version` of 1 (or absent), applies the
registered `script` 1→2 conversion in memory, and returns a loaded, valid object — the file on
disk is **not** rewritten by the load path (FR-041a). **009 still has a sequencing decision**:
whether to run the standalone `cuems-convert-documents` tool as part of the `.deb` post-install
step (rewriting every on-disk document once, with a backup per FR-042) or to rely on
convert-on-every-load indefinitely. The former pays a one-time backup+rewrite cost per document
and then every subsequent load is the cheap, already-current path; the latter re-runs the
(cheap, but non-zero) conversion on every single load forever. Not decided here — a 009 choice,
now that both paths exist and are tested.

### FR-042/SC-019 — the standalone conversion tool, `cuems-convert-documents`

New entry point (`pyproject.toml`'s `[project.scripts]`), implemented in
`cuemsutils.xml.convert_documents`. Takes one or more file paths, converts each whose version
precedes its schema's current one, and writes a timestamped `.bak` copy before rewriting. 009's
packaging work should decide where in the `.deb`'s postinst this runs (candidate: immediately
after the package's own files are in place, before any CUEMS service that reads these
documents is (re)started) and over which directories (`/etc/cuems/*.xml`, every project's
`script.xml`/`mappings.xml`/`settings.xml` under the library path).

### T125a — D3's second through sixth exceptions, one table (FR-012)

Recorded together, with the conditionality that makes three of them safe stated *with* them
rather than filed separately — each of the three that invalidates documents on disk was
granted **only** because ITEM E's conversion (this section) exists to carry it.

| # | Exception | File | Requirement | Item / Phase | Invalidates documents on disk? |
|---|---|---|---|---|---|
| 2nd | `CTimecodeType`/`TimecodeType` deleted (unreachable pair) | `settings.xsd` | FR-007 | A / Phase 1 | No — unreachable from any element |
| 3rd | `Media.duration` promoted to `cms:CTimecodeType` | `script.xsd` | FR-002/FR-003 | A / Phase 1 | **Yes** — carried by `script` 1→2's duration reshape (FR-051) |
| 4th | `doc_version` optional attribute added to all six root types | all six `.xsd` | FR-048a | E / Phase 2 | No — purely additive, `use="optional"` |
| 5th | `ActionType` enumeration drops `fade_in`/`fade_out` | `script.xsd` | FR-029a | D / Phase 1 | **Yes** — carried by `script` 1→2's action-type remap (FR-051a) |
| 6th | Fade-profile surface deleted (3 types, 1 element on 2 cue types) | `script.xsd` | FR-007a | A / Phase 1 | **Yes** — carried by `script` 1→2's fade-profile drop (FR-051c) |

**What this precedent does not license**, stated because a future feature will be tempted to
cite it: not X1–X13 (the schema-evolution convention's own deferred backlog); not a schema edit
in a feature that has no conversion path to carry the invalidation; not anything past this
feature's own boundary. A seventh exception needs its own decision record — this table is not
a blanket pre-approval.

### T126a — the two new user-facing surfaces, checked against existing convention (FR-UX-001)

**The repair report** (`RepairRecord`/`ConversionRecord`, `cuemsutils.errors`). Field names follow
`Violation`'s own pattern in `xml/validators.py` (`tier`/`rule`/`location`/`message`): a `*_name`
suffix for a rule identifier (`rule_name`, matching `Violation.rule`'s role), `field_path` built the
same "cue_id/field, or bare field" join `Violation.__str__`'s `where` computation already uses —
literally the same expression, not a look-alike. No second vocabulary for "what rule caused this" or
"where in the document" was invented.

**The conversion tool's output** (`cuems-convert-documents`). Follows `capture_goldens.py`'s existing
CLI convention in this repository (the only other hand-rolled CLI tool here): one line per item to
`stdout` for a success/neutral outcome (`"{path}: converted"` / `"{path}: already current"`), one line
per item to `stderr` for a problem (`"{path}: skipped (...)"`), and a non-zero exit code when anything
was skipped — the same shape `capture_goldens.main`'s `new`/`unchanged`/`REPLACED`/`CONFLICT` reporting
and exit-code convention uses. No new severity vocabulary, no structured-output format invented for a
tool this feature does not otherwise require one from.

Checked 2026-09-02; no second vocabulary found necessary or introduced.

### FR-051a — `fade_in`/`fade_out` conversion and cuems-engine's stub handlers

Restated at its point of actual effect: once a document on disk is converted (ITEM E, this
section), any `fade_in`/`fade_out` action cue it held is now `play`/`stop` **in the object
model** the moment it loads. `cuems-engine`'s `_handle_fade_in`/`_handle_fade_out`
(`ActionHandler.py:516-553`, named in ITEM A's section above) become unreachable **the moment
009 also deletes their dispatch-table entries** — until then they remain reachable only by an
`action_type` value no schema-valid document can carry once converted, i.e. effectively dead
but not yet removed. 009 should delete them in the same change that adopts this feature.

