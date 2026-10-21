<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Research: Release-line reconciliation before `0.1.1`

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-10-21

The Technical Context had **no `NEEDS CLARIFICATION`**: clarify closed all twelve of the work
order's §12 questions (spec, Clarifications). This file holds:
- the **re-measurement** made at plan time (R1–R2);
- the **design decisions** the plan needs, each read from code rather than assumed (R3–R12);
- the work order's **measured findings** §2, §4.1, §6 and §12, carried here because the work order
  is deleted as 017's last task (FR-060).

The work order is `specs/planning/release-line-reconciliation-0.1.1.md` at `2318dee`. Its numbers
are reproduced, not re-derived, wherever R1 confirms they still hold.

---

## R1 — The lines, re-measured 2026-10-21

`git fetch --all --tags --prune` first, then:

| Ref | 2026-10-17 (work order §2) | 2026-10-21 | Moved? |
|---|---|---|---|
| `origin/debian/bookworm` | `398a9cf` | `398a9cf` | no |
| `origin/main` | `23e4752` | `23e4752` | no |
| `origin/feat/xml-refactor` | `5e4c637` | **`2318dee`** | yes: the pre-spec commit was pushed |
| `xml-refactor-merge-candidate^{commit}` | `4b336cd` | `4b336cd` | no |
| `HEAD..origin/debian/bookworm` | 77 | 77 | — |
| `HEAD..origin/main` | 11 | 11 | — |

The newest tags are still `debian/0.1.0rc17` and `v0.1.0rc17`. No `release/0.1.0rc18` head and no
`debian/0.1.0rc18` tag exist. The spec's snapshot holds, and the §3 trial merge figures (11
conflicting files, 25 hunks) are expected to reproduce. They are re-measured at implementation
start (FR-004).

**Decision.** Arm A of every two-armed comparison stays **`5e4c637`**. `2318dee` differs from it
only by `specs/planning/release-line-reconciliation-0.1.1.md`, which no test reads.
**Rationale:** the work order's §6.1 numbers are against `5e4c637`, and keeping the arm means that
comparison stays direct. **Alternative:** arm A = `2318dee`. Rejected because it gives the same
tree under a different name, and every cited figure would then need a footnote.

## R2 — Stray sweep, re-run 2026-10-21

`git rev-list --no-merges --count <ref> ^HEAD ^origin/debian/bookworm` was run over every
`refs/remotes/origin/*` and `refs/tags/*`. **The same five refs as on 2026-10-17, nothing new:**

| # | Ref | Commit | Verdict (binding, FR-005) |
|---|---|---|---|
| 14 | tag `v0.0.9rc7` | `b0df231` 2025-09-05 "fix: improve properties typing" | **Code: none.** `git diff v0.0.9rc7 v0.0.9rc8 -- src/cuemsutils/cues/{CuemsScript,MediaCue}.py` is empty, and rc8 is an ancestor. **Q9:** a `git merge -s ours v0.0.9rc7` (third merge, tree diff empty) makes it an ancestor. `CHANGELOG.md`: covered by the "Earlier releases" pointer |
| 15 | `origin/feat/faders` | `17436b0` 2026-04-27 | **Exclude.** An engine-facing briefing for a CTimecode migration that has landed (features 002–003). This repository's `docs/` is end-user only |
| 16 | `origin/options` | `a224e9f` 2025-02-26 | **Exclude.** Logger renames, superseded by `log.py`'s history |
| 17 | `origin/parser-fixxes` | `8c86761` 2025-04-02 | **Exclude.** For the legacy parser tree, which 006 deleted |
| — | `origin/gh-pages` | `dc2aab6` "Deployed 23e4752" | Not source |

The other branch heads are all already in one of the two lines, including every `feat/*` and
`fix/*` head (`feat/stop-project-actiontype`, `fix/debian-replaces-engine-cffi-gen-src`,
`feat/869fat84r-media-dimensions`, the `fix/ctimecode-*` series, `fix/journal-log-duplication`,
`fix/media-duration-tightening`, `fix/mtc-bias-compensation`…). FR-004 re-runs this sweep before
hand-off, because the release line's author works on PR branches and Q10 lets that line keep
releasing.

---

## R3 — A-1: where the targetless set lives, and its name

**Decision.** A module-level `frozenset` in `src/cuemsutils/cues/ActionCue.py`:

