# Changelog

## 0.1.1 — Unreleased

The coordinated `xml-refactor` release
(`specs/planning/coordinated-release-version-bump.md`). This section is being filled in as items
land; the date goes on when the release is cut.

### Coordinated release — every CUEMS repository moves to its next stable minor

`cuems-utils` **0.1.1** is cut directly (no `0.1.1~rc1`), together with `cuems-common 1.3.1-1`,
`cuems-engine 0.1.1-1`, `cuems-editor 0.1.1-1`, `cuems-nodeconf 0.1.1-1`, `cuems-power-bridge
0.4.0-1` and `cuems-frontend 0.2.0` (feature 016). Every consumer now bounds this library
`>= 0.1.1`, `<< 0.1.2~`. `0.1.0rc16`, the old floor, was released from another line without the
public object API, so it no longer names this surface. The deprecated surface that `0.1.0` and
`0.1.1` still ship now goes away in **`v0.1.2`**. The warnings say so, and the removal plan is
`specs/planning/deprecated-surface-removal-v0-1-2.md`. `Breaks: cuems-common (<< 1.3.1~)` replaces
`(<< 1.3.0-23~)`, which the released `1.3.0-23`…`-25` satisfied without carrying the `/etc/cuems`
handover.

### Not yet reconciled — do not publish until it is

The parallel release line (`debian/bookworm`, 77 commits ahead on 2026-10-15) has shipped two
builds whose content is **not** in this branch yet. They are absorbed before publication, and the
package relations are re-verified after the merge:

- **`0.1.0rc16+1`**: stops shipping `/usr/lib/cuems/CACHEDIR.TAG`, a file-overwrite conflict with
  `cuems-power-bridge` and `cuems-engine` at `dpkg -i` time.
- **`0.1.0rc17`**: `script.xsd`'s `ActionType` gains `stop_project`. A project saved by an rc17
  cluster with a `stop_project` cue is **refused** by `0.1.1` until this is absorbed.

### Fixed — migrating a library no longer destroys the backup of the original

`cuems-reshape-devices` and `cuems-convert-documents` both named their backup
`<name>.<YYYYMMDDTHHMMSS>.bak` and overwrote an existing file. Run in their required order inside
one second, which a small library does, the second backup replaced the first. The pre-upgrade
document was then on disk nowhere, and both tools still exited 0. A backup now never replaces another file:
a taken name gets a `.<n>` suffix (`<name>.<YYYYMMDDTHHMMSS>.1.bak`), and a document's **oldest**
backup is its pre-upgrade state. **If you migrated before this fix**, check each migrated document
for two backups. One backup alone may already be the reshaped one.

### Added — `cuems-convert-documents --check`

Reports each document's version and a summary (`N documents: X current, Y needs conversion`) and
writes nothing. Exit `0` when everything is current, `1` when anything needs conversion or was
skipped. It answers "has this library been converted?" for a rollback, so no document has to be
opened by hand. Since the device-class reshape, the complete answer also needs
`cuems-reshape-devices --check`.
A conversion run now ends with the same summary line, `N documents: X converted, Y current`, so
the check and the run it predicts read alike.

### Changed — a too-new configuration document says so in a field

A configuration document whose `doc_version` is newer than this library raised `ValidationError`
with no `violation`, so a consumer could tell it from a broken document only by the message. It now
carries `violation.rule == "document_version_too_new"`, as a show document already did. The fix
for it is to upgrade the software, not to edit the document.

### Fixed — another cluster's controller no longer joins this one's network map

Several CUEMS clusters can share one LAN, and every controller announces itself over mDNS. A
network-map refresh added every discovered node and marked every controller adopted, so a
controller's `network_map.xml` picked up the **other** clusters' controllers as adopted members,
and `cuems-engine` then counted them as part of its own cluster. This happened in the field on
2026-10-01 and 2026-10-06.

`cuems-nodeconf 0.1.0-8` fixed this inside its daemon. On this release line the map logic belongs
to this library, so the fix is re-implemented here. Under rule 4 of the coordinated release
(nothing already shipped is lost), it **must** be in `0.1.1`.

- **`CuemsNetworkMapType.refresh(discovered, path, *, cluster=None)`**: the new keyword-only
  `cluster` scopes a pass to one cluster. A discovered controller outside it is ignored, and one an
  earlier pass saved is **removed** from the map (deleted, not marked offline: an offline row means
  "ours, currently absent"). Without `cluster`, or with an empty one, behaviour is unchanged.
