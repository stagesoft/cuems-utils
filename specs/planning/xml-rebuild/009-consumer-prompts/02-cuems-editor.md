# Feature 009 — `cuems-editor`: it does not start today

**Status:** ready to run — **gated on [00-cuems-utils](00-cuems-utils.md)**
**Date:** 2026-09-03
**Repository:** `/disk/Projects/StageLab/cuems-editor`
**Run order:** 02 of 06. See the [index](README.md).

The largest Python-side migration in feature 009, and the only repository whose
**first** task is making the process start at all.

---

## 0. State of this repository, measured 2026-09-03

| | |
|---|---|
| Current branch | `rc1` @ `d9e0a39` (2026-08-03), clean |
| Base for `feat/xml-refactor` | **`rc1`** — the live release line, not `main` |
| Spec-kit | **absent** — added on first run (§1) |
| Constitution | **absent** — written on first run (§2) |
| Existing features | none → this becomes **`001-cuems-utils-migration`** |
| Tests | `hatch test` (hatchling backend, `testpaths = ["tests"]`) — **5 test files** |
| `cuemsutils` pin | `pyproject.toml` `cuemsutils>=0.1.0rc10`; no `debian/control` entry |
| **Runs against current `cuemsutils`?** | **NO — `ImportError` at import** (C2) |

**`CuemsWsServer.py:24` is `from cuemsutils.create_script import create_script,
new_uuid`, and 008 deleted that module with no deprecation shim.** Unlike the six
entry points 006 retired — which all still resolve and warn at `0.1.0rc15` — this
one simply is not there. The editor process does not start, so no call site is
reached and "the suite is green" says nothing until it does.

---

## 1. Branch and bootstrap

```bash
cd /disk/Projects/StageLab/cuems-editor
git checkout rc1 && git pull --ff-only        # if a remote is configured
git checkout -b feat/xml-refactor

# spec-kit is not installed in this repository; add it on this first run
specify init --here --integration claude --script sh --force
```

That matches how `cuems-utils` was initialized (spec-kit `0.5.1.dev0`, sequential
branch numbering) so the repositories stay comparable. Commit the scaffold as its
own commit before `/speckit.constitution` — GPG-signed, per the standing rules.

Spec-kit's sequential branch numbering will want its own branch. **Stay on
`feat/xml-refactor`**; let it name `specs/001-cuems-utils-migration/` only.

---

## 2. Constitution — write one, this repository has none

```
/speckit.constitution

Establish the constitution for cuems-editor, grounded in what this repository actually is
rather than in a generic template. Read CLAUDE.md first; it is accurate and current.

WHAT THIS REPOSITORY IS: WebSocket middleware for multi-user project editing and media
management, sitting between the browser frontend (cuems-frontend) and the engine
(cuems-engine). Python 3.11+, PyPI name cuemseditor, systemd service cuems-editor.service
on the controller. Frontend -> Editor is WebSocket :9092 carrying JSON
{"action": ..., "value": ...}; Editor -> Engine is a Unix IPC socket /tmp/editor.ipc over
NNG. Main classes: CuemsWsServer (asyncio WS server, session multiplexer, command router),
CuemsWsUser (per-connection session), CuemsProjectManager (owns the DB managers),
CuemsDBProject (project CRUD, XML script I/O, filesystem management). The project store is
/opt/cuems_library/, resolved from settings.xml's library_path.

PRINCIPLES THE CODE ALREADY IMPLIES — derive from these, do not invent unrelated ones:
- It is a WIRE-CONTRACT repository. Its output is consumed verbatim by an Angular UI that
  this repository does not control and cannot deploy in lockstep with. Payload shape is a
  contract, not an implementation detail, and a change to it is a coordinated multi-repo
  event. Make this a principle, because the single largest risk in this codebase is a
  payload change nobody noticed.
- It is MULTI-USER and stateful per session. CuemsWsServer multiplexes sessions and routes
  commands; concurrency and per-session isolation are correctness concerns, not performance
  ones.
- It OWNS USER DATA on disk. Project XML and the media library are the customer's work.
  Destructive operations need a recovery story, and "the parser accepted it" is not one.
- It has FIVE test files against a codebase of this size. State the testing expectation
  you actually intend to hold, and make it honest: a gate this repository will meet, with
  a stated direction of travel, beats an aspirational rule that gets waived in the first PR.
- Its dependency on cuemsutils is a CONSUMER relationship with a library that versions
  deliberately. Reaching into that library's internal modules is a violation to name now,
  before the temptation arrives (cuemsutils.xml declares __all__ == [] for this reason).

Include a performance principle only if you can state a measurable budget this repository
can actually check — project load and WS round-trip are the candidates. Do not copy
cuems-utils' Principle IV wording; its budgets are per-test and this repository's are not.

Do NOT weaken any rule to accommodate the migration that follows. If the migration
violates the constitution you write, that is information, and the spec records the
exception explicitly.
```

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything. They live in the SIBLING checkout
/disk/Projects/StageLab/cuems-utils, not in this repository:
  .../cuems-utils/specs/007-node-model-migration/migration-guide.md      §6 IS THIS REPO'S INVENTORY
  .../cuems-utils/specs/008-rebuild-extension/migration-guide.md         what 008 handed here
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md  the editor<->UI payload contract
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md    C2, C3, C4, C5 are this repo's
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md   §2 = the FULL decision list

