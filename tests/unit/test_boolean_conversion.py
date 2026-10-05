# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Feature 014 — the boolean rewrite inside the 1 -> 2 steps (T014).

Two things to prove, and the second is the one the task exists for:

* the rewrite **happens**, on both schemas, with in-corpus evidence rather than
  only synthetic trees;
* it is **order-independent with respect to the media elements**. The rewrite
  matches on element *name*, and this feature's four ``MediaType`` additions
  are different names, so there is no overlap — but "there is no overlap" is an
  argument, and this file is the assertion.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cuemsutils.xml.versioning import convert, read_version

PRE_008 = Path("tests/data/corpus/pre-008")

#: The four elements feature 014 adds, as text, in schema order.
MEDIA_BLOCK = (
    "<pixel_width>3840</pixel_width>"
    "<pixel_height>2160</pixel_height>"
    "<file_size>107374182400</file_size>"
    "<file_hash>d41d8cd98f00b204e9800998ecf8427e</file_hash>"
)


def _script(media_first: bool) -> ET.ElementTree:
    """A version-1 script: old-form booleans **and** the media block.

    *media_first* swaps which cue carries the block, so the conversion meets
    the two kinds of element in either order.
    """
    with_block = (
        "<Cue class=\"video\"><enabled>True</enabled><autoload>False</autoload>"
        "<timecode>False</timecode>"
        f"<Media><file_name>a.mov</file_name>{MEDIA_BLOCK}</Media></Cue>"
    )
    without = (
        "<Cue class=\"audio\"><enabled>False</enabled><autoload>True</autoload>"
        "<timecode>True</timecode>"
        "<Media><file_name>b.wav</file_name></Media></Cue>"
    )
    order = (with_block, without) if media_first else (without, with_block)
    return ET.ElementTree(
        ET.fromstring(
            "<CuemsProject><CuemsScript><CueList>"
            "<enabled>True</enabled><autoload>False</autoload><timecode>False</timecode>"
            f"<contents>{''.join(order)}</contents>"
            "</CueList></CuemsScript></CuemsProject>"
        )
    )


def _texts(tree: ET.ElementTree, name: str) -> list[str]:
    return [(e.text or "") for e in tree.getroot().iter(name)]


# --- the rewrite happens ----------------------------------------------------


@pytest.mark.parametrize("media_first", [True, False], ids=["media-first", "media-last"])
@pytest.mark.parametrize("name", ["enabled", "autoload", "timecode"])
def test_every_script_boolean_is_rewritten_whatever_the_document_order(media_first, name):
    tree = _script(media_first)
    before = _texts(tree, name)
    assert before and all(v in ("True", "False") for v in before), before

    convert("script", tree, 1, 2)

    after = _texts(tree, name)
    assert all(v in ("true", "false") for v in after), after
    # case-only: the *values* are preserved, not merely lowercased into shape
    assert [v.lower() for v in before] == after


@pytest.mark.parametrize("media_first", [True, False], ids=["media-first", "media-last"])
def test_the_media_block_is_untouched_by_the_boolean_rewrite(media_first):
    """T013's order-independence requirement, asserted rather than argued.

    The rewrite must not care whether ``pixel_width`` is present, absent, or
    arriving in the same pass.
    """
    tree = _script(media_first)
    convert("script", tree, 1, 2)

    assert _texts(tree, "pixel_width") == ["3840"]
    assert _texts(tree, "pixel_height") == ["2160"]
    assert _texts(tree, "file_size") == ["107374182400"]
    assert _texts(tree, "file_hash") == ["d41d8cd98f00b204e9800998ecf8427e"]


def test_a_cue_with_no_media_block_converts_beside_one_that_has_it():
    """Both shapes in one document, which is the realistic library state."""
    tree = _script(media_first=True)
    convert("script", tree, 1, 2)

    medias = list(tree.getroot().iter("Media"))
    assert len(medias) == 2
    assert medias[0].find("pixel_width") is not None
    assert medias[1].find("pixel_width") is None


def test_the_network_map_step_rewrites_its_two_booleans():
    tree = ET.ElementTree(
        ET.fromstring(
            "<CuemsNetworkMap><node_list><node>"
            "<adopted>True</adopted><online>False</online>"
            "</node></node_list></CuemsNetworkMap>"
        )
    )
    convert("network_map", tree, 1, 2)
    assert _texts(tree, "adopted") == ["true"]
    assert _texts(tree, "online") == ["false"]


# --- the properties a second run depends on --------------------------------


def test_the_rewrite_is_idempotent():
    """Why the migrated corpus can stay unmarked at version 1.

    The top tier carries current content with no ``doc_version``, so the
    conversion runs over already-converted documents on every read. That is
    only safe because a second pass is a no-op — ``_BOOLEAN_LITERALS`` is keyed
    on the *old* spellings, so a lowercase value matches nothing and is left
    alone.
    """
    tree = _script(media_first=True)
    convert("script", tree, 1, 2)
    once = ET.tostring(tree.getroot())
    convert("script", tree, 1, 2)
    assert ET.tostring(tree.getroot()) == once


def test_a_value_that_is_neither_literal_is_left_alone_not_guessed_at():
    """It cannot occur in a document that was valid under ``cms:BoolType``.

    If one appears anyway, the strict decode that follows refuses it **by
    name**, which is a better outcome than this function inventing a value —
    the exact failure mode ``_Bool.decode`` was tightened to remove in
    ``be3e86e``.
    """
    tree = ET.ElementTree(
        ET.fromstring("<CuemsProject><CueList><enabled>yes</enabled></CueList></CuemsProject>")
    )
    convert("script", tree, 1, 2)
    assert _texts(tree, "enabled") == ["yes"]


def test_the_step_reports_what_it_rewrote():
    """A conversion that changes a document and says nothing is unauditable."""
    steps = convert("script", _script(media_first=True), 1, 2)
    assert len(steps) == 1
    dropped = steps[0].dropped_elements
    assert any("xs:boolean" in record for record in dropped), dropped


# --- in-corpus evidence, not only synthetic trees (T015a's thin-coverage note)


def test_the_pre_008_fixture_actually_exercises_the_boolean_rewrite():
    """The corpus evidence, asserted explicitly rather than relied on.

    ``T015a`` recorded that ``pre-008/script_v1_all_transforms.xml`` is read
    through the registry by ``test_conversion.py`` and happens to carry an
    old-form boolean — one element, incidentally. "Incidentally" is not
    coverage: a future edit to that fixture could remove the only in-corpus
    document that proves this step runs on real bytes, and nothing would fail.
    This is what fails.
    """
    source = PRE_008 / "script_v1_all_transforms.xml"
    tree = ET.parse(source)
    assert read_version(tree) == 1, "the fixture must stay at version 1"

    old_form = [
        (name, text)
        for name in ("enabled", "autoload", "timecode")
        for text in _texts(tree, name)
        if text in ("True", "False")
    ]
    assert old_form, (
        f"{source} no longer carries an old-form boolean, so the 1 -> 2 "
        "boolean rewrite has no in-corpus evidence. Add one back, or move the "
        "evidence to a fixture that is also read through the registry."
    )

    convert("script", tree, 1, 2)
    for name in ("enabled", "autoload", "timecode"):
        assert all(t in ("true", "false", "") for t in _texts(tree, name))