- **`NodeIndex.cluster_controllers(own_uuid, own_role)`** computes that set. On a controller it is
  the controller's own uuid; on any other node it is the controllers its map already records; on a
  fresh node it is empty, which means no scoping. Compute it **before** calling `refresh`.
- **`NodeIndex.foreign_controllers(cluster)`** lists what a scoped pass would remove, for logging.
  **`NodeIndex.drop_foreign_controllers(cluster)`** and the static
  **`NodeIndex.is_foreign_controller(n, cluster)`** are the underlying primitives.

**Who needs to change**: `cuems-nodeconf` only. It passes `cluster=` and can drop its interim
discovery filter. No other consumer calls `refresh`.

**Known limitation**: a fresh node whose first discovery pass hears two clusters' controllers
accepts both, because it has no recorded controller to scope by. The shipped daemon fix has the
same limitation. Fixing it needs a join protocol, which belongs to `cuems-nodeconf`'s planned
controller election.

### Changed — `get_schema_descriptor` is cached, and each call returns its own instances

Feature 015 made every descriptor `instance` wire-shaped and fully populated. That tripled the
cost of `ConfigManager.get_schema_descriptor`, because the whole descriptor was rebuilt on
every call: about 2.9 ms for `script`, against 1.05 ms before 015. The descriptor depends only on
the bundled schemas, so it is now built **once per process** and cached.

- **Each call still returns its own `instance` objects**, copied out of the cache, so filling one
  in never affects another caller. The `fields` are shared, as before; they are frozen.
- A repeated call for `script` now takes **0.165 ms instead of 2.85 ms** (17×), faster than before
  015. The other schemas improve by 7–17×. The first call in a process is unchanged, because
  schema compilation dominates it.
- **No change is required of any consumer.** One simplification becomes available to
  `cuems-editor`: its `json.loads(json.dumps(instance, default=_json_safe))` round trip in
  `_root_instance` and `schema_descriptor_value` is no longer needed to keep instances apart.
  It is still needed if `_json_safe` converts anything.

### Changed — new outputs start at sensible values, stated by the schema

A new audio output used to start at volume 0, and a new video output at scale 0, which is
invisible. Those were the descriptor's generic seeds ("the zero of the type"), so
`cuems-frontend` kept its own table of starting values to work around them.

- `script.xsd` now declares `default="…"` on four elements: `output_vol` 80, `channel_vol` 80,
  `x_scale` 1, `y_scale` 1. These are the first `default` attributes in any of the six schemas.
- `get_schema_descriptor`'s instances use an element's XSD default as its starting value, ahead
  of the generic seed.
- **Nothing about loading changes.** These elements are still required, and a document that
  omits them or leaves one empty is still refused. They are starting values, not defaults: the
  matching `FieldDescriptor.default` stays unset, and the fields are still not repaired on load.
- `cuems-frontend` can delete its `toWireShape` transform and `UR1_UI_STARTING_VALUES` table.
  A new output then looks exactly as before.

## Unreleased — `outputs` renamed to `hardware_outputs`, and X14 resolved

The sixth schema is renamed as the first step of making it the node's **hardware capability
descriptor** — what its name always implied — rather than the stub it has been since it was
imported from `cuems-engine`.

**Nothing on disk is invalidated.** No `CuemsOutputs` document has ever existed in production
(both audited machines carry `/etc/cuems/outputs.xsd` and no instance), nothing anywhere loads
one, and the only instances are four test fixtures. The file's *content* is unchanged by this
commit.

What moved, and why the key had to move with the file: `schema_path()` builds the filename
from the schema key, so `"outputs"` -> `"hardware_outputs"` in `SCHEMA_NAMES`, `SCHEMA_ROOTS`,
the version registry, the document-root map and the corpus manifest. `SchemaName.OUTPUTS`
keeps its **member** name and takes the new **value**; the member rename is deferred so it is
settled once rather than twice.

Still **reserved, not usable**. Two independent blockers remain, both re-measured:

- its `OutputsType` collides by name, in the same namespace, with `script.xsd:142`'s
  (audit X14) — a list of strings against a choice of `AudioCueOutput`/`VideoCueOutput`/
  `DmxCueOutput`;
