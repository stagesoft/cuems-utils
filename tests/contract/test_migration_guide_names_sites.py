# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T053 — the guide names every measured site, at a pinned sibling commit.

Two kinds of assertion, following ``test_migration_guide.py``'s precedent for
feature 012, and the second is the one that earns its keep:

1. **Presence** — every site research R7–R10 measured appears in the guide, with
   its path and its line, and each of the three fault classes is used by name. A
   checklist, worth having, but it only catches an omission.
2. **Resolution** — the guide records the sibling commit each line number was
   checked against, and that commit exists in that sibling's tree. Line numbers
   drift; the commit pin is what makes the check repeatable. Where a sibling is
   not checked out the check **skips with a reason** rather than passing — a
   green run on a machine with no siblings must not read as evidence that the
   cross-repository facts hold.

The sites live here as data because that is what makes the test a ratchet: a
spec amendment that adds a site has to add it here too, which is a review item
rather than a silent omission.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDE = REPO_ROOT / "specs" / "013-device-class-reshape" / "migration-guide.md"
SIBLINGS = REPO_ROOT.parent

#: ``sibling -> commit the guide pins its line numbers to``. Each must appear in
#: the guide *and* resolve in that sibling's git tree.
PINNED_COMMITS = {
    "cuems-engine": "1662a99",
    "cuems-common": "6ab4655",
    "cuems-editor": "106015c",
    "cuems-frontend": "3183845",
}

#: ``(file, line)`` pairs the guide must name, per repository. Measured in
#: research R7–R10 and re-verified at the commits above (T051).
SITES = {
    "cuems-engine": [
        ("NodeEngine.py", 456), ("NodeEngine.py", 457), ("NodeEngine.py", 566),
        ("NodeEngine.py", 508), ("NodeEngine.py", 598),
        ("NodeEngine.py", 472), ("NodeEngine.py", 473),
        ("NodeEngine.py", 530), ("NodeEngine.py", 531), ("NodeEngine.py", 534),
        ("NodeEngine.py", 565), ("NodeEngine.py", 571),
        ("NodeEngine.py", 645), ("NodeEngine.py", 646), ("NodeEngine.py", 651),
    ],
    "cuems-common": [
        ("cuems-extract-video-latency", 39),
        ("cuems-generate-display-conf", 66),
        ("cuems-generate-display-conf", 67),
        ("cuems-generate-display-conf", 76),
        ("cuems-display-setup", 527),
        ("cuems-display-setup", 569),
        ("cuems-display-setup", 571),
    ],
    "cuems-editor": [
        ("CuemsWsServer.py", 439),
        ("CuemsDBProject.py", 385), ("CuemsDBProject.py", 408),
        ("CuemsDBProject.py", 422), ("CuemsDBProject.py", 78),
        ("CuemsDBProject.py", 82), ("CuemsDBProject.py", 883),
        ("CuemsDBProject.py", 895),
        ("repair_durations.py", 204), ("repair_durations.py", 231),
    ],
    "cuems-frontend": [
        ("projects.service.ts", 39), ("projects.service.ts", 41),
        ("sequence.component.ts", 232), ("sequence.component.ts", 233),
        ("sequence.component.ts", 918), ("sequence.component.ts", 940),
        ("sequence.component.ts", 1088),
        ("sequence.component.ts", 343), ("sequence.component.ts", 344),
        ("sequence.component.ts", 347), ("sequence.component.ts", 348),
        ("sequence.component.ts", 890),
        ("sequence.component.ts", 117), ("sequence.component.ts", 132),
        ("sequence.component.ts", 379), ("sequence.component.ts", 449),
        ("sequence.component.ts", 682), ("sequence.component.ts", 683),
        ("audio-mixer.component.ts", 61), ("audio-mixer.component.ts", 63),
    ],
}

#: The three fault classes FR-031 enumerates. Every repository section has to
#: classify its sites in these words, because "it changes" is not a
#: classification a maintainer can act on.
FAULT_CLASSES = (
    "raises",
    "keeps resolving and becomes wrong",
    "keeps resolving correctly",
)


