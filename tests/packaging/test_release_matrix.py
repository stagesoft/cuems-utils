# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The coordinated release matrix (feature 016, FR-013).

This file used to be ``test_no_version_bump.py`` (feature 011, T067), which held
every package at its pre-release number because "no package version moves". Feature
016 reverses that premise. The coordinated ``xml-refactor`` landing moves every
CUEMS repository to its own next stable minor, so this file now pins that matrix.
It is rewritten rather than deleted because its job is unchanged: a stray bump has
to fail the suite, not slip through review. Moving a version means updating
``PINNED`` in the same commit, with the reason in the message.
"""

from __future__ import annotations

import json
import re

import pytest

from tests.packaging.conftest import REPO_ROOT

PINNED = {
    "cuems-utils": "0.1.1",
    "cuems-common": "1.3.1-1",
    "cuems-nodeconf": "0.1.1-1",
    "cuems-power-bridge": "0.4.0-1",
    "cuems-engine": "0.1.1-1",
    "cuems-editor": "0.1.1-1",
    "cuems-frontend": "0.2.0",
}
SIBLINGS = [name for name in PINNED if name != "cuems-utils"]


def _head_version(changelog_text: str) -> str:
    first = changelog_text.splitlines()[0]
    return re.match(r"^\S+ \(([^)]+)\)", first).group(1)


def _sibling_version(read, name: str) -> str:
    """The version a sibling states, read through ``read(relpath)``.

    ``cuems-frontend`` has no ``debian/`` and states its version in ``package.json``.
    """
    if name == "cuems-frontend":
        return json.loads(read("package.json"))["version"]
    return _head_version(read("debian/changelog"))


def test_this_repository_is_at_0_1_1():
    changelog = (REPO_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
    assert _head_version(changelog) == PINNED["cuems-utils"]
    init = (REPO_ROOT / "src/cuemsutils/__init__.py").read_text(encoding="utf-8")
    assert re.search(r'__version__\s*=\s*"0\.1\.1"', init)


@pytest.mark.parametrize("name", SIBLINGS)
@pytest.mark.reads_siblings
def test_siblings_at_their_candidate_tags(name):
    """Asserted **at the sibling's coordinated tag**, not at its tip (015, FR-080c).

    This was a strict xfail until the maintainer re-cut the tags at 016's numbers
    (2026-10-16). From then it passed, ``strict`` turned that into a failure, and
    the marker went (017 T077). A sibling with no tag skips with the resolver's
    reason.
    """
    from tests.support.sibling_tags import tagged

    tree = tagged(name)
    assert _sibling_version(tree.read, name) == PINNED[name]


@pytest.mark.parametrize("name", SIBLINGS)
@pytest.mark.reads_siblings
def test_siblings_at_feat_xml_refactor(name):
    """What feature 016 itself guarantees: each sibling's ``feat/xml-refactor`` head.

    Added in 016's record commit, once those heads exist; in its bump commit this
    would have failed by construction. Read with ``git show``, so the working tree's
    checked-out branch does not matter. Skips with a reason when the checkout or
    the branch is absent.
    """
    import subprocess

    checkout = REPO_ROOT.parent / name
    if not (checkout / ".git").exists():
        pytest.skip(f"no sibling checkout at {checkout}")

    def read(relpath: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(checkout), "show", f"feat/xml-refactor:{relpath}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"{name}: feat/xml-refactor:{relpath} not readable ({result.stderr.strip()})")
        return result.stdout

    assert _sibling_version(read, name) == PINNED[name]
