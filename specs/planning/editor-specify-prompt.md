<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Prompt — start `cuems-editor`'s `001-cuems-utils-migration` specification

**Paste everything below the rule into a new session running in
`/disk/Projects/StageLab/cuems-editor`.** It is written for a session with no
memory of the `cuems-utils` work: everything it cannot discover from its own
repository is inlined.

Authored in `cuems-utils` at `specs/planning/` (this project's canonical home for
agent prompts). Measured 2026-10-01.

---

You are starting the specification for `cuems-editor`'s feature
**`001-cuems-utils-migration`** — flow 02 of the seven-repository CueMS
xml-refactor, and the **last Python consumer** that has not migrated.

Branch: **`feat/xml-refactor`**, already checked out, already based on
`feat/nodelist-adoption-api` as the flow requires. Do not re-base it.

## 1. Read these first, in this order

All five are **in this repository**. The bundle was derived 2026-09-25 from
`cuems-utils`' upstream prompt and re-verified against the live tree; where the
two differ, the bundle wins.

| Order | Document | Why |
|---|---|---|
| 1 | `specs/planning/xml-refactor/00-runnable-flow.md` | **the flow to run.** §3 carries a context block meant to be pasted verbatim into `/speckit.specify`; §4 the chain, §5 what `/speckit.clarify` must force, §6 exit criteria, §8 traps |
| 2 | `specs/planning/xml-refactor/04-wire-contract.md` | the payload contract. The flow says read this one first for a reason — the two-delta constraint is the sharpest thing in the feature |
| 3 | `specs/planning/xml-refactor/03-migration-inventory.md` | the inventory, per call site, with both `rc1` and base-branch line numbers |
| 4 | `specs/planning/xml-refactor/01-settled-decisions.md` | the eleven decisions that bind this repository |
| 5 | `specs/planning/xml-refactor/02-consumer-audit-findings.md` | C2, C3, C4, C5, C11 |

Then `.specify/memory/constitution.md` — **ratified today, 1.0.0**, and the
reason this feature exists in the form it does. See §4.

**§2 of the flow ("Constitution — write one, this repository has none") is
done.** Skip it.

## 2. What has changed since the bundle was derived — §0 and §7 are stale

The bundle's state table and tag table were measured 2026-09-25. Both have
moved. Use the values here.

| Bundle says | Actually, 2026-10-01 |
|---|---|
| Spec-kit **absent**, added on first run | **present** — `.specify/` and `.claude/` exist |
| Constitution **absent**, written on first run | **present and ratified**, 1.0.0, 2026-10-01 — but **untracked**. `git status` shows `?? .specify/` and `?? .claude/`. **Commit it before `/speckit.specify`**, or the feature's first commit will bury the governance it is judged against |
| Checked-out branch `rc1` | **`feat/xml-refactor`** at `33d6915`, one commit (the bundle vendor) above `feat/nodelist-adoption-api`'s tip `886f649` |
| Existing features: none | still none. `specs/` holds only `planning/`. This becomes `001-cuems-utils-migration` |
| "Three siblings have already cut their tags" at `d5c4226` / `3af31cc` / `6c0cca7` | **four have, and every one of those three SHAs has moved** — see §3 |

## 3. Ecosystem state, inlined — you cannot discover this from here

Four of six consumer flows have landed. **This repository is one of the two that
have not**, and it is the one everything else is waiting on (§5).

| Repo | Flow | State | Candidate tag |
|---|---|---|---|
| `cuems-common` | 03 | landed | `e3c9430`, pushed |
| `cuems-nodeconf` | 04 | landed; re-cut 2026-10-01 for `cuems-utils` 012 | `5be6cf0`, pushed |
| `cuems-power-bridge` | 07 | landed, closed | `399baf7`, pushed |
| `cuems-engine` | 01 | **landed** as its own `008-cuems-utils-migration`, 64/64 | `1662a99`, cut 2026-10-01, **not pushed** |
| **`cuems-editor`** | **02** | **not started — this feature** | — |
| `cuems-frontend` | 05 | not started; **deliberately after `cuems-utils` 013** | — |
| `cuems-utils` | — | 011 and 012 **landed on their branches**; 013/014 not begun | none — tags **last**, by D27 |

### The `cuems-utils` features that have landed since the bundle, and what they mean here

