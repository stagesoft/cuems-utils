# Feature 010 — `cuems-frontend`: characterization first, then the port

**Status:** ready to run — **gated on [00](00-cuems-utils.md) and [02](02-cuems-editor.md)**
**Date:** 2026-09-03
**Repository:** `/disk/Projects/StageLab/cuems-frontend`
**Run order:** 05 of 06. See the [index](README.md).

The largest single port in feature 010, in the repository with the least test
coverage. That combination is why D35 puts characterization tests before
anything else.

---

## 0. State of this repository, measured 2026-09-03

| | |
|---|---|
| Current branch | `main` @ `c69dc1c` (2026-05-14), clean |
| Base for `feat/xml-refactor` | **`main`** |
| Spec-kit | **absent** — added on first run (§1) |
| Constitution | **absent** — written on first run (§2) |
| Existing features | none → this becomes **`001-schema-descriptor-migration`** |
| Stack | Angular 19.2, Tailwind 4.1, `osc-js`, `@ngx-translate`; package name `formitgo-tw` |
| Tests | `npm test` (`ng test`) — **5 `.spec.ts` files against 112 `.ts` files** |
| `cuemsutils` | none — this repository consumes the editor's WS payloads, not the library |

**The three files this feature rewrites have no tests:**

| File | Lines | Spec? |
|---|---|---|
| `src/app/components/projects/project-edit/sequence/sequence.component.ts` | 1662 | no |
| `src/app/services/projects/projects.service.ts` | 640 | no |
| `src/app/components/settings/settings.component.ts` | 140 | no |

The five specs that exist cover `app.component`, `design`, `ui/icon`,
`layout/app-footer` and `layout/app-header`. So a green suite here currently
evidences nothing about this feature's blast radius — which is the finding
(C8) behind D35.

---

## 1. Branch and bootstrap

```bash
cd /disk/Projects/StageLab/cuems-frontend
git checkout main && git pull --ff-only     # if a remote is configured
git checkout -b feat/xml-refactor

specify init --here --integration claude --script sh --force
```

Commit the scaffold as its own commit before `/speckit.constitution`.

Spec-kit's sequential branch numbering will want its own branch. Stay on
`feat/xml-refactor`; let it name `specs/001-schema-descriptor-migration/` only.

---

## 2. Constitution — write one, this repository has none

```
/speckit.constitution

Establish the constitution for cuems-frontend, grounded in what this repository actually is.
It has no CLAUDE.md; read README.md, package.json, and src/app/services/projects/
projects.service.ts before writing anything.

WHAT THIS REPOSITORY IS: the Angular 19 browser UI for CueMS, package name formitgo-tw.
Tailwind 4 for styling, @ngx-translate for i18n, osc-js on the wire alongside a WebSocket
connection to cuems-editor on :9092. It is the operator's entire view of the system: project
editing (the sequence editor), media management, audio/video mixers, and node adoption. It
holds no database and no files; every piece of state it shows arrives over the WS connection
or is cached in localStorage.

PRINCIPLES THE CODE ALREADY IMPLIES — derive from these, do not invent unrelated ones:
- IT IS A CONSUMER OF A CONTRACT IT DOES NOT OWN. Payload shape comes from cuems-editor,
  which comes from cuemsutils' schemas. This repository cannot change that contract; it can
  only track it. Defensive reads of payload fields are correctness, not paranoia — note that
  the existing code already reads booleans as `=== true || === 'True'` for exactly this
  reason.
- STATE ARRIVES ASYNCHRONOUSLY AND PARTIALLY. Signals hold nullable payloads; localStorage
  holds stale ones. A component that assumes a payload is present, complete, or fresh is
  the recurring bug shape here.
- IT IS THE ONLY PLACE A HUMAN SEES ANYTHING. When the backend repairs a corrupt document or
  refuses to load one, this repository is where that becomes visible or is lost. Silence is
  a failure mode with a user attached.
- COMPONENTS ARE LARGE AND UNDER-TESTED, and that is a stated position rather than an
  accident to leave unremarked: 5 spec files against 112 TypeScript files, with the three
  largest and most business-critical components untested. State the direction of travel and
  the gate that actually applies to NEW and CHANGED code, rather than a repository-wide rule
  that would be waived immediately.
- LOCALSTORAGE IS A CACHE, NEVER A SOURCE OF TRUTH. initial_template and initial_mappings are
  both cached there today; a cache that outlives a schema change is how a UI shows the wrong
  shape after an upgrade.

Include an accessibility or i18n principle only if this repository actually holds itself to
one — @ngx-translate is wired up, so i18n has a real claim; do not assert an a11y standard
nothing checks.

Do NOT weaken any rule to accommodate the port that follows. In particular: if the
constitution says changed code carries tests, the characterization work below is that rule
being honoured, not an exception to it.
```

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything. They live in the SIBLING checkout
/disk/Projects/StageLab/cuems-utils, not in this repository:
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md  the editor<->UI contract
  .../cuems-utils/specs/008-rebuild-extension/migration-guide.md   ITEM D's T081 = THIS REPO'S INVENTORY
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md    C3, C5, C8 are this repo's
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md   §2 = the FULL decision list

