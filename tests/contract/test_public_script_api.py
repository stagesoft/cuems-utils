"""Contract C0/C1 (T016) — the six methods, and nothing behind them.

The claim under test is narrow and worth stating precisely: *a consumer moving
show data in and out of this library names ``CuemsScript`` and nothing else*.
Three things follow, and each is asserted separately because each fails
independently:

* the six methods exist and are callable;
* **no** public signature takes a ``schema_name`` (SC-004) — it is a property
  of the type, not of the caller, and passing it is what six call sites across
  three repositories do today;
* this module reaches them without naming ``cuemsutils.xml``.
"""

from __future__ import annotations

import inspect
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support.public_api import PUBLIC_SCRIPT_METHODS, assert_no_xml_import


@pytest.mark.parametrize("name", PUBLIC_SCRIPT_METHODS)
def test_the_six_methods_exist_and_are_callable(name):
    assert callable(getattr(CuemsScript, name, None)), (
        f"CuemsScript.{name} is missing or not callable"
    )


def test_load_and_from_json_are_classmethods():
    """Both build a script; neither needs one to exist first."""
    for name in ("load", "from_json"):
        member = inspect.getattr_static(CuemsScript, name)
        assert isinstance(member, classmethod), f"{name} is not a classmethod"


@pytest.mark.parametrize("name", PUBLIC_SCRIPT_METHODS)
def test_no_public_method_accepts_a_schema_name(name):
    signature = inspect.signature(getattr(CuemsScript, name))
    assert "schema_name" not in signature.parameters, (
        f"CuemsScript.{name}{signature} still takes a schema name (SC-004)"
    )


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])


def test_every_public_method_documents_what_it_raises():
    """FR-035a: error behaviour that is only discoverable by reading source
    is not specified. ``to_wire``/``to_json`` raise nothing on a violation, and
    say *that* instead — the absence is the contract (FR-005a)."""
    for name in PUBLIC_SCRIPT_METHODS:
        doc = inspect.getdoc(getattr(CuemsScript, name)) or ""
        assert "Raises:" in doc, f"CuemsScript.{name} has no Raises: entry"
