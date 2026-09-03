# XML infrastructure rebuild — Part 6: feature 009 consumer audit

**Status:** ready to inform `/speckit.specify` for feature `009`
**Date:** 2026-09-03
**Purpose:** measured current-state evidence backing the feature-009 prompt in
[Part 4](xml-rebuild-07-speckit-prompts.md) §8 — the same role
[Part 1](xml-rebuild-01-audit.md) plays for 004–007 and
[Part 5](xml-rebuild-08-extension-audit.md) plays for 008. Findings are
labelled `C1`–`C12` (consumer) rather than continuing `F`/`X`/`E`, since this
is a third pass, run **after** 008 landed rather than before it.

**Why this document exists.** §8 was written on 2026-08-25, from 007's
migration checklist and 008's *plan*. 008 has since landed in full (both
phases, 2026-09-02; tasks and checklist 100% closed), and three further
commits landed on `feat/xml-refactor` after its close-out. This pass checks
§8's claims against the live code in every repository that consumes
`cuemsutils`, before any speckit flow runs — the same discipline Part 5's
revision note applied to its own first draft.

## Verification baseline

`hatch test` on `feat/xml-refactor` @ `7c5896c`, measured 2026-09-03:
**2562 passed, 96 skipped, 2 xfailed in 53.24 s = 20.8 ms/test.** This is
009's Principle IV baseline, **not** 008's recorded 22.06 ms/test — the suite
grew by 40 tests after 008 closed (`TimeoutLoop`, `StringSanitizer`,
`CopyMoveVersioned`). Derive the budget from 20.8 ms/test.

## What §8 got right

Every call site §8 names was re-checked against the live file and still
exists where it says. Recorded so this document is read as an *extension* of
§8, not a correction of it:

| §8's claim | Verified |
|---|---|
| Five `CuemsParser` call sites | `CuemsDBProject.py:356,489,571,808` + `repair_durations.py:230` — all five, exact lines |
| `cuems-editor`'s `XmlReaderWriter` sites | `CuemsDBProject.py:883` (`save_xml`), `:895` (`load_xml`), `repair_durations.py:204,231` |
| Raw-dict pre-parse fixups | `_fix_media_durations:367`, `_clean_dangling_targets:387`, `_nullify_dangling_refs:417` |
| `cuems-engine` script load | `BaseEngine.py:509` (`XmlReaderWriter`), `:510` (`read_to_objects`) |
| `CONTROLLER_NETWORK_FLAG` and its two comparisons | `BaseEngine.py:33,410,440` — plus `:443`'s `online == "True"`, which 007's guide §5 added |
| `get_nodes_by_adoption` call sites | `ControllerEngine.py:249`, `CuemsWsServer.py:470`; the non-mutating workaround at `ControllerEngine.py:1152` |
| `cuems-editor`'s node field list | `CuemsWsServer.py:425`, `reload_network_map_nodes` at `:439` |
| `cuems-nodeconf` row 5 | all nine methods present: `:229,281,413,440,490,501,516,537,562` |
| `cleanup()`'s dead `self.cm` | `CuemsNodeConf.py:579-581`, unassigned anywhere in the class |
| The live config-domain UI | `settings.component.ts:35,48,56,122` (`nodelist_modify` + `initialMappings`) |

---

## C1 — `cuems-wsclient` is a sixth consumer, unlisted everywhere, already silently wrong

`cuems-wsclient` appears in **no** repo list: not §0's feature table, not §8's
per-repo scope, not 007's migration guide, not 008's. It declares
`cuemsutils = {version = ">=0.1.0rc5", optional = true}`
(`pyproject.toml:36`) and `cuems-utils (>= 0.1.0rc5)` in `debian/control:18`,
but imports **nothing** from the library. Instead it reimplements the reader:

`src/cuemswsclient/network_map.py` parses `/etc/cuems/network_map.xml` with
stdlib `ElementTree`, namespace-agnostically, and carries the retired
vocabulary in three places:

- `:33` — `node_type: str | None  # "NodeType.master" | "NodeType.slave" | None`
- `:93` — `node_type=_text(el, "node_type")`
- `:108` — `if n.node_type != "NodeType.slave": continue`

