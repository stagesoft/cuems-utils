# Feature 009 — `cuems-engine`: node-role readers, strict loads, dead handlers

**Status:** ready to run
**Date:** 2026-09-03
**Repository:** `/disk/Projects/StageLab/cuems-engine`
**Run order:** 01 of 06 — independent; may start immediately. See the
[index](README.md).

---

## 0. State of this repository, measured 2026-09-03

| | |
|---|---|
| Current branch | `rc_1` @ `fc8d2bb` (2026-08-14), clean |
| Base for `feat/xml-refactor` | **`rc_1`** — this is the live release line, not `main` |
| Spec-kit | **present** (`.specify/`, 14 skills incl. `speckit-git-*`) |
| Constitution | **present** — SOLID (I) and **TDD, NON-NEGOTIABLE** (II) |
| Existing features | `specs/004-*` … `specs/007-*` → this becomes **`008-cuems-utils-migration`** |
| Tests | `poetry run pytest` — 43 test files under `tests/`, `testpaths = ["tests"]` |
| `cuemsutils` pin | `pyproject.toml` `>=0.1.0rc10`; `debian/control` **`>= 0.1.0rc4`** — the two disagree |

**Its constitution makes TDD non-negotiable.** That is not a formality here: the
whole `FR-030a-ii` caller class (below) is *defined* as "a caller that keeps
working and returns the wrong answer", so the only thing that can prove one is
fixed is a test written to fail against the old value first. This repository's
own constitution already requires exactly that discipline — cite it rather than
re-arguing it.

---

## 1. Branch

```bash
cd /disk/Projects/StageLab/cuems-engine
git checkout rc_1 && git pull --ff-only   # if a remote is configured
git checkout -b feat/xml-refactor
```

Base on **`rc_1`**, not `main`: `rc_1` is where this repository's live work is,
and branching from `main` would silently drop it.

Spec-kit's sequential branch numbering will want its own branch. Stay on
`feat/xml-refactor`; let it name `specs/008-cuems-utils-migration/` only.

---

## 2. Constitution — check, do not amend

Read `.specify/memory/constitution.md`. Two clauses bind this work and neither
needs changing:

- **II (TDD, non-negotiable)** — every `FR-030a-ii` caller gets a red test
  against the old value before the fix. This is the rule that makes the silent
  class findable.