```python
#: Action types that act on the whole loaded project and take no target
#: (feature 017, A-1). Consulted by three T2 rules — ``action_target_required``
#: (passes ``None``), ``action_target_resolves`` (skips), and
#: ``project_action_takes_no_target`` (repairs a leftover target to ``None``) —
#: and by ``ActionCue.__init__`` / ``set_action_target`` (``from_json`` reaches
#: those two). Adding a value is a one-line change here plus its own test.
TARGETLESS_ACTION_TYPES: frozenset[str] = frozenset({"stop_project"})
```

**Rationale.**
- **The domain owns the set.** Whether an action needs a target is a property of the action
  vocabulary. The rule, the guard and the constructor all ask the model the same question.
- **No import cycle.** `xml/validators.py` imports only `dataclasses` and `typing` at module level,
  and every model import inside it is local to a function (`from ..cues.Cue import Cue` inside the
  walk). The rule imports the set the same way. `ActionCue` already imports `validators` inside
  `set_action_target`.
- **`frozenset`** follows the repository's convention for closed sets (`STRING_TYPED_KEYS`,
  `DELIBERATE_IDENTITY_STEPS`) and cannot be mutated at runtime.

**Alternatives.**
- Put it in `validators.py`. Rejected: the constructor would then import the T2 tier to construct
  a cue, which reverses today's direction.
- Derive it from the schema, e.g. `*_project` values or an `xs:annotation`. Rejected for two
  reasons. Q1 chose `stop_project` only, so a naming rule would sweep in `pause_project` and
  `resume_project`. And an annotation reader is new machinery for one value.
- Export it publicly from `cuemsutils.cues`. Rejected: no consumer asked for it, and adding it
  would be a public-API change that FR-026a does not record. If the editor or frontend later want
  it, they ask through an upstream report.

## R4 — A-1: the three consultation points, read from code

Probed on `2318dee` with the hatch `test.py3.11` interpreter (CPython 3.11.9):

| Point | Today | After A-1 |
|---|---|---|
| T2 rule `action_target_required` (`xml/validators.py:541-551`) | `if value is None: raise ValueError("action_target is required")`. The walk (`_iter_t2_findings`, `:440-446`) calls `rule.check(node[field], node)` with **the `ActionCue` itself as `obj`** | `if value is None and (obj is None or obj.get("action_type") not in TARGETLESS_ACTION_TYPES): raise …`. Same message (FR-UX-001), still `repairable=False` |
| `ActionCue.__init__` (`cues/ActionCue.py:37-40`) | raises when `init_dict` carries `action_target: None`, whatever the action type | raises only when `init_dict.get("action_type")` is **not** in the set. It reads the type from `init_dict`, because population order is not guaranteed |
| `ActionCue.set_action_target` (`:58-87`) | after `_initialized`, `enforce('action_target_required', value, self)` | unchanged code. `enforce` already passes `self`, so the rule's new branch covers it |
| `from_json` | goes through `__init__` | covered by row 2 |

**Measured facts that shape the tests:**
- `ActionCue({'action_type': 'stop', 'action_target': ''})['action_target']` is **`None`**: the
  refactor's coercion maps `""` to `None` at construction. This is A-3a's cause. rc17's
  "constructor accepts an empty target" is therefore re-expressed as "a `stop_project` cue with no
  target constructs, and its target is `None`".
- **The writer already emits `<action_target />` for `None`.** On a loaded corpus document with an
  `ActionCue`'s target forced to `None`, `_build_tree()` writes `b'<action_target />'`. T1 accepts
  it: the element is required, and `TargetType`'s pattern admits `()`. The **only** violation is
  `T2 action_target_required`. So A-1 needs **no writer or reader change**; the empty element
  already round-trips to `None`.
- **Setting `action_type` after construction** (e.g. `stop_project` → `stop` with a `None` target)
  is not caught at assignment, because `set_action_type` runs no rule. It is caught at `save`
  (T2). This is unchanged behaviour, and FR-023's "no path changes a cue's `action_type`" test
  pins the save-time refusal.

**Decision.** The changes above, in one commit with A-2d's hash (FR-025), red tests first
(FR-021, FR-023). *(Revised 2026-10-21: Q2 revisited adds the repairable rule
`project_action_takes_no_target` and its two companion edits. See R16.)*

## R5 — A-1 fixture capture (FR-022)

**Decision.** Capture with rc17's own writer in a scratch worktree at `398a9cf` (work order §13),
using `XmlReaderWriter.write_from_object` on objects built in rc17's own model:
- a `VideoCue` with `pixel_width=1920`, `pixel_height=1080`, `file_size=107374182400` and an
  **uppercase** md5, which rc15's setter lowercases on write;
- an `AudioCue`;
- an `ActionCue` with `action_type="stop_project"` and `action_target=""`.