SETTLED — the decisions that bind THIS repository. Do not reopen. Anything
outside this subset: read §2 of the prompts file above.
  D25 template/config generation moves onto a schema-derived descriptor covering all six
      schemas, emitting per type: field name, XSD type, cardinality, restricted
      xs:enumeration values, AND model-layer defaults. Defaults are not optional --
      two of this repository's template call sites consume VALUES, not shape.
  D26 initial_template-as-a-concrete-instance is retired. Script domain is a MIGRATION of
      this repository's template call sites. Config domain is ALSO a MIGRATION, NOT a
      greenfield build -- a network_map editing UI exists and is IN DAILY USE
      (settings.component.ts, nodelist_modify adopt/unadopt), and project_mappings has read
      consumers (audio-mixer, video-mixer). Port the existing machinery onto dynamic-form
      entities WITH ITS LOGIC PRESERVED. Adopt/unadopt must keep working through the port.
  D35 this port is PRECEDED BY CHARACTERIZATION TESTS of the three files it rewrites --
      mirroring exactly what feature 008 did for cuems-nodeconf's network-map logic. Pin
      today's behaviour BEFORE moving it, so equivalence is measured rather than asserted.
  D17/D18b Media.duration is now {"CTimecode": "HH:MM:SS.mmm"} on the JSON wire, not a bare
      string. Fade durations already arrive wrapped and this repository already unwraps them.
  D21 a corrupt-but-current document is REPAIRED to a default and reported. The report
      reaches this repository as a WS message from cuems-editor, and rendering it is this
      repository's job. A silent repair is the exact outcome the three-outcome design exists
      to prevent.
  D27 nothing in the ecosystem releases until every 010 flow lands

THE WIRE CHANGES IN EXACTLY TWO WAYS (C3) — this is the whole payload delta, and the
pre-2026-09-03 planning wording said something stronger and wrong:
  (a) schemaLocation is ABSENT from the project_load payload;
  (b) Media.duration is {"CTimecode": "HH:MM:SS.mmm"} instead of a bare string.
Everything else -- every other key, the ordering, and the STRING boolean form -- is
unchanged. The `=== true || === 'True'` dual-read still holds and its simplification remains
OPTIONAL, a follow-up rather than a blocker. doc_version never reaches this repository.

MEASURED STARTING STATE — verified against live files 2026-09-03, not transcribed:
  TEMPLATE CONSUMERS — FOUR files, not two; the earlier count was low:
    services/projects/projects.service.ts:150   projectTemplate = signal<ProjectTemplate|null>
    services/projects/projects.service.ts:159,162,243   the localStorage 'initial_template'
        round trip;  :219 the response-type list;  :240-243 the intake;  :395, :420 reads
    services/projects/handlers/project-create.handler.ts:37,41,53   clone + existence check;
        DISCARDS the cloned cue examples for whole-project creation, keeping only the
        CuemsScript scaffold. No concrete value reads.
    components/projects/project-edit/project-edit.component.ts:141   no value reads
    components/projects/project-edit/sequence/sequence.component.ts:687, :716, :850, :909,
        :1571   FIVE sites
  THREE OF THEM READ CONCRETE VALUES, not two:
    sequence.component.ts:688   template...AudioCue?.master_vol || 20
        ^ the `|| 20` fallback ALREADY diverges from the schema's own default (100). The
          descriptor answer replaces the template walk AND silently fixes that drift.
    sequence.component.ts:726-727   walks contents, finds DmxCue, reads
        DmxScene.DmxUniverse.dmx_channels (unwrapping each {DmxChannel: {...}}) to seed the
        new cue's channel list. The descriptor's default here is None -- an empty starting
        list, not a channel to copy -- so this is a BEHAVIOUR CHOICE, not a mechanical
        substitution.
    sequence.component.ts:1570-1600   getTemplateOutputStructure(cueType) -- deep-clones the
        example AudioCue's first AudioCueOutput (or VideoCue's VideoCueOutput) as the
        structure for a new cue's outputs. LISTED BY NO EARLIER PASS. This one is NOT a
        field default at all: it needs a constructible instance of a whole nested complex
        type (output_geometry, canvas_region, the mapping shape).
  MEDIA DURATION DISPLAY:
    components/projects/project-show/sequence/sequence.component.ts:194
        return cueData?.Media?.duration || '-';     <- renders [object Object] post-008
    The fade path ALREADY unwraps correctly and is the pattern to copy:
        project-edit/sequence/sequence.component.ts:506  cueData.duration?.CTimecode
        project-edit/sequence/sequence.component.ts:980  { CTimecode: ... } on write
  CONFIG-DOMAIN UI — EXISTS AND IS IN DAILY USE:
    components/settings/settings.component.ts:35   subscribes to the nodelist_modify response
    components/settings/settings.component.ts:48, :56   reads projectsService.initialMappings()
        (.value.nodes and .value.new_nodes)
    components/settings/settings.component.ts:~122, :~133   emits
        {action:'nodelist_modify', modify_action:'ADD'|'REMOVE', value: uuid}
        ^ this is the far end of cuems-nodeconf's adopt/unadopt dispatch chain
    components/.../audio-mixer.component.ts:80  and  video-mixer.component.ts:94
        read the initial_mappings localStorage key
    NOTE: settings.component.ts is NAMED for the `settings` domain and EDITS network_map
    nodes. Do not let the new per-domain views inherit that naming.
  services/projects/projects.service.ts:120   schemaLocation: string;  — a REQUIRED interface
        property nothing reads. Delete it (C3).