That last line gates the bridge's shutdown fan-out over adopted nodes. After
007's rename the element is `<node_role>node</node_role>`, so `_text` returns
`None` for every node, the `!=` is true for every node, and **every node is
skipped**. Nothing raises. This is 007 FR-030a-ii's "keeps resolving but
becomes semantically wrong" class, in its purest form, in the one repository
nobody was searching.

It also carries 5 of the ecosystem's `node_type` occurrences, so 009's "zero
occurrences, counted rather than reviewed" exit criterion cannot pass without
it.

**Decision (D32, 2026-09-03):** `cuems-wsclient` joins 009's per-repo scope in
full — its private `ElementTree` reader is replaced by the library's
`ConfigManager`/`network_map` path, not merely re-spelled. A second XML reader
for a schema `cuemsutils` owns is the F15 failure the rebuild exists to end.

---

## C2 — `cuems-editor` does not start against the current branch

`cuems-editor/src/cuemseditor/CuemsWsServer.py:24`:

```python
from cuemsutils.create_script import create_script, new_uuid
```

008 deleted `src/cuemsutils/create_script.py` outright (FR-033, ITEM D).
Unlike the six entry points 006 retired — which all still resolve and warn
through `deprecated_alias` at `0.1.0rc15`, verified in `xml/__init__.py:79-91`
— `create_script` got **no shim**. So this is an `ImportError` at module
import: the editor process does not start, and no call site is reached.

Two consequences §8 does not state:

1. It is 009's **first** task in `cuems-editor`, not a downstream consequence
   of the template cutover. Until it is done, nothing else in that repository
   can be tested against the new library at all.
2. `new_uuid` is imported from the same deleted module and must be re-sourced
   from `cuemsutils.helpers` (where `cuems-editor` already imports it at four
   other sites — `CuemsDBProject.py:4`, etc.). It is not part of the template
   question and should not wait on it.

Downstream: `CuemsWsServer.py:84` (`self.initital_template = create_script()`,
sic) and `:501-503` (the `initial_template` payload) are the actual template
surface, and those are the ones D26's cutover replaces.

---

## C3 — the shared context block's HARD CONSTRAINT now contradicts 008

Part 4 §2's context block ends with:

> **HARD CONSTRAINT (Part 2d): cuems-editor's `project_load` payload must stay
> byte-identical**, because it is transmitted verbatim to the Angular UI.

and §8's `/speckit.specify` prompt restates it: *"its project load path returns
`script.to_wire()` so the payload sent to the UI is byte-identical to today's."*

Both are now false, by two deliberate, already-landed decisions:

- **006** dropped `schemaLocation` from `to_wire()` — recorded in
  `xml/__init__.py`'s `_READ_NOTE` as the one per-method migration note in the
  whole feature, precisely because a caller told only "use `to_wire`" would
  discover it by diffing payloads in production.
- **008** changed `Media.duration` from `"00:00:30.000"` to
  `{"CTimecode": "00:00:30.000"}` on both wires (D17/D18b).

Pasted verbatim, that block makes `/speckit.specify` produce a spec carrying a
contradiction with its own inputs. The constraint must be **restated as an
enumerated delta**: the payload is byte-identical *except* for these two
changes, and every other key, ordering and string-boolean form is unchanged
(the `enabled === true || enabled === 'True'` dual-read still holds).

`doc_version` is **not** a third change: it is excluded from every wire
projection (008, `spec._derive_attributes`), and the frontend never sees it.

Incidentally, `cuems-frontend/src/app/services/projects/projects.service.ts:120`
declares `schemaLocation: string;` as a required property of its mappings
response interface. Nothing reads it, so 006's `frontend-note.md` ("no frontend
change is required") stays true at runtime — but it is a type-level lie the
moment the editor moves to `to_wire()`, and it is one line to delete.

---

## C4 — the schema descriptor has no public import path

009 requires `cuems-editor` to serve the descriptor over WS (D25/D26), but it
lives at `cuemsutils.xml.descriptor` (`SchemaDescriptor`, `generate_script_example`,
`generate_settings_example`) and `cuemsutils.xml.__all__` is `[]` — Q14's
"`xml/` is internal machinery", asserted by 006's FR-019 and SC-005.

The erosion is not hypothetical: `cuems-nodeconf` **already** imports
`cuemsutils.xml.mapper` (`Mapper`, `read_config_document`) and
`cuemsutils.xml.settings` (`NetworkMap as _NetworkMapReader`) today, from
`CuemsNodeConf.py:22-23`. No feature recorded that as a violation.