- **011 `/etc/cuems` first install.** A plain `apt install` leaves a node that
  loads and is unique. New entry point `cuems-init-node`. Identity minting moved
  off `cuems-config-node`.
- **012 uuid4 convergence.** Three schemas narrow their node-identity type to
  **uuid4 lowercase plus the not-provisioned sentinel**
  (`00000000-0000-0000-0000-000000000000`) — `network_map` 1→2,
  `project_mappings` 1→2, `settings` 2→3. Three things follow for this feature:
  1. **A node identity that is not uuid4 is now refused on read and on write.**
     Measured: this repository is **unaffected** — 54 passed / 7 failed,
     identical before and after. Its fixtures carry no non-uuid4 node identity.
     `cuems-nodeconf` was the only repository that broke, on four test fixtures.
  2. **`ConfigManager.node_uuid` now answers with `Uuid` on a provisioned node**
     and with the sentinel string on an unprovisioned one. `Uuid` compares and
     hashes like its string and now **sorts**, but it is **not a `str`
     subclass**. `CuemsWsUser.py:407` does
     `if not node_uuid or not isinstance(node_uuid, str)` — fed from the
     websocket, so unreachable today. **Keep it unreachable**: do not let a
     library identity into a wire payload.
  3. **`cuemsutils.tools.coerce_identity`** is published — the rule that turns a
     raw value into an identity (uuid4 → `Uuid`, anything else non-empty
     unchanged, empty → `None`). If this feature needs to compare an identity
     from JSON against one from the map, use it. `cuems-engine` deleted its own
     hand-written copy in favour of it.
- **A node identity collision now raises.** `network_map` with two rows sharing
  one identity used to load, silently collapsing the duplicate. It now raises
  `ValidationError` for every reader. **This repository is a map reader** and
  this is relevant to §6.
- **No `cuems-utils` rollback once the stack restarts.** The three schemas took a
  version step, so a document **written** by the new library carries a marker the
  old one refuses. Nothing for this feature to do; know it before an upgrade
  window.

## 4. What this feature actually is, in constitutional terms

Your constitution was ratified **today**, and it records its own violations at
ratification. **Principle V — "cuemsutils Is Consumed Through Its Public
Surface" — is violated by this repository right now**, and closing that
violation is what this feature is.

> Imports MUST come from the surface `cuemsutils` declares public.
> `cuemsutils.xml` is internal machinery (`__all__ == []`), and any import from
> it or its submodules is a violation. … If something needed exists only
> internally, **the gap is the library's to close. Raise an upstream report. Do
> not work around it here.**

That last sentence is load-bearing and §6 is where it bites.

**The census, measured 2026-10-01** — seven imports, three shipped files:

| File:line | Import | Kind |
|---|---|---|
| `src/cuemseditor/CuemsWsServer.py:26` | `from cuemsutils.xml import NetworkMap` | deprecated **alias** |
| `src/cuemseditor/CuemsWsServer.py:27` | `from cuemsutils.create_script import create_script, new_uuid` | **module already deleted** |
| `src/cuemseditor/CuemsDBProject.py:9` | `cuemsutils.xml.Parsers.CuemsParser` | deprecated shim |
| `src/cuemseditor/CuemsDBProject.py:10` | `cuemsutils.xml.XmlReaderWriter.XmlReaderWriter` | deprecated shim |
| `src/cuemseditor/repair_durations.py:39` | `cuemsutils.xml.Parsers.CuemsParser` | deprecated shim |
| `src/cuemseditor/repair_durations.py:40` | `cuemsutils.xml.XmlReaderWriter.XmlReaderWriter` | deprecated shim |
| `tests/test_repair_durations.py:6` | `cuemsutils.xml.XmlReaderWriter.XmlReaderWriter` | deprecated shim |

```bash
grep -rnE "cuemsutils\.(xml|timeoutloop|create_script)" src tests | grep -v '\.pyc'
```

## 5. Why this is the critical path for the whole ecosystem

Inline this in the spec's motivation, because it is the strongest argument the
feature has and it is invisible from inside this repository.

`cuems-utils`' feature 010 has a gate, **T049**, that requires an import census
of its deprecated surface across all six consumers to **record zero**. Its
T051–T061 are *structurally* blocked on that zero. Measured 2026-10-01:

