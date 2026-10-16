#!/bin/sh
# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# verdicts.sh [parent-dir] — every verdict of contracts/relation-matrix.md against the
# current files (feature 016, T009). `packaging` comes from uvx, so the pyenv base
# interpreter stays untouched (research R16).
exec uvx --quiet --python 3.11 --from packaging python "$(dirname "$0")/verdicts.py" "${1:-/disk/Projects/StageLab}"
