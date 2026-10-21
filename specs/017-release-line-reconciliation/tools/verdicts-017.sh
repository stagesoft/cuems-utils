#!/bin/sh
# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
#
# verdicts-017.sh <parent-dir> — 016's 121 relation verdicts, unchanged, plus row 26's five
# (feature 017, FR-040, contracts/relation-row-26.md). Prints 016's lines, then row 26's in the
# same form, then "# 126 verdicts, N FAIL". Exits 1 on any FAIL.
#
# <parent-dir> must hold one checkout per repository: cuems-utils plus the six siblings. Build it
# from git worktrees at fixed commits, never from the live checkouts, whose current branch can be
# anything (cuems-engine was on its own 009 branch on 2026-10-21):
#
#   for r in cuems-common cuems-nodeconf cuems-power-bridge cuems-engine cuems-editor cuems-frontend; do
#     git -C ../$r worktree add --detach $S/rel/$r feat/xml-refactor; done
#   git worktree add --detach $S/rel/cuems-utils HEAD
#   specs/017-release-line-reconciliation/tools/verdicts-017.sh $S/rel
#
# 016's matrix (specs/016-…/contracts/relation-matrix.md) is landed record and is not edited.
set -u
PARENT="${1:?usage: verdicts-017.sh <parent-dir>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
V016="$HERE/../../016-coordinated-minor-bump/tools/verdicts.sh"

echo "# parent: $PARENT"
for r in cuems-utils cuems-common cuems-nodeconf cuems-power-bridge cuems-engine cuems-editor cuems-frontend; do
    printf '# %-20s %s\n' "$r" "$(git -C "$PARENT/$r" rev-parse --short HEAD 2>/dev/null || echo MISSING)"
done

out016="$("$V016" "$PARENT")"; rc016=$?
printf '%s\n' "$out016" | grep -v '^# [0-9]* verdicts'
n016=$(printf '%s\n' "$out016" | grep -c '^row ')
f016=$(printf '%s\n' "$out016" | grep '^row ' | grep -c ' FAIL$')

# Row 26: the Replaces line must be in the cuems-utils binary stanza, exactly.
control="$PARENT/cuems-utils/debian/control"
relation="$(awk '
    /^[[:space:]]*#/ { next }
    /^Package:[[:space:]]*cuems-utils[[:space:]]*$/ { inpkg=1; next }
    /^$/ { inpkg=0 }
    inpkg && /^Replaces:/ { sub(/^Replaces:[[:space:]]*/, ""); print }
' "$control")"
n26=0; f26=0
for pair in "0.1.0rc5-6:yes" "0.1.0rc6-1:yes" "0.1.0rc6-2:no" "0.1.0rc6-5:no" "0.1.1-1:no"; do
    cand="${pair%%:*}"; expected="${pair#*:}"
    if [ "$relation" = "cuems-engine (<< 0.1.0rc6-2~)" ]; then
        if dpkg --compare-versions "$cand" lt "0.1.0rc6-2~"; then observed=yes; else observed=no; fi
    else
        observed=absent
    fi
    n26=$((n26 + 1))
    if [ "$observed" = "$expected" ]; then verdict=OK; else verdict=FAIL; f26=$((f26 + 1)); fi
    printf 'row %-6s %-26s %-46s %-12s expected %s observed %-6s %s\n' \
        26 "Replaces cuems-engine" "cuems-utils/debian/control" "$cand" "$expected" "$observed" "$verdict"
done

total=$((n016 + n26)); fails=$((f016 + f26))
echo "# $total verdicts, $fails FAIL (016: $n016 with $f016 FAIL, rc $rc016; row 26: $n26 with $f26 FAIL)"
[ "$fails" -eq 0 ]