@pytest.fixture(scope="module")
def guide() -> str:
    assert GUIDE.is_file(), f"{GUIDE} does not exist"
    return GUIDE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def guide_words(guide: str) -> str:
    """``guide`` reduced to lower-case words.

    Markdown emphasis, table pipes, backticks and line wrapping are removed.
    Matching raw text makes a re-wrap look like a deleted warning, which is the
    kind of failure that gets a checking test deleted rather than fixed.
    """
    stripped = re.sub(r"[*`>#|]", " ", guide.lower())
    return re.sub(r"\s+", " ", stripped)


@pytest.mark.parametrize("repo", sorted(SITES))
def test_every_measured_site_is_named_with_its_line(guide: str, repo: str):
    missing = [
        f"{name}:{line}"
        for name, line in SITES[repo]
        if f"{name}:{line}" not in guide
    ]
    assert not missing, (
        f"{repo}: the guide does not name {missing}. Every site research "
        f"R7-R10 measured must appear with its path and its line, or a "
        f"maintainer cannot find it (T051)."
    )


@pytest.mark.parametrize("repo", sorted(PINNED_COMMITS))
def test_the_guide_pins_the_commit_each_line_number_was_checked_against(
    guide: str, repo: str
):
    commit = PINNED_COMMITS[repo]
    assert commit in guide, (
        f"{repo}: the guide does not record the commit {commit} its line "
        f"numbers were checked at. Line numbers drift; without the pin the "
        f"check is not repeatable."
    )
    assert repo in guide


@pytest.mark.parametrize("repo", sorted(PINNED_COMMITS))
def test_each_pinned_commit_resolves_in_its_sibling_tree(repo: str):
    """The resolution half. A pin that names nothing is worse than no pin."""
    tree = SIBLINGS / repo
    if not (tree / ".git").exists():
        pytest.skip(f"{tree} is not checked out; the pin cannot be resolved here")
    commit = PINNED_COMMITS[repo]
    result = subprocess.run(
        ["git", "-C", str(tree), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"{repo}: the guide pins {commit}, which does not resolve in {tree}. "
        f"Either the commit was never pushed to this checkout or the pin is "
        f"wrong; a guide whose named commit does not exist sends a maintainer "
        f"looking at the wrong lines."
    )


@pytest.mark.parametrize("fault", FAULT_CLASSES)
def test_every_fault_class_is_used_by_name(guide_words: str, fault: str):
    assert fault in guide_words, (
        f"the guide never classifies a site as {fault!r}. FR-031's three "
        f"classes are the whole point of the per-site tables: 'it changes' is "
        f"not something a maintainer can act on."
    )


def test_the_wire_contract_is_written_out(guide_words: str):
    """FR-032: ``cuems-frontend`` must not have to read a schema for this."""
    assert '"cue": {' in guide_words or '"cue": {...,' in guide_words.replace(" ", " ")
    assert '"class": "audio"' in guide_words
    assert "audiocue" in guide_words and "cueoutput" in guide_words


def test_the_two_editor_edge_cases_are_stated(guide_words: str):
    """Both follow from there being no conversion on read; neither is obvious."""
    assert "half-migrated" in guide_words
    assert "repair_durations.py" in guide_words
    assert "no conversion on read" in guide_words


def test_the_rollback_section_says_what_the_version_marker_does_not_do(guide_words: str):
    """FR-028, scenario 8. The marker does not move, so the error is raw."""
    assert "documenttoonewerror" in guide_words
    assert "rollback" in guide_words
    assert "backup" in guide_words


def test_the_rollback_section_names_when_the_backup_stops_working(guide_words: str):
    """The shape of feature 012's guide section 9b, answered for a reshape.

    A rollback section that lists the steps but not the expiry is the one a
    maintainer follows too late.
    """
    assert "stops being a usable rollback" in guide_words


def test_the_tool_ordering_is_stated(guide_words: str):
    """reshape, then convert — and why the other order is a dead end."""
    assert "cuems-reshape-devices" in guide_words
    assert "cuems-convert-documents" in guide_words
    assert "reshape, then convert" in guide_words


def test_the_silent_latency_loss_is_stated_plainly(guide_words: str):
    """``cuems-common``'s worst case: wrong, with no error and exit 0."""
    assert "output_latency_flag" in guide_words
    assert "silently discarded" in guide_words


def test_the_fixture_finding_is_recorded(guide_words: str):
    """The breakage a call-site census cannot see — feature 012's lesson, again."""
    assert "cuems-power-bridge" in guide_words
    assert "cuems-nodeconf" in guide_words
    assert "fixture" in guide_words
