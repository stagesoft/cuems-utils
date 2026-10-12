"""Contract C5 (T022a) — the error hierarchy, and what it lets a caller do.

Exceptions are the one part of this feature's surface that has to be
**importable**: a returned type can stay internal because the caller only
inspects what it is handed, but an exception the caller cannot name is an
exception the caller cannot catch. The alternative — which is what consumers do
today — is matching on message strings.

Four claims, each of which fails independently:

* every failure path raises its **declared** type, and none raises a bare
  ``ValueError``/``RuntimeError``;
* a validation failure is catchable as ``ValidationError`` and a structural one
  as ``SchemaError`` **without catching the other**;
* I/O failures propagate **unwrapped** — a missing file is an ``OSError``,
  because every consumer already handles one;
* the ``ValidationError`` ``save()`` raises **carries** the violation, in the
  same form ``validate()`` reports it (FR-034b). Implementing the hierarchy is
  not enough: the failure mode is a consumer catching the exception and finding
  nothing on it to show a user.
"""

from __future__ import annotations

import inspect
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import CuemsError, IngestError, SchemaError, ValidationError
from tests.support import invalid_scripts as broken
from tests.support.public_api import PUBLIC_SCRIPT_METHODS, assert_no_xml_import


def test_the_hierarchy_is_exactly_as_specified():
    assert issubclass(CuemsError, Exception)
    assert issubclass(ValidationError, CuemsError)
    assert issubclass(SchemaError, ValidationError)
    assert issubclass(IngestError, CuemsError)
    assert not issubclass(IngestError, ValidationError)


def test_a_structural_failure_is_catchable_as_schema_error_alone(tmp_path):
    with pytest.raises(SchemaError):
        broken.structurally_invalid().save(tmp_path / "show.xml")


def test_a_semantic_failure_is_not_a_schema_error(tmp_path):
    """The two tiers must not collapse into one exception type."""
    with pytest.raises(ValidationError) as caught:
        broken.semantically_invalid().save(tmp_path / "show.xml")
    assert not isinstance(caught.value, SchemaError)


def test_ingest_error_is_distinct_from_both():
    with pytest.raises(IngestError) as caught:
        CuemsScript.from_json("[1, 2, 3]")
    assert not isinstance(caught.value, ValidationError)


def test_a_missing_file_raises_oserror_unwrapped(tmp_path):
    with pytest.raises(FileNotFoundError) as caught:
        CuemsScript.load(tmp_path / "absent.xml")
    assert not isinstance(caught.value, CuemsError)


@pytest.mark.skipif(
    hasattr(__import__("os"), "geteuid") and __import__("os").geteuid() == 0,
    reason="root bypasses file permissions, so the unreadable case cannot occur",
)
def test_an_unreadable_file_raises_oserror_unwrapped(tmp_path):
    target = tmp_path / "unreadable.xml"
    broken.valid_script().save(target)
    target.chmod(0o000)
    try:
        with pytest.raises(OSError) as caught:
            CuemsScript.load(target)
        assert not isinstance(caught.value, CuemsError)
    finally:
        target.chmod(0o600)


def test_a_structurally_invalid_document_on_disk_raises_schema_error(tmp_path):
    target = tmp_path / "bad.xml"
    target.write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<cms:CuemsProject xmlns:cms="https://stagelab.coop/cuems/">'
        "<CuemsScript><nonsense /></CuemsScript></cms:CuemsProject>",
        encoding="utf-8",
    )
    with pytest.raises(SchemaError):
        CuemsScript.load(target)


def test_no_public_failure_path_raises_a_bare_builtin(tmp_path):
    """A bare ``ValueError`` is not an API; it is the absence of one."""
    cases = [
        lambda: CuemsScript.from_json("[1, 2, 3]"),
        lambda: broken.structurally_invalid().save(tmp_path / "a.xml"),
        lambda: broken.semantically_invalid().save(tmp_path / "b.xml"),
    ]
    for case in cases:
        with pytest.raises(CuemsError):
            case()


def test_the_raised_violation_matches_what_validate_reports(tmp_path):
    """FR-034b, field by field rather than by identity."""
    script = broken.semantically_invalid()

    with pytest.raises(ValidationError) as caught:
        script.save(tmp_path / "show.xml")

    carried = caught.value.violation
    reported = [
        v
        for v in script.validate()
        if (v.tier, v.rule, v.location, v.message)
        == (carried.tier, carried.rule, carried.location, carried.message)
    ]
    assert reported, (carried, list(script.validate()))


def test_the_carried_violation_is_reachable_from_the_base_class(tmp_path):
    """A consumer catching ``CuemsError`` still gets somewhere useful."""
    with pytest.raises(CuemsError) as caught:
        broken.semantically_invalid().save(tmp_path / "show.xml")
    assert getattr(caught.value, "violation", None) is not None


@pytest.mark.parametrize("name", PUBLIC_SCRIPT_METHODS)
def test_every_public_method_documents_its_error_behaviour(name):
    doc = inspect.getdoc(getattr(CuemsScript, name)) or ""
    assert "Raises:" in doc, f"CuemsScript.{name} has no Raises: entry"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("load", ("SchemaError", "OSError")),
        ("from_json", ("IngestError", "SchemaError")),
        ("save", ("ValidationError", "OSError")),
    ],
)
def test_the_raises_entry_names_the_actual_types(name, expected):
    doc = inspect.getdoc(getattr(CuemsScript, name)) or ""
    for type_name in expected:
        assert type_name in doc, f"CuemsScript.{name} does not name {type_name}"


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