- the only instance outside this repository carries a namespace typo, `…/cuems` against a
  `targetNamespace` of `…/cuems/` (X15).

The transcription is literal and complete, so no half-renamed spelling survives:

| Was | Is |
|---|---|
| `outputs.xsd` | `hardware_outputs.xsd` |
| schema key `"outputs"` | `"hardware_outputs"` |
| `SchemaName.OUTPUTS` | `SchemaName.HARDWARE_OUTPUTS` |
| root element `CuemsOutputs` | `CuemsHardwareOutputs` |
| type `OutputsType` | `HardwareOutputsType` |

**The type rename resolves X14.** `script.xsd` keeps its own `OutputsType` — a different type
that was never the problem — and is now the only declaration of that name, so the two schemas no
longer collide. The per-schema registry split that the collision forced (research R4) stays:
every binding and cached derivation is built on it, and nothing has established that a shared
schema object would now be correct. Two tests were rewritten to pin the **resolution** instead of
the workaround, including an assertion that the hardware schema no longer answers to the script
schema's type name.

**X15 still stands**, so the schema remains reserved rather than usable: the only instance outside
this repository carries a namespace typo. It also still has no model bindings.

Scope note: `tests/contract/test_schema_scope.py` pins each schema's Phase-1-end content, and
this schema no longer carries it. It is **excluded** from that assertion with the reason recorded,
rather than re-pinned to a recomputed hash — a fresh hash would silently re-baseline an
attestation whose stated meaning is *Phase-1-end content*. It stays covered by the
doc_version and exactly-six-schemas checks.

Corpus: the two live instances are renamed with the schema. `tests/data/corpus/pre-008/` is a
frozen snapshot the corpus walk excludes, and is left untouched.

## Unreleased — schema-derived XML serialization core (feature 004)

Replaces four independent implementations of the same mapping rules with one engine driven
by a field specification derived from the XSD. **Observable behaviour does not change**:
written XML and the read dict stay byte-identical, and every pre-existing consumer import
keeps working behind a deprecation shim — with one declared exception, below.

### ⚠️ Breaking — `cuems-nodeconf` handler injection is no longer consulted

`cuems-nodeconf` registers its node handlers by assigning into this library's private
module namespaces (`NodeXmlBuilders.py:105-111`):

```python
XmlBuilderModule.nodeXmlBuilder = nodeXmlBuilder
ParsersModule.nodeParser        = nodeParser
```

`CuemsParser.get_parser_class` and `XmlBuilder.get_builder_class` used to resolve handlers
through `globals()` of their own module, so an injected name was found. Every path now
routes through an explicit registry, and **an injected name is never consulted**.

Note what does *not* break: the imports still resolve and the assignments still execute
without error. Only their effect is gone — the node serializes through a generic instead of
through `nodeXmlBuilder`, silently. That is why the break is pinned by a test
(`tests/contract/test_declared_break_nodeconf.py`) rather than left to be noticed.

No shim can preserve it: honouring an injected name means keeping the implicit `globals()`
lookup that the explicit registry exists to delete.

- **Affected consumer**: `cuems-nodeconf` only. `cuems-editor` and `cuems-engine` need no
  change at this release.
- **The fix is carried by feature 007**, not by this release. It must target an API that is
  internal here, becomes public in feature 006, and absorbs the node model in 007 — written
  now it would be rewritten twice. `cuems-nodeconf` is not shipping against this release.
- **Details**: `specs/004-xml-serialization-core/migration-map.md` §3.

### Deprecated

All of the following keep working and will be **removed in `v0.1.2`**. Importing is silent;
each *call* warns, at the caller's line, naming its replacement. Full table with consumer
call sites: `specs/004-xml-serialization-core/migration-map.md`.

- `cuemsutils.xml.XmlReaderWriter` → `cuemsutils.xml.xml_reader_writer` (the module was
  renamed to snake_case; the class name is unchanged).
- `cuemsutils.xml.Settings` → `cuemsutils.xml.settings`.
- `cuemsutils.xml.Parsers` — the `*Parser` family, `GenericParser`, `GenericDict`,
  `CuemsParser.str_to_value` and `STRING_TYPED_KEYS`.
- `cuemsutils.xml.XmlBuilder` — the `*XmlBuilder` family and `VALUE_TYPES`.

