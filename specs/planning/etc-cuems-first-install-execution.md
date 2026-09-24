<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# `/etc/cuems` first install — execution status and SDD sequencing

**Companion to** [`etc-cuems-first-install.md`](etc-cuems-first-install.md). That document holds
the *design*: seventeen decisions, the identity invariant, the splitting basis and the
duplication-avoidance flags. **This one holds the state of the build** — what is actually in the
tree, measured rather than asserted — and the sequence that turns the remainder into four
speckit features, `011` through `014`.

**Written for** whoever picks the work up next: a contributor on a fresh checkout, or an agent
session with no memory of how any of this got here. It is meant to be read *before* touching the
parent document, because several of the parent's own status lines are older than the code.

**Audited**: 2026-09-24, against `feat/xml-refactor` at `e421e31`, library version `0.1.0rc16`.
**Suite at audit**: 2719 passed, 100 skipped, 2 xfailed.

Paths are relative to this repository's root; `../<repo>` is a sibling checkout.

---

## 0. How to use this document

| You are… | Start at |
|---|---|
| picking up the next piece of work | §5 (the step sequence), then the brief for your feature in §6 |
| trying to find out whether *X* is built | §3 (the audit), which is measured per decision |
| about to change a schema | §4 (findings) and §7 (traps) — both will save you a revert |
| a fresh agent session | §1, §2, §3 in order; do not skip §7 |

**The parent document is the authority on *why*. This one is the authority on *where things
stand*.** Where they disagree, this one was measured more recently — and §4 lists the specific
places the parent was stale. Corrections are **recorded in §4 and then applied** to the parent,
never applied silently — so the two documents agree while the reason they once disagreed stays
readable.

---

## 1. Environment — reproducing the audit

```bash
cd <this repo>                     # /disk/Projects/StageLab/cuems-utils on the dev box

# Tests run under pyenv 3.11.9. A bare `hatch` may not resolve; this form always does:
PYENV_VERSION=3.11.9 pyenv exec hatch test -q              # full suite, ~55 s
PYENV_VERSION=3.11.9 pyenv exec hatch test tests/contract/test_duplication_flags.py -q
```

Facts worth having up front, each of which has cost someone time:

- **Commits are GPG-signed.** On `gpg failed to sign`, retry — never `--no-gpg-sign`.
- **`debian/` lives on the working branch** as of 2026-09-24. It was integrated from
  `debian/bookworm` — eight real packaging files, without the nineteen committed build artifacts,
  which are now `.gitignore`d. The old branch is preserved and tagged `packaging-rc14`. Feature
  011 therefore edits one tree, not two. `debian/README.source` records why, and carries the
  trixie and CI/CD intentions.
- **The two production machines were unreachable on 2026-09-23 and again on 2026-09-24**
  (`ssh -i ~/.ssh/id_stagelab cuems-admin@10.16.10.{2,3}`, connection timed out). Every
  production figure in the parent document dates from the 2026-09-21 audit. Treat them as
  evidence, not as a live source, and re-measure before relying on one.
- **Sibling repos sit beside this one** under `/disk/Projects/StageLab/`. A "read by nothing"
  claim is only valid if it was checked across them — see §7.1.

---

## 2. What has landed, in order

