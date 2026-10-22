<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract: changelog completeness — FR-030–FR-033 (D3), permanent

**Test:** `tests/packaging/test_changelog_completeness.py`. **Must fail on `5e4c637`** and pass on
the 017 head. Works on a shallow checkout: the data is carried, and the git cross-checks skip with
a reason when the refs are absent.

## Data (research R9; re-measured at hand-off)

```python
RELEASED_DEBIAN = {"0.1.0rc8", "0.1.0rc9", "0.1.0rc10", "0.1.0rc11", "0.1.0rc12",
                   "0.1.0rc14", "0.1.0rc15", "0.1.0rc16", "0.1.0rc16+1", "0.1.0rc17"}
RELEASED_PYPI   = {"0.1.0rc7", "0.1.0rc8", "0.1.0rc10", "0.1.0rc11",
                   "0.1.0rc14", "0.1.0rc15", "0.1.0rc16"}      # ≥ 0.1.0rc5, PyPI JSON API
NEVER_PUBLISHED = {"0.1.0rc5", "0.1.0rc6", "0.1.0rc13"}       # spec M1
OLDEST_RELEASED_DEBIAN = "0.1.0rc8"
RELEASE_LINE_REF = "origin/debian/bookworm"
```

## Checks

| # | Check | Needs refs? |
|---|---|---|
| 1 | `dpkg-parsechangelog -S Version` (or a stdlib parse of the first header) == `cuemsutils.__version__` == `CHANGELOG.md`'s first `## <version>` | no |
| 2 | `debian/changelog` headers ⊇ `RELEASED_DEBIAN`; **and** ⊇ the non-`UNRELEASED` headers of `RELEASE_LINE_REF` and of every `debian/*` tag | data: no; refs: yes (skip with reason) |
| 3 | every non-`UNRELEASED` entry on `RELEASE_LINE_REF` is **byte-identical** here (header line through trailer line) | yes (skip with reason) |
| 4 | among the entries above `OLDEST_RELEASED_DEBIAN`, only the top is `UNRELEASED` (spec M2) | no |
| 5 | `CHANGELOG.md` has a `## <v>` section or a `<!-- debian: <v> … -->` comment for every `v ∈ RELEASED_DEBIAN ∪ RELEASED_PYPI`; has a `## Earlier releases` section; has exactly one section whose heading contains `Unreleased`, and it is the first | no |
| 6 | every section for `v ∈ RELEASED_DEBIAN − RELEASED_PYPI` carries `(Debian only; not published to PyPI)` (rc16+1 is satisfied by its comment); every `v ∈ NEVER_PUBLISHED` carries `never published` in its section or one-line entry; no `v ∈ RELEASED_PYPI` carries either | no |

## Expected `5e4c637` failures (fail-before)

- (2): rc15 (released), rc16, rc16+1 and rc17 are missing.
- (3): HEAD's rc15 is a different entry.
- (4): HEAD's rc15 is `UNRELEASED`.
- (5): three sections are missing (rc17, rc16, rc15), and two `Unreleased — …` sections sit
  mid-file.
- (6): no markings exist.

## Hand-off re-measure

`RELEASED_PYPI` is re-read from PyPI's JSON API (yanked files included), and `RELEASED_DEBIAN`
from the fetched release line. A new member updates the data **and** the changelogs in the same
commit (FR-004).
