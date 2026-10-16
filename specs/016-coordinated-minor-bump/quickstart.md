<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Quickstart — running 016 by hand

Paths are relative to `/disk/Projects/StageLab/`. `F=cuems-utils/specs/016-coordinated-minor-bump`.

## 0. Preflight (FR-018) — before any repository is touched

```bash
for t in mmdebstrap newuidmap newgidmap equivs-build dpkg-buildpackage dpkg-parsechangelog \
         dpkg-deb dh dh_virtualenv fakeroot uv uvx git gpg node npm google-chrome; do
  command -v $t >/dev/null || echo "MISSING $t"; done
grep "^$USER:" /etc/subuid /etc/subgid
~/.pyenv/versions/3.11.9/bin/python -c "import sysconfig;print(sysconfig.get_config_var('CONFIG_ARGS'))"
  # must contain --enable-optimizations --with-lto CC=gcc-12
for r in cuems-*; do git -C $r config commit.gpgsign; done        # all true
echo t | gpg --clearsign --batch -o /dev/null && echo SIGN_OK
curl -sfI http://deb.debian.org/debian/dists/bookworm/Release >/dev/null && echo MIRROR_OK
curl -sfI https://pypi.org/simple/pip/ >/dev/null && echo PYPI_OK
```

Plus: every repository clean and 0/0 with `origin/feat/xml-refactor`; `cuems-engine/.venv` imports `pyossia` `2.0.0rc6+124.cuems.3` (FR-020)
in the spec. Anything needing root goes to the maintainer as one command.

## 1. Shared `cuemsutils` worktrees (research R8)

```bash
git -C cuems-utils worktree add ../.016-utils-start b83d5c2      # start runs (Phase 2)
# after cuems-utils' bump commit (made FIRST, FR-016):
git -C cuems-utils worktree add ../.016-utils-bump <bump-commit> # arms A/B, builds, demos (UTILS=)
```

Remove both at the end (`git worktree remove`).

## 2. Sibling venv (once per Python sibling)

```bash
cd cuems-<x>
grep -qxF '.venv/' .git/info/exclude || echo '.venv/' >> .git/info/exclude
rm -rf .venv && ~/.pyenv/versions/3.11.9/bin/python -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e '.[dev]' 2>/dev/null || .venv/bin/pip install -e .   # extras vary
.venv/bin/pip install pytest pytest-mock
.venv/bin/pip install --no-deps -e ../.016-utils-start
.venv/bin/python -c "import sys,cuemsutils;print(sys.executable, cuemsutils.__file__)"
```

## 3. Per sibling (FR-001 → FR-009), after the cuems-utils bump; order: common, nodeconf, power-bridge, engine, editor, frontend

```bash
R=cuems-<x>
git -C $R switch feat/xml-refactor && git -C $R status --porcelain   # must print nothing
git -C $R rev-list --left-right --count feat/xml-refactor...origin/feat/xml-refactor   # 0 0
# measure (records/<R>.md), then arm A:
(cd $R && .venv/bin/python -m pytest -q -p no:cacheprovider) | tee $F/evidence/$R/suite-A.txt
# edit: version sites → changelog top entry (UNRELEASED) → tests pinning literals → relations LAST
git -C $R commit -S -m "chore(release): <pkg> <target> — coordinated xml-refactor minor (cuems-utils 016)"
(cd $R && .venv/bin/python -m pytest -q -p no:cacheprovider) | tee $F/evidence/$R/suite-B.txt
UTILS=../.016-utils-bump OUT=$F/evidence/$R/bookworm-build.txt $F/tools/bookworm-build.sh $R
# cuems-common / cuems-nodeconf only — the demo, every ref explicit, at the committed bump:
#   see research R10 for the values
# write ../.xml-refactor-tag-messages/$R.txt per contracts/tag-message.md, verify, STOP (FR-021)
```

**Correction at a stop**: edit, `git -C $R commit -S --amend --no-edit`, re-run arm B and the
build, regenerate the tag message, and record the replaced hash.

## 4. `cuems-utils` — bump FIRST, record and message LAST

```bash
# FIRST: bump commit on 016-coordinated-minor-bump (research R11), then:
uvx hatch run test.py3.11:lint && uvx hatch run types:check   # ruff 0, mypy ≤ 72
uvx hatch run test.py3.11:run -- -q   # interleaved with b83d5c2 (also .py3.12, .py3.13)
git -C cuems-utils worktree add ../.016-utils-bump <bump>; repoint every sibling .venv to it
# ... the six siblings ...
# LAST: record commit (sibling-head test, CLAUDE.md, planning document, records, evidence),
#       then cuems-utils' tag message naming the RECORD commit
```

## 5. Frontend

```bash
cd cuems-frontend && npm ci && npm run build && CHROME_BIN=/usr/bin/google-chrome npm run test:ci
```

## 6. Final checks (SC-005, SC-006)

```bash
for r in cuems-*; do git -C $r status -sb | head -1; done      # each "ahead N", never pushed
for r in cuems-*; do git -C $r rev-parse 'xml-refactor-merge-candidate^{commit}' 2>/dev/null; done
  # unchanged from research R12, so no tag was moved
```