Imports through the **package root** are unaffected and need no change:
`from cuemsutils.xml import XmlReaderWriter, Settings, NetworkMap, ProjectMappings,
ProjectSettings`. Most consumer code falls in this category.

`CuemsParser` itself is **not** deprecated — it becomes the engine's delegating facade and
remains a supported entry point. Its `str_to_value` method is deprecated; the class is not.

`STRING_TYPED_KEYS` and `VALUE_TYPES` are deprecated but **cannot warn**: both are values
read in membership checks, never called, so there is no call for a warning to attach to.

### Changed — the one intentional, non-breaking behaviour difference

Log output. This feature guarantees byte-identical XML and byte-identical read dicts; log
records are explicitly outside that guarantee.

- INFO is now declared at the level of **XML file access** (read, write, validate). Element
  construction and per-cue work drop to DEBUG, so the record count scales with files
  touched rather than with cues — a 1000-cue script no longer emits a thousand INFO lines.
- No record at any level carries a field value or an object repr. As a side effect, show
  content — cue names, file paths — no longer appears in log files.

### Fixed

- `MediaCue` declared `fade_profiles` in `REQ_ITEMS` while `script.xsd` declares it on
  `AudioCueType` and `VideoCueType` — the two concrete types — and not on `MediaCueType`.
  The field moved to `AudioCue` and `VideoCue` to match. No document changes: both
  subclasses inherited it and both schema types have it, so the base class was simply
  claiming a field its own schema type does not define. Found by the new coherence check on
  its first run.

### Performance

The engine is **faster** than the code it replaces, measured best-of-5 on a fixed machine
and interpreter (`specs/004-xml-serialization-core/baseline.md`):

| | Before | After |
|---|---|---|
| `validate_object`, dummy script | 0.00627 s | **0.00555 s** (−11%) |
| `validate_object`, with fade profiles | 0.00653 s | **0.00595 s** (−9%) |
| Pre-existing 561 tests | 19.72 s | 19.66 s |

Deriving a field specification once per type and reusing it beats re-deciding per object.
Derivation is bounded by the 56 distinct complex types across all six schemas and does not
grow with document size — asserted by a counter, not a clock, so it holds on show files
larger than anything in the test corpus.

### Testing

The suite grows from **561** to **1255** tests. The additions are the deliverable as much
as the engine is: a 28-document corpus vendored from all four repositories with recorded
provenance, byte-level goldens for XML and for both read-dict configurations, and a
`xml → object → json → object → xml` chain test that compares **every** intermediate rather
than only the endpoints.

The goldens were captured from unmodified code and committed before any machinery moved.
They have one commit each and have never been edited.

### Notes

- Element order for order-free (`xs:all`) content models is derived as **arrival order**,
  which is what the current builder produces. An earlier draft specified sorted keys; the
  goldens showed that two of four captured `CuemsScript` roots are not sorted, so a sorted
  rule would have rewritten the root element of every hand-authored script. See FR-001b.
- Five schema defects and two code defects are recorded and deferred, not fixed — see
  `specs/agreements/schema-evolution-convention.md`, "Recorded schema debt", X13–X17 (relocated
  from the deleted planning audit in 010 T069c). The two worth knowing about:
  `outputs.xsd` declares an `OutputsType` that collides with `script.xsd`'s, **and** the
  only `outputs.xml` in existence has a namespace missing its trailing slash. Between them,
  nothing has ever validated against `outputs.xsd`.
- `gradient_osc_port` was added to `NodeType` as *required* in 0.1.0rc8, which invalidated
  every settings file written before it — including two this project shipped. Recorded as
  X13; the fix is scheduled under feature 006's schema-evolution convention.
- `mediaParser` has never been reached: the handler lookup builds `'Media' + 'Parser'`
  while the class is spelled `mediaParser`. Thirteen occurrences across the corpus, no
  error, no log line. Preserved unchanged here — binding it would start running code that
  has never run — and scheduled for feature 005.

## 0.1.0rc17 — 2026-10-15

New project-scope action for the authored end of an unattended show: the cuems-engine `stop_project` ActionCue (ClickUp 869fhjdq5). This package only carries the vocabulary; the behaviour is in the engine.