The control twin replaces the last cue with `stop` aimed at the audio cue. Both files go to
`tests/data/rc17/` with a `PROVENANCE.md`: commit, interpreter, the capture script, the
date and each file's sha256. Being pre-013 in shape (`True`/`False`, bare duration, no
`doc_version`) is the point of the fixture: it exercises reshape → convert → load.

The capture script lives in `specs/017-…/tools/capture_rc17_fixture.py`, so the provenance can be
re-run. **Alternative:** hand-write the XML. Rejected: S-1′ is about what rc17 *actually writes*,
and a hand-written file would only test our belief about that.

## R6 — S-3 report (FR-029c): what "the loader's own check" means

**Decision.** After each write, both tools validate the written document **through the same
function the loader uses**. For a script that is `CuemsScript.load_with_report`'s T1 + T2 path,
applied to a throwaway copy, as `cuems-reshape-devices` already does for its T1 pre-write check
(013: "validates the reshaped tree as the load path will see it"). The finding is reported:
- as a WARNING through the tool's existing logger: `<path>: would be refused on load: [T2]
  <rule> at <cue>/<field>: <message>`;
- as a new summary bucket. `cuems-convert-documents` already summarises like `--check` (010
  T068); its outcome buckets are read at implementation time, and the new one is named after the
  existing convention there.

The exit status and the written bytes are unchanged (Q3). **Cost:** one extra validation per
written document, and documents the tool skipped are not re-validated. It is measured interleaved
A/B over `tests/data/corpus/` and recorded in `evidence/perf.md`, without a budget (013's
SC-PERF-003 precedent).

**Alternative:** run T2 *before* writing and refuse. Rejected by Q3 (option C).

## R7 — FR-012: the rc15 legacy edits' behaviours on the public path

The rc15 legacy edits provide two behaviours (Q5):

| Behaviour | Public-path status, from 014's record | Planned check |
|---|---|---|
| An all-digit `file_md5` reads back as `str` | **Held** (014: the adapter table binds types, and `Md5Type` restricts `xs:string`, so `STRING_TYPED_KEYS`' defect class cannot recur) | A public `save` → `load` test with an all-digit 32-char md5 asserts `type(...) is str` |
| The four media children are written in schema order | **Expected to hold**: the mapper emits in `content.iter_elements()` order (004), except for `xs:all` types, and `MediaType` is a sequence | A public `save` test asserts the element order of `<Media>` children against the XSD's declared order |

**Decision.** Write both tests red-first against the merge commit. If either is already green
there, the evidence records "**held; no port needed**" rather than inventing a red. FR-080's
red→green obligation attaches to **adaptations**, and a check that passes from the start is not
one. Only a failing check becomes an adaptation commit.

## R8 — FR-026a: extending the snapshot to `MediaCue`

`tests/contract/test_public_api_surface.py:47` has `PUBLIC_CLASSES = {CuemsScript, ConfigManager,
ConfigBase, NodeIndex}`. `tests/golden/api/public_api.json` is the snapshot, and
`tests/contract/test_golden_immutability.py`'s docstring records every earlier re-hash: 009, 011,
013, axis D (twice), and foreign-controller scoping.

**Decision.** Add `"MediaCue": ("cuemsutils.cues.MediaCue", "MediaCue")`. The `MediaCue` block is
inserted into `public_api.json` **by hand, in sorted position**. The diff between the old and new
JSON must show **only added lines** (evidence: `git diff --stat` plus a script asserting that every
removed line count is 0). Then `MANIFEST.sha256` is updated for that one file, and a paragraph is
added beside the earlier re-hash paragraphs. This runs **after** A-1, A-3 and A-4, because those
settle `MediaCue`'s surface. **Alternative:** re-cut the whole golden with the generator.
Rejected: it would re-serialize unrelated entries, and 015 S3 made "surgical, not re-cut" the rule
for baseline goldens.

## R9 — Changelog completeness test (FR-033): the released sets

**Decision.** The test carries three sets as data, measured 2026-10-21:
- **Debian**: every non-`UNRELEASED` header of `origin/debian/bookworm:debian/changelog`.
- **PyPI**: PyPI's JSON API (`https://pypi.org/pypi/cuemsutils/json`, `releases`, yanked files
  included). That API is used rather than `pip index`, which omits yanked releases.
- **Never published**: versions that were set in the source but released nowhere.

They are re-measured at hand-off (Q7).

