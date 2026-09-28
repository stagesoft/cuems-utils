# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T067 — no package version moves in feature 011 (research R19): the three
unreleased entries absorb the change and land together under the re-pointed
xml-refactor-merge-candidate tag. A bump is a deliberate act that updates this
file in the same commit, with the reason in the message."""

from __future__ import annotations

import re

import pytest

from tests.packaging.conftest import REPO_ROOT

PINNED = {
    "cuems-utils": "0.1.0rc16",
    "cuems-common": "1.3.0-23",
    "cuems-nodeconf": "0.1.0-8",
}


def _head_version(changelog) -> str:
    first = changelog.read_text(encoding="utf-8").splitlines()[0]
    return re.match(r"^\S+ \(([^)]+)\)", first).group(1)


def test_this_repository_stays_at_rc16():
    assert _head_version(REPO_ROOT / "debian" / "changelog") == PINNED["cuems-utils"]
    init = (REPO_ROOT / "src/cuemsutils/__init__.py").read_text(encoding="utf-8")
    assert re.search(r'__version__\s*=\s*"0\.1\.0rc16"', init)


@pytest.mark.parametrize("name", ["cuems-common", "cuems-nodeconf"])
def test_the_siblings_stay_at_their_unreleased_heads(name):
    changelog = REPO_ROOT.parent / name / "debian" / "changelog"
    if not changelog.exists():
        pytest.skip(f"../{name} not checked out beside this repository")
    assert _head_version(changelog) == PINNED[name]
