<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# What to do next — the xml-refactor, measured 2026-10-01

A sequencing decision: **013's SDD, the `cuems-editor` migration, the
`cuems-frontend` migration, or a combination.** Every number below was measured
today, not carried forward.

**Answer: the editor next, scoped to its deprecated-surface half, with 013's SDD
in parallel. The frontend waits for 013.** §4 is the reasoning; §5 is what would
change it.

---

## 1. Where everything actually is

| Repo | Flow | State | Candidate tag | Suite vs `cuems-utils` 012 |
|---|---|---|---|---|
| `cuems-utils` | — | 010 **59/118**; 011 82/82; 012 101/101 | **none** — D27 gates it behind 011–014, and 013/014 do not exist | 3247 passed |
| `cuems-common` | 03 | landed | `e3c9430`, pushed | no Python reader |
| `cuems-nodeconf` | 04 | landed; re-cut today for 012 | `5be6cf0`, pushed | **174 passed**; 173 + 1 skip pre-012 |
| `cuems-power-bridge` | 07 | landed, closed here | `399baf7`, pushed | 276 passed, both arms |
| `cuems-engine` | 01 | **landed** as its own 008 (64/64) | `1662a99`, **local only** | **923 passed**; *fails* pre-012 |
| `cuems-editor` | 02 | **not started** | none | 54 passed / 7 failed, both arms |
| `cuems-frontend` | 05 | **not started** | none | TypeScript; 5 spec files over 9184 LOC |

Four of six consumer flows have landed. Three remaining items of work: the
editor, the frontend, and 013/014 in this repository.

Two tag facts worth holding: **`cuems-engine`'s tag is not pushed**, so the
published set is still three of five cut; and **`cuems-engine`'s candidate is now
hard-coupled to feature 012** — `c31734c` imports `coerce_identity`, which does
not exist before it, so 23 of its test modules fail to collect against
`a451036`. Every other consumer's candidate still composes with either library.
That removes the engine from the independently-orderable set and is a real
constraint on merge order, not a detail.

## 2. The finding the decision turns on

**`cuems-editor` is the only thing standing between this repository and the rest
of feature 010.**

T049 requires an import census of the deprecated surface across all six
consumers, and **requires the value zero**. T050 re-runs it immediately before
T051. T051–T061 are structurally blocked on that zero (FR-090).

Census run 2026-10-01, excluding `specs/` and `.md`:

| Repo | Hits | Classification |
|---|---|---|
| **`cuems-editor`** | **4** | **live imports in shipped source** — `src/cuemseditor/CuemsDBProject.py:9,10` and `src/cuemseditor/repair_durations.py:39,40` |
| `cuems-engine` | 1 | `dev/CuemsEngine_old.py:13` — **not packaged**. `pyproject.toml` declares `packages include = "cuemsengine"`; `dev/` ships nowhere |
| `cuems-nodeconf` | 1 | **prose in a docstring** (`tests/test_no_injection.py`), naming the pattern it asserts is gone. Not an import |
| `cuems-power-bridge` | 0 | clean |
| `cuems-common` | 0 | clean |
| `cuems-frontend` | 0 | clean (TypeScript) |

```bash
grep -rnE "cuemsutils\.xml\.(Settings|XmlReaderWriter|Parsers|CMLCuemsConverter)|cuemsutils\.timeoutloop" \
  ../cuems-* | grep -vE "\.pyc|node_modules|/specs/|\.md:"
```

**What the editor therefore holds hostage**: the deletion of five modules
(`xml/Settings.py`, `xml/XmlReaderWriter.py`, `xml/Parsers.py`,
`xml/CMLCuemsConverter.py`, `timeoutloop.py`), the seven aliases in
`xml/__init__.py`, two deprecated-symbol sites, the retirement of 22 contract
tests, **and T060 — the `v0.1.1` version move that
`_deprecation.REMOVAL_RELEASE` has promised for two features**. Feature 010
cannot close while that promise is unkept.

Nothing else on the board unblocks it. The other five consumers are already at
zero.

## 3. What 013 and 014 move, and who reads it

This is the case *against* doing consumer migrations now, and it is real — but
it does not apply equally to the two consumers.

**Feature 013 (device-class reshape, F6)**: `<device class="…">` with XSD 1.1
`xs:alternative`; `_DEVICE_SECTIONS` derived from the document rather than
declared; **`node_hw_outputs`' fixed six keys become per-class**. Its own brief
prices one new class today at *"~20 sites across 4 schemas and 4 repositories,
including four cue-type unions in `../cuems-frontend/src/app/.../sequence.component.ts`"*.

Verified: those four unions are at
`src/app/components/projects/project-edit/sequence/sequence.component.ts:294-304`
— a 1662-line file, and **the same file US8's T032 names** as needing
characterization tests committed *before* the port.

**Feature 014 (`hardware_outputs` becomes real)**: the port inventory moves out
of `project_mappings`; `default_mappings.xml` retires; `settings/outputs`
retires; `get_{video,audio}_output_id` gets a real backing document or goes. Its
repo list names *"`cuems-editor`/`cuems-frontend` (read the inventory from a new
place)"*.

Verified: the editor reads `default_mappings.xml` at
`src/cuemseditor/cli.py:59`.

### The asymmetry, which is the whole answer

**The editor splits cleanly; the frontend does not.**