| Repo | Hits | Classification |
|---|---|---|
| **`cuems-editor`** | **6 in shipped `src/`** | **the only live ones** |
| `cuems-engine` | 1 | in `dev/CuemsEngine_old.py` — **not packaged** |
| `cuems-nodeconf` | 1 | **prose in a docstring**, not an import |
| `cuems-power-bridge`, `cuems-common`, `cuems-frontend` | 0 | clean |

So this repository alone holds: the deletion of five `cuemsutils` modules, seven
deprecated aliases, two deprecated-symbol sites, the retirement of 22 contract
tests — **and the `v0.1.1` version move that `cuemsutils`'
`_deprecation.REMOVAL_RELEASE` has promised for two features.** Feature 010
cannot close while those seven imports exist.

## 6. The decision the bundle does not frame — settle it in `/speckit.clarify`

`CuemsWsServer.py:26` imports the deprecated `NetworkMap` alias for exactly one
call, at `:478`:

```python
nodes, new_nodes = NetworkMap.get_nodes_by_adoption(network_map_dict)
```

Three facts collide here, and the bundle predates the third:

1. `get_nodes_by_adoption` is itself **deprecated** — it mutates its argument,
   which is the opposite of what the replacement promises.
2. Its documented replacement, `partition_by_adoption`, lives on
   `cuemsutils.xml.settings.NetworkMap` — **inside the internal package**.
   There is **no public path to it**. `cuems-engine` reported this as
   `UR-1-no-public-adoption-partition`; `cuems-utils` records it as **open** in
   `specs/010-consumer-migration/migration-guide.md` §5b.
3. **`cuems-engine` resolved it by deleting its caller.** Its `find_hosts` and
   the `get_nodes_by_adoption` call are gone, adopted-node selection is computed
   from the map it already holds, and its `tests/test_public_surface.py` asserts
   all three names absent so the deletion cannot be undone by re-spelling.

Principle V says the gap is the library's to close and forbids working around it
here. So there are exactly three honest options, and the spec must pick one
rather than discover it mid-implementation:

