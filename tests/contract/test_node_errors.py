"""Contract C8 — errors name the migration (T041, T041a).

Two failure modes, both raised as ``SchemaError`` from the configuration
accessor (``ConfigBase.load_config_document``, contract C2's posture), each
carrying document, node, offending value, accepted values and a remedy —
distinguishing "this is the old vocabulary, here's the replacement" from
"this value is simply wrong" (FR-011c, FR-011h-i, FR-UX-001).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cuemsutils.errors import SchemaError
from cuemsutils.tools.ConfigBase import load_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.corpus import REPO_ROOT

VALID_NETWORK_MAP = REPO_ROOT / "tests" / "data" / "network_map.xml"


def _write(doc: str) -> str:
    path = Path(tempfile.mkdtemp()) / "network_map.xml"
    path.write_text(doc)
    return str(path)


def _doc(node_role_or_type_element: str) -> str:
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="https://stagelab.coop/cuems/ network_map.xsd">'
        "<node_list><node>"
        "<uuid>0367f391-ebf4-48b2-9f26-000000000042</uuid>"
        "<mac>aabbccddeeff</mac><name>n</name>"
        f"{node_role_or_type_element}"
        "<ip>192.168.1.5</ip>"
        "</node></node_list></cms:CuemsNetworkMap>"
    )


# -- <node_type> still present (the migration) --------------------------------


def test_legacy_node_type_document_names_the_migration():
    path = _write(_doc("<node_type>NodeType.master</node_type>"))
    with pytest.raises(SchemaError) as caught:
        load_config_document(NetworkMap, path, "network_map")

    message = str(caught.value)
    assert "node_type" in message
    assert "node_role" in message
    assert "0367f391-ebf4-48b2-9f26-000000000042" in message  # the node
    assert path in message  # the document
    assert "controller" in message and "node" in message and "firstrun" in message  # accepted
    assert "conversion" in message.lower() or "convert" in message.lower()  # the remedy


def test_recognisable_legacy_value_gets_a_deprecation_notice_naming_its_replacement():
    """T041a — 'old' distinguished from 'meaningless': a recognisable legacy
    spelling additionally says what it becomes."""
    path = _write(_doc("<node_type>NodeType.master</node_type>"))
    with pytest.raises(SchemaError) as caught:
        load_config_document(NetworkMap, path, "network_map")
    assert "controller" in str(caught.value)  # what NodeType.master becomes

    path2 = _write(_doc("<node_type>slave</node_type>"))
    with pytest.raises(SchemaError) as caught2:
        load_config_document(NetworkMap, path2, "network_map")
    assert "'node'" in str(caught2.value) or '"node"' in str(caught2.value)


# -- <node_role> out of the enumeration (meaningless, not old) ----------------


def test_out_of_vocabulary_role_names_the_field_and_accepted_values():
    path = _write(_doc("<node_role>gibberish</node_role>"))
    with pytest.raises(SchemaError) as caught:
        load_config_document(NetworkMap, path, "network_map")

    message = str(caught.value)
    assert "node_role" in message
    assert "gibberish" in message
    assert "controller" in message and "node" in message and "firstrun" in message


def test_out_of_vocabulary_role_is_distinguishable_from_the_legacy_migration_case():
    """'old' (a recognised legacy spelling) is a different message from
    'meaningless' (never a valid value in any vocabulary)."""
    legacy_path = _write(_doc("<node_type>NodeType.master</node_type>"))
    with pytest.raises(SchemaError) as legacy_caught:
        load_config_document(NetworkMap, legacy_path, "network_map")

    gibberish_path = _write(_doc("<node_role>gibberish</node_role>"))
    with pytest.raises(SchemaError) as gibberish_caught:
        load_config_document(NetworkMap, gibberish_path, "network_map")

    assert str(legacy_caught.value) != str(gibberish_caught.value)
    # The legacy case names a replacement; the gibberish case cannot.
    assert "retired spelling" in str(legacy_caught.value)
    assert "retired spelling" not in str(gibberish_caught.value)


def test_a_valid_document_still_loads():
    """The control: a well-formed, in-vocabulary document is not caught by
    either diagnostic."""
    loaded = load_config_document(NetworkMap, str(VALID_NETWORK_MAP), "network_map")
    assert loaded.get_dict()["node_list"]
