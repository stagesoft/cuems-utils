#!/bin/sh
# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
#
# 010 T062 (FR-070-FR-073a, SC-006): the ecosystem-wide count of the retired
# network-map vocabulary, with its method stated by the script itself (FR-070b).
#
#   specs/010-consumer-migration/tools/count-retired-vocabulary.sh [ROOT]
#
# ROOT defaults to the directory holding this checkout. The DENOMINATOR IS
# DISCOVERED, never listed: every git checkout directly under ROOT whose HEAD
# tracks a file naming network_map.xml. Checkouts are DE-DUPLICATED BY ROOT
# COMMIT, not by directory name and not by remote URL: a renamed repository can
# keep its old URL in a stale checkout (cuems-wsclient / cuems-power-bridge,
# 2026-09-18), while its first commit cannot change. The remote is printed
# beside each so a reader can see both.
#
# What is counted: the retired element name `node_type` and the retired type
# prefix `NodeType.`, in SHIPPED sources at HEAD only (FR-073, 007's Q1). The
# pathspecs below are what "shipped" means here; the not-shipped files FR-073
# names are reported separately, by name, so that no wildcard hides them.
set -eu

ROOT="${1:-$(cd "$(dirname "$0")/../../../.." && pwd)}"
PATTERN='node_type|NodeType\.'
NOT_SHIPPED='tests test specs dev docs *.md **/test_*.py **/*.spec.ts debian/changelog'

echo "# root: $ROOT"
echo "# pattern: $PATTERN (git grep -E, tracked files at HEAD)"
echo "# not shipped (excluded): $NOT_SHIPPED"
echo

seen=""
total=0
for dir in "$ROOT"/*/; do
    dir="${dir%/}"
    [ -e "$dir/.git" ] || continue
    git -C "$dir" grep -qI 'network_map\.xml' HEAD -- 2>/dev/null || continue
    root_commit="$(git -C "$dir" rev-list --max-parents=0 HEAD | tail -n 1)"
    case " $seen " in
        *" $root_commit "*)
            echo "## $(basename "$dir"): same history as an earlier checkout (root $root_commit), skipped"
            continue
            ;;
    esac
    seen="$seen $root_commit"
    remote="$(git -C "$dir" remote get-url origin 2>/dev/null || echo '(no origin)')"
    echo "## $(basename "$dir")  root=$(echo "$root_commit" | cut -c1-10)  remote=$remote  head=$(git -C "$dir" rev-parse --short HEAD)"
    set -f
    # shellcheck disable=SC2086  # the exclusions are deliberately word-split
    hits="$(git -C "$dir" grep -nIE "$PATTERN" HEAD -- . \
        $(for p in $NOT_SHIPPED; do printf ' :(exclude)%s' "$p"; done) 2>/dev/null \
        | sed 's/^HEAD://' || true)"
    set +f
    if [ -n "$hits" ]; then
        echo "$hits" | sed 's/^/  /'
        n="$(echo "$hits" | wc -l)"
    else
        n=0
    fi
    total=$((total + n))
    echo "  -> $n"
done
echo
echo "TOTAL shipped occurrences: $total"
echo "Each must appear in the exempt set (migration-guide.md section 5) or be fixed. The live count is TOTAL minus the exempt sites."
