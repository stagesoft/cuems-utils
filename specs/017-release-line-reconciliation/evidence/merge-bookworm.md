# M1 — merge of `origin/debian/bookworm` (T007–T013)

Made on the trial branch `017-m1-trial` (worktree), from the 017 head `cb4dad3`
(spec FR-002, checklist CHK021). Default strategy, no `-X`. M1 = **`6a17392`**, signed (G),
parents `cb4dad3` + `398a9cf`. After it, `HEAD..origin/debian/bookworm` = 0.

## Conflict set (T007): 11 files, 25 hunks, as plan §5

| File | Hunks | Resolution | Plan §5 row / reason |
|---|---|---|---|
| `src/cuemsutils/__init__.py` | 1 | ours `__version__ = "0.1.1"` + theirs' `SPDX-FileContributor` line | D6 |
| `src/cuemsutils/cues/ActionCue.py` | 1 | theirs' 3 SPDX lines; theirs' `from .Cue import Cue` dropped (already imported below the hunk) | headers |
| `src/cuemsutils/cues/CuemsScript.py` | 1 | theirs' 3 SPDX lines + ours' `Mapping`/`Any` imports; theirs' `import json` (unused on HEAD) and `import json_fix` (already below) dropped | headers |
| `src/cuemsutils/cues/CueList.py` | 2 | h1: theirs' SPDX + ours' `from typing import Any` (theirs' Cue/MediaCue imports already below); h2 `get_media`: **theirs** (`media_status()` branches) | item 2 |
| `src/cuemsutils/cues/MediaCue.py` | 5 | h1: theirs' SPDX + ours' `import re`; h2–h5: **ours** (014's `_set_positive_int`, accessors, strict `set_file_md5`). `media_status()` merged cleanly (line 621) | item 3, D4/A-4 |
| `src/cuemsutils/xml/schemas/script.xsd` | 2 | h1 media-block comment: ours; h2: ours, theirs' second `Md5Type` dropped (one declaration remains). `stop_project` enumeration merged cleanly | item 3 |
| `debian/control` | 3 | h1 theirs (SPDX); h2 ours (`debhelper-compat (= 13)`, `Standards-Version: 4.6.2`); h3 **both**: `Breaks: cuems-common (<< 1.3.1~)` then `Replaces: cuems-engine (<< 0.1.0rc6-2~)`, both in the `cuems-utils` binary stanza (checked) | row 1 + item 4 |
| `debian/rules` | 2 | h1 theirs (SPDX); h2 **theirs then ours**: `rm -f …/CACHEDIR.TAG` directly after `dh_virtualenv` in `override_dh_virtualenv`, then 011's schema/defaults install and `override_dh_installdeb` | item 5 |
| `debian/README.Debian` | 1 | ours, whole file (`git checkout --ours`; byte-identical to HEAD) | 011 |
| `debian/changelog` | 6 | rebuilt by entry (below) | FR-030 |
| `CHANGELOG.md` | 1 | ours' `0.1.1` + two mid-file `Unreleased` sections, a blank line, then theirs' `0.1.0rc17`, `0.1.0rc16` sections. Folding and new sections are T053 | FR-032 |

## `debian/changelog` rebuild (T010)

17 entries in dpkg order: `0.1.1` (HEAD, body unchanged in M1) → `0.1.0rc17`, `0.1.0rc16+1`,
`0.1.0rc16`, `0.1.0rc15` (**byte-for-byte from bookworm**) → `0.1.0rc14`…`0.1.0rc8`
(**byte-identical on both lines**, measured) → `0.1.0rc5`, `0.0.7-31`, `0.0.7-3`, `0.0.7-2`,
`0.0.6-0`, `0.0.1-0` (HEAD's form). `dpkg-parsechangelog`: top `0.1.1`, no warning.

HEAD's retrospective `0.1.0rc15 UNRELEASED` entry is replaced by the released one. Its body is
recovered for `0.1.1` in T052 from `git show 5e4c637:debian/changelog`.

**Correction to the work order §7.1:** bookworm does not merely carry *different* copies of the
old `UNRELEASED` entries. Its `0.1.0rc5`, `0.0.7-31`, `0.0.7-3` and `0.0.7-2` entries are
**truncated, with no trailer**: `dpkg-parsechangelog` warns "found start of entry where expected
more change data or trailer". HEAD's copies are the completed ones (`b7db53e`), which is why
FR-030 keeps HEAD's form. `0.0.1-0` differs only by bookworm's missing final newline.

## Strays (T011)

Three-way list re-derived from the merge-base `07a7f9f`: 52 added = **42 strays + 10 kept**,
an exact match with research R17. The 42 are not taken (removed from the index and the work
tree; their empty directories `.pybuild/`, `debian/.debhelper/` and `debian/cuems-utils/` are
gone). The 10 kept additions are tracked. Unmerged paths: 0. Conflict markers in tracked files: 0.

## What M1 changes against `cb4dad3` (16 paths)

The 11 resolved files; the clean merges `src/cuemsutils/xml/Parsers.py`,
`src/cuemsutils/xml/XmlBuilder.py` (rc15's legacy-path edits, kept, Q5) and `CLAUDE.md` (the
rc17 field note, rewritten in T055); and the three kept test files
`tests/test_action_cue_stop_project.py`, `tests/test_media_guards.py`,
`tests/unit/test_media_pixel_dimensions.py`.

`src/cuemsutils/cues/FadeCue.py`, `tests/test_fade_cue.py` and `debian/cuems-utils.links`
auto-merged to **exactly HEAD's content**: bookworm's side of them was already on HEAD (the
subject-twin commits of work order §2). No content is lost.

## T013 — suite on M1, review, fast-forward

`evidence/suite-M1.txt`: **3835 passed, 6 failed**, 134 skipped, 2 xfailed. The red set is
exactly research R13's six (A-2a, A-2b, A-2c, A-2d, A-3a, A-4); the laziness flake did not
appear. The maintainer approved on 2026-10-21. `git merge --ff-only 017-m1-trial` brought the
017 branch to `6a17392`, the reviewed, signed commit, and the trial branch and worktree were
removed.

## T014 — M2, `origin/main`

`909d6f3` (G), parents `6a17392` + `23e4752`. Tree diff against M1: **empty**.
`v0.1.0rc17` is an ancestor.

## T015 — M3, `v0.0.9rc7` (ancestry only, Q9)

`97ee1f9` (G), parents `909d6f3` + `b0df231`, `-s ours`. Tree diff against M2: **empty**.
- Equivalence re-checked: `git diff v0.0.9rc7 v0.0.9rc8 -- src/cuemsutils/cues/CuemsScript.py
  src/cuemsutils/cues/MediaCue.py` is empty, and rc8 is an ancestor. rc7's third file is
  `__init__.py`, its own version bump.

## After Phase 2

- `HEAD..origin/debian/bookworm` = **0**, `HEAD..origin/main` = **0**.
- `v0.1.0rc17`, `v0.0.9rc7` and every `debian/*` tag are ancestors.
- The stray sweep (`git rev-list --no-merges --count <ref> ^HEAD`) lists only
  `origin/feat/faders`, `origin/options` and `origin/parser-fixxes` (excluded, research R2) and
  `origin/gh-pages` (not source).
