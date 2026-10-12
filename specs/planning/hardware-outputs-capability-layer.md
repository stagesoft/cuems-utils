<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# `hardware_outputs` becomes real — the node capability layer, deferred and re-owned

**Status: deferred, and deliberately unnumbered.** This work was feature **014** until 2026-10-02,
then feature **015** until 2026-10-12. It is now **neither**: feature 015 is the consumer-gate
closure ([`upcoming-feature-requirements-2026-10-02.md`](upcoming-feature-requirements-2026-10-02.md)),
and this becomes an upcoming feature **coordinated with `cuems-nodeconf` and `cuems-common`**,
numbered when it is scheduled. It will probably land with the `xml-refactor` arc; that is a decision
for later and is not made here.

**Do not give it a number in passing.** Two renumberings have already left eight code and test
sites naming a feature that no longer means what they think — §6 lists them, and they are now
re-pointed at this document instead of at a number.

**This document is the single home for the work.** It supersedes the briefs in
[`etc-cuems-first-install-execution.md`](etc-cuems-first-install-execution.md) §6 and keeps
[`etc-cuems-first-install.md`](etc-cuems-first-install.md) §7–§8 as the *design argument* it rests
on — that parent is the authority on **why** the split exists; this is the authority on **what is
left, who owns it, and what still points at it**.

**Measured 2026-10-12** against `feat/xml-refactor` after 014's merge (`2a4b892`), and against
`cuems-nodeconf` `feat/xml-refactor` `65605de`, `cuems-common` `feat/xml-refactor` `e595e67`.

---

## 1. The decision that moved it, and the review behind it

Reviewed 2026-10-12, comparing this work against the five consumer gates. Four findings, each
measured rather than argued:

| # | Finding |
|---|---|
| 1 | **Nothing is waiting on it.** `hardware_outputs.xsd` has no registry binding, no `ConfigManager` accessor, no writer, and **no instance anywhere in the ecosystem**. The gates, by contrast, hold a sibling's work open — `cuems-nodeconf`'s [`12-node-set-alias.md`](../../../cuems-nodeconf/specs/planning/12-node-set-alias.md) says *"Order: the library first, then this repository"* and carries an unchecked prerequisite on `NodeIndex.set_alias` |
| 2 | **Its primary writer did not exist.** `cuems-hardware-discovery` is named in this library's own schema comments (`settings.xsd:16`), in `xml-rebuild-08` §444 and in `../cuems-common/docs/latency-tuning.md:15` — and **has no checkout**. §3 resolves this |
| 3 | **Its one sibling obligation was unrepresented on both sides.** `grep` over all of `cuems-nodeconf`'s `specs/` finds **zero** mentions of `display.conf`, `hardware_outputs` or `hardware-discovery`, while the `display.conf` generator — `cuems-generate-display-conf` — is shipped by **`cuems-common`** (`debian/install:18`, `usr/lib/cuems/bin/`, and the systemd drop-in `cuems-videocomposer.service.d/display-conf-gen.conf`), with **zero hits in `cuems-nodeconf`**. §3 fixes the assignment |
| 4 | **The fossil it was going to repair is not urgent.** `ConfigManager.get_video_output_id` / `get_audio_output_id` read `node_conf['default_video_output']`, a key `settings.xsd` does not declare — and both have **zero callers**. A latent fossil, not a live defect |

**It is also the largest remaining breaking change in the arc**: the port inventory moves out of
`project_mappings`, `default_mappings.xml` retires, `settings/outputs` retires. Landing that inside
the same coordinated tag as 011–014's migration multiplies the migration surface at the moment seven
repositories are trying to converge. The gates are additive and public-surface only.

**Not deferred because it is unimportant.** §7.3 of the parent is still correct that this is a
*missing layer*, not a wart: a project document carries a node's physical port inventory, which is
why `default_mappings.xml` exists at all.

## 2. What it delivers

From the parent's §7.3, unchanged in substance:

> The system lacks a split between **hardware** (per node, discovered, stable across projects, not
> human-authored) and **mappings** (per project, authored, referencing hardware). Today they are
> fused inside `project_mappings`.

| Supersedes | How |
|---|---|
| `settings.xml`'s three counts | derived (`len(video_outputs)`) — the OPEN-6 fields **retire** rather than becoming optional |
| `project_mappings`' `node/{audio,video,dmx}/outputs` inventory | mappings keep *assignment* and reference output **ids**; they stop restating the inventory |
| `ConfigManager.get_{video,audio}_output_id` | the dead pair gets a real backing document, or goes |
| — `network_map` | **no overlap.** The map says which nodes exist and are adopted; this says what each node can do. `uuid` is the join key |
| — `script.xsd` | **no overlap** (X14 resolved in rc16). Cue outputs are *intent*; hardware outputs are *capability* |