```python
RELEASED_DEBIAN = {"0.1.0rc8", "0.1.0rc9", "0.1.0rc10", "0.1.0rc11", "0.1.0rc12",
                   "0.1.0rc14", "0.1.0rc15", "0.1.0rc16", "0.1.0rc16+1", "0.1.0rc17"}
RELEASED_PYPI   = {"0.1.0rc7", "0.1.0rc8", "0.1.0rc10", "0.1.0rc11",       # ≥ 0.1.0rc5 only
                   "0.1.0rc14", "0.1.0rc15", "0.1.0rc16"}
NEVER_PUBLISHED = {"0.1.0rc5", "0.1.0rc6", "0.1.0rc13"}
```

**⚠ Correction to the work order (§7.2): `0.1.0rc5` and `0.1.0rc6` were never published.**
§7.2's table gives "rc8, rc7, rc6, rc5: PyPI". Measured 2026-10-21, PyPI's 0.1.0 line is rc1–rc4,
rc7, rc8, rc10, rc11 and rc14–rc16, with **no rc5 or rc6, not even yanked**. Neither has a git tag
(only `v0.1.0rc7` exists in that range). rc5's Debian entry is `UNRELEASED`, and rc6 has no Debian
entry. Both are source versions that already have `CHANGELOG.md` sections (2026-04-22,
2026-04-27). So they are in rc13's situation, except that they carry a section.
- **Decision**, applying Q7's intent (a reader must not mistake an unpublished version for an
  installable one): their existing sections are **kept** and marked "(never published: no Debian
  build, not on PyPI)". rc13, which has no section, gets the one line Q7 asked for.
- **Consequence for D3.** "Complete from `0.1.0rc5`" stays true as a range. The earliest released
  version in it is rc7 (PyPI) or rc8 (Debian).
- **Not a reason to stop:** this changes FR-032's marking list and FR-033's check (6), and nothing
  else. It is applied to the spec as a measured correction (spec, Clarifications).

From these sets, `RELEASED_DEBIAN − RELEASED_PYPI` = {rc9, rc12, rc16+1, rc17}. That set is what
the "Debian only" check (6) covers. rc16+1 is a Debian revision, written as a `<!-- debian: … -->`
comment under rc16, so check (6) applies the marking to **sections**, and to comments by their
form. `RELEASED_PYPI` is checked against `pip index versions cuemsutils --pre` at hand-off, and
that output is kept in evidence.

The git cross-checks (2)'s ref half and (3) use `git rev-parse --verify` with
`subprocess.run(..., check=False)`. When a ref is absent, they `pytest.skip` with the reason, as
`tests/support/sibling_tags.py` does. Byte comparison works on the entry block exactly as
`dpkg-parsechangelog` delimits it, from the header line through the trailer line.

**Fail-before.** It must fail on `5e4c637`, where four of the `RELEASED_DEBIAN` headers (rc15
released, rc16, rc16+1, rc17) are missing or are a different entry.

## R10 — Directory markers (FR-063)

**Decision.**
- In `tests/conftest.py`, a `pytest_collection_modifyitems` hook adds
  `item.add_marker(<dir>)` for `<dir>` ∈ {`unit`, `integration`, `contract`, `packaging`}, taken
  from `item.path.relative_to(tests_root).parts[0]`.
- The four markers are registered in `pyproject.toml` next to `slow` and `expects_deprecation`,
  and `addopts` gains `--strict-markers`.
- A contract test, `tests/contract/test_test_layout.py`, asserts two things: no
  `tests/test_*.py` exists (by glob), and every collected item has exactly one of the four
  markers. The second runs via `pytester`, or by collecting with `--collect-only -q` and reading
  the marker set in a hook-free subprocess.

**Moves.** The §14.3 destinations are checked file by file at move time with the signal grep
(sockets, `pynng`, `asyncio`, threads, `tmp_path`, `/etc/cuems`). Root files today (2026-10-21,
**17 + 1**): `test_canvas_region_roundtrip`, `test_communicatorservices`, `test_configmanager`,
`test_cuelist`, `test_cue_output`, `test_cue`, `test_fade_cue`, `test_funcdict`, `test_helpers`,
`test_hubservices`, `test_logger`, `test_name_coercion`, `test_project_mappings`,
`test_signalengine`, `test_superproperty`, `test_version`, `test_xml`, plus `testdev_nng_talk.py`
(retired).

**Alternative:** markers from `pytestmark` in each file. Rejected: the release line keeps adding
files at the root, and a marker that depends on each file remembering it is the defect this
section exists to remove.

## R11 — CI (FR-070–FR-076): measured constraints