### Added
- `script.xsd` `ActionType` gains `stop_project`. It is the first project-scope action and needs no target, so its `action_target` is written empty (`<action_target />`), which `TargetType` already allowed. On parse that comes back as `None`: `str_to_value` maps the empty string to `None` and the parsers assign without going through the setter. The `ActionCue` constructor and setter still refuse an explicit `None`.
- `tests/test_action_cue_stop_project.py`: writer → XSD → reader round trip, parsed target is falsy, the editor's JSON path (`CuemsParser` on a `null` target) gives the same, unknown action types are still rejected by the schema, the model still refuses `None`.

### Notes
- **Every box of a cluster needs ≥ rc17 before a project carrying the cue is saved.** A box on ≤ rc16 rejects such a project at validation: the editor cannot save or open it, the controller fails the load early, and a node fails the load after tearing down its previous project (no `armed_ready`, "Load stalled" at 120 s). **Rollback hazard:** downgrading utils on a box that holds such a project strands it until the `<ActionCue>` whose `<action_type>` is `stop_project` is removed from `cue_script.xml` by hand.
- `pause_project`, `resume_project`, `load`, `unload` and `wait` stay in the enum and stay unimplemented.

## 0.1.0rc16 — 2026-10-08

Media cues without a usable media block no longer crash the editor's save with a bare `KeyError 'file_name'`, and never make a project unloadable (ClickUp 869fej07m).

### Fixed
- `CueList.get_media` (editor path: update, new, duplicate, relink) guarded with `hasattr(cue.media, 'file_name')`, but `file_name` is a property that raises `KeyError`, which `hasattr` does not catch. A client that dropped a cue's media block (the UI does, when the file is not in its library list) produced an empty `Media` object and the save died inside the atomic block. Now: a media block without a file raises a named `ValueError` that says which cue — still no write, but readable. A cue with **no** media object (`None`, i.e. an empty `<Media/>` or a JSON `Media: null`) is logged at WARNING and skipped, so legacy projects stay listable and duplicable; refusing to *save* that shape is the editor's validator's job.
- `CuemsScript.get_own_media` (engine path, every node, every load) had the same `hasattr` guard. It now classifies the media without raising: a cue without a usable media file is logged at ERROR and left out of the media list, the project still loads and that cue fails at arm, locally — exactly what an empty `<Media/>` did before, now visible in the journal. Raising here would have aborted the load on every node.

### Added
- `MediaCue.media_status()` → `('none' | 'invalid' | 'ok', file_name)`: the non-raising classifier both call sites use.

## 0.1.0rc11 — 2026-07-28

Free-text fields are no longer type-coerced during parsing (closes ClickUp 869cqbpxa).

### Fixed
- `CuemsParser.str_to_value` no longer coerces values whose key names a string-typed field. It previously ran every scalar through `int` → `float` → `strtobool` → `Uuid` regardless of key, so free text was silently rewritten. Because `strtobool` accepts the truth abbreviations, a cue named `n`/`N`/`f`/`F` was persisted as `False`, `y`/`Y`/`t`/`T` as `True`, and any bare digit as an `int` — 18 of the 62 alphanumeric single characters were corrupted, along with the words `yes`/`no`/`true`/`false`/`on`/`off`. Sergio reported the symptom as "can't name a cue with a single letter"; there was never a length rule, the failing characters were exactly `strtobool`'s vocabulary. The affected keys reachable in practice are `name`, `description` and `file_name`.
- A cue named lowercase `none` or `null` hit the `['none', 'null', '']` → `None` branch, serialised to `<name/>`, and failed `NameStringType`'s `minLength=1` — a hard `XMLSchemaValidationError` at save time rather than silent corruption. The new short-circuit precedes that branch, so both failure modes are fixed together.

### Added
- `STRING_TYPED_KEYS` in `xml/Parsers.py` — the set of keys exempt from coercion. `name`, `description` and `file_name` are the ones reachable today; `output_name`, `parameter_name`, `icon`, `color` and `unix_name` are defensive entries, currently shielded by unrelated bypasses in `outputsParser`, `_normalize_fade_parameters` and the `GenericDict` fallback, listed so that fixing any of those bypasses cannot silently reintroduce this bug.
- `str_to_value` takes an optional `key` argument, threaded through all four call sites (`CuemsScriptParser`, `CueListParser`, `GenericParser`, `fade_profileParser`). The argument is optional, so existing single-argument callers are unaffected.
- `tests/test_name_coercion.py` — exhaustive sweep over all 62 alphanumeric single characters for each reachable key, the boolean/nullish word set, a full XML round-trip, and negative tests pinning that `enabled`/`autoload`/`timecode`/`loop` still coerce and that `id` still parses to a `Uuid`.

