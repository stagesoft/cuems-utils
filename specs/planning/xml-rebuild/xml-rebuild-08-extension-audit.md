# XML infrastructure rebuild — Part 5: feature 008 extension audit

**Status:** ready to inform `/speckit.specify` for feature `008`
**Date:** 2026-08-25 (revised same day — see "Revision note" below)
**Purpose:** measured current-state evidence backing the feature-008 prompts in
[Part 4](xml-rebuild-07-speckit-prompts.md) §7 — the same role
[Part 1](xml-rebuild-01-audit.md) plays for features 004–007. Findings are
labelled `E1`–`E26` (evidence) rather than continuing audit's `F`/`X` series,
since this is a second, later pass over a codebase 004–007 already rebuilt.

**Why 008 exists:** after 004–007 and the (not yet executed) consumer
migration landed as a plan, the team decided the rebuild's scope should grow
*before* consumer migration starts, because doing several more structural
changes as one coordinated multi-repo pass is cheaper now than shipping them
as independent releases later. The findings below are the evidence for five
requirements gathered in conversation with the repo owner on 2026-08-25; they
are not independent audit discoveries the way F1–F24 were — each was raised as
a specific ask, then grounded against the current code before being scoped.

## Revision note (2026-08-25, after review)

The first draft of this document was reviewed against the live code in all
four repositories before any speckit flow ran. Five findings were wrong or
incomplete and are corrected here rather than left for `/speckit.plan` to trip
over:

| Finding | First draft said | Actually |
|---|---|---|
| **E1–E4** | six `CTimecodeType` elements, five storing `CTimecode`, `duration` the exception; wire unaffected | six `CTimecodeType` elements, **all six** already storing `CTimecode`. `Media.duration` is a **seventh, differently typed** element (`cms:TimecodeType`) bound to a **different adapter**. The wire **does** change. |
| **E6** | both types "unreferenced" | `TimecodeType` *is* referenced, by `CTimecodeType`. Both are **unreachable from any element** — a different claim with the same conclusion. |
| **E11** | ten responsibilities, table complete | three methods unplaced; one of them (`refresh_network_map`) belongs in the row 008 moves. |
| **E18** | four `CuemsParser` call sites | four in `CuemsDBProject.py`, plus a **fifth** in `repair_durations.py` — the tool most affected by ITEMs A and E. |
| **E20** | no config-domain UI exists | a `network_map` **editing** UI exists and is in daily use (`nodelist_modify` adopt/unadopt). The config domain is a **migration**, not greenfield. |

E21–E26 are new, added by the same pass. The decisions recorded throughout
were settled with the repo owner after that review.

---

## 1. Timecode storage and typing — the real inventory (E1–E4)

**E1 — the complete inventory, corrected.** `script.xsd` declares **six**
elements of type `cms:CTimecodeType`:

| Element | Owning type | Line |
|---|---|---|
| `offset` | `CueType` | 63 |
| `postwait` | `CueType` | 66 |
| `prewait` | `CueType` | 67 |
| `in_time` | `RegionType` | 205 |
| `out_time` | `RegionType` | 206 |
| `duration` | **`FadeCueType`** | 269 |

The first draft attributed line 269 to `MediaType`. It does not belong to
`MediaType`; `FadeCueType` spans lines 264–274 and `duration` is its second
element. No other schema declares a timecode-typed element — confirmed by
grepping `time|duration|timecode` across `project_settings.xsd`,
`project_mappings.xsd`, `network_map.xsd` and `outputs.xsd`: no hits.

**E2 — all six already store `CTimecode` objects.** Every one of the six
routes through `helpers.format_timecode()`, which returns a `CTimecode`
instance for every input shape (`str`, `int`/`float`, `dict`, or a `CTimecode`
passed through unchanged) and never a string:

- `Cue.py:187` (`offset`), `:224` (`prewait`), `:243` (`postwait`)
- `MediaCue.py:145` (`Region.in_time`), `:164` (`Region.out_time`)
- `FadeCue.py:181` (`FadeCue.duration`)

So D17 as first worded — "all persisted timecode values are `CTimecode`
objects" — is **already true of every `CTimecodeType` element**. It is not the
requirement. The requirement is E3.

**E3 — `Media.duration` is a different element with a different schema type.**
`script.xsd:182`, inside `MediaType` (lines 178–186):

```xml
<xs:element name="duration" type="cms:TimecodeType" />
```

`cms:TimecodeType` is a **simpleType** — a pattern-restricted string
(`script.xsd:528–531`) — not the `cms:CTimecodeType` **complexType** that
wraps a `<CTimecode>` child (`script.xsd:164–169`). The two produce different
documents, and the corpus proves it:

```xml
<!-- Media (MediaType, TimecodeType)   -->  <duration>00:00:30.000</duration>
<!-- FadeCue (FadeCueType, CTimecodeType) --> <duration><CTimecode>00:00:03.000</CTimecode></duration>
```

(`tests/data/corpus/cuems-utils/fade_showcase.xml` carries both shapes in one
file.) The same split appears in JSON: `tests/data/sample_script.json` has
`"duration": "00:03:01.000"` for media, against `{"CTimecode": …}` for fades.

`MediaCue.py`'s setter (`:246–287`) stringifies deliberately, and the class
comment at `:180–184` states the typing difference outright:

> "``duration`` is a ``TimecodeType`` — a restricted **string** — not the
> ``CTimecodeType`` that ``FadeCue.duration`` uses. It is out of scope for
> every coercion change in this feature (FR-009b)."

The stringification was a documented choice at the time (task T073), made to
avoid touching `cuems-engine`'s `CTimecode(cue.media.duration)` call site.

**Decision (this feature): `Media.duration` is promoted to
`cms:CTimecodeType`** — same type, same setter machinery (`format_timecode`),
same adapter as the other six. Confirmed by the repo owner, 2026-08-25: *"All
time elements must be `CTimecodeType` and common machinery need to be applied
throughout their corresponding entities, any dead code that appears after
modifications must be removed."*

This is a **`script.xsd` edit** and therefore the **third** recorded exception
to standing rule 6 (D3), after `network_map.xsd` (007) and `settings.xsd`
(E6 below). It is also the only one of the three that changes the shape of
documents already on disk.

**E4 — the wire *does* change, and the first draft's reasoning named the
wrong adapter.** `Media.duration` resolves to `TimecodeType`, which the
adapter table binds to `_String()` (`xml/adapters.py:227`) — **not** to
`_CTimecodeAdapter` (`:214`). `_String` inherits `_Passthrough`, whose
`to_wire` returns the object **unchanged** (`:58–59`):

```python
def to_lexical(self, obj):
    return None if obj is None else str(obj)

def to_wire(self, obj):
    return obj
```

So storing a `CTimecode` under the *old* type would have put a `CTimecode`
**object** into the JSON payload — not a string, and not serializable. There
was no version of this change that left the wire alone. Promoting the schema
type (E3) is the coherent option precisely because it moves the field onto
`_CTimecodeAdapter`, whose `to_wire` is `{"CTimecode": str(obj)}` and whose
`decode` already accepts `str`, `dict` and `CTimecode` alike.

**Consequences that the plan must carry as work, not as risk notes:**

1. **Every `script.xml` on disk becomes an old-version document.**
   `<duration>00:00:30.000</duration>` no longer validates against the new
   `MediaType`. This is what makes the versioning-and-conversion machinery
   (§3) *this feature's delivery mechanism* rather than parallel
   infrastructure — see E24.
2. **The golden corpus must be deliberately re-cut, once.** Standing rule 3
   ("goldens are never regenerated to make a test pass") is not violated by a
   *recorded, reviewed* re-cut of a deliberately changed wire — but it needs
   saying out loud, and the pre-change goldens should be **kept as the
   conversion path's test corpus** rather than deleted. See E24.
3. **Consumer impact, 009's to execute.** `cuems-engine`'s
   `CTimecode(cue.media.duration)` becomes `CTimecode(CTimecode_instance)`;
   `cuems-editor`'s duration read/write paths (E18, E21) move from string to
   object; `cuems-frontend` unwraps `{"CTimecode": …}` for media durations the
   way it already does for fades.
4. **Dead code to remove after the change**, per the repo owner's standing
   instruction: `MediaCue.set_duration`'s three-branch type dispatch collapses
   to `format_timecode`; the `str` branch of the `media_duration` T2 rule
   (`validators.py:549–574`) becomes unreachable through the setter; and the
   `"TimecodeType": _String()` adapter binding is a **candidate** for removal —
   verify first, because `TimecodeType` survives as the lexical type of the
   inner `<CTimecode>` element (`script.xsd:168`) and may still resolve there.

---

## 2. Canonical timecode form — one correct, one dead and wrong (E5–E6)

**E5 — `script.xsd`'s live `TimecodeType` is already correct.**
`xs:pattern value="[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}"` (script.xsd:530) —
`HH:MM:SS.mmm`, dot-millisecond. This is what `CTimecode.__str__()` produces
by construction: the class defaults to `framerate="ms"`, an upstream-library
mode that formats with a decimal millisecond field rather than a frame
number. **This type is not deleted by E6** — it stays as the lexical type of
the `<CTimecode>` child inside `CTimecodeType`, and after E3 it is the only
`TimecodeType` left in the tree.