| Commit | What |
|---|---|
| `e68d082` | `project_mappings` `NodeType` → `NodeMappingType` (§8.5 item 2) |
| `9d8e966` | `test_schema_scope` re-based onto current content (§11) |
| `c0fb614` | the golden-capture harness, repaired — it could no longer regenerate |
| `782f669` | **F3/F4** — derived counts and authored defaults out of the schemas (§8.5 item 3) |
| `37489b5` | **F3/F4/F5 as standing ratchets** (this document's step 1) |
| `e421e31` | **D15/D16/D17** — the settings seed values corrected, the generator's hole closed (step 2) |
| `429f414` | this document |
| *(the commit that added this row)* | **step 0** — the stale statements in both planning documents, and two schemas' version comments, corrected (§4) |

Everything above is on `feat/xml-refactor`, unreleased, merging under `0.1.0rc16` (§12 of the
parent — `0.1.1` is reserved by `_deprecation.REMOVAL_RELEASE` and refused outright by three
consumers' `<< 0.1.1~` ceilings).

---

## 3. The audit — what is built, measured per section

### 3.1 By section

| § | Covers | Status |
|---|---|---|
| 1–2 | Problem, measured state | Still true. rc16 changed nothing about first install |
| 3 | D1–D17 | **2 satisfied, 1 a stance, 14 unbuilt** → §3.2 |
| 4 | End-to-end design | Nothing built. The block still generates `default_mappings.xml`, which §8.5 item 5 retires — left standing for 011 to decide (§4.4) |
| 4.1 | Packaging hygiene | **Partly done** — the committed build artifacts are gone with the branch integration; `debian/compat 11`, `Standards-Version 4.1.4` and the `dh_python2` postinst remain for 011 |
| 5 | Eight identity practices | All unimplemented; they *are* `cuems-init-node`'s body |
| 6 | OPEN-1…6 | 1,2,3,4 open · 5 closed · 6 closed by F3, **now marked as such** (§4.1) |
| 7 | `hardware_outputs` | Rename + F4 landed; capability descriptor not started → §3.4 |
| 8 | Basis, writers, flags | → §3.3 |
| 9–10 | uuid4 + re-mint | Decided and written; no code. Gated on `cuems-init-node` |
| 11–12 | Schema pin, version | Done |

### 3.2 The seventeen decisions

**Satisfied**: **D8** (nothing converts at install; conversion on read) — by feature 008's
machinery plus F3/F4's two registered conversions. **D10** (`DECLARED_DEFAULTS` stays Python) —
by the status quo, and F3 removed two entries from it.

**A stance, no artifact**: **D1** (the XSD is SSOT for structure, never values).

**Unbuilt, with the evidence**:

| Decision | Measured 2026-09-24 |
|---|---|
| D2, D3, D4, D5, D6 | No `debian/install`, no `postinst`, no `postrm`. Nothing ships to `/etc` or `/usr/share`. `cuems-common` still carries the `network_map.xsd` mirror |
| D7, D9 | Values still in `descriptor._SETTINGS_EXAMPLE_VALUES`. **No `.toml` in the repo** except `pyproject.toml` |
| D11, D12, D13 | `cuems-init-node` does not exist. `[project.scripts]` has exactly one entry, `cuems-convert-documents` |
| D14 | No `node-identity-contract.md` in `../cuems-common` |
| D15, D16, D17 | ✅ **landed `e421e31`** — the one block of §3 that is now built |

So of the fourteen, **three are done** and eleven remain, all of them packaging or tooling.

### 3.3 The six flags

| Flag | State |
|---|---|
| **F1** — one writer per document, declared in the schema's annotation | ✗ **Not checkable yet.** Measured: five of six schemas contain **zero** `xs:annotation`; only `script.xsd` has any (2). Nothing to check until the annotations are written — packaging work |
| **F2** — a fact is declared once | ✅ `tests/contract/test_schema_name_overlap.py`. One entry left in `KNOWN_DIVERGENT_DECLARATIONS`: `UuidType`, gated on `cuems-init-node` |
| **F3** — derived facts computed, never stored | ✅ ratchet in `tests/contract/test_duplication_flags.py`. Two live violations enumerated → §4.2 |
| **F4** — one provenance per document | ✅ same file. `network_map`'s straddle recorded as a decision |
| **F5** — references volatile → stable | ✅ same file. **Zero violations today** |
| **F6** — a new device class is data, not schema | ✗ Proven feasible under the pinned `xmlschema==3.4.3`, not designed. Feature 013 |

### 3.4 `hardware_outputs` — honest, not yet useful

Measured content of `src/cuemsutils/xml/schemas/hardware_outputs.xsd`: **two flat lists of
`xs:string`** (`video_outputs`, `audio_outputs`), one type (`HardwareOutputsType`), plus the
`doc_version` marker. No DMX. No `id` / `name` / `mapped_to`. No geometry. No
`output_latency_ms`.

Measured wiring: **no registry binding** (no `_config_models` branch — it falls through to
`GENERIC`), **no `ConfigManager` accessor**, **no writer**, **no instance anywhere in the
ecosystem**. X15 (the external instance's namespace typo) still stands.

What rc16 did accomplish is worth stating precisely, because it is easy to over- or under-read:
the rename (`CuemsHardwareOutputs`, `HardwareOutputsType`, `SchemaName.HARDWARE_OUTPUTS`)
resolved X14 and F4 removed the authored `default_*` pair. The schema **stopped lying**. It did
not start working.

One consequence of F4 to carry forward: `ConfigManager.get_video_output_id` /
`get_audio_output_id` read `self.node_conf['default_video_output']` — a key that
`settings.xsd` does not declare and that `hardware_outputs.xsd` no longer declares either. Both
methods have **zero callers**. The fossil is now unambiguous; feature 014 either gives it a real
backing document or deletes it.

---

## 4. Findings new to this audit

Each of these is a correction or an addition to the parent document. **Step 0 acted
on four of the six** — the parent document now carries the corrections, marked ✅ below. The two
that remain are findings, not staleness: they describe the tree as it is.

### 4.1 ✅ OPEN-6 is closed, and closed the *stronger* way

The parent's OPEN-6 read *"Making them `minOccurs="0"` is a rule-4 file-format change … Not done
here"*. F3 **retired** `audio_cards` and `universes` outright rather than making them optional —
which is what §7.3 prescribed: a count that restates `len(inventory)` has no declaration site at
all, so making it optional would have left the duplication in place and merely excused it.

Marked closed in the parent by step 0, at OPEN-6 itself and at the two other places that still
described the fields in the present tense (D15's closing paragraph and §8.1's violation 2).

### 4.2 Two derived facts are still stored, and one has already drifted

Enumerated in `test_duplication_flags.KNOWN_STORED_DERIVED_FACTS` with a resolution each:

- **`settings/outputs`** (`VideoPlayerType/outputs`) — the third of §7.2's three counts, the one
  F3 did not take. Re-measured across every sibling repository on 2026-09-24: **read by
  nothing.** The engine reads only `videoplayer/osc_port` (`NodeEngine.py:555`);
  `../cuems-common/usr/lib/cuems/bin/cuems-extract-video-latency` reads only
  `videoplayer/output_latency_ms`. It survives rc16 solely because F3's scope was OPEN-6's two
  fields. **Retires with 014, not before** — `hardware_outputs` must be able to answer
  `len(video_outputs)` first, or the count disappears with nothing to replace it.
- **`project_mappings/number_of_nodes`** — `len(nodes/node)` restated at the root. Unlike the
  counts above, this one **is** read: `ConfigManager.py:505` assigns `self.number_of_nodes`, and
  `../cuems-frontend/src/app/services/projects/projects.service.ts:37` types it. So the *field*
  retires while the *accessor* stays and computes. **It has already drifted**:
  `tests/data/corpus/cuems-engine/default_mappings.xml` declares `number_of_nodes=1` over **two**
  node entries. That is F3's argument standing in the corpus, not a hypothetical.

### 4.3 ✅ Two schemas carried a version comment that was false

`settings.xsd` and `hardware_outputs.xsd` both still say

```xml
<!-- … this schema stays at version 1 (FR-048b). -->
```

while `versioning.CURRENT_VERSION` puts both at **2** (F3/F4 moved them, each with a registered
conversion). Cosmetic — a comment, so no document on disk was affected — but exactly the class of
drift `test_schema_scope` exists to make visible.

Corrected by step 0, each comment now naming what moved it and pointing at
`versioning.CURRENT_VERSION` as the authority rather than restating a version number that can go
stale again. Both hashes moved with it in the same commit, which is the pin working as designed.

### 4.4 ◐ The parent's D6 and two tables were stale; the §4 block is deferred

**Fixed by step 0**, all three being plain factual errors: D6's `postrm` snippet listed
`outputs.xsd`, renamed in rc16 (the path count stays 9); §7.2's row still counted
`hardware_outputs`' "2 defaults" after F4 removed them; and §8.4's new-device-class cost table
still charged a `default_X_output` that no longer exists.

**Deliberately not fixed**: the §4 end-to-end block still generates `default_mappings.xml` as a
first-class artifact, which §8.5 item 5 schedules for retirement. That is a design decision, not
a stale fact — it is 011's to take (§6, clarification 2), and pre-empting it here would settle in
housekeeping a question the spec should force.

### 4.5 ✅ The production byte-count table had aged

§2.6 compares each machine's `.xsd` against a "canonical" byte count. Re-measured 2026-09-24:
**three of the four rows had moved**, not two as first reported — `project_mappings.xsd` 7701 →
7722 (the `NodeMappingType` rename) and `settings.xsd` 8717 → 8844 (F3's drops plus §4.3's
comment); `network_map.xsd` and `script.xsd` are unchanged.

Step 0 relabelled the column as the 2026-09-21 snapshot it is and recorded the current figures
beneath it, rather than half-refreshing a table whose machine columns **cannot** be re-measured
— both hosts have been unreachable since 2026-09-23. The conclusion is unaffected and now
stronger: every `.xsd` on both machines is stale, the two disagree with each other, and the
canonical side has moved again since.

### 4.6 A flaky performance test

`tests/contract/test_descriptor_laziness.py::test_no_individual_schema_regresses_where_it_is_measurable[project_mappings]`
failed once during the audit at **1.23x** against a **1.10x** budget on a **~1 ms** measurement,
then passed 9/9 across re-runs of both the modified and the unmodified tree. It is a timing
assertion with no noise floor of its own on a sub-2 ms figure. **Do not "fix" a schema in
response to it**; re-run first. If it becomes frequent, the budget needs a floor, not the code.

---

## 5. The step sequence

```
step 0  housekeeping                     no SDD    DONE  2026-09-24
step 1  F3/F4/F5 ratchets                no SDD    DONE  37489b5
step 2  D15/D16/D17 values + generator   no SDD    DONE  e421e31
step 3  feature 011  /etc/cuems first install         SDD
step 4  feature 012  uuid4 convergence                SDD
step 5  feature 013  device-class reshape (F6)        SDD
step 6  feature 014  hardware_outputs + inventory     SDD
```

**Two orderings are forced. One is advice.**

- **011 before 012** — §9.4: narrowing `UuidType` without `cuems-init-node` invalidates every
  node identity in the field with no tool able to repair them. That ships a brick.
- **011 before everything** — it is the only step that makes a fresh node boot, and it is the
  base package the whole stack installs first.
- **013 before 014** *(advice)* — reshaping device classes after moving the port inventory means
  moving the inventory twice.

Steps 3–6 each cross a repository boundary, change a file format, or add a public entry point.
That is the line the numbered features have held in this repo, and it is why these four get a
spec and steps 0–2 did not.

---

## 6. Feature briefs

Each brief gives what the `/speckit` spec must cover. They are **scoping input, not a
substitute** for the spec: the clarification pass is where OPEN items get decided.

### Feature 011 — `/etc/cuems` first install

**Delivers**: a fresh `apt install` leaves a node that loads and is unique.

**Scope**: D2–D7, D9, D11–D14, D17's shipped consequence; the `cuems-init-node` entry point;
the `cuems-common` handover; `postrm`; §4.1's packaging hygiene.

| | |
|---|---|
| **Repos** | `cuems-utils` (owner), `cuems-common` (hands over `network_map.{xml,xsd}`, gains the identity contract) |
| **Branches** | `feat/xml-refactor` alone — `debian/` was integrated 2026-09-24, so source and packaging move together |
| **Depends on** | nothing. This is the entry point |
| **Blocks** | 012 (hard), and every "fresh node" claim in the ecosystem |
| **Closes** | OPEN-1, OPEN-2, OPEN-3, OPEN-4 |

**Clarifications the spec must force** (do not let these be assumed):

1. **OPEN-1** — `default_mappings.xml`'s values table, per field, for a *fresh unconfigured*
   node. Neither production file is copyable: one maps a **disconnected** `DP-2`, and the two
   disagree on whether `default_audio_output` holds an output **id** or an output **name**. That
   disagreement is unresolved and one of the two spellings is wrong.
2. **The `default_mappings.xml` tension.** §8.5 item 5 retires this document, and 011 is about to
   build a generator for it. Recommended: build it anyway — a node must boot long before 014
   lands, and the table is seven scalars plus a node entry — but the spec should say so
   deliberately rather than discovering it in review.
3. **OPEN-3** — package ordering between `postinst` and first service start, confirmed rather
   than assumed. The units are `cuems-common`'s.

**Exit criteria, measured**: `ConfigManager(load_all=True)` succeeds on a machine whose
`/etc/cuems` was populated only by `dpkg -i`; `--reinstall` and `remove`+install leave identity
untouched; `purge` of this package alone damages no other package's files; `dpkg-deb` shows
`home = /usr/bin` in `pyvenv.cfg` (the pyenv trap in CLAUDE.md).

**The constraint that dominates every design choice here**: `cuems-utils` is the base
dependency. A non-zero `postinst` exit blocks the configure of **every** CUEMS package. Every
step either succeeds or degrades to a pristine copy with a warning and `exit 0`.

**Trap**: `/etc/cuems/power-bridge.key` is a **private SSH key** belonging to another package.
Nothing in this feature may `rm -rf /etc/cuems` (D6).

### Feature 012 — uuid4 convergence

**Delivers**: one uuid version across the project, and the machinery that gets deployed clusters
there.

**Scope**: narrow `network_map.xsd`'s `UuidType` to `script.xsd`'s (already exactly
`Uuid.UUID4_REGEX`); the version step and conversion; `cuems-convert-documents --check` gaining
detect-and-report; `cuems-init-node`'s cross-document re-mint; §10's procedure as a migration
guide.

| | |
|---|---|
| **Depends on** | **011 — hard.** §9.4 |
| **Completion marker** | `UuidType` leaves `KNOWN_DIVERGENT_DECLARATIONS` in `test_schema_name_overlap.py`. While the entry is there, that test *requires* the collision to still exist |

**The two things that make this harder than it looks**, both already established:

- **The re-mint is not a document conversion.** `convert()` walks one document at a time; a node
  uuid is a cross-document identity that also appears **inside compound strings**
  (`<uuid>_<output_id>` in every `<output_name>`, and in the three `default_*_output` values). A
  structural rewrite handles `settings.xml` and `network_map.xml` and leaves **every script in
  the library wrong** — and wrong without raising, because `output_name` is a `NameStringType`,
  so a stale prefix stays schema-valid. Rewrite by **literal 36-char token substitution**
  (§10.2).
- **A property is lost, and must be lost knowingly**: a MAC-derived uuid1 survives a reimage; a
  uuid4 does not. After this, reimaging a node produces a new identity and the node must be
  re-adopted. That belongs in the migration guide, not in a venue's discovery.

**Before a first real run**, confirm §10.7 on hardware: library layout, the configured
`script_file_name` (it is **configuration, not a constant** — `script.xml` in one repo,
`cue_script.xml` in another; a procedure that hardcodes it skips a library silently and
completely), and whether `trash/` mirrors `projects/`.

### Feature 013 — device-class reshape (F6)

**Delivers**: a new hardware class costs data, not schema.

**Scope**: `<device class="…">` with XSD 1.1 `xs:alternative` conditional type assignment;
`_DEVICE_SECTIONS` derived from the document rather than declared
(`ConfigManager.py:69`); `node_hw_outputs`' fixed six keys become per-class.

| | |
|---|---|
| **Depends on** | nothing hard; **before 014** by advice |
| **Kind** | a rule-4 file-format migration — version step **and** conversion, per `specs/agreements/schema-evolution-convention.md` |

**Already proven** (2026-09-23, under the pinned `xmlschema==3.4.3`): a document carrying
`<device class="lighting">` validates with **no schema change**, while `<canvas_region>` on a
non-video device is still rejected. The mechanism works; the migration is the work.

**Today's cost of one new class, for the spec's motivation section**: ~20 sites across 4
schemas and 4 repositories, including four cue-type unions in
`../cuems-frontend/src/app/.../sequence.component.ts`.

### Feature 014 — `hardware_outputs` becomes real

**Delivers**: the missing layer — node **hardware capability**, split from project **mappings**.

**Scope**: the structure pass (DMX section, `id`/`name`/`mapped_to`, measured
`output_latency_ms`, transcribed geometry); registry bindings and model classes; a public
`ConfigManager` accessor; the port inventory moves out of `project_mappings`;
`default_mappings.xml` retires; `settings/outputs` retires (§4.2);
`get_{video,audio}_output_id` gets a real backing document or goes.

| | |
|---|---|
| **Depends on** | 013 (advice), and on 011 for anything that has to ship |
| **Repos** | this one, `cuems-nodeconf` (transcribes `display.conf`), `cuems-editor`/`cuems-frontend` (read the inventory from a new place), and **`cuems-hardware-discovery`, which has no checkout** |

**The seam that must be stated in the spec**, because it looks like two writers: discovery owns
the probed port inventory; nodeconf owns the transcribed geometry. They never write the same
element, so F1 holds at element granularity. `display.conf` keeps its videocomposer ownership at
run time — nodeconf transcribes its *contents* and records the provenance rather than claiming
authorship.

**Also settle**: X15, the namespace typo in `../cuems-engine/dev/test_xml_files/outputs.xml` —
the only instance outside this repo, and it declares `https://stagelab.coop/cuems` against a
`targetNamespace` of `https://stagelab.coop/cuems/`.

---

## 7. Traps — the register

Every entry here cost a revert, a destroyed file or a wrong claim during this work.

### 7.1 "Dead code" is not provable from this repo

`cuems-utils` is a library. A grep that finds no in-repo caller finds nothing at all. Check
`../cuems-engine`, `../cuems-editor`, `../cuems-frontend`, `../cuems-nodeconf`,
`../cuems-power-bridge` and `../cuems-common` before writing "unused" — and note that
`cuems-wsclient` **is** `cuems-power-bridge`, the same repository renamed, which once inflated
the ecosystem count from seven to eight.

This audit's own §4.2 claim ("read by nothing") was made that way and is only as good as that
sweep.

### 7.2 The golden harness, and the one file it must never regenerate

`tests/support/capture_goldens.py` was **unable to regenerate** between features 006/007 and
`c0fb614`: it reported ten permanent conflicts on a clean tree because `_json_bytes` was a bare
`json.dumps` while the contract tests compare through `roundtrip.json_dumps`. It is fixed.

**`tests/golden/outcomes.json` is not a regeneration target.** It records *pre-refactor*
verdicts, and `test_config_documents_fail_to_write_with_a_changed_exception_class` asserts the
**difference** between it and live behaviour. Running `capture_goldens --force` over it destroys
that baseline; the hazard is now recorded at the call site. Edit it surgically or not at all.

FR-021 stands: **a golden is never regenerated to make a test pass.** Re-basing is a recorded,
argued event — this feature has sanctioned exactly one, and diffed every file to confirm the
change was only what was intended.

### 7.3 Negative fixtures fail for a reason, and the reason is the assertion

When F3 retired `audio_cards`, `tests/data/corpus/negative/settings_bad_dmx_auto.xml` began
raising `XMLSchemaChildrenValidationError` (retired element) instead of `XMLSchemaDecodeError`
(its bad `auto` value). **It still failed, so the suite stayed green while the fixture tested
the wrong thing.** Any schema change must move the negative fixtures too, and must re-check
*which* error each one now raises.

### 7.4 `tests/data/corpus/pre-008/` is deliberately not migrated

It holds the v1 shapes that give the registered conversions their coverage. Migrating it would
delete the evidence that convert-on-read works. `test_pre008_corpus_retained.py` guards this.

### 7.5 Schema edits are visible by construction

`tests/contract/test_schema_scope.py` pins every schema's SHA-256. Changing a schema **requires**
updating `CURRENT_SCHEMA_HASHES` in the same commit, with the reason in the commit message. That
pairing is the whole mechanism — a reviewer sees the hash and the diff together. Do not exclude
a schema from the pin to avoid the update; the pin was already re-based once for exactly that
reason (§11) and a second exclusion round would leave it guarding nothing.

### 7.6 Rule targets are matched by string

`validators.register` binds T2 rules to `(class-name, field)` pairs matched against an object's
MRO **by string**. A rename that misses a rule key leaves the rule registered, reported as
registered, and never firing. `tests/contract/test_rule_targets_resolve.py` exists because
`NodeMappingType` nearly shipped that way.

### 7.7 Registry bindings: paths, and a sentinel that is a string

Document roots are bound by **path**, not type name — walking only `bound_type_names` reports
`CuemsScript` as unbound. And `Binding.model` is the sentinel **string** `"GENERIC"`, so the
filter is `isinstance(model, type)`, never a `None` check; getting it wrong raises
`AttributeError: 'str' object has no attribute '__name__'` from inside every parametrised case
at once.

### 7.8 Match names by segment, never by substring

Every root element here is `Cuems*`, and `"cue" in "cuems"` is true. F5's first implementation
reported all six schemas as show-layer violations for that reason alone. See
`test_duplication_flags._segments`.

---

## 8. What not to do

- **Do not narrow `UuidType` before `cuems-init-node` exists.** It invalidates every node
  identity in the field with nothing able to repair them.
- **Do not move the library version off `0.1.0rc16`.** `0.1.1` is reserved by
  `_deprecation.REMOVAL_RELEASE` and refused by three consumers' `<< 0.1.1~` ceilings; `rc17`
  would say nothing true. Schema changes are signalled by `doc_version`, not by the library
  version (§12).
- **Do not transcribe production configuration into a default.** Both audited machines predate
  this refactor. D15 corrected the values by *consumption* — who reads the field — and that is
  the method to repeat, not the result to copy.
- **Do not ship anything from this branch alone.** D27: nothing in this ecosystem releases by
  itself. The coordinated merge is what the `xml-refactor-merge-candidate` tag marks, and the
  tag comes after 011–014, not before.