THE DOMAINS ARE ENTANGLED ON THE WIRE (E25), and untangling them is a SIMULTANEOUS behaviour
change for settings.component, audio-mixer and video-mixer: cuems-editor's
reload_network_map_nodes merges network_map node status INTO mappings_dict and serves it as
initial_mappings, so a network_map edit reaches this UI inside a project_mappings payload.
Flow 02 untangles the editor side; this flow moves the three consumers. They land together.

THE WS PATTERN ALREADY EXISTS. Model the new per-domain messages on
initial_mappings (serve) + nodelist_modify (accept a mutation) -- a config domain that
already has BOTH halves -- not on initial_template, which is serve-only.
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Move cuems-frontend off cloning a concrete example script and onto the schema descriptor,
port the existing config-domain UI onto descriptor-driven forms with its logic preserved,
and render the repair report — with characterization tests written FIRST.

PHASE ZERO, BEFORE ANY PORT: characterization tests (D35). This repository has 5 spec files
across 112 TypeScript files, and none of them covers the three files this feature rewrites.
Pin today's behaviour first, so the port is MEASURED rather than asserted — this is exactly
what feature 008 did before moving cuems-nodeconf's network-map logic, and it is the reason
that swap has an acceptance criterion at all. Minimum surface:
  - settings.component.ts's adopt/unadopt cycle: the emit shape
    ({action:'nodelist_modify', modify_action, value}) and the response subscription.
  - the five projectTemplate() reads in sequence.component.ts, INCLUDING
    getTemplateOutputStructure — capture what each one produces from a representative
    template payload.
  - projects.service.ts's initial_template and initial_mappings handling, including the
    localStorage round trip and the nullable-payload paths.
These same tests are what prove the domain untangling preserved behaviour, so they are not
overhead ahead of the real work; they are the instrument the real work is measured with.

WHAT MUST BE TRUE WHEN DONE:
- The template call sites are on the descriptor. All four consuming files, with the three
  value-reading sites migrated onto descriptor DEFAULTS: master_vol at :688 (which also
  retires the `|| 20` fallback's drift from the schema's actual default of 100),
  dmx_channels at :726-727, and getTemplateOutputStructure at :1570-1600.
- getTemplateOutputStructure's answer is DECIDED, not defaulted into. The descriptor emits
  field-level defaults; this site needs a constructible instance of a whole nested complex
  type. Either the descriptor grows that capability (a cuems-utils decision, flow 00 recorded
  it as a gap rather than resolving it) or this component keeps an explicit hand-authored
  seed. Both are defensible; leaving it to fall through to `undefined` is not.
- dmx_channels' behaviour choice is made explicitly. The descriptor's default is None — an
  empty list, not a channel to copy — so preserving today's behaviour means keeping this
  component's own [{channel: 1, value: 0}] seed. Decide against the live UI.
- The media-duration display unwraps the wrapper.
  project-show/sequence/sequence.component.ts:194 renders [object Object] post-008; copy the
  pattern project-edit/sequence/sequence.component.ts:506 and :980 already use for fades.
- The config-domain UI is PORTED, NOT REBUILT. settings.component.ts (network_map
  adopt/unadopt), audio-mixer:80 and video-mixer:94 (initial_mappings) move onto a generic
  schema-form renderer WITH THEIR LOGIC PRESERVED. Adopt and unadopt must still work end to
  end through the port — the chain terminates in a real daemon and operators use it today.
  The characterization tests from phase zero are how that is proven.
