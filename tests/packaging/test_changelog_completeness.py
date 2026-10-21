# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Both changelogs are complete from ``0.1.0rc5`` on, and stay that way (feature 017, D3, FR-033).

Two release candidates once left this tree with no changelog entry at all. A header-only check
missed that this tree's ``0.1.0rc15`` was a different, never-built entry with the same number as
the released one. So this test carries the released sets as **data**, and compares released
entries **byte for byte** against the release line whenever that line's ref is present.

The data was measured on 2026-10-21, from ``origin/debian/bookworm``'s non-``UNRELEASED`` headers
and PyPI's JSON API (yanked files included; ``pip index`` omits them). It is re-measured at every
reconciliation, and a new release updates the data and the changelogs in the same commit. See
``specs/017-release-line-reconciliation/contracts/changelog-completeness.md``.

Checks that need git refs (the release line, the ``debian/*`` tags) skip with a reason on a checkout
without them, such as a shallow CI clone. Everything else runs anywhere.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

import cuemsutils

ROOT = Path(__file__).resolve().parents[2]
DEBIAN_CHANGELOG = ROOT / "debian" / "changelog"
CHANGELOG_MD = ROOT / "CHANGELOG.md"

RELEASED_DEBIAN = {"0.1.0rc8", "0.1.0rc9", "0.1.0rc10", "0.1.0rc11", "0.1.0rc12",
                   "0.1.0rc14", "0.1.0rc15", "0.1.0rc16", "0.1.0rc16+1", "0.1.0rc17"}
#: PyPI releases from 0.1.0rc5 on (PyPI's JSON API, 2026-10-21).
RELEASED_PYPI = {"0.1.0rc7", "0.1.0rc8", "0.1.0rc10", "0.1.0rc11",
                 "0.1.0rc14", "0.1.0rc15", "0.1.0rc16"}
#: Set in the source but released nowhere (spec M1, Q7).
NEVER_PUBLISHED = {"0.1.0rc5", "0.1.0rc6", "0.1.0rc13"}
OLDEST_RELEASED_DEBIAN = "0.1.0rc8"
RELEASE_LINE_REF = "origin/debian/bookworm"
DEBIAN_ONLY_MARK = "(Debian only; not published to PyPI)"
NEVER_MARK = "never published"

_HEADER = re.compile(r"^(\S+) \(([^)]+)\) ([^;]+);")


# --- parsing --------------------------------------------------------------------------

def _entries(text: str) -> list[tuple[str, str, str]]:
    """``(version, distribution, exact text)`` per entry: header line through trailer line."""
    out, cur = [], None
    for line in text.splitlines(keepends=True):
        if _HEADER.match(line):
            cur = [line]
        elif cur is not None:
            cur.append(line)
            if line.startswith(" -- "):
                body = "".join(cur)
                m = _HEADER.match(body)
                out.append((m.group(2), m.group(3).strip(), body))
                cur = None
    return out


def _sections() -> dict[str, str]:
    """``CHANGELOG.md``'s ``## <heading>`` sections, keyed by the heading's first token."""
    text = CHANGELOG_MD.read_text(encoding="utf-8")
    sections, key, buf = {}, None, []
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            if key is not None:
                sections[key] = "".join(buf)
            key, buf = line[3:].split(" ", 1)[0].strip(), [line]
        elif key is not None:
            buf.append(line)
    if key is not None:
        sections[key] = "".join(buf)
    return sections


def _git(*args: str) -> str | None:
    run = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return run.stdout if run.returncode == 0 else None


def _ref_changelog(ref: str) -> str | None:
    if _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}") is None:
        return None
    return _git("show", f"{ref}:debian/changelog")


# --- check 1: the three version sites agree ------------------------------------------

def test_1_the_top_versions_agree():
    top_debian = _entries(DEBIAN_CHANGELOG.read_text(encoding="utf-8"))[0][0]
    top_md = next(iter(_sections()))
    assert top_debian == cuemsutils.__version__ == top_md, (top_debian, cuemsutils.__version__, top_md)


# --- check 2: every released Debian version has its entry ------------------------------

def test_2_debian_changelog_carries_every_released_version():
    ours = {v for v, _d, _e in _entries(DEBIAN_CHANGELOG.read_text(encoding="utf-8"))}
    assert RELEASED_DEBIAN <= ours, f"missing: {sorted(RELEASED_DEBIAN - ours)}"


def test_2_debian_changelog_carries_every_release_line_and_tag_version():
    refs = [RELEASE_LINE_REF] + sorted((_git("tag", "-l", "debian/*") or "").split())
    texts = {ref: _ref_changelog(ref) for ref in refs}
    texts = {ref: t for ref, t in texts.items() if t is not None}
    if RELEASE_LINE_REF not in texts:
        pytest.skip(f"{RELEASE_LINE_REF} is not available in this checkout (shallow clone?)")
    ours = {v for v, _d, _e in _entries(DEBIAN_CHANGELOG.read_text(encoding="utf-8"))}
    missing = {
        ref: sorted({v for v, d, _e in _entries(t) if d != "UNRELEASED"} - ours)
        for ref, t in texts.items()
    }
    assert not any(missing.values()), {k: v for k, v in missing.items() if v}


# --- check 3: released entries are byte-identical to the release line ------------------

def test_3_released_entries_are_byte_identical_to_the_release_line():
    theirs = _ref_changelog(RELEASE_LINE_REF)
    if theirs is None:
        pytest.skip(f"{RELEASE_LINE_REF} is not available in this checkout (shallow clone?)")
    ours = {v: e for v, _d, e in _entries(DEBIAN_CHANGELOG.read_text(encoding="utf-8"))}
    differs = [v for v, d, e in _entries(theirs) if d != "UNRELEASED" and ours.get(v) != e]
    assert not differs, f"released entries that differ from {RELEASE_LINE_REF}: {differs}"


# --- check 4: no stray UNRELEASED entry among the released ones ------------------------

def test_4_only_the_top_entry_is_unreleased_above_the_oldest_release():
    """The six older never-built entries (``0.1.0rc5``, ``0.0.*``) are ``UNRELEASED`` by nature
    and sit below the oldest release, so they are exempt (spec M2). Above it, an ``UNRELEASED``
    entry other than the top is what this tree's retrospective ``0.1.0rc15`` was."""
    entries = _entries(DEBIAN_CHANGELOG.read_text(encoding="utf-8"))
    versions = [v for v, _d, _e in entries]
    above = entries[1:versions.index(OLDEST_RELEASED_DEBIAN)]
    stray = [v for v, d, _e in above if d == "UNRELEASED"]
    assert entries[0][1] == "UNRELEASED" or entries[0][0] in RELEASED_DEBIAN
    assert not stray, f"UNRELEASED entries below the top: {stray}"


# --- check 5: CHANGELOG.md covers every release ----------------------------------------

def test_5_changelog_md_covers_every_release():
    text = CHANGELOG_MD.read_text(encoding="utf-8")
    sections = _sections()
    uncovered = sorted(
        v for v in RELEASED_DEBIAN | RELEASED_PYPI
        if v not in sections and f"<!-- debian: {v}" not in text
    )
    assert not uncovered, f"no section or <!-- debian: --> comment for: {uncovered}"


def test_5_changelog_md_has_an_earlier_releases_pointer():
    assert "Earlier" in _sections(), "no '## Earlier releases' section"


def test_5_exactly_one_unreleased_section_and_it_is_first():
    headings = [line for line in CHANGELOG_MD.read_text(encoding="utf-8").splitlines()
                if line.startswith("## ")]
    unreleased = [h for h in headings if "Unreleased" in h]
    assert len(unreleased) == 1, unreleased
    assert headings[0] == unreleased[0], (headings[0], unreleased[0])


# --- check 6: the markings say where each version was published ------------------------

def test_6_debian_only_and_never_published_versions_are_marked():
    text = CHANGELOG_MD.read_text(encoding="utf-8")
    sections = _sections()
    problems = []
    for v in sorted(RELEASED_DEBIAN - RELEASED_PYPI):
        if v in sections:
            if DEBIAN_ONLY_MARK not in sections[v]:
                problems.append(f"{v}: section lacks {DEBIAN_ONLY_MARK!r}")
        elif f"<!-- debian: {v}" not in text:  # a Debian revision (rc16+1) is a comment
            problems.append(f"{v}: neither a marked section nor a debian comment")
    for v in sorted(NEVER_PUBLISHED):
        where = sections.get(v) or "".join(
            line for line in text.splitlines(keepends=True) if f"`{v}`" in line
        )
        if NEVER_MARK not in where:
            problems.append(f"{v}: no {NEVER_MARK!r} marking or line")
    for v in sorted(RELEASED_PYPI):
        if v in sections and (DEBIAN_ONLY_MARK in sections[v] or NEVER_MARK in sections[v]):
            problems.append(f"{v}: on PyPI but marked otherwise")
    assert not problems, problems