- **Today.** `tests.yml` has one job, `hatch run test:run-cov` on 3.11 only, with Codecov uploaded
  unconditionally. Its triggers are `push: [main]`, `pull_request` and `workflow_dispatch`.
  `gh-pages.yml` runs `mkdocs gh-deploy --force` on push to `main`, on **every** `pull_request` and
  on **every** dispatch. `pyproject.toml`'s hatch matrix is 3.11/3.12/3.13, and its scripts are
  `run-cov = "pytest --cov {args:tests/}"` and `lint = "ruff check {args:src/ tests/}"`.
- **Dispatch needs the file on `main`.** `tests.yml` is on `main`, so the restructure keeps its
  name. A dispatch with `--ref feat/xml-refactor` then runs that ref's copy (work order §14.5).
- **Static check (FR-075).** `tests/contract/test_ci_workflow.py` parses `tests.yml` and
  `gh-pages.yml`. **Measured 2026-10-21: `import yaml` fails in the hatch `test.py3.11`
  environment**, whose dependencies are `pytest`, `pytest-cov`, `pytest-mock`, `hypothesis`,
  `coverage[toml]` and `ruff`.
  - **Decision:** add `pyyaml` to `[tool.hatch.envs.test] dependencies` only. It is not a runtime
    dependency: FR-081 and the constitution's "no new runtime dependency" are untouched, and the
    `.deb` and the wheel are unchanged. It is recorded in the plan's Complexity Tracking, as the
    constitution requires for any dependency addition.
  - **Alternatives:** a line-based parser, rejected because YAML's block scalars and anchors make
    one fragile and it would itself need tests. Skip-if-absent, rejected because the gate would
    then never check itself.
  - One YAML caveat for the test: PyYAML reads `on:` as the boolean `True`, so the test looks the
    trigger map up under both `"on"` and `True`.
- **Sibling checkout.** The `siblings_ref` input (default `xml-refactor-merge-candidate`) drives
  six `actions/checkout` steps into `../<repo>`, each with `fetch-depth: 0` and tags, so
  `tests/support/sibling_tags.py` finds them. The siblings are public in the `stagesoft`
  organisation. If any is private, the step needs a token, which is recorded at hand-off and is
  not 017's to create. The ran/skipped count comes from the pytest summary of the sibling-reading
  modules, identified by their use of `sibling_tags`.
- **`packaging` job.** `container: debian:bookworm`, `apt-get install` of the build-deps from
  `debian/control`, then `dpkg-buildpackage -us -uc -b`. After that: the three FR-035 checks on the
  `.deb`, `Version` against `dpkg-parsechangelog`, and `pytest tests/packaging` without
  `CUEMS_CHROOT_TAR` (those tests skip with a reason).

## R17 — The 42 stray paths, enumerated (measured 2026-10-21, three-way)

`git diff --name-only --diff-filter=A $(git merge-base HEAD origin/debian/bookworm)
origin/debian/bookworm -- . ':!specs'` gives **52** paths added on bookworm since `07a7f9f`.
**Ten are kept**, merged or ported:
- seven `debian/` sources: `README.Debian`, `changelog`, `control`, `copyright`,
  `cuems-utils.links`, `cuems-utils.triggers`, `rules`;
- the three absorbed test files: `tests/test_action_cue_stop_project.py`,
  `tests/test_media_guards.py`, `tests/unit/test_media_pixel_dimensions.py`. These are ported by
  A-3 and A-4, not deleted in M1.

**The other 42 are deleted in M1 (FR-011).** This list, not a pattern, is binding, and the plan's
pattern summary was incomplete (it missed `debian/cuems-utils/usr/…` and `.debhelper/…/dbgsym-*`).

*Build outputs (21):*
- `.pybuild/cpython3_3.11/.pydistutils.cfg`;
- `debian/.debhelper/cuems-utils/dbgsym-build-ids`;
- `debian/.debhelper/cuems-utils/dbgsym-root/DEBIAN/{control,md5sums}`;
- `debian/.debhelper/cuems-utils/dbgsym-root/usr/share/doc/cuems-utils-dbgsym`;
- `debian/.debhelper/generated/cuems-utils/{dh_installchangelogs.dch.trimmed,installed-by-dh_installdocs}`;
- `debian/compat`;
- `debian/cuems-utils.{postinst,prerm}.debhelper`;
- `debian/cuems-utils.substvars`;
- `debian/cuems-utils/DEBIAN/{control,md5sums,postinst,prerm,triggers}`;
- `debian/cuems-utils/usr/share/doc/cuems-utils/{README.Debian,changelog.gz,copyright}`;
- `debian/debhelper-build-stamp`;
- `debian/files`.

