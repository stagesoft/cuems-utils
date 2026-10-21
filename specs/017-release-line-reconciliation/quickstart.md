<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Quickstart: running and checking 017

These are the work order's §13 recipe and 017's own checks, as commands. Paths are absolute. `$S`
is the session scratchpad, and worktrees live there and are removed afterwards. Nothing here
pushes, tags or publishes.

```bash
R=/disk/Projects/StageLab/cuems-utils
PY=$(uvx hatch env find test.py3.11)/bin/python      # uv CPython 3.11.9 (record the build)
S=<session scratchpad>
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq   # before trusting any absolute figure
```

## 1. Re-measure (phase 0 and phase 8)

```bash
git -C $R fetch --all --tags --prune
git -C $R rev-list --count HEAD..origin/debian/bookworm         # 77 before M1, 0 after
git -C $R rev-list --count HEAD..origin/main                    # 11 before, 0 after
git -C $R rev-list --left-right --count origin/main...origin/debian/bookworm   # 1 67
git -C $R diff origin/main origin/debian/bookworm -- src tests CHANGELOG.md    # empty
git -C $R cherry -v HEAD origin/debian/bookworm | grep '^-'     # 9c17418 only
git -C $R merge-tree --write-tree HEAD origin/debian/bookworm   # 11 conflicted files
# stray sweep (research R2): expected 5 refs: feat/faders, gh-pages, options, parser-fixxes, v0.0.9rc7
for r in $(git -C $R for-each-ref --format='%(refname)' refs/remotes/origin refs/tags); do
  n=$(git -C $R rev-list --no-merges --count "$r" ^HEAD ^origin/debian/bookworm); [ "$n" != 0 ] && echo "$n $r"
done
# released sets (research R9)
git -C $R show origin/debian/bookworm:debian/changelog | grep -E '^cuems-utils \(' | grep -v UNRELEASED
curl -s https://pypi.org/pypi/cuemsutils/json | python3 -I -c \
  'import json,sys; print(sorted(v for v in json.load(sys.stdin)["releases"] if v.startswith("0.1.0")))'
```

## 2. Two arms (A = `5e4c637`, B = the 017 head)

```bash
git -C $R worktree add $S/wt-a 5e4c637
git -C $R worktree add $S/wt-b 017-release-line-reconciliation
run() { env -u CUEMS_CONF_PATH PYTHONPATH=$1/src $PY -m pytest $1/tests -q -p no:cacheprovider; }
# interleaved, three times: A B A B A B   (SC-003); keep each output under evidence/
for i in 1 2 3; do run $S/wt-a > evidence/suite-A-$i.txt; run $S/wt-b > evidence/suite-B-$i.txt; done
# 3.12 / 3.13 once each, on B
uvx hatch run test.py3.12:run -- -q ; uvx hatch run test.py3.13:run -- -q
# B's failures must be a subset of A's (the laziness flake may appear in either)
```

The suite must be run with `CUEMS_CONF_PATH` unset (`tests/conftest.py`'s session guard names any
test that touches a host `/etc/cuems`).

## 3. The rc17 fixture (research R5) and the probes (S-1, S-1′, S-2, X-4)

> ⚠ **Use `-P`, never `-I`, whenever `PYTHONPATH` selects an arm.** `python -I` (isolated
> mode) **ignores `PYTHONPATH`**, so it loads whichever `cuemsutils` the interpreter has
> installed and silently measures the wrong arm. This happened once in 017 (T017's first probe
> run) and was caught only by the probe's `# arm` line. `-P` keeps the script's own directory
> off `sys.path`, which is the protection `-I` was there for, and honours `PYTHONPATH`.


```bash
git -C $R worktree add $S/wt-bw 398a9cf
# writes stop_project.xml and stop_control.xml with rc17's own XmlReaderWriter
env -u CUEMS_CONF_PATH PYTHONPATH=$S/wt-bw/src $PY -P \
  $R/specs/017-release-line-reconciliation/tools/capture_rc17_fixture.py --out $R/tests/data/rc17/
sha256sum $R/tests/data/rc17/*.xml        # → PROVENANCE.md
# migrate a COPY, then load, on each arm (the tools through main(), see S-4)
for arm in $S/wt-a $S/wt-b; do
  cp $R/tests/data/rc17/stop_project.xml $S/probe.xml
  env -u CUEMS_CONF_PATH PYTHONPATH=$arm/src $PY -P \
    $R/specs/017-release-line-reconciliation/tools/probes.py --arm $arm --file $S/probe.xml
done
# expected on B after A-1: reshape ok → convert "converted" → load_with_report CLEAN
```

