"""Contract C1 (T018) — ``save()`` never half-writes (FR-003).

The failure this pins is the one that costs a show: an editor saves over a
project file, validation fails partway through serialization, and what is left
on disk is a truncated document that neither the editor nor the engine can
read. "Raises on invalid input" is not enough — *what happened to the file* is
the requirement.

Two states, both asserted:

* the target **existed** — its bytes are unchanged, to the byte;
* the target **did not exist** — it still does not, and no stray temporary is
  left beside it either.
"""

from __future__ import annotations

import sys

import pytest

from cuemsutils.errors import ValidationError
from tests.support import invalid_scripts as broken
from tests.support.public_api import assert_no_xml_import

CASES = {
    "structural": broken.structurally_invalid,
    "semantic": broken.semantically_invalid,
}


@pytest.fixture(params=sorted(CASES), ids=sorted(CASES))
def invalid_script(request):
    return CASES[request.param]()


def test_a_valid_script_writes_and_reloads(tmp_path):
    """The control. Without it, every assertion below passes on a no-op."""
    from cuemsutils.cues.CuemsScript import CuemsScript

    target = tmp_path / "show.xml"
    broken.valid_script().save(target)

    assert target.exists()
    assert CuemsScript.load(target) is not None


def test_an_existing_file_is_byte_unchanged_when_the_save_fails(
    tmp_path, invalid_script
):
    target = tmp_path / "show.xml"
    broken.valid_script().save(target)
    before = target.read_bytes()

    with pytest.raises(ValidationError):
        invalid_script.save(target)

    assert target.read_bytes() == before


def test_the_target_is_not_created_when_the_save_fails(tmp_path, invalid_script):
    target = tmp_path / "new.xml"

    with pytest.raises(ValidationError):
        invalid_script.save(target)

    assert not target.exists()


def test_no_temporary_file_is_left_behind(tmp_path, invalid_script):
    """An atomic write needs a scratch file; a failed one must not keep it."""
    target = tmp_path / "new.xml"

    with pytest.raises(ValidationError):
        invalid_script.save(target)

    assert list(tmp_path.iterdir()) == []


def test_save_accepts_str_and_pathlike(tmp_path):
    script = broken.valid_script()
    script.save(str(tmp_path / "a.xml"))
    script.save(tmp_path / "b.xml")
    assert (tmp_path / "a.xml").read_bytes() == (tmp_path / "b.xml").read_bytes()


def test_a_missing_parent_directory_raises_oserror_unwrapped(tmp_path):
    """FR-035: I/O failures are not wrapped in a library exception."""
    with pytest.raises(OSError) as caught:
        broken.valid_script().save(tmp_path / "no" / "such" / "dir" / "show.xml")
    assert not isinstance(caught.value, ValidationError)


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