**Scope: per node, aggregated by discovery.** `/etc/cuems/hardware_outputs.xml` on each node
describes only that node. The node that owns the hardware describes it.

## 3. The ownership decision — `cuems-nodeconf` takes all of it (2026-10-12)

**Decided by the maintainer.** `cuems-hardware-discovery`, the `display.conf` transcriber **and any
related machinery** become **`cuems-nodeconf`'s responsibility**. There is no new repository.

**Why this is the right owner, not merely the available one.** The parent's §7.3 already assigned the
*transcription* here, with the reason: nodeconf *"is already the per-node agent that runs discovery
and writes node identity, so it is the one process positioned to read the generated geometry and
record it."* The probe half was separated only because a `cuems-hardware-discovery` repository was
assumed. Removing that assumption collapses two writers into the one agent that already:

- runs per-node discovery and owns the node's own map row (`NodeIndex.ensure`);
- renders the node-identity record from `settings.xml` at every start and role change (011's D14,
  shape B, its feature `003-startup-readiness`);
- delegates every map mutation to this library rather than hand-editing XML.

**What stays where it is**, and must not be absorbed by this move:

| Thing | Owner | Unchanged because |
|---|---|---|
| `cuems-generate-display-conf` | **`cuems-common`** (`debian/install:18`; videocomposer's `ExecStartPre`) | it runs outside the start-up path, into tmpfs, for videocomposer. §7.3: *"`display.conf` keeps its videocomposer ownership at run time"* |
| `/run/cuems/display.conf` itself | `cuems-videocomposer` at run time | the engine ignores XML `canvas_region` by design and reads the generated geometry |
| The XML schema, model, registry bindings and `ConfigManager` accessor | **`cuems-utils`** | it is this library's sixth schema |

So the seam is: **`cuems-common` generates, `cuems-nodeconf` probes and transcribes, `cuems-utils`
describes and persists.** Discovery owns the probed port inventory; transcription owns the geometry;
they never write the same element, so **F1 holds at element granularity** — which is the statement
the eventual spec must carry, because it looks like two writers and is not.

**Three obligations this creates, none of which exist yet:**

1. **`cuems-nodeconf` has no record of any of it.** Its `specs/` must acquire the obligation before
   this is a gate. Its [`nodeconf-atomization.md`](nodeconf-atomization.md) is the natural place to
   state where a probe/transcribe responsibility sits among its ten — it is already written as *"the
   target-design basis for a future, dedicated `cuems-nodeconf` feature"*.
2. **`cuems-common` must agree that generation stays its own** while a second consumer reads the
   generated file. Today nothing but videocomposer and the engine read it.
3. **Every reference to `cuems-hardware-discovery` as a repository is now wrong** — this library's
   `settings.xsd:16` comment, `xml-rebuild-08` §444, and `../cuems-common/docs/latency-tuning.md:15`.
   They name the *role*, which survives; they imply a *repository*, which does not. §6.

## 4. Scope, item by item, with its measured state

| Item | State on `feat/xml-refactor` @ `2a4b892` |
|---|---|
| The structure pass — DMX section, `id`/`name`/`mapped_to`, measured `output_latency_ms`, transcribed geometry | **Not started.** The schema is two flat lists of `xs:string` (`video_outputs`, `audio_outputs`), one type, plus `doc_version`. No DMX, no ids, no geometry |
| Registry bindings and model classes | **None.** No `_config_models` branch; falls through to the `GENERIC` sentinel |
| A public `ConfigManager` accessor | **None.** `SchemaName.HARDWARE_OUTPUTS` is reserved and `from_json` refuses it by design |
| The port inventory moves out of `project_mappings` | **Not started.** `project_mappings` is still authoritative and the engine reads it (`node_hw_outputs`, `node_mappings`) |
| `default_mappings.xml` retires | **Not started**, and 011 deliberately built a generator for it anyway — a node must boot long before this lands (its clarification 2) |
| `settings/outputs` retires (`settings` 2 → 3) | **Blocked on this work by construction.** Pinned in `tests/contract/test_duplication_flags.py`'s `KNOWN_STORED_DERIVED_FACTS`: *read by nothing*, but the count cannot go until `hardware_outputs` can answer `len(video_outputs)` |
| `project_mappings/number_of_nodes` | The **field** retires while the **accessor** stays and computes. It has **already drifted**: `tests/data/corpus/cuems-engine/default_mappings.xml` declares `number_of_nodes=1` over **two** node entries |
| `get_{video,audio}_output_id` — real backing document or deletion | Fossil, **zero callers**. §1 finding 4. On this evidence **deletion is the cheaper answer** unless the structure pass gives them a real read |
| **X15** — the namespace typo in `../cuems-engine/dev/test_xml_files/outputs.xml` | **Still stands.** It declares `https://stagelab.coop/cuems` against a `targetNamespace` of `https://stagelab.coop/cuems/`. The only instance outside this repository |

**Already done and not to be re-litigated** (rc16): the rename to `hardware_outputs.xsd` /
`CuemsHardwareOutputs` / `HardwareOutputsType` / `SchemaName.HARDWARE_OUTPUTS`, which resolved
**X14**; F4's removal of the authored `default_*` pair; and the F1 annotations, which **have landed**
— all six schemas now carry `xs:annotation` (verified 2026-10-12; the parent's §3.3 described them
as pending 011's T072/T073).

> The schema **stopped lying** in rc16. It did not start working. That sentence is the whole status.

## 5. Ordering, when it is scheduled

| Relation | Kind |
|---|---|
| **013 before this** | advice, **satisfied** — reshaping device classes after moving the port inventory would move the inventory twice |
| **014 before this** | advice, **satisfied** — both edit `settings.xsd` and so both move `test_schema_scope`'s hashes, a guaranteed conflict in parallel |
| **011 before this** | hard for anything that ships — 011 is what makes a fresh node boot |
| **Feature 015 (the gates) before this** | **advice, and the reason is the file**: 015 changes `conf_path`/`project_path` and adds to `_PROJECTABLE_SECTIONS`, and this work adds a public `ConfigManager` accessor and must flip the `HARDWARE_OUTPUTS` refusal — same module. Gates first gives this a settled surface |
| `cuems-nodeconf` acquiring the obligation (§3) | **hard, and it is the real gate.** Not schedulable before that |

## 6. What still points at this work, and had to be re-pointed

Two renumberings (014 → 015 → unnumbered) left a trail. **Measured 2026-10-12**, these name a
feature number for *this* work; all are re-pointed at this document in the same change:

| Site | Said |
|---|---|
| `src/cuemsutils/xml/make_defaults.py:22,24,65` | *"must boot long before feature 014 retires that document"*, *"retires with feature 014"* ×2 |
| `src/cuemsutils/defaults/system-defaults.toml:98` | *"default_mappings.xml; retires with feature 014"* |
| `src/cuemsutils/tools/init_node.py:514` | *"default_mappings.xml — retires with feature 014"* |
| `src/cuemsutils/tools/ConfigManager.py:75` | *"no model bindings until feature 015"* — the refusal message a consumer actually reads |
| `src/cuemsutils/tools/ConfigManager.py:667` | *"bindings until feature 015"* |
| `tests/contract/test_duplication_flags.py:121` | *"with feature 014, not before"* |
| `tests/integration/test_default_mappings_fresh.py:10,38` | *"the fossil is feature 014's"* ×2 |
| `tests/integration/test_config_ingestion.py:329` | *"model bindings until feature 015"* |

**The lesson, since it has now cost two passes**: a code comment that names a feature *number* for
work in another document ages badly, because numbers get reassigned and comments do not get swept.
Name the **document**, or name the **behaviour**. The `ConfigManager.py:75` case is the one that
matters most — it is a refusal message a consumer reads at runtime, and it was telling them to wait
for a feature that had become something else entirely.

Also re-pointed, in the planning set: the parent's §7/§8 and the execution companion's §5 step
sequence and §6 brief.

## 7. What this document does not settle

1. **When, and under which number.** Deferred by decision, not scheduled. It will probably ride the
   `xml-refactor` arc's coordinated tag; that is explicitly a later call.
2. **Whether `get_{video,audio}_output_id` is repaired or deleted.** §4 recommends deletion on the
   zero-caller evidence, but the structure pass may give them a real read. Decide in the spec, not
   before.
3. **How `cuems-nodeconf` splits probe from transcribe** among its ten responsibilities, and whether
   that is one feature there or two. `nodeconf-atomization.md` is the basis; the split is theirs.
4. **Whether the geometry is transcribed on every start or on change.** `display.conf` is regenerated
   by videocomposer's `ExecStartPre`; the durable copy's refresh policy is a nodeconf design question
   with a cost this document has not measured.
5. **X15's fix venue** — it is a fixture in `cuems-engine`, so it is that repository's commit, taken
   under whichever feature touches it first.
