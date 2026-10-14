# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T098 — the coordinated-tag resolver resolves what it says (FR-080c, FR-080e).

Four behaviours, against throwaway repositories so the result does not depend
on which siblings happen to be checked out: an absent checkout skips, an absent
tag skips with a *different* reason, a resolving tag whose tree contradicts a
claim fails, and a partial tag set yields a partial honest result.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.support import sibling_tags as st


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
         "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _repo(base: Path, name: str, files: dict[str, str], tag: bool) -> Path:
    repo = base / name
    repo.mkdir()
    _git(repo, "init", "-q")
    for rel, text in files.items():
        (repo / rel).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "tagged state")
    if tag:
        _git(repo, "tag", "-a", st.TAG, "-m", "candidate")
    return repo


def test_an_absent_checkout_skips_with_its_own_reason(tmp_path):
    reason = st.resolve("nowhere", tmp_path)
    assert isinstance(reason, str) and "not checked out" in reason
    with pytest.raises(pytest.skip.Exception):
        st.tagged("nowhere", tmp_path)


def test_an_absent_tag_skips_with_a_different_reason(tmp_path):
    _repo(tmp_path, "untagged", {"a.txt": "x"}, tag=False)
    reason = st.resolve("untagged", tmp_path)
    assert isinstance(reason, str) and st.TAG in reason
    assert "not checked out" not in reason
    with pytest.raises(pytest.skip.Exception):
        st.tagged("untagged", tmp_path)


def test_a_resolving_tag_reads_the_tagged_tree_not_the_tip(tmp_path):
    repo = _repo(tmp_path, "tagged", {"v.txt": "at the tag"}, tag=True)
    (repo / "v.txt").write_text("after the tag")
    _git(repo, "commit", "-qam", "tip moves on")

    tree = st.tagged("tagged", tmp_path)
    assert tree.read("v.txt") == "at the tag"
    # the commit, never the annotated tag object
    assert tree.commit == _git(repo, "rev-parse", f"{st.TAG}^{{commit}}")
    assert tree.commit != _git(repo, "rev-parse", st.TAG)


def test_a_claim_the_tagged_tree_contradicts_fails_rather_than_skips(tmp_path):
    _repo(tmp_path, "tagged", {"v.txt": "1"}, tag=True)
    tree = st.tagged("tagged", tmp_path)
    assert tree.exists("v.txt") and not tree.exists("gone.txt")
    with pytest.raises(AssertionError, match="has no gone.txt"):
        tree.read("gone.txt")


def test_a_partial_tag_set_yields_a_partial_honest_result(tmp_path):
    _repo(tmp_path, "one", {"f": "1"}, tag=True)
    _repo(tmp_path, "two", {"f": "2"}, tag=False)
    results = {n: st.resolve(n, tmp_path) for n in ("one", "two", "three")}
    assert isinstance(results["one"], st.TaggedTree)
    assert isinstance(results["two"], str) and isinstance(results["three"], str)
    assert results["two"] != results["three"]