- The remaining three config domains become editable through the same renderer.
  settings, project_settings and project_mappings have no editing UI today; the renderer that
  serves network_map serves them, driven by the descriptor's enumerations and defaults.
- The network_map-inside-initial_mappings entanglement is untangled, in step with flow 02.
  It is a simultaneous behaviour change for three components; do not land either half alone.
- The new per-domain views are NOT named after settings.component.ts's mistake. That file is
  named for the `settings` domain and edits network_map nodes; the new views are named for
  the domain they actually edit.
- The repair report is RENDERED. cuems-editor forwards 008's structured LoadReport as a WS
  message; this repository shows it to the operator. A repair that happens silently is the
  outcome the whole three-outcome design exists to prevent, and this repository is the only
  place a human sees anything.
- projects.service.ts:120's unread required schemaLocation property is deleted.

OPTIONAL, explicitly a follow-up and not a blocker: simplifying the
`=== true || === 'True'` dual-read. The string boolean form has NOT changed, so this is
cleanup, not migration.

CONSIDER, as a design option rather than a requirement: having cuems-editor serve PARTIAL
elements on demand — a script sub-object, a DB-backed duration query — rather than requiring
this repository to hold or compute full payloads client-side, if it simplifies the new
config and form entities. Weigh it in /speckit.plan; feature 008 deliberately did not fix it.
```

---

## 5. Clarify

```
/speckit.clarify
```

Force the two behaviour choices out into the open before planning:
`getTemplateOutputStructure`'s source of shape, and whether `dmx_channels` keeps
its hard-coded seed. Both change what the port produces, not merely how.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Per-file scope:
- src/app/services/projects/projects.service.ts — :120 schemaLocation, :150 signal,
  :159/:162/:243 localStorage, :219 response types, :395/:420 reads, plus the new
  descriptor/config-save/repair-report message handling.
- src/app/services/projects/handlers/project-create.handler.ts — :37/:41/:53.
- src/app/components/projects/project-edit/project-edit.component.ts:141.
- src/app/components/projects/project-edit/sequence/sequence.component.ts — :687, :716,
  :850, :909, :1571, and the value reads at :688, :726-727, :1570-1600.
- src/app/components/projects/project-show/sequence/sequence.component.ts:194.
- src/app/components/settings/settings.component.ts — the whole file, ported and renamed.
- audio-mixer.component.ts:80, video-mixer.component.ts:94.
- new: the generic schema-form renderer and the per-domain views.
- new: .spec.ts files for the three untested files (phase zero).

Sequencing: gated on flow 00 (the descriptor exists publicly) and flow 02 (the editor serves
it, and accepts config-domain saves). The characterization tests are gated on NOTHING and
should start immediately — they pin current behaviour, which requires none of the above.

Constitution check, against the constitution written in §2:
- The consumer-of-a-contract principle: the two enumerated wire deltas are the whole change;
  anything else that moves is a bug in flow 02, not something to accommodate here.
- The nothing-is-silent principle: rendering the repair report is that principle's whole
  point, not a feature request.
- The localStorage-is-a-cache principle: an initial_template cached before this upgrade is
  exactly the stale-shape scenario it warns about. Say what invalidates it.
- Testing: whatever gate the constitution sets for changed code, phase zero satisfies it for
  the three files at issue. If the gate would otherwise be waived here, it is the wrong gate.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Port readiness: the three characterization spec files written and green
BEFORE any port task starts, and still green after; all four template-consuming files
migrated with the THREE value-reading sites on descriptor defaults; getTemplateOutputStructure's
source of shape decided, not defaulted; dmx_channels' seed decided against the live UI;
the media-duration display unwrapping {"CTimecode": ...} at project-show/sequence:194;
adopt/unadopt proven to still work END TO END through the ported UI, not just to compile;
the remaining three config domains editable through the same renderer, checked against every
enumeration AND every default the six schemas actually declare rather than a hand-picked
subset; the entanglement untangled in step with flow 02 and neither half landed alone; the
new views not inheriting settings.component.ts's misleading name; the repair report actually
rendered; and schemaLocation deleted from the interface.
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

`npm test` green, including three new spec files that did not exist before and
that pin the behaviour this feature moved; every template call site on the
descriptor with the three value-reading sites on its defaults;
`getTemplateOutputStructure` and `dmx_channels` decided explicitly; media duration
displayed rather than `[object Object]`; adopt/unadopt working end to end through
the ported UI; the other three config domains newly editable through the same
renderer; the entanglement untangled together with flow 02; and a repaired
document producing a notification the operator actually sees.

**Does not ship alone** (D27).