| Option | Shape | Cost |
|---|---|---|
| **A** | Raise an upstream report asking `cuemsutils` to publish `partition_by_adoption`, and **block** this call site on it | correct per Principle V, but puts this feature — the ecosystem's critical path — behind a library release |
| **B** | Compute the partition here from `ConfigManager.network_map`, as the engine does. Not a re-implementation of a *model* (Principle V's third bullet) — it is a two-line selection over an object the library hands you | unblocks immediately; needs the spec to say explicitly that it is a selection and not a ported model, or it reads as a violation |
| **C** | Raise the report **and** take B, recording B as the interim with the report as its successor | both; most honest; two things to track |

**Recommended: C.** It matches what the engine actually did (it reported *and*
removed its need), it does not block the critical path, and it leaves the
library's gap recorded rather than silently routed around. Say so in the spec,
with the report filed under `specs/001-cuems-utils-migration/upstream-reports/`
following `cuems-engine`'s convention.

## 7. TASK ZERO is three things, not one

The bundle's §3 context block says *"`CuemsWsServer.py:24` imports
`create_script` and `new_uuid` from a module 008 deleted"*. Correct in substance,
two corrections in detail:

- the line is **`:27`**, not `:24` — the base branch is 88 lines longer than
  `rc1`;
- it names one import and there are **two adjacent ones**, with three separable
  problems.

Verified today — the server does not import at all:

```
$ python -c "import cuemseditor.CuemsWsServer"
ModuleNotFoundError: No module named 'cuemsutils.create_script'
  File ".../CuemsWsServer.py", line 27
```

| # | Problem | Resolution | Blocking? |
|---|---|---|---|
| 0a | `new_uuid` from the deleted module | re-source from `cuemsutils.helpers` — **four other files in this repository already do exactly that** (`CuemsDBMedia.py:6`, `CuemsDBProject.py:11`, `db.py:4`, `CuemsWsUser.py:7`) | **yes** — one line, do it first |
| 0b | `create_script()` at `:87` → `self.initital_template` *(the typo is in the source)* | the descriptor work. `cuemsutils` publishes a schema descriptor and `generate_script_example()`; which to use is a real decision | **no** — separable from 0a |
| 0c | `from cuemsutils.xml import NetworkMap` at `:26` | §6's decision | **no** — separable from 0a |

**Do 0a alone, first, and verify the process starts.** Do not let 0b's template
decision or 0c's partition decision hold the import fix hostage; they are three
problems on two adjacent lines and only one of them blocks every other task.

## 8. Scope — defer the hardware inventory to `cuems-utils` 014

`cuems-utils` 014 (`hardware_outputs` becomes real) **moves the port inventory
out of `project_mappings`** and **retires `default_mappings.xml`**. This
repository reads it at `src/cuemseditor/cli.py:59`:

```python
settings_file = cf_manager.conf_path('default_mappings.xml')
```

That read is **not** one of the seven imports in §4 and is **not** on the
critical path in §5. Migrating it now means migrating it twice.

**Declare it out of scope, in the spec, as a deferral rather than an omission** —
with a named successor (`cuems-utils` 014) so it is findable. The same applies to
anything else that reads the port inventory.

This is the scope split that makes this feature small enough to be the next
thing done. Do not let it widen.

## 9. What `/speckit.clarify` must force

The flow's §5 has its own list — run it. Add these four, which postdate it:

1. **§6's option A, B or C.** Recommended C. Do not leave it implicit.
2. **`repair_durations.py` under a strict load path.** `cuems-utils` 008 made
   reading strict; this tool's input is corrupt by definition. Measured: it
   already wraps its read in `try/except Exception` and reports
   `SKIPPED_INVALID`, so strictness **degrades** it rather than breaking it, and
   the documents it repairs are corrupt in *duration values* that stay
   schema-valid. **But they are version-1 scripts**, so a repair run now
   converts them to version 2 in passing and writes that back. Is that wanted?
   It is a document rewrite nobody asked this tool to perform. Decide and record.
3. **The two test modules that have not imported since feature 008** —
   `tests/test_media.py` and `tests/test_repair_durations.py` both import
   `cuemsutils.create_script`. In scope or not? They have been broken silently
   for two features, which is itself the argument for in.
4. **The 7 pre-existing failures** in `tests/test_nodelist_actions.py`
   (`TestNodeconfAvailableFlag`), identical before and after `cuems-utils` 012.
   Unrelated to this migration. Fix, or record as pre-existing with a named
   owner — but do not carry them silently through a migration and let them look
   like its doing.

## 10. Traps

The flow's §8 has the repository-specific ones. These are the cross-repository
ones measured in the last week:

- **Do not regenerate a golden to make a test pass.** `cuems-utils` sanctions
  exactly one re-base per feature, argued and diffed. The same discipline
  applies to any payload fixture here — and §2 of the wire contract is the
  reason: the two-delta constraint is only evidence if the baseline predates the
  change.
- **Do not pin `cuemsutils` to an older version** to make something go away.
  `pyproject.toml:27` declares `cuemsutils>=0.1.0rc10`, an open floor with no
  ceiling, and your constitution records that as a violation at ratification.
  Bounding it on both sides is in scope; lowering it is not.
- **Do not cut the candidate tag yourself.** Moving or creating a published tag
  in this ecosystem is the maintainer's call. Prepare the message — the
  convention is a file in `../.xml-refactor-tag-messages/` applied with
  `git tag -a -F` — and say the tag is ready.
- **A fifth consumer repository exists that is easy to miss.**
  `cuems-power-bridge` **is** `cuems-wsclient`, renamed in 2026-06;
  `../cuems-wsclient` is a stale checkout 30 commits behind. Never census it.
- **Commits in this ecosystem are GPG-signed.** On `gpg failed to sign`, retry;
  never `--no-gpg-sign`.

## 11. Run it

```bash
# 0. the governance is untracked — commit it before the feature's first commit
git add .specify .claude && git commit   # "chore: spec-kit and the ratified constitution"

# 1. then
/speckit.specify
```

Paste the bundle's **§3 context block verbatim** into `/speckit.specify`, then
add, in your own words, the four things from this prompt that the block
predates: §3's ecosystem state, §5's critical-path argument, §6's partition
decision, and §8's deferral of the hardware inventory to 014.

Expected feature directory: `specs/001-cuems-utils-migration/`.

## 12. If something does not match

Measured 2026-10-01 against `cuems-editor` `feat/xml-refactor` @ `33d6915` and
`cuems-utils` `012-uuid4-convergence` @ `eed7eb5`. Line numbers move; the
*imports* in §4 are the thing to grep for, and the command is there. If the
count is no longer seven, re-run it and say so in the spec rather than
reconciling silently — a census that changes between measurement and use is the
failure `cuems-utils`' T050 exists to catch.