SETTLED — the decisions that bind THIS repository. Do not reopen. Anything
outside this subset: read §2 of the prompts file above.
  D12 public surface returns objects, never raw dicts
  D15 public objects are CuemsScript (show) and ConfigManager/ConfigBase (config)
  D17/D18b Media.duration is cms:CTimecodeType. <duration>TC</duration> is now
      <duration><CTimecode>TC</CTimecode></duration>, and {"CTimecode": TC} on the JSON wire.
  D19/D21 load() runs T1 AND T2. Three outcomes: OLD converts in memory (file untouched);
      CURRENT-but-repairable loads with the field repaired and the repair carried in a
      structured report; UNREPAIRABLE raises. A document NEWER than the library raises.
      CuemsScript.load_with_report(path) -> (script, LoadReport) is the entry point that
      returns the report; load() keeps its signature and discards it.
  D21b SAVING A REPAIRED DOCUMENT OVERWRITES THE CORRUPT ORIGINAL WITH NO BACKUP. What makes
      that safe is that a human saw the report first. cuemsutils cannot enforce the ordering
      -- load_with_report and save() are two independent calls -- so the obligation is THIS
      repository's, procedurally. See 008's migration guide, FR-053a.
  D25 template/config generation moves onto a schema-derived descriptor covering all six
      schemas, emitting field name, XSD type, cardinality, xs:enumeration values AND
      model-layer defaults
  D26 initial_template-as-a-concrete-instance is retired. The config domain is a MIGRATION,
      not a greenfield build: a network_map editing UI exists and is in daily use.
  D34 the descriptor reaches this repository THROUGH ConfigManager (feature 009 flow 00).
      Do NOT import cuemsutils.xml.descriptor directly; that package declares __all__ == [].
  D27 nothing in the ecosystem releases until every 009 flow lands
  Q14 -> (i) cuemsutils.xml is internal machinery

