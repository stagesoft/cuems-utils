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

### Reconciled — the release line's `0.1.0rc15` … `0.1.0rc17` are in this release

The parallel release line (`debian/bookworm`, 77 commits ahead) and `main` (tag `v0.1.0rc17`) are
**merged in** (feature 017), with their history, so both are ancestors of `0.1.1` and nothing they
shipped is lost:

- **`stop_project` ActionType** (rc17, 869fhjdq5): the authored end of an unattended show. A project
  an rc17 cluster saved with such a cue **loads on `0.1.1`** after `cuems-reshape-devices` and
  `cuems-convert-documents`.
- **Media guards** (rc16, 869fej07m): `MediaCue.media_status()`. `CueList.get_media` raises a named
  `ValueError` for a media block without a file and skips a missing one with a warning;
  `CuemsScript.get_own_media` never raises.
- **Stored media values** `pixel_width`, `pixel_height`, `file_size`, `file_md5` (rc15, 869fat84r),
  carried by this release's own media block. ⚠ An **uppercase** md5 is **refused** here; rc15
  lowercased it. Lowercase before assigning.
- **`Replaces: cuems-engine (<< 0.1.0rc6-2~)`** (rc15): `cffi-gen-src` belongs to this package.
- **No `/usr/lib/cuems/CACHEDIR.TAG`** in the package (rc16+1).

### Changed — `stop_project` takes no target, and a leftover one is cleared

A `stop_project` cue accepts a `None` target, at construction and from JSON (`null`, as the frontend
sends it). It is written `<action_target />` and loads clean. A target left on such a cue, typically
kept when a `stop` cue was retyped, is **repaired to `None` on load** (the load report names the rule
`project_action_takes_no_target` and the uuid it replaced) and **refused on save**. Every other
action type still requires a target. rc17 refused a `None` target at construction; this release
accepts it.

### Removed — `pause_project` and `resume_project`

Both values leave `ActionType`, which now has 11. Project pause/resume is deferred to a future
release, and no producer ever wrote either value, so no document is affected. The record and the
way to reinstate them are in `specs/planning/project-pause-resume-deferred.md`.

### Changed — the migration tools say when the loader would refuse what they wrote

`cuems-reshape-devices` and `cuems-convert-documents` validated the schema only. After writing,
each now asks the loader's own question and reports every document the loader would refuse:
`WARNING <path>: would be refused on load: …`, and a `refused on load` count in the summary.
`--check` reports the same for what would be written. What they write and their exit status are
unchanged. `python -m cuemsutils.xml.reshape_devices` now runs the tool; it exited 0 doing nothing.

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

### Added — `AsyncCommsThread`, the thread that runs a service's NNG event loop

`cuemsutils.tools.AsyncCommsThread` is the base class `cuems-engine` had, absorbed here so
`cuems-nodeconf` can stop keeping a copy of it
(`specs/planning/async-comms-thread-absorption.md`). It is the engine's class with the same surface,
plus three changes:

- **It notices when its communications end.** A task that raises, or a task marked with
  `essential()` that returns, cancels the others, records `end_reason`, calls the overridable
  `on_comms_ended()` and stops the loop. The engine's version waited for every task, so a bus hub
  whose socket had closed left the thread running with no bus. A task that is not essential may
  finish early, and the others keep running. The library never exits the process; the subclass
  decides what an ended thread means for its service.
- **`stop()` is safe to call more than once**, before `start()`, or after the communications ended
  on their own. Called from the comms thread itself it raises `RuntimeError` instead of deadlocking.
  `stop()` still blocks until the thread has gone, which keeps the process from aborting at exit
  (ClickUp 869ed00ya). Measured in a child process with an NNG receive pending: without `stop()`,
  11 of 20 runs aborted with status 134; with it, 20 of 20 exited 0.
- **The loop is closed in its own thread**, and `run_coroutine()` refuses with the reason once the
  communications have ended. `AsyncCommsThread.stop_all()` stops every live instance, for test
  teardown.

### Fixed — one bad request no longer stops a service from answering