**E6 — `settings.xsd` separately declares a same-named, incompatible,
unreachable pair.** `settings.xsd:132` restricts `TimecodeType` to
`[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2}` — colon-separated, frame-based (SMPTE
style), with a matching wrong-shaped default `"00:00:00:00"` on its
`CTimecodeType` wrapper (line 140).

Precisely stated (the first draft over-claimed): `CTimecodeType` is referenced
by **nothing**; `TimecodeType` is referenced by exactly one thing — line 140,
inside `CTimecodeType` itself. So the pair is **unreachable from any element**,
not literally unreferenced. Same conclusion, sounder evidence.

`config/settings.py::CTimecodeType` exists purely so the registry's "every
complex type must be bound" rule and the coherence test (T041) stay satisfied,
per its own docstring:

> "No element in `settings.xsd` references it. It is declared and
> unreachable... Modelling it costs nothing and keeps 'every type in the
> schema is accounted for' true without an exception list."

Note also that the two `CTimecodeType` definitions differ in content, not only
in pattern: `script.xsd`'s is `<xs:choice minOccurs="0">` with a single
`CTimecode` child; `settings.xsd`'s is a mandatory choice of `CTimecode` **or**
`NoneType`. Two incompatible definitions of one QName (E25).

**Decision (this feature):** delete both — the dead `.xsd` types and the
Python `CTimecodeType` model class that exists only to bind them — mirroring
007's precedent of deleting the unreferenced `PutType` (X9, which was
`network_map.xsd`'s; `project_mappings.xsd`'s `PutType` is live and untouched)
rather than patching in place. This is the **second** recorded exception to
standing rule 6 (D3); E3's `script.xsd` promotion is the third.
See the update to that rule in [Part 4](xml-rebuild-07-speckit-prompts.md) §10.

---

## 3. `load()`/`validate()`, versioning, and repair (E7–E10, E22, E24)

**E7 — `load()` deliberately skips T2 today, and says so in three places.**
`CuemsScript.load()`'s docstring (`cues/CuemsScript.py:309–313`):

> "Runs T1 (schema-derived, structural) validation and **no** T2 (semantic)
> validation: a document that violates a semantic rule loads, because reading
> never becomes stricter (FR-026)."

The same phrase — "reading never becomes stricter" — is also standing rule 8 in
[Part 4](xml-rebuild-07-speckit-prompts.md) §10, and was asserted independently
across three prior features (004's FR-035 area, 005's clarification on the
load/write validation asymmetry, 006's FR-026). Making `load()` semantically
strict is a **deliberate reversal** of a principle that has held since 004,
not a tweak — recorded as such, not silently changed.

**E8 — rule 4 of the schema-evolution convention has never actually been
built.** `specs/planning/schema-evolution-convention.md` rule 4 (adopted in
006) calls for exactly this: *"a version marker that lets a reader tell old
from new; a conversion that runs on read, or a documented tool that runs
once."* But **no schema anywhere has an explicit version marker** — confirmed
by grepping `version` across all six `.xsd` files: only XML declarations
(`<?xml version="1.0"` in five, `1.1` in `script.xsd`) and `vc:minVersion="1.1"`
(an XSD-language version, not a document-content one).

**E9 — 007's `network_map` migration satisfied rule 4 with an *implicit*
marker, not an explicit one.** Per
[schema-evolution-convention.md](../schema-evolution-convention.md)'s
"rule 4, exercised three ways" section: the marker was "the element's own
presence" — a document has either `<node_type>` or `<node_role>`, and
`xs:sequence` validation makes the two mutually exclusive, so no separate
version field was needed *for that one change*. The conversion was a one-off
tool (`cuems-migrate-network-map`) run from `postinst`, not something `load()`
itself detects and repairs.

**E22 — T2 coverage today is `script.xsd` plus exactly one `project_mappings`
rule.** Every `@register`ed rule in `xml/validators.py` targets a `script.xsd`
type — `ActionCue`, `FadeCue`, `FadeProfile`, `MediaCue`, `VideoCueOutput`,
`Media`, `CuemsScript` — except `one_custom_template_per_node`
(`validators.py:591`), which targets `project_mappings`' `NodeType.video`.
**`settings`, `project_settings`, `network_map` and `outputs` have zero T2
rules.** "Run T2 across all six schemas" is therefore mostly *plumbing* today,
not enforcement; the spec should say so, or the measured performance cost gets
attributed to work that is not happening.

**E10 — the version marker's design is open, and is `/speckit.plan`'s job.**
No design exists yet for *where* the marker lives (a root attribute? a
dedicated element? per-schema or document-wide?), how it interacts with
`xmlschema`'s own validation pass, or how it composes with T1 (does a version
mismatch surface as a T1 failure or a new tier?). Flagged so it is not
mistaken for settled. E24 constrains it: whatever it is, it must be able to
express E3's `Media.duration` conversion.