**Decision (D34, 2026-09-03):** the descriptor becomes reachable **through
`ConfigManager`**, the existing public config object (D15), rather than through
a new public module. Two things follow, and the spec states them deliberately
rather than leaving them to be inferred:

1. `ConfigManager`'s descriptor accessor covers **all six schemas**, `script`
   included. `ConfigManager` is otherwise a config-domain object, so serving
   the show schema's descriptor from it is a deliberate widening of its role —
   justified because the alternative is two public paths for one mechanism,
   and because the editor that serves config forms is the same one that serves
   the script template.
2. `cuems-nodeconf`'s two internal imports move onto public equivalents in the
   same feature, so 009 ends the Q14 erosion rather than extending it.

---

## C5 — the frontend template inventory undercounts, in files and in kind

E19 measured "~7 call sites across 2 files"; 008's T081 enumerated two
value-reading sites (`:688` `master_vol`, `:726-727` `dmx_channels`) and two
shape-only files. Checked 2026-09-03 against `/disk/Projects/StageLab/cuems-frontend`:

`projectsService.projectTemplate()` is consumed in **four** files:

- `services/projects/projects.service.ts:395,420` — the signal's own
  definition site (`:150`) plus two internal reads; also `:159,162,243`, the
  `localStorage` `'initial_template'` round trip
- `services/projects/handlers/project-create.handler.ts:37,41,53` — clone +
  existence check, no value reads
- `components/projects/project-edit/project-edit.component.ts:141` — no value
  reads
- `components/projects/project-edit/sequence/sequence.component.ts` — **five**
  sites: `:687, :716, :850, :909, :1571`

**A third value-reading site nobody has listed** is `:1571`, inside
`getTemplateOutputStructure(cueType)` (`:1570-1600+`): it walks the example
script's contents, finds the `AudioCue`/`VideoCue`, and deep-clones its **first
`AudioCueOutput` / `VideoCueOutput`** as the structure for a new cue's outputs.

