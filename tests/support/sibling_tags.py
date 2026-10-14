# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The coordinated-tag resolver (feature 015, FR-080c..FR-080f).

A cross-repository claim resolves a sibling at its ``xml-refactor-merge-candidate``
**tag**, never at its tip:

=====================================  =========
checkout absent                        skip, with a reason
checkout present, tag absent           skip, with a *different* reason
tag resolves, claim holds              pass
tag resolves, claim does not hold      fail
=====================================  =========

A skip is never a silent pass. A *partial* tag set yields a partial, honest
result: the resolver is usable while only some siblings are tagged.

Re-cutting any one tag re-validates the **whole** set (FR-080d): a candidate tag
set is only as current as its least current member, and no packaging relation
expresses that. Moving a published tag is maintainer-only, never an agent's.

⚠ Annotated tags have two ids. ``git rev-parse <tag>`` is the *tag object*;
``<tag>^{commit}`` is the commit it points at. Everything this repository
records (``CLAUDE.md``, the migration guides) means the **commit**, and this
module only ever returns that one.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

TAG = "xml-refactor-merge-candidate"
SIBLINGS = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class TaggedTree:
    """A sibling checkout, resolved at its coordinated tag."""

    root: Path
    commit: str

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True
        )

    def exists(self, relpath: str) -> bool:
        return self._git("cat-file", "-e", f"{self.commit}:{relpath}").returncode == 0

    def read(self, relpath: str) -> str:
        """``relpath`` as it was at the tag. Fails (not skips) when absent: the
        tag resolved, so a missing file is a claim that does not hold."""
        result = self._git("show", f"{self.commit}:{relpath}")
        assert result.returncode == 0, (
            f"{self.root.name} at {TAG} ({self.commit[:7]}) has no {relpath}"
        )
        return result.stdout


def resolve(name: str, siblings: Path | None = None) -> TaggedTree | str:
    """The tagged tree, or the **reason** it cannot be had (a string).

    Returns the reason rather than skipping so the resolver itself is testable;
    :func:`tagged` is the form a contract test calls.
    """
    base = siblings if siblings is not None else SIBLINGS
    root = base / name
    if not (root / ".git").exists():
        return f"{root} is not checked out"
    found = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "--quiet",
         f"refs/tags/{TAG}^{{commit}}"],
        capture_output=True, text=True,
    )
    if found.returncode != 0:
        return f"{name} carries no {TAG} tag"
    return TaggedTree(root=root, commit=found.stdout.strip())


def tagged(name: str, siblings: Path | None = None) -> TaggedTree:
    """:func:`resolve`, skipping with the reason when there is no tree."""
    resolved = resolve(name, siblings)
    if isinstance(resolved, str):
        pytest.skip(
            f"{resolved}; the cross-repository claim cannot be verified here. "
            "Skipped rather than passed, so a partial tag set does not read "
            "as evidence."
        )
    return resolved