*Root files (21):*
- `.python-version`;
- 13 documents: `CHANGES_SUMMARY.md`, `CONNECTION_HEALTH_EXAMPLE.md`, `OSC_NODES_EXAMPLE.py`,
  `OSC_NODES_HUB_GUIDE.md`, `OSC_NODES_IMPLEMENTATION_SUMMARY.md`, `PING_PONG_GUIDE.md`,
  `PLAYER_BASED_ARCHITECTURE.md`, `QUICK_START_OSC_NODES.md`, `QUICK_START_OSC_PLAYERS.md`,
  `README_PLAYERS.md`, `REFACTORING_BASE_CLASS_QUEUES.md`, `REFACTORING_COMPLETE.md`,
  `TCP_MIGRATION_NOTES.md`;
- 7 scripts: `bus_test.py`, `bus_test_slave.py`, `test_bus_controller.py`, `test_bus_node.py`,
  `test_osc_hub_controller.py`, `test_osc_hub_node.py`, `test_player_queue.py`.

**Also measured:** no file the refactor deleted since the merge-base was modified on bookworm (the
D-on-HEAD ∩ M-on-bookworm intersection is empty), so the merge has **no modify/delete conflicts**.
Files that a two-way `HEAD..bookworm` diff shows as "added" (`create_script.py`, `FadeProfile.py`,
`outputs.xsd`, the fade-profile tests) are refactor **deletions**, and they stay deleted. They are
not strays, and not part of the 42. At implementation, the list is re-derived by the same command
and compared with this one. A difference is a delta under FR-004, not something to resolve by
editing patterns.

## R16 — Q2 revisited: repairing a leftover `stop_project` target to `None`

All of this was read from `2318dee`'s code on 2026-10-21.

- **Repair runs only on load.** `CuemsScript.load_with_report` calls `validators.repair(obj)`
  (`CuemsScript.py:406`). `save` (`:517`) raises on **every** violation `_violations(tree)` yields,
  repairable or not. `from_json` (`:429`) only constructs. So "repair to `None`" means three
  things: REPAIRED on load, refused on save, reported by `validate()`. This is the same posture
  as the existing repairable `target_resolves`.
- **The repair value is free.** `repair()` substitutes `type(node).declared_defaults()[field]`,
  and `ActionCue.REQ_ITEMS['action_target']` is `None`. The new rule accepts `None` by
  construction, which is the property every `repairable=True` rule must have.
- **Order hazard 1, in the walk.** `_iter_t2_findings` runs rules in **registration order**, and
  `repair()` raises at the **first** unrepairable finding. A dangling leftover uuid on
  `stop_project` would hit `action_target_resolves` (unrepairable, registered earlier) before the
  new rule. **Decision:** `action_target_resolves` returns early when
  `obj.get("action_type") in TARGETLESS_ACTION_TYPES`. A target that is going to be cleared has
  no resolution to check, and one fault gives one finding, as that rule's own docstring requires
  of its sibling.
- **Order hazard 2, in the descriptor.** `descriptor._repairability_map` (`:217-236`) assigns
  `mapping[(key, field)] = rule.repairable` in a loop, so **the last-registered rule wins**.
  Registering the new rule after the two unrepairable `action_target` rules would publish
  `ActionCue.action_target` as REPAIRABLE, which is false for every action type outside the set.
  The frontend reads the descriptor (015 G3).
  - **Measured:** rules per field today: `action_target` has 2 (both unrepairable). Every other
    field has exactly one. **No field has disagreeing rules.**
  - **Decision:** combine conservatively, `mapping[k] = mapping.get(k, True) and rule.repairable`.
    That is a no-op for every field today, so no golden moves, and it is correct for
    `action_target` after the change. Pinned by FR-023a's two tests.
  - **Alternative:** register the new rule first. Rejected: it is correct only by accident of
    ordering, and the next rule added would break it silently.
- **The closed rule list.** `SEMANTIC_RULES` is derived from `RULES` (`validators.py:243-256`).
  `tests/unit/test_t2_registry.py` asserts `len(RULES) >= 10`, and
  `tests/contract/test_rule_targets_resolve.py` is parametrized over `sorted(RULES)`, so it picks
  up the new rule automatically. Any test pinning the exact rule set is updated in A-1's commit.
- **Rule name and message.** The name is `project_action_takes_no_target`. The message:
  `f"action_target {value} must be empty: {action_type} acts on the whole project and takes no
  target; clear it"`. It follows the rule-naming form (snake case, states the invariant) and the
  messages' form (it names the field and the value; FR-081).
- **Alternatives (from the Q2 table).**
  - Silent clearing in the model (B). Rejected: load would change data without a report.
  - Skip-only (D). Rejected by the maintainer in favour of cleaning the data.

## R15 — Q13: retiring `pause_project` / `resume_project`