### Notes
- `id` is deliberately **not** in the allowlist: the `Uuid()` branch inside `str_to_value` is the only thing that produces `Uuid` objects on parse (the parsers assign via raw `dict.__setitem__` and never reach the property setters), so adding it would downgrade every cue, script and media id to a plain `str`. The consequence is that `DmxSceneType.id` (`script.xsd:403`, declared `xs:string`) cannot be protected by this mechanism — accepted, since DMX scene ids are system-assigned rather than operator-typed.
- Projects saved before this release have the corrupted name baked into their `cue_script.xml`; the original text is unrecoverable (`n`, `no`, `N`, `off` all collapse to `False`) and must be renamed by hand.
- `cuems-nodeconf` calls the inherited `str_to_value` without a key (`NodeXmlBuilders.py:80`), so node names remain exposed to the identical bug. Tracked separately.

## 0.1.0rc8 — 2026-05-20

Production call-site migration to the `CTimecode` v2 API, removal of a long-deprecated method, and a new required settings field for `gradient-motiond` integration.

### Fixed
- `AudioCue`, `VideoCue`, `DmxCue`: migrated three remaining `.milliseconds` call-sites to the v2 API. `AudioCue.py:100` and `VideoCue.py:84` polling loops now use `.milliseconds_rounded` (int comparison, no silent float contamination). `AudioCue.py:106` and `DmxCue.py:195` offset calculations now use `.milliseconds_exact` (float, precision-sensitive). These production consumers still emitted `DeprecationWarning` at runtime even after 0.1.0rc6 completed the library-level migration.

### Removed
- `VideoCue.video_media_loop` — deprecated since 0.0.9rc5 (`"Use loop_cue from CueHandler instead"`). Confirmed zero callers across cuems-engine, cuems-editor, and cuems-utils. Superseded by `loop_videoCue` in `cuems-engine/cues/loop_cue.py`. Also drops now-unused imports `time.sleep` and `deprecated.deprecated` from `VideoCue.py`.

### Added
- `gradient_osc_port` element added as a required field on `NodeType` in `settings.xsd`. This is the UDP port number that `gradient-motiond` listens on for incoming OSC commands; the engine's `GradientClient` reads it from `ConfigManager` when building the datagram endpoint. The field is propagated to `templates/settings.xml` (with a placeholder value and operator guidance) and all test XML fixtures so schema validation stays aligned.

### Notes
- After this release, `python -W error::DeprecationWarning pytest tests/` should produce zero `DeprecationWarning` from `.milliseconds` in the cuems-utils test suite. Run it before merging any future change that touches `CTimecode` consumers.

## 0.1.0rc7 — 2026-04-27

24h SMPTE rollover fix (closes ClickUp 869cpdbzy). Layer 1 of a two-layer fix; Layer 2 lives in cuems-engine's MtcListener (PR #10 there).

### Fixed
- `CTimecode.__str__` now passes `skip_rollover=True` to upstream's `frames_to_tc`, keeping the string representation monotonic past 24h. `frames=2_160_002` at 25fps now renders as `"24:00:00:01"` instead of wrapping to `"00:00:00:01"`. Sergio reported the symptom: long-running install (>24h continuous MTC) where audio cues + sequence stop while video keeps looping. The underlying `.frames`, `.milliseconds_exact`, and `.milliseconds_rounded` accessors were already monotonic post-`0.1.0rc6` (PR #6) — this completes the coverage so any consumer that round-trips through `str()` also stays correct.

### Added
- `TestRollover` class in `tests/unit/test_ctimecode.py` pinning the 24h-immune contract: `.milliseconds_exact`/`.milliseconds_rounded` monotonic at the boundary, `__add__` advances correctly across 24h, `__str__` shows `24:00:00:01`, the loop-rebase pattern from `loop_cue.py:107,224` survives 5+ iterations past 24h, polling comparisons (`<`) work past the boundary.