## 4. Merge M1 (phase 2), by the §5 table only, on a trial branch

```bash
git -C $R worktree add -b 017-m1-trial $S/wt-m1 017-release-line-reconciliation
R=$S/wt-m1        # everything below, up to the commit, runs in the trial worktree
git -C $R merge --no-ff --no-commit origin/debian/bookworm
git -C $R diff --name-only --diff-filter=U            # the 11 files
git -C $R checkout --ours debian/README.Debian         # NEVER a marker-splitting script
# … each other hunk by plan.md §5 …
# the 42 strays: three-way, from the merge-base (a two-way HEAD..MERGE_HEAD diff wrongly includes
# files the refactor deleted); compare with research R17 before any git rm
git -C $R diff --name-only --diff-filter=A $(git -C $R merge-base HEAD MERGE_HEAD) MERGE_HEAD -- . ':!specs'
grep -rn '^<<<<<<<\|^>>>>>>>' $R --include='*' -l | grep -v '\.git/'   # must be empty
git -C $R commit -S        # retry on "gpg failed to sign"; never --no-gpg-sign
R=/disk/Projects/StageLab/cuems-utils
# after review: approved → fast-forward; rejected → delete the trial and redo
git -C $R merge --ff-only 017-m1-trial && git -C $R worktree remove $S/wt-m1 && git -C $R branch -d 017-m1-trial
# rejected instead:  git -C $R worktree remove --force $S/wt-m1 && git -C $R branch -D 017-m1-trial
```

## 5. Packaging (phase 5)

```bash
# build 0.1.1 in a throwaway bookworm chroot. The tool needs a CLEAN cuems-utils checkout (UTILS)
# and an evidence file OUT that does not exist yet (it refuses both a dirty UTILS and an existing
# OUT, which is what protects 016's evidence). It does not write to stdout.
git -C $R worktree add --detach $S/wt-build 017-release-line-reconciliation
UTILS=$S/wt-build OUT=$R/specs/017-release-line-reconciliation/evidence/bookworm-build.txt \
  $R/specs/016-coordinated-minor-bump/tools/bookworm-build.sh $S/wt-build
DEB=<the .deb under the tool's WORK/build/out, as named in OUT>
dpkg-deb -f $DEB Version                                                  # 0.1.1
dpkg-deb --fsys-tarfile $DEB | tar -xO ./usr/lib/cuems/pyvenv.cfg | grep '^home'   # home = /usr/bin
dpkg-deb -c $DEB | grep -E 'bin/python ->|CACHEDIR.TAG|bin/cffi-gen-src'  # link relative; no TAG; cffi-gen-src?
# relations (contracts/relation-row-26.md): 126/126
$R/specs/017-release-line-reconciliation/tools/verdicts-017.sh /disk/Projects/StageLab \
  > $R/specs/017-release-line-reconciliation/evidence/verdicts-017.txt
dpkg-parsechangelog -l $R/debian/changelog -S Version                     # 0.1.1
```

## 6. Performance bands (FR-PERF-001)

Measure arms A and B interleaved, at least 16 samples across three windows (015's lesson):
- the show-document load: the established harness, against its band of 16.465–17.750 ms;
- the `script` descriptor warm call:
  `python -m tests.support.perf_descriptor --arm A=$S/wt-a/src --arm B=$S/wt-b/src`;
- suite ms/test, from §2's runs;
- the tools' post-write cost (FR-029c), over `tests/data/corpus/`, recorded without a budget.

Record each figure with its interpreter build, governor and `scaling_cur_freq` in
`evidence/perf.md`. An exceeded budget is recorded as exceeded.

## 7. Cleanup checks (phase 9, SC-012)

```bash
git -C $R grep -nE "dev/parsers|test_bus_(controller|node)|testdev_nng_talk" -- . ':!specs'   # empty
ls $R/tests/test_*.py 2>/dev/null                                          # empty
uvx hatch run test.py3.11:run -- tests/unit tests/contract -q              # passes offline
# pass-set comparison before/after each cleanup commit
uvx hatch run test.py3.11:run -- -q -rA | grep -E '^(PASSED|FAILED|ERROR)' | sort > $S/passset-<commit>.txt
```

## 8. Last task (phase 12, FR-060)

```bash
git -C $R grep -n release-line-reconciliation-0.1.1 -- . ':!specs/017-*'   # must print nothing
git -C $R rm specs/planning/release-line-reconciliation-0.1.1.md
```

## Clean up

```bash
for w in wt-a wt-b wt-bw; do git -C $R worktree remove --force $S/$w; done
```