`NngRequestResponse.reply()`, which `Communicator.reply()` runs, ended its loop on the first request
whose processor raised, or that was not JSON. From then on, **every** request to that service
waited forever. A response that could not be JSON-encoded was never sent, so its requester waited
forever too. Every request now gets exactly one reply. When a request cannot be answered normally,
the reply is `{"OK": false, "error": "<ExceptionType>: <message>"}`: the shape `cuems-nodeconf`
already uses, which `cuems-editor` reads as a refusal. Only a socket error ends the loop.

The context API had the same gap: `responder_get_request` logged a request that was not JSON and
dropped it, with no reply and no close. It now answers with the same error reply and closes the
context. A callback that raises is still not answered for, because it owns its context and may
already have replied.

### Fixed — a bus hub whose socket closes stops instead of idling

`NngBusHub.start()` kept running after its bus socket closed: its receiver stopped, but `start()`
waited on. It now returns as soon as its receiver or sender stops, and logs why (`bus socket closed`,
or the handler's error). It still raises only for startup errors. A service that must react should
watch for the `start()` task ending; `cuems-engine` has been asked to do so.

### Fixed — enabling auto-ping on a running hub takes effect at once

`NngBusHub.enable_auto_ping()` or `disable_auto_ping()` called after `start()` took effect only once
the interval already in progress had run out (10 s by default). The handler now wakes on the change
and starts a new interval with the new settings. The calls are safe from any thread.

### Fixed — every message on the bus reaches the receiver

`NngBusHub` counted a frame as received and then dropped it when the frame was valid JSON but not an
object (`[1, 2]`, `"text"`, `42`), or was not UTF-8. Every frame is now delivered. A JSON object is
the message data, as before. Anything else arrives as `{"raw_data": "<its text>"}`, as non-JSON text
already did, with undecodable bytes replaced by `\ufffd`.

### Fixed — SIGTERM and SIGINT stop a service on any interpreter

`SignalEngine`'s exit handlers called the `site` builtin `exit()`, which an interpreter without the
`site` module (`python -S`, frozen or embedded builds) does not define. The handler then raised
`NameError`, and the service kept running. They call `sys.exit()` now.

### Fixed — a request no longer waits forever, and a cancelled service always stops

`send_request` had no deadline: asking a service that was not running blocked in the send for good.
It now takes `timeout` (seconds, default **100**) for the send and the reply together. When the
deadline passes it returns `None`, as its other failures do, and logs which address did not answer.
`Communicator.send_request` takes the same parameter. A custom `communicator_service` must now accept
`timeout` too.

Cancelling a service's `reply()` loop, or a pending `responder_get_request`, could hang about 1 time
in 1000. pynng's asyncio bridge waits for an NNG callback that occasionally never arrives. The
library now never exposes a pynng operation to cancellation: a cancelled server returns at once and
closes its socket or context. Measured: no hang in 7000 cancellations.

### Fixed — `Communicator` accepts an `ipc://` address

`Communicator("ipc:///tmp/editor.ipc")` checked the prefixed string as a file path, which resolves to
the relative path `./ipc:/tmp/...`, and called `sys.exit(1)`. That stopped the calling service. A plain
path always worked, and still does.

### Fixed — a failed bus send no longer counts as traffic

`NngBusHub` counted a message as sent, and stamped its send time, before `asend()`. A send that
failed therefore kept `is_connection_healthy()` `True` while nothing reached the bus. The counters
now move only after a successful send.

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

### Folded — `outputs` renamed to `hardware_outputs`, and X14 resolved

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

### Folded — schema-derived XML serialization core (feature 004)

Replaces four independent implementations of the same mapping rules with one engine driven
by a field specification derived from the XSD. **Observable behaviour does not change**:
written XML and the read dict stay byte-identical, and every pre-existing consumer import
keeps working behind a deprecation shim — with one declared exception, below.

#### ⚠️ Breaking — `cuems-nodeconf` handler injection is no longer consulted

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

#### Deprecated

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

#### Changed — the one intentional, non-breaking behaviour difference

Log output. This feature guarantees byte-identical XML and byte-identical read dicts; log
records are explicitly outside that guarantee.

- INFO is now declared at the level of **XML file access** (read, write, validate). Element
  construction and per-cue work drop to DEBUG, so the record count scales with files
  touched rather than with cues — a 1000-cue script no longer emits a thousand INFO lines.
- No record at any level carries a field value or an object repr. As a side effect, show
  content — cue names, file paths — no longer appears in log files.

#### Fixed

- `MediaCue` declared `fade_profiles` in `REQ_ITEMS` while `script.xsd` declares it on
  `AudioCueType` and `VideoCueType` — the two concrete types — and not on `MediaCueType`.
  The field moved to `AudioCue` and `VideoCue` to match. No document changes: both
  subclasses inherited it and both schema types have it, so the base class was simply
  claiming a field its own schema type does not define. Found by the new coherence check on
  its first run.

#### Performance

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

#### Testing

The suite grows from **561** to **1255** tests. The additions are the deliverable as much
as the engine is: a 28-document corpus vendored from all four repositories with recorded
provenance, byte-level goldens for XML and for both read-dict configurations, and a
`xml → object → json → object → xml` chain test that compares **every** intermediate rather
than only the endpoints.

The goldens were captured from unmodified code and committed before any machinery moved.
They have one commit each and have never been edited.

#### Notes

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

*(Debian only; not published to PyPI)*

New project-scope action for the authored end of an unattended show: the cuems-engine `stop_project` ActionCue (ClickUp 869fhjdq5). This package only carries the vocabulary; the behaviour is in the engine.

### Added
- `script.xsd` `ActionType` gains `stop_project`. It is the first project-scope action and needs no target, so its `action_target` is written empty (`<action_target />`), which `TargetType` already allowed. On parse that comes back as `None`: `str_to_value` maps the empty string to `None` and the parsers assign without going through the setter. The `ActionCue` constructor and setter still refuse an explicit `None`.
- `tests/test_action_cue_stop_project.py`: writer → XSD → reader round trip, parsed target is falsy, the editor's JSON path (`CuemsParser` on a `null` target) gives the same, unknown action types are still rejected by the schema, the model still refuses `None`.

### Notes
- **Every box of a cluster needs ≥ rc17 before a project carrying the cue is saved.** A box on ≤ rc16 rejects such a project at validation: the editor cannot save or open it, the controller fails the load early, and a node fails the load after tearing down its previous project (no `armed_ready`, "Load stalled" at 120 s). **Rollback hazard:** downgrading utils on a box that holds such a project strands it until the `<ActionCue>` whose `<action_type>` is `stop_project` is removed from `cue_script.xml` by hand.
- `pause_project`, `resume_project`, `load`, `unload` and `wait` stay in the enum and stay unimplemented.

## 0.1.0rc16 — 2026-10-08

<!-- debian: 0.1.0rc16+1 (c01ca36) -->
**`0.1.0rc16+1`** (Debian revision, 2026-10-09) stops shipping `/usr/lib/cuems/CACHEDIR.TAG`, which `cuems-editor` 0.1.0rc1-5 and `cuems-engine` 0.1.0rc4/rc5 also ship, so installing one over the other failed with "trying to overwrite". No code change from `0.1.0rc16`.

Media cues without a usable media block no longer crash the editor's save with a bare `KeyError 'file_name'`, and never make a project unloadable (ClickUp 869fej07m).

### Fixed
- `CueList.get_media` (editor path: update, new, duplicate, relink) guarded with `hasattr(cue.media, 'file_name')`, but `file_name` is a property that raises `KeyError`, which `hasattr` does not catch. A client that dropped a cue's media block (the UI does, when the file is not in its library list) produced an empty `Media` object and the save died inside the atomic block. Now: a media block without a file raises a named `ValueError` that says which cue — still no write, but readable. A cue with **no** media object (`None`, i.e. an empty `<Media/>` or a JSON `Media: null`) is logged at WARNING and skipped, so legacy projects stay listable and duplicable; refusing to *save* that shape is the editor's validator's job.
- `CuemsScript.get_own_media` (engine path, every node, every load) had the same `hasattr` guard. It now classifies the media without raising: a cue without a usable media file is logged at ERROR and left out of the media list, the project still loads and that cue fails at arm, locally — exactly what an empty `<Media/>` did before, now visible in the journal. Raising here would have aborted the load on every node.

### Added
- `MediaCue.media_status()` → `('none' | 'invalid' | 'ok', file_name)`: the non-raising classifier both call sites use.

## 0.1.0rc15 — 2026-10-06

Stored media values, measured once at upload so the engine does not probe the file when it arms a
cue (ClickUp 869fat84r).

### Added
- `MediaType` gains optional `pixel_width` and `pixel_height` (VideoCue), and `file_size` and
  `file_md5` (every media type). The builder writes them in schema order, and the parser keeps
  `file_md5` a string. Same code as `cuemsutils 0.1.0rc15` on PyPI (tag `v0.1.0rc15`).

### Fixed
- `Replaces: cuems-engine (<< 0.1.0rc6-2~)`. Engine packages up to `0.1.0rc6-1` also ship
  `/usr/lib/cuems/bin/cffi-gen-src` (cffi's console script), so upgrading `cuems-utils` on a box with
  any of them failed with "trying to overwrite" unless forced. `cuems-engine 0.1.0rc6-2` stops
  shipping it.

## 0.1.0rc14 — 2026-08-03

### Fixed
- `HubServices` stops its receive and send loops for good when the socket reports `Closed`, instead
  of looping straight back into another `arecv_msg()`/`asend()`. pynng's `atexit` hook calls
  `nng_fini()`, and CPython does not join daemon threads before `atexit` hooks run, so the comms
  thread kept polling and aborted the process with "panic: pthread_mutex_lock: Invalid argument".
  Both loops also stop once `_closing` is set. Measured on a node engine: 5/5 instrumented restarts
  core-dumped before, 0/10 after (ClickUp 869ed00ya).

### Added
- `VideoCue.opacity`, and the corrected `AudioCue.master_vol` default.

## 0.1.0rc13

*(never published: no Debian build, not on PyPI)*. The source moved to rc13 for `VideoCue.opacity`
and the `AudioCue.master_vol` default, and both were released as rc14.

## 0.1.0rc12 — 2026-07-29

*(Debian only; not published to PyPI)*

### Fixed
- `log.py` records each message **once** in the journal, with its real priority:
  - the root logger is seeded with a `NullHandler`, so third-party import-time logging cannot arm an
    implicit `basicConfig` stderr handler;
  - under systemd (`JOURNAL_STREAM`) only the `SysLogHandler` is attached, the only copy that
    carries a true per-record priority, so `cuems-logs -l/-e` can filter;
  - `SysLogHandler.ident` is set from `argv[0]`, so journald records the full `SYSLOG_IDENTIFIER`.

  Verified on a controller: 3 copies became 1, priorities 7/4/3.

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

## 0.1.0rc10 — 2026-07-09

### Security
- `lxml` 5.3.0 → **6.1.0**, clearing CVE-2026-41066 (XXE via `iterparse()` / `ETCompatXMLParser()`
  with `resolve_entities=True`). This package uses only `lxml.etree.Element` and
  `register_namespace`, never the parser entry points, so the flaw was never reachable here. The
  bump clears the advisory. The suite was green before and after.

## 0.1.0rc9 — 2026-07-06

*(Debian only; not published to PyPI)*

### Fixed
- Media duration correctness, paired with the `cuems-editor` and `cuems-frontend` fixes for the
  ffprobe duration-extraction bug. `Media.duration` is validated and canonicalised on write
  (accepts `str`/`CTimecode`/`None`, rejects malformed), and the getter still returns `str`.
  `script.xsd` escapes the literal dot in `TimecodeType`, and constrains `MediaType/duration` to
  `cms:TimecodeType`. Existing documents still validate; malformed values are now rejected.

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

*(never published: no Debian build, not on PyPI)*

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

*(never published: no Debian build, not on PyPI)*

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

## Earlier releases

Releases before `0.1.0rc5` (`0.1.0rc1`…`rc4`, and the `0.0.*` series, including `0.0.9rc7`) have no
section here. They are recorded by their git tags (`git tag -l 'v0.*'`) and on PyPI
(<https://pypi.org/project/cuemsutils/#history>).
