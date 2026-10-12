# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Feature 014 — ``xs:boolean`` end to end (T010, T018).

A unit test on the adapter cannot catch a ``Mapper`` path that bypasses
``_lexical``, and ``:868``'s attribute call is the one most easily missed since
013 made attributes load-bearing. So these assert the **bytes on disk** and the
**descriptor**, which are the two places a half-applied change would hide.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cuemsutils.cues import CuemsScript
from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName

FIXTURE = "tests/data/media_block/media_block_showcase.xml"

#: Every ``cms:BoolType`` element, now ``xs:boolean``.
SCRIPT_BOOLEANS = ("autoload", "enabled", "timecode")
MAP_BOOLEANS = ("adopted", "online")


@pytest.fixture
def saved_script(tmp_path):
    """The fixture loaded and written back through the public path."""
    script, _ = CuemsScript.load_with_report(FIXTURE)
    out = tmp_path / "out.xml"
    script.save(str(out))
    return out


# --- T010: the bytes on disk ------------------------------------------------


def test_the_written_document_carries_the_lowercase_form(saved_script):
    text = saved_script.read_text(encoding="utf-8")
    assert "<enabled>true</enabled>" in text
    assert "<autoload>false</autoload>" in text


def test_no_capitalised_boolean_survives_anywhere_in_the_bytes(saved_script):
    """The whole-document assertion, not one element.

    ``to_lexical`` has five call sites in ``Mapper`` and this is the only check
    that covers all of them at once — including ``element.set``, which writes
    every attribute.
    """
    text = saved_script.read_text(encoding="utf-8")
    for name in SCRIPT_BOOLEANS:
        assert f"<{name}>True<" not in text, name
        assert f"<{name}>False<" not in text, name


def test_the_written_document_revalidates_and_reloads(saved_script):
    """Round trip: the form we write is the form we accept."""
    reloaded, report = CuemsScript.load_with_report(str(saved_script))
    assert report.outcome.name == "CLEAN"
    cue = reloaded["CueList"].contents[0]
    assert cue["enabled"] is True
    assert cue["autoload"] is False


def test_the_object_holds_real_booleans_after_a_reload(saved_script):
    reloaded, _ = CuemsScript.load_with_report(str(saved_script))
    for name in SCRIPT_BOOLEANS:
        value = reloaded["CueList"][name]
        assert isinstance(value, bool), f"{name} decoded to {type(value).__name__}"


# --- the wire: the whole point of X1 ---------------------------------------


def test_the_wire_carries_json_booleans_not_strings():
    """The contract change ``cuems-frontend`` is coupled to.

    This replaces ``test_wire_booleans.py``'s premise: that file asserted the
    strings, and its docstring called decoding them to JSON booleans "the
    single most natural improvement available in this code", deferred as X1.
    This is X1.
    """
    script, _ = CuemsScript.load_with_report(FIXTURE)
    payload = json.dumps(script.to_wire())
    assert '"enabled": true' in payload or '"enabled":true' in payload
    assert '"enabled": "True"' not in payload
    assert '"autoload": "False"' not in payload


def test_a_wire_boolean_is_a_bool_not_a_truthy_string():
    """``"False"`` is truthy, which is why this asserts the type.

    A consumer doing ``if cue["enabled"]`` against the old string form got
    ``True`` for a *disabled* cue. That hazard is what the retype removes.
    """
    script, _ = CuemsScript.load_with_report(FIXTURE)
    cue = script.to_wire()["CuemsScript"]["CueList"]["contents"][0]["Cue"]
    assert cue["enabled"] is True
    assert cue["autoload"] is False


# --- T018: the descriptor stops reporting a boolean as an enum -------------


def _fields(schema: SchemaName, type_name: str):
    for t in ConfigManager(load_all=False).get_schema_descriptor(schema):
        if t.key.name == type_name:
            return {f.name: f for f in t.fields}
    raise AssertionError(f"{type_name} not in {schema.value}'s descriptor")


@pytest.mark.parametrize("name", SCRIPT_BOOLEANS)
def test_the_descriptor_reports_a_script_boolean_as_a_boolean(name, monkeypatch):
    """T018 — the acceptance criterion for the finding that decided X1.

    Before this feature ``enabled`` came back as
    ``enum_values=('True', 'False')``, structurally identical to ``post_go``'s
    three values, so a descriptor-driven form rendered a two-option **dropdown
    where a checkbox belongs** — and 010's T031a would have verified that as
    correct.
    """
    monkeypatch.setenv("CUEMS_CONF_PATH", "tests/data/corpus/cuems-utils")
    field = _fields(SchemaName.SCRIPT, "CommonPropertiesType")[name]
    assert field.enum_values is None, f"{name} still looks like an enumeration"
    assert "bool" in field.xsd_type.lower(), field.xsd_type


@pytest.mark.parametrize("name", MAP_BOOLEANS)
def test_the_descriptor_reports_a_map_boolean_as_a_boolean(name, monkeypatch):
    monkeypatch.setenv("CUEMS_CONF_PATH", "tests/data/corpus/cuems-utils")
    field = _fields(SchemaName.NETWORK_MAP, "NodeType")[name]
    assert field.enum_values is None, f"{name} still looks like an enumeration"
    assert "bool" in field.xsd_type.lower(), field.xsd_type


def test_no_schema_declares_a_bespoke_bool_type_any_more():
    """Three ``simpleType`` declarations deleted, replaced by the built-in."""
    from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema

    carriers = [n for n in SCHEMA_NAMES if "BoolType" in get_schema(n).types]
    assert carriers == [], f"BoolType still declared in {carriers}"