**Measured 2026-10-21** with `git grep` on every checkout's working head and on its release
lines. `specs/` and lock files are excluded.

| Repository | Working head | Release lines | Finding |
|---|---|---|---|
| cuems-utils | `2318dee` | `origin/debian/bookworm` | `script.xsd:321-322` (enum) and `tests/contract/test_enum_audit.py:24` (retained set) only. Bookworm also has `ActionCue.py:27` (docstring) and `CHANGELOG.md:13` (rc17: "stay in the enum and stay unimplemented"). No corpus document, no golden |
| cuems-engine | `aa0ffe6` (its 009 branch) | `debian/bookworm`: 2 hits; `dev`: 4; `main`: 1 | `ActionHandler.py:29` names them unimplemented. bookworm `tests/test_action_cue.py:1519` parametrizes them with `load`/`unload`/`wait`. **`origin/dev` `9852d79` (2020-12-17) `src/cuems/ActionCue.py:95-97` is the only implementation ever written** (legacy layout) |
| cuems-frontend | `9e91464` | `dev`, `main` | **0**: never authored |
| cuems-editor | `a2431f0` | `debian/bookworm`, `main` | **0** |
| cuems-nodeconf, cuems-power-bridge | heads | all lines | **0** |

**Decision.**
- Remove both enumerations from `script.xsd` in A-1's commit, so A-2d's hash moves once.
- Remove both from `RETAINED`, which A-2c edits in any case.
- Write the handover document in the same commit (FR-053).
- **No conversion entry**: no producer ever wrote either value, so no field document needs
  rewriting.
- A version-1 document carrying one, if any surfaced, would be refused by T1 after conversion,
  naming the value. That is the honest outcome for an action nothing implements. Silently
  rewriting it into `pause`/`play` would invent semantics.

**Rationale for doing it now:** `0.1.1` publishes `script` version 2. After that, removing a value
is a 2 → 3 narrowing step with a registry entry. Today it costs one hash change.

**Alternatives.**
- Keep them, as rc17 did. Rejected by Q13.
- Retire them in `v0.1.2` with the deprecated surface. Rejected: they are schema vocabulary, not
  Python surface, and by then version 2 is released.

**Consequences for the counts:** `ActionType` goes 12 (HEAD) + 1 (merge) − 2 = **11**. A-2a/b
become "eleven", and the frontend's published list is 11.

## R12 — FR-053 inputs, read from the checkouts (for the planning document)

The document itself is a task, and these are its starting citations:
- **`../libmtcmaster` at `6afe645`.** `interface.h` exports `MTCSender_create`, `_release`,
  `_openPort`, `_play`, `_stop`, **`_pause`** and `_setTime`. Pause and play are separate calls
  from stop, so a project pause need not reset time.
- **`../cuems-engine` at `aa0ffe6`**, on its own `009-release-line-reconciliation` branch.
  `src/cuemsengine/core/libmtc.py:29-39` wraps `MTCSender_play`, `_stop` and `_pause` through
  `ctypes`. `cues/ActionHandler.py:29` lists `pause_project` and `resume_project` among the
  **unimplemented** actions. `NodeEngine.py:366` and `ActionHandler.py:34,759` are the `stop`
  dispatch sites the `stop_cue` option (Q2) would touch.
- **⚠ Branch caveat.** That checkout does not yet carry the engine's rc17 `stop_project` handler,
  because its reconciliation (its 009) is in flight. The document must cite the engine's
  **release-line** commit for `stop_project`'s handler (`origin/debian/bookworm` there), not the
  checkout's HEAD.

---

## R13 — The work order's measured seams (§6), carried

**§6.1, the merged tree against `5e4c637`.** Hatch `test.py3.11`, scratch worktrees,
`PYTHONPATH=<arm>/src`, `CUEMS_CONF_PATH` unset, governor `powersave`. Indicative only:

| Run | Arm A `5e4c637` | Arm B merged |
|---|---|---|
| 1 | 3769 p / **1 f** (laziness flake) / 134 s / 2 xf, 44.8 s | 3834 p / 7 f (the six + the flake) / 134 s / 2 xf, 41.4 s |
| 2 | 3770 p / 0 f, 42.2 s | 3835 p / **6 f**, 39.3 s |
| 3 | 3770 p / 0 f, 38.4 s | 3835 p / **6 f**, 38.9 s |

The merged tree adds 65 passing tests and 198 more warnings (379 → 577). The extra warnings are
the absorbed tests' `DeprecationWarning`s, and D4's port removes them. ruff 0.17.0 found 0 in both
arms. mypy was not compared: its count on this box is disputed (283 vs 71–72).