- **I (SOLID)** — relevant when `find_hosts`/`_controller_ip_from_map` move from
  poking dicts to consuming typed node objects; the change is an opportunity to
  stop conflating map access with host-list construction, not a licence to
  rewrite `BaseEngine`.

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything. They live in the SIBLING checkout
/disk/Projects/StageLab/cuems-utils, not in this repository:
  .../cuems-utils/specs/007-node-model-migration/migration-guide.md      §5 IS THIS REPO'S INVENTORY
  .../cuems-utils/specs/008-rebuild-extension/migration-guide.md         what 008 handed here
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md   C1-C11 (C7, C11 are this repo's)
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md  §2 = the FULL decision list

SETTLED — the decisions that bind THIS repository. Do not reopen. Anything
outside this subset: read §2 of the prompts file above.
  D11 the node model moved in from cuems-nodeconf; it lives in cuemsutils ONLY
  D12 public surface returns objects, never raw dicts
  D15 public objects are CuemsScript (show) and ConfigManager/ConfigBase (config)
  D17/D18b EVERY time-carrying element is cms:CTimecodeType and stores a CTimecode.
      Media.duration was promoted from a restricted string; <duration>TC</duration> is now
      <duration><CTimecode>TC</CTimecode></duration> in XML and {"CTimecode": TC} in JSON.
  D19/D21 load() now runs T1 AND T2. Three outcomes: an OLD document converts in memory
      (file untouched); a CURRENT but repairable one loads with the field repaired and the
      repair carried in a report; an UNREPAIRABLE one raises. A document NEWER than the
      library raises, distinguishably.
  D27 nothing in the ecosystem releases until every 009 flow lands
  Q14 -> (i) cuemsutils.xml is internal machinery; do not import from it

MEASURED STARTING STATE — verified against live files 2026-09-03, not transcribed:
  core/BaseEngine.py:17   from cuemsutils.xml import XmlReaderWriter   <- DEPRECATED PATH
  core/BaseEngine.py:33   CONTROLLER_NETWORK_FLAG = "NodeType.master"
  core/BaseEngine.py:410  node.get("node_type") == CONTROLLER_NETWORK_FLAG  (_controller_ip_from_map)
  core/BaseEngine.py:440  node.get("node_type") == CONTROLLER_NETWORK_FLAG  (find_hosts)
  core/BaseEngine.py:443  node.get("online") == "True"                 <- string compare, now bool
  core/BaseEngine.py:433  self.cm.network_map.get_nodes_by_adoption(network_dict)  <- deprecated, MUTATING
  core/BaseEngine.py:509-510  XmlReaderWriter(schema_name="script", ...).read_to_objects()  (read_script)
  ControllerEngine.py:249     NetworkMap.get_nodes_by_adoption(self.cm.network_map)
  ControllerEngine.py:1152-1168  _adopted_uuids_from_network_map — an INLINE WORKAROUND whose
      own comment says it avoids get_nodes_by_adoption because that method mutates the dict
  ControllerEngine.py:12      from cuemsutils.xml.Settings import NetworkMap  <- DEPRECATED PATH
  cues/ActionHandler.py:30, :516, :542, :784-785  _handle_fade_in/_handle_fade_out, their
      _ACTION_HANDLERS entries and SUPPORTED_CUE_ACTIONS members
  cues/loop_cue.py:112,:276  cues/run_cue.py:176,:430  cues/CueHandler.py:166
      CTimecode(cue.media.duration)  <- the getter now returns a CTimecode already
  tools/CuemsDeploy.py:329,:649  NodeEngine.py:730,:805  script.xml rsynced controller -> node
  dev/network_map.xml, dev/test_xml_files/network_map.xml, dev/CuemsEngine_old.py
      carry <node_type>NodeType.master</node_type> — NON-SHIPPED fixtures; see the
      count question in the spec prompt
  tests/test_core_baseengine_controller_ip.py:34,38,101  build {"node": {"node_type": ...}}
  pyproject.toml:41  cuemsutils = ">=0.1.0rc10"   debian/control:18  cuems-utils (>= 0.1.0rc4)

CALLERS THAT KEEP RESOLVING BUT BECOME WRONG (007 FR-030a-ii) are a distinct and more
dangerous class than callers that stop resolving: nothing fails, the suite stays green,
and the answer is silently wrong. BaseEngine.py:410/:440/:443 are all in it. Search for
them against 007's §5 inventory; do NOT wait for a red suite to surface them. This
repository's constitution (II, TDD non-negotiable) already requires the test-first
discipline that finds them.

DO NOT re-implement or re-test the node model here. It lives in cuemsutils exclusively
(007 FR-030a-i). A node-model test appearing in this repository is a regression, not
coverage.
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Migrate cuems-engine onto cuems-utils' post-008 public API: typed node objects, the
node_role vocabulary, CuemsScript.load, and the new duration wire.

WHAT MUST BE TRUE WHEN DONE:
- CONTROLLER_NETWORK_FLAG's three sites are on the role enum. The constant at
  BaseEngine.py:33 becomes NodeRole.controller (from cuemsutils.tools.NodeList), and the
  two comparisons at :410 and :440 compare against it. Each of the three gets a test that
  FAILS against the string "NodeType.master" — that failure is the only evidence the
  silent class is closed at that site.
- The string-typed reads follow the retyping. BaseEngine.py:443's
  node.get("online") == "True" becomes a bool test — 007's guide §5 found this one during
  verification, independently of the rename, and it is the same silent class.
- The mutating adoption call is gone. BaseEngine.py:433 and ControllerEngine.py:249 move
  to NetworkMap.partition_by_adoption, which returns bare node objects rather than
  {"node": ...} wrappers — so the unpacking at each call site changes shape, not just
  name. ControllerEngine.py:1152's _adopted_uuids_from_network_map exists ONLY because
  the old method mutated; it is deleted, not ported, and its own comment is the evidence
  that it was a workaround rather than a behaviour.
- read_script uses the public API. BaseEngine.py:509-510's XmlReaderWriter(...).
  read_to_objects() becomes CuemsScript.load — and with it, this repository inherits
  load()'s new failure modes (D19/D21). DECIDE, and state in the spec, what an
  unrepairable violation at engine startup should do: abort (today's effective behaviour,
  and defensible) or surface. Either is acceptable; leaving it undecided is not, because
  the caller currently catches SchemaError only and ValidationError is now reachable.
- The two deprecated import paths are gone: core/BaseEngine.py:17's
  `from cuemsutils.xml import XmlReaderWriter` and ControllerEngine.py:12's
  `from cuemsutils.xml.Settings import NetworkMap`. Both still resolve and warn at
  0.1.0rc15 and are removed in the next release, so this is a hard requirement, not
  hygiene.
- Media.duration's new type is handled at all five reader sites (loop_cue.py:112/:276,
  run_cue.py:176/:430, CueHandler.py:166). CTimecode(a_ctimecode) already round-trips, so
  these keep WORKING — which is exactly why they need attention rather than trust: the
  wrapping is now redundant and the sites should say what they mean.