| | Editor | Frontend |
|---|---|---|
| Work US6/US8 asks for | 9 call sites in 2 files (1190 lines): 4 × `CuemsParser(data).parse()`, 2 × `XmlReaderWriter`, plus 3 in the repair tool | port `projects.service.ts` (640), `project-edit/sequence/sequence.component.ts` (**1662**), `settings.component.ts` (140) |
| Touched by 013 | **no** | **yes — `sequence.component.ts` is 013's named site** |
| Touched by 014 | **yes, but at one site that is not among the nine** (`cli.py:59`) | yes (the inventory read) |
| Characterization tests required first | its own suite exists (61 tests) | T032 requires them committed **before** the port; only 5 spec files exist today |

So the editor's deprecated-surface migration — the part that unblocks T049 — is
**orthogonal to 013 and 014**. Moving 9 call sites from `CuemsParser`/
`XmlReaderWriter` to `CuemsScript.load`/`save`/`from_json` changes *how it reads
a script*, not *what the hardware inventory looks like*.

The frontend's largest site is exactly what 013 reshapes. Porting it now means
porting it twice, and — worse — writing T032's characterization tests twice,
since they must precede each port.

## 4. The recommendation

**Do both of these, in parallel. They do not contend.**

### 4a. `cuems-editor` flow 02, scoped to the deprecated-surface half

Its bundle is already vendored at `specs/planning/xml-refactor/` (six documents)
and its prompt is at
`specs/planning/xml-rebuild/010-consumer-prompts/02-cuems-editor.md`.

**In scope** — the nine call sites, and the two things US6 asks for that are
actually the work:

- **T027a, the fixup split.** Delete the editor's dangling-reference walk (now
  the library's `target_resolves`, FR-043a, and deleting it is specified — two
  implementations of one repair is how they drift). **Keep** the DB-sourced
  duration correction, moved from dict-level to object-level. This is the
  thinking part, not the imports.
- **T028, `repair_durations.py` under a strict load path.** Feature 008 made
  reading strict; this tool's input is by definition damaged. Measured today: it
  already wraps its read in `try/except Exception` and reports
  `SKIPPED_INVALID`, so strictness **degrades** it rather than breaking it — and
  the documents it repairs are corrupt in *duration values*, which stay
  schema-valid. But they are version-1 scripts, so they now convert in memory on
  read and are written back at version 2. That is a conversion performed by a
  repair tool, and it needs recording rather than discovering.
- The two test modules that have not imported since feature 008 retired
  `cuemsutils.create_script`, and the 7 pre-existing failures in
  `test_nodelist_actions.py`. Both predate this work; neither should be carried
  through a migration.

**Explicitly deferred to 014**: `cli.py:59`'s `default_mappings.xml` read and
anything else that touches the port inventory. Record the deferral in the flow's
own tasks so it is a decision and not an omission.

**Why this ordering is safe**: the editor's nine sites move onto public API that
011 and 012 have already settled, and 013/014 do not touch that API.

### 4b. Feature 013's SDD, here

Specification work in this repository. It does not touch the editor's
deprecated-surface path, it contends for nothing the editor flow needs, and its
output is the precondition the frontend is waiting on.

It also has a dependency worth stating early: 013 is *"a rule-4 file-format
migration — version step **and** conversion"*, so it inherits feature 012's
machinery and its lesson. 012 registered **no** conversion deliberately (the
repair was cross-document); 013's **does** need one, which makes it the first
real exercise of the registry since feature 008's `script` 1→2.

### 4c. `cuems-frontend` flow 05 — **after 013 lands**

Two reasons, and the first is sufficient: its principal site is 013's principal
site, and T032's characterization tests must precede the port.

The second: 010 already records that *"the adoption/liveness UI tier does not
exist"*. That is **new feature work, not a migration**, and bundling it into
flow 05 would make a migration's completion depend on a product decision. Split
it out before starting, whenever that is.

## 5. What would change this answer

- **If `v0.1.1` is not wanted soon.** The editor-first argument rests on T049
  → US10 → the version move. If the release can wait, the ordering is free and
  013-then-frontend-then-editor is defensible.
- **If 014 turns out to reach `CuemsDBProject.py`** — not just `cli.py:59`. The
  measurement says it does not, but 014 is unspecified; its SDD could widen.
  Re-run the two greps in §2 and §3 before committing to the scope split.
- **If the editor's fixup split proves larger than specified.** T027a is the one
  item here whose size is specified rather than measured. If it turns out to
  touch the save path broadly, the "orthogonal to 013/014" claim weakens and the
  work should be re-sized before continuing.

## 6. Items this does not sequence, carried so they are not lost

- **`cuems-engine`'s tag is not pushed.** Three of five cut tags are published.
- **`cuems-utils` has no tag and cannot have one** until 013/014 exist (D27).
- **UR-1 and UR-5 are open** (`migration-guide.md` §5b): no public adoption
  partition, and `validate`'s deprecation advice fits only scripts. Both are the
  same shape — a capability inside `cuemsutils.xml` with no public path out —
  and both are natural candidates for 013/014's public-surface pass rather than
  for a feature of their own.
- **T025 clause (a)** needs two hosts. Hardware debt, independent of everything
  above.
- **Two §10.7 items** from feature 012 remain unconfirmed on hardware, mitigated
  by design (`specs/012-uuid4-convergence/baseline.md` §7).