| Id | Failing test | Cause | Adaptation |
|---|---|---|---|
| A-2a | `contract/test_action_type.py::test_action_type_enumerates_exactly_twelve_values` | 13 values | **eleven** after Q13 (R15), by name, renamed; no `fade_in`/`fade_out`, no retired value |
| A-2b | `…::test_the_descriptor_publishes_exactly_those_twelve_values` | descriptor publishes 13 | same (11), the frontend's STOP chips |
| A-2c | `contract/test_enum_audit.py::test_the_schemas_carry_no_more_and_no_fewer_than_the_retained_set` | `stop_project` not retained | add, evidence recorded in 017 |
| A-2d | `contract/test_schema_scope.py::test_every_schema_matches_its_recorded_hash` | `script.xsd` changed | new hash **in A-1's commit**; no version step |
| A-3a | `tests/test_action_cue_stop_project.py::test_constructor_accepts_an_empty_target_and_refuses_none` | `""` → `None` at construction | ported; re-expressed by A-1 |
| A-4 | `tests/unit/test_media_pixel_dimensions.py::TestFileMd5::test_stored_lowercase` | rc15 lowercases, 014 raises | **retired**, recorded |

**§6.2, found by probing the public path:**

| Id | Probe | Arm A | Arm B | Required |
|---|---|---|---|---|
| S-1 | public `ActionCue(stop_project, "")` → `save` | T1 `XsdEnumerationFacets` | **T2** `action_target_required` | A-1 |
| S-1′ | rc17-written document → reshape → convert → `load_with_report` | reshape **skips** it (enum) | reshape ✅ convert ✅ **load refused (T2)** | A-1 |
| control | same document, `stop` aimed at the audio cue | CLEAN | CLEAN | none |
| S-2 | `ActionCue({"action_type": "stop_project", "action_target": None})` (frontend `sequence.component.ts:1507`) | raises | raises | A-1 |
| X-4 | migrated rc17 media values via `.get` / attribute / `in` / `to_wire` | present → `int`/`str` (`file_size` 107374182400 intact); **absent → `None`**, key absent, omitted by `to_wire`; `Unset` never exposed | same | answer **`None`**, A-6 |
| S-3 | convert on the S-1′ document | — | "converted", written, then refused | FR-029c (Q3) |
| S-4 | `python -m cuemsutils.xml.reshape_devices <file>` | exits 0, does nothing | same | FR-029a (Q4) |

## R14 — The clarify answers (§12), as decisions

| Q | Decision | Rationale | Alternative rejected |
|---|---|---|---|
| Q1 | `{stop_project}` only, plus the FR-053 document | the only implemented project action (YAGNI) | all `*_project`: gives rules to actions nobody built |
| Q2 | **revised 2026-10-21:** repair a leftover target to `None` (repairable rule `project_action_takes_no_target`; R16). `stop_cue` naming stays a future option | cleans data the engine ignores anyway, and reports the repair | accept and ignore (the first answer); silent clearing; skip-only |
| Q3 | tools report T2 after writing, with bytes and exit status unchanged | ends the silent success without changing `postinst` outcomes | out of scope; or refuse to write |
| Q4 | `__main__` guard plus a `python -m` test | silent success removed; one line | defer |
| Q5 | keep the legacy edits; prove each behaviour on the public path | rule 4; consumers rely on the public path | revert |
| Q6 | `Replaces:` only | as released; the engine floor co-upgrades | add `Breaks:` (row 27) |
| Q7 | mark Debian-only, one line for rc13, PyPI re-measured at hand-off | the reader can't otherwise know | no marking |
| Q8 | `MediaCue` joins `PUBLIC_CLASSES`, one surgical re-hash | the snapshot should see `media_status` | leave the scope alone (the work order's recommendation) |
| Q9 | `-s ours` merge of `v0.0.9rc7` | later sweeps stop flagging it | pointer only (the work order's recommendation) |
| Q10 | the release line continues; re-merge per FR-004 | agreed with the team | freeze, or retire |
| Q11 | blocking: 3.11 + `packaging`; informational: 3.12/3.13 | 3.11 ships; the `.deb` is the venv-interpreter check | 3.11 only; or everything |
| Q12 | triage `ToDo.md`, then delete; untrack `settings.local.json` | no stale list in a stable release | keep |
| Q13 | retire `pause_project`/`resume_project`; handover document | deferred to a future release; free to remove before version 2 ships (R15) | keep them unimplemented; retire in `v0.1.2` |
| gate | the CI run moves to after hand-off | it needs a push, which is a maintainer act | an agent push; or local `act` |
