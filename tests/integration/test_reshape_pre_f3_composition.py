"""G5 (US3), T030-T033 — the defeated conversion, as a **composition** test
(FR-053): a unit test on the converter with an already-reshaped tree would
pass the moment the paths were added and would not catch the next instance
of this class. These exercise the real tool, ``cuems-reshape-devices``,
against documents in either device shape, and then the real load path.
"""

from __future__ import annotations

import shutil

import pytest

from cuemsutils.tools.ConfigBase import load_config_document
from cuemsutils.xml.reshape_devices import reshape_file
from cuemsutils.xml.settings import Settings
from tests.support.corpus import REPO_ROOT

#: Pre-013 (flat players) **and** pre-F3 (the retired counts) —
#: sourced from ``../cuems-nodeconf@4d7c91d:tests/fixtures/etc_cuems/settings.xml``,
#: itself copied from ``cuems-utils@d0340fc`` (0.1.0rc16). Provenance recorded
#: in the file's own header comment (T029, SC-003).
PRE_F3_PRE_013 = REPO_ROOT / "tests" / "data" / "settings_pre013_pre_f3.xml"


def test_a_pre_013_pre_f3_document_reshapes_and_then_loads(tmp_path):
    """FR-050, FR-057, SC-003 — the dead end, inverted. Before G5 this
    document's own reproduction (quickstart.md §4) was::

        skipped (would not validate: ... Unexpected child with tag
        'audio_cards' at position 3 ...)

    After G5 it must say ``reshaped``, and the result must then load, with
    both retired counts gone."""
    target = tmp_path / "settings.xml"
    shutil.copy2(PRE_F3_PRE_013, target)

    verdict = reshape_file(target, write=True, dry_run=False, clock="20261013T000000")
    assert verdict == "reshaped"

    document = load_config_document(Settings, str(target), "settings")
    node = document.xml_dict["Settings"]["node"]  # type: ignore[index]
    players = {wrapper["player"]["class"]: wrapper["player"] for wrapper in node["players"]}
    assert "audio_cards" not in players["audio"]
    assert "universes" not in players["dmx"]

    # FR-057 — every drop is still named in the load report, under the
    # reshaped predicate path exactly as it always was under the flat one.
    drops = {d for step in document.document_conversions for d in step.dropped_elements}
    assert "players/player[@class='audio']/audio_cards" in drops
    assert "players/player[@class='dmx']/universes" in drops


def test_a_flat_document_without_the_retired_counts_still_migrates(tmp_path):
    """FR-055 — the eight-day window between F3 and the reshape is a real
    population: a flat document that never carried the retired counts must
    migrate cleanly too."""
    text = PRE_F3_PRE_013.read_text(encoding="utf-8")
    text = text.replace(
        "<audio_cards>1</audio_cards>", ""
    ).replace(
        "<universes>1</universes>", ""
    )
    target = tmp_path / "settings.xml"
    target.write_text(text, encoding="utf-8")

    verdict = reshape_file(target, write=True, dry_run=False, clock="20261013T000001")
    assert verdict == "reshaped"

    load_config_document(Settings, str(target), "settings")  # must not raise


def test_a_second_run_over_an_already_migrated_document_changes_no_bytes(tmp_path):
    """FR-052 — idempotence of the tool composition, not only of the step."""
    target = tmp_path / "settings.xml"
    shutil.copy2(PRE_F3_PRE_013, target)
    reshape_file(target, write=True, dry_run=False, clock="20261013T000002")
    before = target.read_bytes()

    verdict = reshape_file(target, write=True, dry_run=False, clock="20261013T000003")

    assert verdict == "already current"
    assert target.read_bytes() == before


def test_the_tool_still_refuses_a_document_that_would_not_validate(tmp_path):
    """T037 — the fix makes more documents valid (both player shapes,
    with or without the retired counts) and must not relax the guarantee
    that a document the schema genuinely rejects is never written. Removing
    a player's required ``<path>`` is invalid under every version and every
    device shape."""
    text = PRE_F3_PRE_013.read_text(encoding="utf-8")
    text = text.replace(
        "<path>/usr/local/bin/cuems-audioplayer</path>", ""
    )
    target = tmp_path / "settings.xml"
    target.write_text(text, encoding="utf-8")
    before = target.read_bytes()

    verdict = reshape_file(target, write=True, dry_run=False, clock="20261013T000005")

    assert verdict.startswith("skipped (would not validate")
    assert target.read_bytes() == before


def test_tool_order_is_reshape_then_convert_not_inverted(tmp_path):
    """FR-054 — convert-before-reshape dead-ends for ``script`` (013's own
    documented reason); this fix must not invert that into the mirror image
    for ``settings``. Reshaping first and validating against the conversion
    registry (what this tool already does) is the order that completes."""
    target = tmp_path / "settings.xml"
    shutil.copy2(PRE_F3_PRE_013, target)

    verdict = reshape_file(target, write=True, dry_run=False, clock="20261013T000004")

    assert verdict == "reshaped"