**E24 — E3 gives the versioning machinery a real first client.** Because the
`Media.duration` promotion invalidates every `script.xml` in every library,
the conversion is not a hypothetical exercised by a synthetic fixture: it is
the mechanism by which ITEM A reaches existing installations at all. Two
consequences for the plan:

- The version-marker design (E10) is **validated against a real migration**
  in the same feature that introduces it, which is strictly better evidence
  than 007's implicit-marker precedent could give.
- The **pre-change golden corpus becomes the conversion test corpus.** The
  goldens under `tests/data/corpus/` and `tests/golden/` are the only
  first-party collection of real old-shape documents that exists. Keep them,
  under an old-version fixture path, and re-cut new-shape goldens alongside.
  Re-cutting without keeping the originals destroys the evidence the
  conversion path needs.

**Decision (this feature), three outcomes not two.** `validate()` (T1 **and**
T2) runs inside `load()`, across all six schemas (`CuemsScript` and every
`ConfigManager`/`ConfigBase` accessor). What happens next depends on *why* the
document failed — confirmed by the repo owner, 2026-08-25:

| Document state | Outcome |
|---|---|
| **Old** (version marker precedes current) | Transparent auto-conversion in memory, timestamped backup written first (mirroring 007's backup-before-write pattern). Also available as a standalone tool for batch/offline/`postinst` use. |
| **Current but semantically invalid** | **Repair-and-notify**: recover a default state for the offending field, carry the repair in a structured report, continue loading. |
| **Unrepairable** | **Raise.** |

The middle row is the one the first draft missed entirely, and it is the row
that matters most: D20/D21's machinery rescues documents that are *old*, but
a document that is *corrupt and current-version* was left with no path at all
— it simply became unloadable, and every tool that would repair it (E18, E21)
is itself a `load()` consumer.

**Where the defaults come from, and who notifies the UI.** Two design
consequences the plan must honour:

- *Defaults* are the schema-derived descriptor's job (§6). "Recover a default
  state" has no source of truth otherwise, and hand-written per-field
  fallbacks would recreate the drift problem the descriptor exists to end.
  This is why the descriptor is sequenced **before** the load path in Part 4's
  reordered items.
- *Notification* cannot live in `cuemsutils` — the library has no UI channel
  and must not acquire one. `load()` produces a **structured repair report**;
  `cuems-editor` forwards it as a WS message; the frontend renders it. The
  report type is public, under `cuemsutils.errors`, on 006's precedent that
  "an exception the caller cannot name is one it cannot catch" — a repair the
  caller cannot inspect is one it cannot surface. **008 produces the report;
  009 wires it to the UI.**

---

## 4. `CuemsNodeConf` — one class, ten responsibilities (E11–E14)

**E11 — the catalog.** `cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py` (756
lines, one class, `feat/xml-refactor` branch as of this audit) bundles:

| # | Responsibility | Representative methods |
|---|---|---|
| 1 | Daemon lifecycle | `start`, `stop`, `run`, `_run_worker_loop`, `notify_systemd` |
| 2 | Network interface discovery | `get_ips` (hardcoded interface names `bridge0:avahi`, `ethernet1:avahi`, `bond0`) |
| 3 | Avahi/mDNS listener orchestration | `start_avahi_listener`, `on_node_event`, `callback`, `check_nodes`, `check_first_run`, `wait_for_local_service_registration`, `retreive_local_node` |
| 4 | Node role election | `set_node_role`, `_should_resume_master` |
| 5 | **Network-map domain/config logic** | `read_network_map`, `write_network_map`, `refresh_network_map`, `merge_discovered_nodes`, `set_master_always_adopted`, `check_missing_adopted_nodes`, `adopt_node`, `unadopt_node`, `_map_signature` |
| 6 | OS network reconfiguration | `change_network_to_master`, `change_network_settings_to_master` (dbus `StopUnit`/`StartUnit` on `networking.service`/`avahi-daemon.service`, copies `/etc/network/interfaces`) |
| 7 | Avahi service-template file management | `_install_master_service_template`, the inline slave-template copy in `set_node_role` |
| 8 | mDNS alias publishing | `publish_aliases_if_master`, `_ui_alias` |
| 9 | Master lock file | `update_master_lock_file`, part of `_should_resume_master` |
| 10 | Engine IPC dispatch | `set_comms`, `engine_callback` (routes `nodelist_modify` ADD/REMOVE to `adopt_node`/`unadopt_node`) |

Corrected from the first draft: `refresh_network_map` (line 229) belongs to
row 5 and is therefore **in scope for the move**; `callback` (585) and
`check_first_run` (605) belong to row 3 and are not. All three were unplaced.

**E12 — row 5 is the one with no proper object today.** `cuems-utils`'
`NodeIndex` (`tools/NodeList.py:51`) is a thin `dict` subclass — `from_nodes`,
`by_role`, `controllers`, and nothing else (the class ends at line 88).
`CuemsNetworkMapType` (`config/network_map.py:108`) has only `save()` (E15).
None of `merge_discovered_nodes`/`adopt_node`/`unadopt_node`/
`set_master_always_adopted`/`check_missing_adopted_nodes`/`_map_signature`/
`refresh_network_map` exist anywhere in `cuems-utils` — all of it is
reimplemented ad hoc on the daemon class, mutating a bare `NodeIndex` through
loose methods, unlike the `ConfigManager`/`ConfigBase` pattern the other five
schemas already have.

**E13 — a live bug, found while reading.** `cleanup()` (line 579) references
`self.cm.show_lock_file` at line 581; `self.cm` is never assigned anywhere in
`__init__` or elsewhere in the class — the only occurrence of `self.cm` in the
file is that read. Dead/broken code; `cleanup()` presumably has never been
called successfully. Flagged for a one-line fix or deletion when this work
touches the file; not itself a reason to scope more work.

**E23 — 008 ships row 5's API with no first-party caller, and that is a
measurable risk, not just a noted one.** D22 puts merge/adopt/unadopt in
`cuems-utils`; D16 permits but does not require touching `cuems-nodeconf`; 009
does the swap. So without mitigation, 008 would ship an API whose only proof
is its own tests, against a caller it never runs. **Mitigation, adopted:**
port `CuemsNodeConf`'s current behaviours into `cuems-utils` as
*characterization* tests — `merge_discovered_nodes`, `_map_signature`,
`adopt_node`/`unadopt_node` and `set_master_always_adopted` are pure enough
over a `NodeIndex` to be pinned this way — so equivalence is **measured in
008** rather than asserted at 009 time.

**Decision (this feature):** row 5 (network-map config-object logic) moves
into `cuems-utils`, extending `NodeIndex`/`CuemsNetworkMapType` to own
merge/adopt/unadopt/refresh/signature/write orchestration, mirroring
`ConfigManager`/`ConfigBase`. Rows 1–4 and 6–10 are **not** split now; this
feature instead records the target-design basis for that full atomization (the
table above, plus which rows are single-class candidates and why) so it can
become its own dedicated `cuems-nodeconf` feature later. `cuems-nodeconf`'s
actual consumption of the new object is 009's job, per the general
consumer-modification rule (D16).

**E14 — the engine IPC dispatch (row 10) is worth naming explicitly for 009,
and it has a live UI on the other end.** `engine_callback` is how
`cuems-engine`'s adopt/unadopt actions reach the network map today — and E20
shows those actions originate in a real `cuems-frontend` component that users
operate. Whatever `NodeIndex`/`CuemsNetworkMapType` grows in 008 has to be a
valid target for `nodelist_modify` → `engine_callback` → `adopt_node` once 009
migrates it, and the behaviour that chain delivers today must be preserved,
not merely re-implemented.

---

## 5. Config domain write paths — one of five (E15)

**E15.** Grepping `def save\b` across `config/*.py` and `tools/*.py` finds
exactly two hits: `config/network_map.py:119` (`CuemsNetworkMapType.save`) and
`tools/ConfigManager.py:246` (`save_network_map`). (`CuemsScript.save` at
`cues/CuemsScript.py:432` is the show domain, not config.) Per CLAUDE.md's own
record, this was "`network_map`'s first first-party write path — it had none
before" (007). **`settings`, `project_settings`, and `project_mappings` have
no write path in `cuems-utils` at all.**

**Decision (this feature, explicit line item):** implement `.save()` for the
three missing config objects, symmetric to `network_map`'s.

**Sequencing note the first draft got wrong.** D24 called this item
"decoupled from templating", which is true — it has nothing to do with the
descriptor. But it is **not** independent of the load path: §3's
auto-conversion writes a timestamped backup, and repair-and-notify may persist
a recovered default state. Both need a config-domain **write** path to exist
first. This item is a *precondition* of the load work, and Part 4's reordered
items reflect that.

---

## 6. Template generation — hand-maintained in two places (E16–E20, E25–E26)

**E16 — `create_script()`'s actual shape.** `src/cuemsutils/create_script.py`
(225 lines) hand-builds one literal instance of each cue type (audio, video,
dmx, action, fade) with hardcoded example values — a real UUID minted then
cleared (with an inline note about F16's `Uuid(None)` fix making that
necessary), `FadeCurveType.linear` typed as a Python literal, a hand-picked
`output_geometry`/`canvas_region` shape — runs the whole thing through real
construction and `validate_template()` (genuine T1+T2 validation via
`.validate()`, line 192), then blanks ids and dates back out (lines 195–203)
before returning it. This is "a lot of machinery" to produce something that is
not really a script at all — a shape descriptor forced through the full
script-construction pipeline because that pipeline is the only thing
available. `cuems-editor`'s `CuemsWsServer` calls it once at startup
(`self.initital_template = create_script()`, sic) and serves the result
verbatim as the `initial_template` payload (`CuemsWsServer.py:501–503`).

Note the ordering: **validation happens before the blanking**, so the object
actually served is one that would fail its own check — ids are `None` and the
example `ActionCue`'s `action_target` points at a now-blanked id. That dangling
reference is what `cuems-editor`'s `_clean_dangling_targets` exists to sweep up
(E18). One causal chain, currently documented in three disconnected places.

**Decision:** `create_script()` is **superseded**, not preserved. Confirmed by
the repo owner, 2026-08-25: its faulty logic does not need to be carried
forward. This removes the "output stays byte-identical" constraint the first
draft imposed on the descriptor item, and with it the reason to ship the
descriptor additively (E26).

**E26 — `create_script()` is not the only hand-maintained template.**
`templates/settings.xml` (5.1 KB) is a hand-written reference instance with
`REPLACE-…` placeholders, and `settings.xsd`'s own header declares it a binding
contract:

> "Any change to this schema MUST be reflected in the template — they are two
> sides of the same contract. In the future, the in-dev
> cuems-hardware-discovery project will consume the template, probe node
> hardware, and populate the final deployed file automatically."

That file is referenced by **no code and no test** in this repository and is
not packaged (`pyproject.toml` does not mention `templates/`). So the contract
its own schema declares is enforced by nothing — drift-prone by construction,
and a second instance of exactly the problem the descriptor exists to solve.
The descriptor should be able to generate it, and the schema header should
stop asserting a hand-maintenance obligation once it can.

**E17 — the schema-derived engine already knows types, but not restricted
values, and not defaults.** `xml/spec.py::FieldSpec` (from 004) carries `name`,
`xsd_type`, `required`, `repeated`, `order`, `kind`, `child` — everything
needed to describe a field's *shape* — but **neither** the field's legal value
set **nor** its default. Restricted values exist today only as hand-written
Python `Enum` classes (`FadeCurveType`, `NodeRole`, …) bound to adapters *by
name* (`xml/adapters.py:242–252`), never introspected from the XSD's
`xs:enumeration` facets. Defaults exist only as `DECLARED_DEFAULTS` on the
model classes. No code path reads either from the schema.

**E19 — the frontend's template-cloning surface is small, concentrated, and
consumes *values*, not only shape.** `cuems-frontend` reads `initial_template`
in exactly one service (`projects.service.ts`, `localStorage` key
`'initial_template'`, lines 159/240/243) and consumes it from two files:

- `project-create.handler.ts` — `safeCloneTemplate` (line 10) and
  `prepareTemplateForNewProject` (line 17), called at line 53/55. Notably it
  **discards** the cloned cue examples for whole-project creation, keeping only
  the `CuemsScript` scaffold.
- `project-edit/sequence/sequence.component.ts` — exactly **5** calls to
  `projectsService.projectTemplate()` (lines 687, 716, 850, 909 and one more in
  the same block), presumably one "add cue of type X" action apiece.
  (`project-show/sequence/sequence.component.ts` has none — the first draft did
  not distinguish the two files of that name.)

~7 call sites across 2 files — bounded and tractable. **But at least two of
them read concrete values out of the template rather than its shape:** line 688
takes `template?.…?.AudioCue?.master_vol || 20`, and line 727 maps the example
`DmxCue`'s `dmx_channels` array. A descriptor emitting only "name, type,
cardinality, enum values" gives those call sites nothing to migrate onto.
**The descriptor must carry model-layer defaults** — which is the same
requirement §3's repair-to-default path generates independently, from the other
direction.

**E18 — `cuems-editor`'s mutation surface, corrected upward.**
`CuemsDBProject.py` is on the deprecated `cuemsutils.xml.Parsers.CuemsParser`
at **four** call sites — `update` (line 356), `new` (489), `duplicate` (571),
`update_projects_existed_media` (808) — already documented 009 debt per 006's
migration guide, which recorded three.

More relevant here: its business logic runs as **raw dict mutation on the JSON
payload before parsing**, not through any object setter —
`_clean_dangling_targets` / `_nullify_dangling_refs` (lines 387–437),
`_fix_media_durations` (367), and id/date stamping. Once `load()`/`from_json()`
raise on T2 violations (§3), these fixups either run **before** the strict
parse as sanctioned, deliberate repair steps, or become real object-level
operations. They cannot continue as ad hoc dict pokes on data about to be
handed to a stricter parser.

**E21 — a fifth `CuemsParser` call site, in the tool this feature disturbs
most.** `cuems-editor/src/cuemseditor/repair_durations.py` imports both
`CuemsParser` (line 39) and the deprecated `XmlReaderWriter` (line 40), and
parses at line 230. It is not in `CuemsDBProject.py`, which is why the
four-call-site count missed it.

It matters out of proportion to its size, because it sits at the intersection
of every decision in this feature:

- **It exists to load deliberately-corrupt documents.** Its docstring: historic
  `CuemsDBMedia.get_duration` "dropped zero-padding, so any duration whose
  millisecond fraction ended in a zero was stored short (by up to ~0.9 s)".
  Pass A rewrites `media.duration` in the DB; **Pass B rewrites `<duration>` in
  each project `script.xml`**. A strict-on-load path that rejects what this
  tool is built to read would break the repair tool with the corruption still
  in place. §3's repair-and-notify contract is what keeps it viable.
- **It hard-codes the old wire shape**:
  `TIMECODE_SHAPE = re.compile(r'^\d\d:\d\d:\d\d\.\d\d\d$')` matched against
  `<duration>` text content — exactly the shape E3 replaces with
  `<duration><CTimecode>…</CTimecode></duration>`.
- **Its Pass B overlaps with §3's conversion path.** Rewriting `<duration>`
  across every project XML is what the standalone conversion tool will do
  anyway. The two should not be built twice.

**Split, per the repo owner's direction:** **008** owns the library side —
the `Media.duration` type promotion, the document conversion that carries it
to existing files, and the repair-and-notify contract that lets a
corrupt-duration document still be read. **009** owns `repair_durations.py`
itself: migrate it off `CuemsParser`/`XmlReaderWriter`, drop its private
`TIMECODE_SHAPE` regex in favour of the library's canonical form, and fold its
Pass B into the standalone conversion tool instead of maintaining a second XML
rewriter. Its ffprobe/DB half (Pass A) stays editor-local — that part is
genuinely the editor's domain.

**E20 — corrected: a config-domain UI exists, and it is in daily use.** The
first draft claimed no UI exists for editing `settings`/`project_settings`/
`project_mappings`/`network_map`, justified by there being no write path to
build one against (E15). That justification is a non-sequitur — the write path
lives in `cuems-nodeconf`'s `write_network_map`, which is E11 row 5's entire
point — and the conclusion is false:

- **`cuems-frontend/src/app/components/settings/settings.component.ts`** (140
  lines, plus `.html`) is a `network_map` **editing** UI. It emits
  `{action: 'nodelist_modify', modify_action: 'ADD' | 'REMOVE', value: uuid}`
  (lines ~122 and ~133) and subscribes to the `nodelist_modify` response
  (line 35). Node state is read from `projectsService.initialMappings()` —
  `.value.nodes` and `.value.new_nodes`. This is the user-facing end of E14's
  dispatch chain.
- **`audio-mixer.component.ts:80` and `video-mixer.component.ts:94`** both read
  the `initial_mappings` `localStorage` key — a `project_mappings` read
  surface.

So the config domain is **a migration with live behaviour to preserve**, not
greenfield. Per the repo owner: *"All existing machinery need to be ported onto
the new dynamic-form UI entities, but logic needs to be preserved."*

**E25 — two structural traps in that migration, neither previously recorded.**

1. **The domains are entangled on the wire.** `CuemsWsServer.reload_network_map_nodes`
   (line 439) loads `network_map.xml` and merges node status **into
   `mappings_dict`** (line 417: "Update basic fields from network_map (online,
   adopted, ip, name, etc.)"), which is then served as `initial_mappings`
   (lines 509–511). A `network_map` edit therefore arrives at the UI inside a
   `project_mappings` payload. Per-domain descriptor-driven forms have to
   untangle this, and the untangling is a behaviour change for
   `settings.component.ts`, `audio-mixer` and `video-mixer` simultaneously.
2. **The WS pattern this feature proposed to invent already exists.** The
   descriptor item's first draft called for "new `cuems-editor` WS message types (serve
   descriptor + accept saves per domain, symmetric to how `initial_template` is
   served today)". The closer precedent is `initial_mappings` (serve) +
   `nodelist_modify` (accept a mutation) — a config domain already has both
   halves. Design the new message types as a generalisation of that pair, not
   of `initial_template`, which is serve-only.

   A third trap, minor but real: `settings.component.ts` is named for the
   `settings` domain and edits `network_map` nodes. Do not let the new
   per-domain views inherit that naming.