### Notes
- Implementation is one method override (`__str__`) — well below the escalation trigger from the 869cyndtv plan (>2-3 upstream method overrides would have signalled "self-maintain CTimecode" instead). The `frames_to_tc` itself is left untouched (it's used internally by upstream's `next_frame_str` and rate accessors with `skip_rollover=True` already where needed).
- Layer 2 (cuems-engine MtcListener wrap detection + 24h offset accumulation) is required to fully close 869cpdbzy: MIDI MTC encodes hours in a 5-bit field (max 23) and real SMPTE senders reset to `00:00:00:00` after 24h, so the listener must detect the wrap and accumulate offset before constructing CTimecodes. Without Layer 2, `mtc.main_tc` resets to ~frames=1 every 24h regardless of CTimecode's internal monotonicity.

## 0.1.0rc6 — 2026-04-27

CTimecode hardening pass (closes ClickUp 869cyndtv items #1–#7 + audit findings). This release is a coordinated semantic fix to the CTimecode wrapper: `__init__` now produces playhead-semantic frames; arithmetic operators are off-by-one-correct and reject cross-framerate operands; `.milliseconds` is split into precision-explicit accessors; the `format_timecode` `+1` workaround is removed; FadeCalculator's silent ms-as-seconds unit error is fixed.

### Changed (breaking)
- `CTimecode.__init__(start_seconds=...)` now produces playhead-semantic frames (one more than before for the same real-time value). The same real time `T` produces the same `.frames` regardless of which constructor path was used (`start_timecode='HH:MM:SS:FF'` vs `start_seconds=T`). Routes through `tc_to_frames` via an HMSF string so drop-frame correction at 29.97/59.94 DF is handled correctly. Empirically: at 29.97 DF, `start_seconds=600` now produces `frames=17983` (matching `start_timecode='00:10:00:00'`), where the old path produced `18000` (off by 17 frames).
- Arithmetic between CTimecodes of different framerates now raises `CTimecodeError` instead of silently using `other.frames` as if same-framerate. Affected: `__add__`, `__sub__`, `__mul__`, `__truediv__`. Cross-framerate use cases must explicitly call `.return_in_other_framerate()` first.
- `__add__`/`__sub__` now produce playhead-correct results: `(CTimecode(start_seconds=10) + CTimecode(start_seconds=20)).milliseconds_rounded == 30000` (was `29960`); `(CTimecode(start_seconds=30) - CTimecode(start_seconds=10)).milliseconds_rounded == 20000` (was `19960`).
- `__truediv__` now `round()`s the float division result (was passing float to upstream's frames setter, which raised `TypeError`); explicitly rejects zero/negative int divisors with `CTimecodeError`.
- `framerate` getter now returns canonical numeric types — `int` for SMPTE integer rates (was `'25'` string), `float` for fractional, `int 1000` for ms (unchanged). `tc.framerate == 25` now works as expected (Option D).
- `return_in_other_framerate` rewritten in frame domain — the old time-domain round-trip dropped one frame per conversion. Round-trips between framerates now stable.
- `helpers.format_timecode(value)` no longer applies a manual `+1` to `.frames` — that compensation is now redundant since `__init__` canonicalizes itself. The combined effect is identical at the default `'ms'` framerate; differs by one frame at other framerates (and matches the `start_timecode` ctor path now).
- `FadeCalculator.calculate_timeline` no longer silently treats milliseconds as seconds — `start_seconds = ms_value / 1000`. The unit error self-cancelled at framerate `'ms'` (where `1 ms-frame == 1 ms`) but produced wildly wrong values at any other framerate.

### Deprecated
- `CTimecode.milliseconds` (int) — now an alias of `.milliseconds_rounded` that emits `DeprecationWarning`. Migrate to `.milliseconds_rounded` (int, rounded) or `.milliseconds_exact` (float, precise) per intent. Will be removed at the first stable release.

### Added
- `CTimecode.milliseconds_exact: float` — exact-precision milliseconds via `frame_number * 1000 / float(framerate)`. Use for precision-sensitive math (offset calc, scheduler, MTC bias measurement).
- `CTimecode.milliseconds_rounded: int` — `round(milliseconds_exact)`. Use for sleep durations, integer CLI args, polling comparisons, dict/set keys.
- Same-framerate assertion error messages on every arithmetic operator.
- `tests/unit/test_ctimecode.py` expanded with full framerate matrix coverage (`24, 25, 29.97, 30, 'ms'`), DF-boundary parametrization at 29.97, the `TestPrecisionSplit` class anchoring the V2 deprecation contract, and hypothesis property tests for round-trip invariants.
- `tests/unit/test_fade_calculator.py` gained intermediate-values correctness test and a no-DeprecationWarning regression pin.

### Fixed
- `CTimecodeTimer._run_loop` migrated from `.milliseconds` to `.milliseconds_exact` (pre-existing internal consumer).
- `CTimecode.__init__` no longer raises `ValueError` for very small positive `start_seconds` (e.g., `0.03125` at 24fps where upstream's `int(s*ifr)` produced `0` and hit the frames>0 setter guard). The wrapper now bypasses upstream's start_seconds path entirely when canonicalizing.

### Migration: `.milliseconds` precision split

The original `.milliseconds: int` truncated via `int()`, losing up to 1ms per call at fractional framerates and accumulating monotonically. The new API splits this into two explicit accessors, with the original retained as a deprecated alias to ease migration.

| If you currently do | Migrate to | Why |
|---------------------|------------|-----|
| `tc.milliseconds == 30000` (integer fr) | `tc.milliseconds_rounded == 30000` | Behavior identical at integer fr; clarifies rounding intent. |
| `tc.milliseconds == 1001` (29.97fps) | `tc.milliseconds_rounded == 1001` (gets 1001 via `round()`) — OR — `tc.milliseconds_exact == pytest.approx(1001.001, abs=1e-6)` for precision | Old code got 1001 via truncation; rounding may differ by ±1 at certain frames. Audit fractional-framerate `==` checks. |
| `int(tc.milliseconds)` | `tc.milliseconds_rounded` | Silences `DeprecationWarning`; semantically identical (V2 returns int already). |
| `time.sleep(tc.milliseconds / 1000)` | `time.sleep(tc.milliseconds_rounded / 1000)` | Same answer; integer-ms intent clearer. |
| polling: `while mtc.milliseconds < target` | polling: `while mtc.milliseconds_rounded < target` | Int comparison; no silent float contamination. |
| dict/set keyed on `tc.milliseconds` | `tc.milliseconds_rounded` | Float keys are fragile with equality. |
| precision-sensitive math (offset calc, scheduler, MTC bias) | `tc.milliseconds_exact` | Float, no precision loss. |

Run `python -W error::DeprecationWarning pytest tests/` to surface every remaining `.milliseconds` call-site as a hard failure during migration.

### Notes
- All public APIs other than `.milliseconds` itself are source-compatible. Engine and editor migrations land in cuems-engine PR #7 and cuems-editor PR #9 (separate ClickUp items in the 869cyndtv plan).
- The `return_in_other_framerate` method retains a `~5μs` per-call throwaway-construction cost that was deliberately not optimized — see the source docstring for the deferred fix sketch (Option D class-level cache) and revisit triggers.

## 0.1.0rc5 — 2026-04-22

### Added
- `settings.xsd` defines optional `<output_latency_ms>` on
  `AudioPlayerType`, `VideoPlayerType`, and `DmxPlayerType`.
  - Audio and video accept `AutoOrIntLatencyMsType` — a union of
    `xs:nonNegativeInteger` (maxInclusive=500) or the literal
    `"auto"`. Integer is an explicit override in ms; `"auto"` defers
    to the binary's built-in default (JACK query for audioplayer;
    hard-coded 33 ms for videocomposer).
  - Dmx accepts `IntLatencyMsType` (integer only) — no auto-measurement
    path exists for the DMX pipeline; `"auto"` is rejected at
    validation time to avoid implying magic that doesn't exist. Absent
    element defers to dmxplayer's hard-coded 35 ms default.
- Tests for the tri-state (int / `"auto"` / absent) round-trip and a
  negative test for `"auto"` on dmxplayer.

### Notes
- Schema change is strictly additive (`minOccurs="0"`); existing
  `settings.xml` files remain valid with no migration.
- Typing contract: `xmlschema.to_dict()` returns Python `int` for
  integer values and `str` for `"auto"`. `cuems-engine`'s NodeEngine
  arg-building relies on `isinstance(value, int)` to decide whether
  to emit the `--output-latency-ms` CLI flag to each player process.
