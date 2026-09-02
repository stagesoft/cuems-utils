"""The conversion registry, exercised through the load path (ITEM E, US6,
T094-T097, T099) — data-model.md §1.1.
"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome
from cuemsutils.xml import versioning
from tests.support.corpus import REPO_ROOT

PRE_008 = REPO_ROOT / "tests" / "data" / "corpus" / "pre-008"
ALL_TRANSFORMS = PRE_008 / "script_v1_all_transforms.xml"
FADE_ACTIONS = PRE_008 / "fade_actions.xml"


# --- T094: a pre-008 document converts in memory; the file stays untouched -


def test_a_pre_008_document_converts_in_memory_and_the_file_is_byte_unchanged(tmp_path):
    working_copy = tmp_path / "doc.xml"
    shutil.copy2(ALL_TRANSFORMS, working_copy)
    before = working_copy.read_bytes()

    loaded, report = CuemsScript.load_with_report(working_copy)

    assert loaded is not None
    assert report.outcome is Outcome.CONVERTED
    assert working_copy.read_bytes() == before, "the load path must write nothing (FR-041)"


# --- T095: no backup is needed (or attempted) to load an old document -----


def test_loading_an_old_document_on_unwritable_media_still_works(tmp_path, monkeypatch):
    """FR-041a: the backup obligation attaches to *persisting* a schema
    upgrade, not to converting — the load path writes nothing, so read-only
    media is not an obstacle. Simulated by making ``os.replace``/``open`` for
    writing raise if the load path ever attempts one."""
    import os as _os

    def _boom(*args, **kwargs):  # pragma: no cover - only invoked on failure
        raise AssertionError("the load path attempted to write")

    monkeypatch.setattr(_os, "replace", _boom)

    working_copy = tmp_path / "doc.xml"
    shutil.copy2(ALL_TRANSFORMS, working_copy)

    loaded = CuemsScript.load(working_copy)
    assert loaded is not None


# --- T096: one version step, three transformations, on the one fixture ----


def test_one_version_step_carries_all_three_transformations():
    working_copy_report = CuemsScript.load_with_report(ALL_TRANSFORMS)[1]
    assert working_copy_report.outcome is Outcome.CONVERTED
    assert len(working_copy_report.conversions) == 1

    record = working_copy_report.conversions[0]
    assert record.from_version == 1
    assert record.to_version == 2
    # All three transformations named in one description, and the drop
    # reported — SC-016d's "one increment, three transformations" made
    # observable rather than merely true internally.
    assert "duration" in record.description
    assert "fade_in" in record.description or "action_type" in record.description
    assert "fade_profiles" in record.description
    assert record.dropped_elements, "the fade_profiles drop must be reported (SC-016e)"


def test_the_fade_in_fade_out_conversion_has_a_dedicated_fixture_too():
    loaded, report = CuemsScript.load_with_report(FADE_ACTIONS)
    assert report.outcome is Outcome.CONVERTED
    action_types = {cue["action_type"] for cue in loaded.cuelist.contents}
    assert action_types == {"play", "stop"}


# --- T097: idempotent, validates, durations preserved to the millisecond --


def test_conversion_is_idempotent_and_durations_survive_to_the_millisecond(tmp_path):
    once = tmp_path / "once.xml"
    shutil.copy2(ALL_TRANSFORMS, once)
    loaded_once = CuemsScript.load(once)

    # Persist the converted, in-memory result and reload — the second load
    # sees an already-current document (doc_version=2 was written), so the
    # registry's step does not run a second time; the values must still
    # agree with the first conversion's.
    twice = tmp_path / "twice.xml"
    loaded_once.save(twice)
    loaded_twice = CuemsScript.load(twice)

    assert not loaded_once.validate()
    assert not loaded_twice.validate()
    from cuemsutils.cues.MediaCue import MediaCue

    media_once = next(c for c in loaded_once.cuelist.contents if isinstance(c, MediaCue))
    media_twice = next(c for c in loaded_twice.cuelist.contents if isinstance(c, MediaCue))
    assert str(media_once.media.duration) == str(media_twice.media.duration)
    assert str(media_once.media.duration) == "00:01:00.000"


def test_converted_document_validates_against_the_current_schema():
    loaded = CuemsScript.load(ALL_TRANSFORMS)
    assert not loaded.validate()


# --- T099: an identity step; a newer-than-library marker still raises -----


def test_an_identity_version_step_loads_with_no_backup_and_no_repair(tmp_path):
    """FR-051d/research R9 — a step with no registered conversion is valid:
    the version increments, the document is untouched, nothing is reported
    dropped or repaired. Exercised directly against the registry rather than
    through a real schema (none of this feature's own schemas has a version
    2 with an identity predecessor — the mechanism needs its own test, per
    R9's own note)."""
    schema_name = "test_identity_scratch_schema"
    tree = ET.ElementTree(ET.Element("Root"))

    steps = versioning.convert(schema_name, tree, 1, 2)
    assert len(steps) == 1
    assert steps[0].description.startswith("identity")
    assert steps[0].dropped_elements == ()
    # Nothing in the (scratch) document changed.
    assert list(tree.getroot()) == []


def test_a_newer_than_library_marker_raises_distinguishably(tmp_path):
    from cuemsutils.errors import ValidationError

    doc = tmp_path / "from_the_future.xml"
    valid = tmp_path / "valid.xml"
    from tests.support import invalid_scripts as broken

    broken.valid_script().save(valid)
    text = valid.read_text().replace('doc_version="2"', 'doc_version="999"')
    doc.write_text(text)

    with pytest.raises(ValidationError) as excinfo:
        CuemsScript.load(doc)
    assert "999" in str(excinfo.value)
    assert excinfo.value.violation is not None
    assert excinfo.value.violation.rule == "document_version_too_new"