**Decisions (this feature and 009):**

- **008** ships a standalone schema descriptor — new machinery, independent of
  the runtime object model, walking the parsed XSD directly (may share
  underlying `xmlschema` schema objects with the existing registry) — for **all
  six schemas**. It emits, per type: field name, XSD type, cardinality,
  the legal value list read from `xs:enumeration` where the type is a
  restricted enumeration, **and the model-layer default** (E19, and §3's
  repair path). Because `create_script()` is superseded rather than preserved,
  008 **replaces** it with descriptor-derived generation rather than shipping
  the descriptor alongside it (E26 applies the same treatment to
  `templates/settings.xml`).
- **009** extends this to the consumer cutover: `initial_template`-as-a-
  concrete-instance is retired. Script domain is a *migration* of the ~7-call-
  site surface (E19), bundled with `CuemsDBProject`'s forced move off
  `CuemsParser` and its raw-dict fixups (E18) and `repair_durations.py`'s
  migration (E21) — all of which had to change for the load-path work anyway.
  Config domain is a *migration onto new machinery* (E20): existing
  `nodelist_modify` behaviour is preserved through a generic
  schema-form-renderer, with the domains disentangled (E25) and new
  `cuems-editor` WS message types generalising the `initial_mappings` /
  `nodelist_modify` pair.