- The dead fade handlers are deleted: _handle_fade_in (ActionHandler.py:516),
  _handle_fade_out (:542), their _ACTION_HANDLERS entries (:784-785) and their
  SUPPORTED_CUE_ACTIONS members (:30). No schema-valid document can carry fade_in/fade_out
  after 008 (its FR-029a remapped them to play/stop in the 1->2 conversion). Note that
  _handle_fade_out carries a recorded zombie-process defect — it bumps _go_generation
  without calling disarm() — which disappears with the handler rather than needing its own
  fix. Deleting them is 008's FR-053b, handed here by name.
- The packaging floors are reconciled and BOUNDED. pyproject.toml says >=0.1.0rc10 and
  debian/control says >= 0.1.0rc4: six release candidates apart, and BOTH are lower bounds,
  which cannot express the release gate. The gate says an unmigrated consumer must REFUSE a
  library that moved past it; supply that bound here (C7).
- Test fixtures follow. tests/test_core_baseengine_controller_ip.py:34/38/101 build node
  dicts with "node_type" keys; they are the tests that must fail first and then pass.

DECIDE EXPLICITLY, do not leave to the counter: whether the non-shipped dev/ fixtures
(dev/network_map.xml, dev/test_xml_files/network_map.xml, dev/CuemsEngine_old.py) count
toward "zero node_type occurrences ecosystem-wide". 007 counted src/ only. Either answer
is defensible; an uncounted third state is not.

RECORD, do not solve here: CuemsDeploy rsyncs /projects/<project>/script.xml from
controller to node (tools/CuemsDeploy.py:329,:649; NodeEngine.py:730,:805). A controller
whose library has been converted to script version 2 therefore pushes v2 documents to
every node it deploys to, and a node on an older cuemsutils fails at SHOW-LOAD time rather
than upgrade time — an ordering constraint no package manager mediates (C11). This
repository's job is to state the exposure precisely for the rollout plan; the rollout
decision belongs to 03-cuems-common's postinst work.
```

---

## 5. Clarify

```
/speckit.clarify
```

Force two questions if they do not surface: the **startup behaviour on an
unrepairable document** (above), and whether `find_hosts`' returned shape
changes when `partition_by_adoption` stops handing back `{"node": ...}`
wrappers — its consumers are the thing most likely to break silently.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Per-file scope:
- core/BaseEngine.py — :17 import, :33 constant, :410/:440/:443 comparisons, :433
  adoption call, :509-510 script load.
- ControllerEngine.py — :12 import, :249 adoption call, :1152-1168 workaround deleted.
- cues/ActionHandler.py — :30, :516, :542, :784-785 deleted.
- cues/loop_cue.py, cues/run_cue.py, cues/CueHandler.py — the five CTimecode(media.duration)
  sites.
- pyproject.toml + debian/control — reconciled, bounded floors.
- tests/test_core_baseengine_controller_ip.py — fixtures.
- dev/ fixtures — per the counting decision.

Sequencing: this repository is independent of the other five and can land whenever its own
suite is green. It does NOT release on its own (D27).

Constitution check:
- I (SOLID): partition_by_adoption's shape change touches find_hosts' construction of the
  host list. Take the opportunity to separate map access from host-list building; do not
  take it as licence to restructure BaseEngine.
- II (TDD, NON-NEGOTIABLE): every FR-030a-ii site gets a test that fails against the old
  value BEFORE the fix. A green suite is not evidence for this class — that is the whole
  reason the class has a name.
- IV: no regression in project-load time. Measure against 008's post-landing figure, not
  007's baseline: 008 added T1+T2 validation to that path deliberately, and charging this
  feature for that decision would misattribute the cost.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Migration readiness: every FR-030a-ii site (BaseEngine.py:410, :440,
:443) has a test that fails against the old value; both deprecated import paths gone;
_adopted_uuids_from_network_map deleted rather than ported; the two fade handlers, their
dispatch entries and their SUPPORTED_CUE_ACTIONS members gone, counted not reviewed;
the load()-failure decision recorded in the spec rather than left to the catch site; the
pyproject/debian floors reconciled AND upper-bounded; the dev/ counting question answered;
and the CuemsDeploy version-exposure written down for the rollout plan.
```
```
/speckit.analyze
```
```
/speckit.implement
```

Then [Part 4 §9](../xml-rebuild-07-speckit-prompts.md)'s quality loop.

---

## 8. Exit criteria

`poetry run pytest` green; zero `node_type` / `NodeType.` occurrences in `src/`
(and in `dev/` if the counting decision says so), counted rather than reviewed;
every `FR-030a-ii` site closed with a test that fails against the old value; both
deprecated import paths gone; the fade handlers and their dispatch entries
deleted; `CuemsScript.load` in the show path with its failure behaviour decided;
the packaging floors reconciled and bounded; and the `CuemsDeploy` exposure
recorded for 03's rollout plan.

**Does not ship alone** (D27).