HARD CONSTRAINT (Part 2d), AS AMENDED BY 006 AND 008 (C3) — this is the one most likely to
be got wrong, because the pre-2026-09-03 wording said something stronger:
  The project_load payload is transmitted verbatim to the Angular UI, so it stays
  byte-identical EXCEPT for exactly two already-landed, deliberate changes:
    (a) schemaLocation is ABSENT -- to_wire() drops it (006, xml/__init__.py's _READ_NOTE);
    (b) Media.duration is {"CTimecode": "HH:MM:SS.mmm"}, not a bare string (008).
  Everything else -- every other key, the ordering, and the STRING boolean form -- is
  unchanged. The UI reads booleans as
  `cueData.enabled === true || cueData.enabled === 'True'` and writes back the STRING form.
  doc_version is NOT a third change: it is excluded from every wire projection and the
  frontend never sees it.
  Do NOT restate this as unconditional byte-equality. That was true until 008 landed.

MEASURED STARTING STATE — verified against live files 2026-09-03, not transcribed:
  src/cuemseditor/CuemsWsServer.py:24  from cuemsutils.create_script import create_script,
      new_uuid   <- MODULE DELETED BY 008. ImportError. The process does not start.
  src/cuemseditor/CuemsWsServer.py:84   self.initital_template = create_script()  (sic)
  src/cuemseditor/CuemsWsServer.py:501-503  the initial_template payload
  src/cuemseditor/CuemsWsServer.py:23   from cuemsutils.xml import NetworkMap  <- DEPRECATED
  src/cuemseditor/CuemsWsServer.py:384-431  merge_nodes; :425 basic_fields list naming
      'node_type'; :439 reload_network_map_nodes; :470 NetworkMap.get_nodes_by_adoption
      (deprecated AND mutating); :417 merges network_map node status INTO mappings_dict;
      :509-511 serves that as initial_mappings  <- E25's DOMAIN ENTANGLEMENT
  src/cuemseditor/CuemsDBProject.py:356,489,571,808   CuemsParser(data).parse()  x4
  src/cuemseditor/CuemsDBProject.py:883  XmlReaderWriter(...)  (save_xml)
  src/cuemseditor/CuemsDBProject.py:895  XmlReaderWriter(...)  (load_xml)
  src/cuemseditor/CuemsDBProject.py:367  _fix_media_durations
  src/cuemseditor/CuemsDBProject.py:387  _clean_dangling_targets
  src/cuemseditor/CuemsDBProject.py:417  _nullify_dangling_refs
      ^ all three are RAW DICT MUTATION on the JSON payload BEFORE parsing
  src/cuemseditor/repair_durations.py:39  CuemsParser   :40  XmlReaderWriter   :230 parse
  src/cuemseditor/repair_durations.py:43  TIMECODE_SHAPE = r'^\d\d:\d\d:\d\d\.\d\d\d$'
  src/cuemseditor/repair_durations.py:87-89  that regex matched against 'duration',
      'in_time', 'out_time', 'offset' VALUES — all dicts on the wire now, so the guard
      silently stops matching. FR-030a-ii, inside the tool this feature migrates.
  pyproject.toml:27  "cuemsutils>=0.1.0rc10"  <- a lower bound; cannot express the gate

CALLERS THAT KEEP RESOLVING BUT BECOME WRONG (007 FR-030a-ii) are the dangerous class:
nothing fails, the suite stays green, the answer is silently wrong. repair_durations.py:87
and the :425 basic_fields drop are both in it. Search for them; do not wait for red.

DO NOT re-implement or re-test the node model here (007 FR-030a-i).
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Migrate cuems-editor onto cuems-utils' post-008 public API, and give the config domain and
the repair report the WS surface they need.

TASK ZERO, BEFORE ANYTHING ELSE: make the process start. CuemsWsServer.py:24 imports
create_script and new_uuid from a module 008 deleted, so this repository currently fails at
import against its own declared dependency. Re-source new_uuid from cuemsutils.helpers
(where this repository already imports it at four other sites). create_script's replacement
is the descriptor work below — but do not let the template decision block the import fix;
they are separable and only one of them is blocking every other task in this spec.

WHAT MUST BE TRUE WHEN DONE:
- All FIVE CuemsParser call sites are gone: four in CuemsDBProject (update:356, new:489,
  duplicate:571, update_projects_existed_media:808) and the fifth in repair_durations.py:230.
  CuemsParser is a deprecated alias for CuemsScript.from_json.
- load_xml/save_xml (CuemsDBProject.py:883/:895) use CuemsScript.load/save, and DBProject's
  load path returns script.to_wire(). The payload obeys the AMENDED hard constraint above:
  two enumerated deltas, nothing else moved. Prove that with a byte-comparison against a
  captured pre-migration payload, not by inspection.
- The raw-dict pre-parse fixups become sanctioned pre-validation steps or real object-level
  operations. _fix_media_durations (:367), _clean_dangling_targets (:387) and
  _nullify_dangling_refs (:417) currently poke a dict that is about to reach a now-strict
  parser. CHECK THEM AGAINST 008's REPAIR-AND-NOTIFY PATH FIRST: some of what they do —
  dangling-target nullification, duration repair — is the library's job now, and
  duplicating it in the editor is exactly how the two drift apart. What survives is what
  the library does NOT do.
- repair_durations.py is handled on its own terms, and it needs the most care of anything
  here. It exists to LOAD DELIBERATELY-CORRUPT DOCUMENTS — its whole purpose is repairing
  durations a historical get_duration bug stored short. Move it off CuemsParser and
  XmlReaderWriter; drop its private TIMECODE_SHAPE regex for the library's canonical form;
  and FOLD ITS PASS B into cuemsutils' cuems-convert-documents tool rather than maintaining
  a second <duration> rewriter. Pass A (ffprobe + DB) stays editor-local — that half is
  genuinely this repository's domain. VERIFY, do not assume, that it can still read the
  corrupt documents it exists to repair; 008's repair-and-notify contract is what makes
  that possible, and this is the test that proves the contract holds.
- 008's repair report reaches the user. load_with_report returns a structured LoadReport;
  this repository forwards it as a WS message and cuems-frontend renders it. A repair that
  happens silently is the exact outcome D21's three-outcome design exists to prevent, and
  cuemsutils deliberately cannot do this half — it has no UI channel and must not gain one.
- The save-after-repair ordering is honoured (D21b). Saving a repaired script overwrites
  the corrupt original with no backup. Wherever this repository calls load_with_report and
  later calls save() on the result, the report MUST have been surfaced first. cuemsutils
  cannot enforce this; state how this repository does.
- The node reads follow the rename and the retyping. basic_fields at CuemsWsServer.py:425
  names 'node_type' — a key the converted document no longer has, so the merge silently
  drops the field. It becomes 'node_role', and online/adopted are bool now, not the strings
  "True"/"False". The deprecated NetworkMap import at :23 goes, and :470's mutating
  get_nodes_by_adoption becomes partition_by_adoption.
- New WS message types serve the schema descriptor and accept config-domain saves. Model
  them on the initial_mappings (serve) + nodelist_modify (accept a mutation) pair, which is
  a config domain that ALREADY has both halves — not on initial_template, which is
  serve-only. Reach the descriptor through ConfigManager (D34), never through
  cuemsutils.xml.descriptor.
- The network_map / project_mappings wire entanglement is untangled. reload_network_map_nodes
  (:439) merges network_map node status INTO mappings_dict (:417) and serves it as
  initial_mappings (:509-511), so a network_map edit reaches the UI inside a
  project_mappings payload. Untangling it is a SIMULTANEOUS behaviour change for
  settings.component, audio-mixer and video-mixer in cuems-frontend — coordinate with flow
  05, and do not land the untangling before the UI that consumes it.
- The cuemsutils pin is bounded, not just floored (C7). >=0.1.0rc10 cannot express "refuse
  a library that moved past me", which is what the release gate says.

DO NOT reach into cuemsutils.xml for any of this (Q14). If something needed is only
available there, that is flow 00's gap to close, not this repository's to work around.
```

---

## 5. Clarify

```
/speckit.clarify
```

Two questions worth forcing: **what survives of the three raw-dict fixups** once
008's repair path is subtracted (the answer decides how much of `CuemsDBProject`
changes), and **whether the descriptor is served per-connection or cached** —
which pairs with the same question in flow 00.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Per-file scope:
- CuemsWsServer.py — :24 import (TASK ZERO), :84 + :501-503 template, :23 NetworkMap
  import, :425 basic_fields, :439/:470 reload_network_map_nodes, :417 + :509-511 the
  entanglement, plus the new descriptor/config-save/repair-report message types.
- CuemsDBProject.py — :356/:489/:571/:808 parser sites, :883/:895 XmlReaderWriter,
  :367/:387/:417 fixups.
- repair_durations.py — :39/:40 imports, :43 + :87-89 regex, :230 parse, Pass B folded out.
- pyproject.toml — bounded cuemsutils dependency.

Sequencing: gated on flow 00 (the descriptor's public path) for the WS descriptor work
ONLY. Task zero and the parser migration do not wait for it. Flow 05 (cuems-frontend) is
gated on this one's WS message types; the entanglement untangling lands with 05, not before.

Constitution check, against the constitution written in §2:
- The wire-contract principle is the one this feature stresses hardest. The byte-comparison
  against a captured pre-migration payload is its gate.
- The user-data principle governs repair_durations.py and D21b: this repository now holds
  the only thing standing between a repaired-in-memory document and an overwritten corrupt
  original.
- Testing: this repository has five test files. Whatever gate the constitution states, the
  payload comparison and the repair_durations round trip are non-negotiable members of it.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Migration readiness: the process STARTS (task zero) — everything else in
this checklist is unverifiable until it does; all FIVE CuemsParser sites gone; the payload
byte-compared against a captured pre-migration capture and differing in exactly the two
enumerated deltas, no more; the raw-dict fixups' surviving form proven to still catch what
they used to (dangling targets, bad durations) WITHOUT duplicating repairs the library now
performs; repair_durations.py proven able to still read the corrupt documents it exists to
repair, with Pass B folded into the library's conversion tool rather than kept; the repair
report reaching a WS message; the save-after-repair ordering stated and honoured; the
node_role rename and the bool retyping at :425 with a test that fails against the old
value; the descriptor reached through ConfigManager and never through cuemsutils.xml; the
entanglement untangled in step with flow 05; and the cuemsutils pin upper-bounded.
```
```
/speckit.analyze
```
```
/speckit.implement
```

Then [Part 4 §9](../xml-rebuild-07-speckit-prompts.md)'s quality loop.
`/speckit.check-integration` matters more here than anywhere: five parser sites
and three fixups are exactly the shape of migration that ends up written
alongside the old code instead of replacing it.

---

## 8. Exit criteria

The editor starts against current `cuemsutils`; `hatch test` green; all five
`CuemsParser` sites gone; the `project_load` payload differs from its
pre-migration capture in exactly the two enumerated deltas; the fixups reduced to
what the library does not do, with proof they still catch what they used to;
`repair_durations.py` still reads corrupt documents and no longer rewrites
`<duration>` itself; the repair report reaches a WS message and the
save-after-repair ordering is honoured; `node_role`/bool retyping done with tests
that fail against the old values; descriptor served through `ConfigManager`; and
the pin bounded.

**Does not ship alone** (D27).