- **Noted for 009's design, not settled**: consider serving **partial**
  elements on demand from the editor backend — a script sub-object, a duration
  value queried against the DB — rather than requiring the frontend to hold or
  compute full payloads client-side, if doing so simplifies the new config/form
  UI entities by shifting work to the editor. An option to weigh during 009's
  `/speckit.plan`, not a requirement fixed here.

---

## Cross-cutting notes for `/speckit.plan`

- **Item order is a dependency chain, not a preference.** Per the repo owner:
  structural soundness over parallelization. Part 4 §7's items are ordered
  A → B → C → D → E where the timecode change defines the new wire, the config
  write paths and the network-map object complete the config surface the load
  path writes through, the descriptor supplies the defaults the repair path
  recovers to, and the load/versioning/repair work lands last, consuming all
  four. E24 explains why the versioning machinery cannot precede the change it
  delivers. The chain is cut once, between D and E, into two gated phases —
  see the last note in this section.
- **Sequencing against other features**: 008 depends on 007 (needs the node
  model and `network_map` object model E11–E14 build on). Because 008 changes
  behaviour incompatible with what consumers assume today (E3's `duration`
  type and wire shape, E7's load-strictness reversal), it inherits the release
  gate 007 established for 009 (FR-030c/FR-030d) — extended so nothing ships
  until **009** lands. **Confirmed by the repo owner, 2026-08-25 (D27)** — 008
  does not ship independently, despite touching no consumer repository
  directly.
- **Scope shape**: none of 008's items *require* editing a consumer repository
  — all five are buildable inside `cuems-utils`, closer in shape to 004–006
  than to 007. The general consumer-modification rule (D16) stays available if
  implementation surfaces a case that needs it.
- **Performance baseline, corrected.** The current baseline is feature 007's,
  not 006's: **2393 passed, 94 skipped, 2 xfailed in 59.33 s = 24.79 ms/test**
  (`specs/007-node-model-migration/baseline.md`, measured 2026-08-24). Derive
  Principle IV's budget from that figure, not from 006's 2222 / ~27 ms/test.
- **Five items, one feature, two gated phases — settled, not left implicit.**
  §0's rule is "independently shippable *and* independently green", and D27
  already concedes 008 is not independently shippable. The items share no
  machinery: A touches adapters and setters; B and C the config surface; D is
  a new module; E is a new subsystem whose central mechanism is undesigned
  (E10) and which is, on its own, larger than 007. The dependency chain is the
  argument *for* one feature — each item is the next one's precondition, so
  five feature numbers would serialise the same work behind five review cycles.

  But the chain has a real seam between **D and E**: A–D change machinery that
  already exists and can be reviewed against it; E adds a subsystem that cannot
  be. So the resolution is neither one undifferentiated feature nor five: **one
  spec, one plan, one feature number, and a hard phase gate in `tasks.md`** —
  Phase 1 (A–D) merged and green before any Phase 2 (E) task starts. Confirmed
  by the repo owner, 2026-08-25 (D30), and applied at a deliberate stop between
  `/speckit.plan` and `/speckit.tasks` (D31, Part 4 §7.2) so the boundary is
  written into the plan rather than hoped for during implementation.

  The gate's real payoff is not a smaller diff. It is that Phase 2 is built
  against ITEM B's `save()` and ITEM D's descriptor **as landed code** rather
  than as planned interfaces — which is the entire reason D28 put them first —
  and that if ITEM E's undesigned mechanism (E10) turns out larger than the
  plan assumed, that is discovered with four items already merged rather than
  with the whole feature in flight. It is **not** a release boundary: D27 holds
  and nothing ships until 009 lands.