This one is materially harder than the other two. `master_vol` is a scalar with
a schema default (`100`, against the component's drifted `|| 20` fallback);
`dmx_channels`'s descriptor default is `None` (T057), which 008 already flagged
as a behaviour choice for 009. But an *entire nested output object* —
`output_geometry`, `canvas_region`, the mapping shape — is not a field default
at all. 009 must decide whether the descriptor emits a constructible empty
instance per type, or whether this component keeps a hand-authored seed.

**The media-duration display site is concrete** and worth naming, since §8
mentions it only in the abstract:
`components/projects/project-show/sequence/sequence.component.ts:194` —
`return cueData?.Media?.duration || '-';`. Post-008 that is an object, so the
cell renders `[object Object]`. (E19 said this file has "none" — true of
template calls, not of duration reads.) The fade path already unwraps
correctly at `project-edit/sequence/sequence.component.ts:506,980`, which is
the pattern to copy.

---

## C6 — the Avahi TXT-record vocabulary has two owners, and §8 assigns one

§8 hands 009 `cuems-common`'s four files. But the retired vocabulary lives in
**both** repositories, and the TXT key is the wire between two daemons:

**`cuems-common`** (27 `node_type` occurrences total):
`etc/avahi/services/cuems.service:6,13`,
`usr/share/cuems/cuems.service.{firstrun,master,slave}:6,13` — the last two
carry the retired word in the **filename**, so `debian/install` and anything
resolving a template by name moves too.

**`cuems-nodeconf`** (30 occurrences — *more* than common):
its own copies at repo root, `cuems.service.{firstrun,master,slave}:12,19`;
the producer `CuemsSettings.py:27`
(`settings_dict['properties'] = {'node_type': 'slave'}`); the consumer
`CuemsAvahiListener.py:96-155` (two blocks, `add_service` and
`update_service`, both keying on `b'node_type'` through
`_AVAHI_NODE_TYPE_TO_ROLE`); and the installer
`CuemsNodeConf._install_master_service_template` + the inline slave-template
copy in `set_node_role`.

`AvahiTool.py:12` and `CuemsAvahiListener.py:19-24` both carry comments
deferring this "to feature 008" — the pre-renumbering name. 008 was
cuems-utils-only, so the work is currently assigned to a feature that has
closed.

**Decision (D33, 2026-09-03):** both halves land **inside 009**, as one
coordinated cutover. The TXT key cannot be half-renamed: a listener reading
`node_role` against a publisher writing `node_type` discovers nothing, and
discovery failure is how a cluster loses its topology. This is the largest
single sub-scope 009 acquires from this audit; the plan sequences it as one
unit (publisher, template files, filenames, `debian/install`, listener,
`_AVAHI_NODE_TYPE_TO_ROLE`'s removal) rather than per-repo.

---

## C7 — the release gate has exactly one mechanically enforced edge

Measured 2026-09-03:

| Repo | `pyproject.toml` | `debian/control` |
|---|---|---|
| `cuems-engine` | `cuemsutils = ">=0.1.0rc10"` | `cuems-utils (>= 0.1.0rc4)` |
| `cuems-editor` | `cuemsutils>=0.1.0rc10` | — |
| `cuems-nodeconf` | `cuemsutils = ">=0.1.0rc15"` | `cuems-utils (>= 0.1.0rc5)` |
| `cuems-wsclient` | `cuemsutils = ">=0.1.0rc5"` (optional) | `cuems-utils (>= 0.1.0rc5)` |
| `cuems-common` | — | `cuems-utils (>= 0.1.0rc15)`, `Breaks: cuems-nodeconf (<< 0.1.0-8)` |

Only `cuems-common` enforces anything, and only against `cuems-nodeconf`
(007's FR-030d / T054a). Three observations:

1. **A `>=` floor cannot express the gate.** The gate says "an unmigrated
   consumer must refuse a library that has moved past it" — that is an upper
   bound or a `Breaks`, and no consumer declares one. Installing
   `cuems-utils` rc16 beside an editor pinned `>=0.1.0rc10` succeeds, and the
   editor then fails at import (C2).
2. **`cuems-engine`'s two floors disagree** — `rc4` in `debian/control`
   against `rc10` in `pyproject.toml`. The packaged floor is six release
   candidates behind the source one.
3. **007 moved the mechanical demonstration here** (T054b, its guide §13):
   no packaging sandbox existed to install an out-of-order combination and
   watch `dpkg` refuse it. 008 then added a second, larger breaking change to
   the same gate without adding an edge. 009 both *runs* that demonstration
   and *supplies the missing edges*.

---

## C8 — the frontend has no test coverage where 009 works hardest

Counted 2026-09-03: **112** `.ts` files, **5** `.spec.ts` files —
`app.component`, `components/design`, `components/ui/icon`,
`components/layout/app-footer`, `components/layout/app-header`.

None of the three files 009 rewrites has one:

| File | Lines | Spec? |
|---|---|---|
| `sequence.component.ts` (project-edit) | 1662 | no |
| `projects.service.ts` | 640 | no |
| `settings.component.ts` | 140 | no |

§8's constitution check says *"II: each consumer PR carries its own green
suite"*. In `cuems-frontend` that sentence currently costs nothing: the suite
is green because it tests a footer.

**Decision (D35, 2026-09-03):** the frontend port is preceded by
**characterization tests**, mirroring exactly what 008 did for `cuems-nodeconf`'s
row 5 (E23) — pin today's behaviour *before* moving it, so equivalence is
measured rather than asserted. Minimum surface: `settings.component`'s
adopt/unadopt emit-and-subscribe cycle, the five `projectTemplate()` reads in
`sequence.component` (including `getTemplateOutputStructure`, C5), and
`projects.service`'s `initial_mappings`/`initial_template` handling including
the `localStorage` round trip. These are also the tests that prove E25's
domain untangling preserved behaviour.

---

## C9 — three stale documents that are 009's own inputs

1. **`cuems-utils/CLAUDE.md`** states the cuems-common node-identity field
   contract is *"not yet updated for the rename"*. **False as of 2026-08-24**:
   `cuems-common`'s local `007-node-model-migration` branch carries four
   commits — schema mirror + shipped-map conversion (`9fc738e`), the conversion
   script wired into `postinst` with three tools updated (`f4a8b3c`), versioned
   package dependencies (`6a9ec7f`), and the documentation pass (`78b89ad`).
   `etc/cuems/network_map.xml:9` already reads `<node_role>controller</node_role>`;
   `debian/postinst:35-58` runs `cuems-migrate-network-map` over both the live
   file and its `.dpkg-new` sibling; `tests/test_network_map_conversion.py`
   covers it. Unmerged and unreleased — but "landed on a branch", not
   "not started".
2. **`cuems-common/CLAUDE.md:88`** says `CONTROLLER_NETWORK_FLAG` and the enum
   constants are *"migrated in feature 008"*. The 2026-08-25 renumbering makes
   that **009**.
3. **`cuems-nodeconf/cuemsnodeconf/AvahiTool.py:12`** and
   **`CuemsAvahiListener.py:19-24`** defer the TXT-record change *"to feature
   008"* — see C6; now 009's, by D33.

All three are read by whoever executes 009. Correcting them is part of the
feature, not housekeeping after it.

---

## C10 — work landed after 008 closed, in no plan

Three commits on `feat/xml-refactor` post-date 008's close-out (`f740711`) and
carry consumer impact §8 predates:

- **`7c5896c`** — `Timeoutloop` relocated to `cuemsutils.tools.TimeoutLoop.TimeoutLoop`,
  with a `deprecated_alias` shim at `cuemsutils.timeoutloop`.
  `cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:26` still imports the old
  path and uses it at `:309, :617, :629`. Recorded as an open follow-up in
  `specs/planning/tools-external-consumers-and-timeoutloop-migration.md`
  (Track 2, item 5) — the only remaining open item in that document.
- **`573daa0`** — `xml/_deprecation.py` promoted to `cuemsutils/_deprecation.py`.
  No consumer imports it directly (checked); recorded so the shim's own import
  path is not mistaken for stable.
- **`841ee3e`** — `StringSanitizer.sanitize_text_size`/`sanitize_name`
  off-by-one fixed (`[0:254]`/`[0:65534]` → the documented 255/65535).
  `cuems-editor` uses `StringSanitizer` on the user-string-to-filesystem-path
  route at three sites; names one character longer now survive sanitizing.

---

## C11 — a third document-distribution surface for the conversion

§8 plans 008's duration conversion as two paths: `postinst` (batch, via
`cuems-convert-documents`) and convert-on-load. There is a third, and it is
node-to-node rather than package-to-disk: **`cuems-engine` deploys project
files across the cluster.** `tools/CuemsDeploy.py:329` and `:649` build
`/projects/<project>/script.xml` into the rsync manifest;
`NodeEngine.py:730,805` receive them.

So a controller whose library has been converted to `script` version 2 pushes
version-2 documents to every node it deploys to. A node running an older
`cuemsutils` cannot read them — and unlike the postinst case, this happens at
**show-load time**, not upgrade time. The reverse order (nodes upgraded first)
is safe, because ITEM E converts version-1 documents in memory.

This is a third ordering constraint alongside 007's postinst-vs-service-restart
question, and it argues the same way the cluster-upgrades-as-a-unit rule does
(007's guide §7): the deploy path gives a mixed-version cluster a way to fail
that no package manager mediates.

**Minor, same family:** `repair_durations.py:87` guards
`duration, in_time, out_time, offset, ...` with
`TIMECODE_SHAPE.match(value)` against string values. Post-008 those are dicts
on the wire, so `match` is never reached with a string and the guard silently
stops catching anything — an FR-030a-ii instance *inside* the tool 009 is
migrating, which is why E21 said this file sits at the intersection of every
008 decision.

---

## C12 — the zero-`node_type` criterion cannot pass as written

§8's exit criterion is "zero occurrences of `node_type` or the `NodeType.`
prefix remain anywhere in the ecosystem, **counted rather than reviewed**". Run
that count against `cuems-utils` itself, 2026-09-03:

```
$ grep -rn 'node_type\|NodeType\.' src/ | wc -l
16
```

All sixteen are correct code, and deleting any of them would be a regression:

| Site | What it is |
|---|---|
| `errors.py:106-110` | the `"NodeType.master"`/`"NodeType.slave"`/`"NodeType.firstrun"` → `controller`/`node`/`firstrun` mapping |
| `errors.py:120-135` | `network_map_node_type_message` — the diagnostic that tells an operator their document still carries `<node_type>`, instead of failing with a bare schema error |
| `tools/ConfigBase.py:6, :46, :76` | wiring that diagnostic into the config load path |
| `config/network_map.py:26, :32` | prose recording the rename and the string `cuems-engine` used to compare against |
| `xml/schemas/network_map.xsd:55` | the schema comment recording feature 007's change |

Code whose **purpose** is detecting or converting the retired spelling has to
contain it. `cuems-common`'s `cuems-migrate-network-map` and its three tests are
exempt on the same grounds — a converter that cannot name what it converts is
not a converter.

So the criterion as written fails against a repository that is fully migrated,
and the failure mode is worse than a false alarm: "counted rather than reviewed"
is a deliberate instruction *not* to exercise judgement, so the natural response
is to delete a working migration diagnostic to make a number reach zero.

**Fix, applied to Part 4 §8:** the count keeps its "counted, not reviewed"
discipline and gains an **enumerated** exempt set — detection and conversion
code, listed site by site rather than described by category. Everything outside
that list still counts.

## The runnable prompts derived from this document

[`009-consumer-prompts/`](009-consumer-prompts/README.md) — one self-contained
spec-kit flow per repository, each starting from that repository's actual state
(branch, spec-kit presence, constitution, test runner) and branching to
`feat/xml-refactor`. This document is their evidence; Part 4 §8 is their shape.

Two things surfaced while writing them that belong with the findings above:

- **C1 is worse than "a filter that selects nothing".** `slave_avahi_names`'s
  only caller is `bridge.py`'s `_run_shutdown`. With an empty list, step 6 SSHes
  nowhere, step 7's reachability poll is skipped outright (`if resolved:`), and
  step 8 arms the Shelly relay that cuts mains power — so every coordinated
  shutdown now kills power to nodes that were never asked to shut down, logging
  `"0 nodes to power off: (none)"` at INFO. `cuems-wsclient` also has **no
  `tests/` directory** while its `pyproject.toml` fully configures pytest, so
  nothing could have caught it.
- **Five of the seven repositories have no spec-kit and no constitution**
  (`cuems-editor`, `cuems-common`, `cuems-nodeconf`, `cuems-frontend`,
  `cuems-wsclient`). Only `cuems-utils` and `cuems-engine` are initialized. Each
  of the five gets spec-kit added on its first run plus a `/speckit.constitution`
  prompt grounded in what that repository actually is — which also means feature
  009 is the first time most of this ecosystem states its own engineering rules.

## Decisions settled by this pass

Added to Part 4 §2's SETTLED block:

- **C12/D36** — the ecosystem-wide `node_type` count gains an enumerated exempt set for
  detection and conversion code (this document's C12). Without it the criterion fails
  against a fully migrated repository and instructs the reader not to notice.
- **D32** — `cuems-wsclient` is in 009's scope, in full: its private
  `ElementTree` network-map reader is replaced by the library's public path,
  not merely re-spelled to `node_role`. (C1)
- **D33** — the Avahi TXT-record vocabulary (`node_type=master|slave|firstrun`)
  is renamed in **both** `cuems-common` and `cuems-nodeconf` inside 009, as one
  coordinated cutover including the two template **filenames** and
  `debian/install`. It cannot be half-renamed. (C6)
- **D34** — `SchemaDescriptor` is exposed to consumers **through
  `ConfigManager`**, covering all six schemas including `script`; and
  `cuems-nodeconf`'s existing `cuemsutils.xml.mapper`/`cuemsutils.xml.settings`
  imports move onto public equivalents in the same feature. (C4)
- **D35** — the `cuems-frontend` port is preceded by characterization tests of
  the three files it rewrites, mirroring 008's E23 treatment of
  `cuems-nodeconf` row 5. (C8)

## What this document does not settle

- **Whether the descriptor emits a constructible empty instance per complex
  type**, which `getTemplateOutputStructure` (C5) needs and field-level
  defaults do not provide. A 009 `/speckit.plan` question.
- **Where the batch conversion runs** — postinst, first-boot, or an operator
  command — given C11's deploy path makes "convert on the controller" a
  cluster-wide event rather than a local one. 008 left this open deliberately.
- **Whether `dev/` fixtures count** toward "zero `node_type` occurrences,
  counted": `cuems-engine/dev/network_map.xml`,
  `dev/test_xml_files/network_map.xml`, `dev/CuemsEngine_old.py` and
  `cuems-nodeconf/test_run_nodeconfig.py` carry the old spelling in
  non-shipped code. 007 counted `src/` only; 009's exit criterion says
  "ecosystem-wide" without saying whether that reaches `dev/`.
