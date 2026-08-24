"""Contract C5 — the write path validates first, does not mutate, and is atomic."""

from __future__ import annotations

import threading
import time
import warnings

import pytest

from cuemsutils.config.network_map import CuemsNetworkMapType, node
from cuemsutils.errors import SchemaError
from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.xml.mapper import Mapper, read_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.corpus import REPO_ROOT


def _decoded(path: str = "tests/data/network_map.xml"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        netmap = NetworkMap(str(REPO_ROOT / path))
    raw = read_config_document(netmap.schema_object, str(REPO_ROOT / path))
    return Mapper("network_map").decode_config(raw)


# -- validate before write ----------------------------------------------------


def test_role_value_outside_the_enumeration_raises_before_any_byte_is_written(tmp_path):
    obj = _decoded()
    obj["node_list"][0]["node"]["node_role"] = "not-a-real-role"
    target = tmp_path / "out.xml"
    assert not target.exists()

    with pytest.raises(SchemaError):
        obj.save(str(target))

    assert not target.exists()


def test_write_to_an_invalid_target_leaves_an_existing_file_untouched(tmp_path):
    target = tmp_path / "out.xml"
    target.write_text("PRE-EXISTING CONTENT")

    obj = _decoded()
    obj["node_list"][0]["node"]["node_role"] = "not-a-real-role"
    with pytest.raises(SchemaError):
        obj.save(str(target))

    assert target.read_text() == "PRE-EXISTING CONTENT"


# -- non-mutation (T037, FR-015) ----------------------------------------------


def test_save_does_not_mutate_the_object_it_is_given(tmp_path):
    obj = _decoded()
    first_node = obj["node_list"][0]["node"]
    assert isinstance(first_node["node_role"], NodeRole)

    obj.save(str(tmp_path / "out.xml"))

    assert isinstance(first_node["node_role"], NodeRole)
    assert first_node["node_role"] is NodeRole.controller
    assert isinstance(first_node["adopted"], bool)


def test_save_does_not_mutate_even_on_a_second_call(tmp_path):
    """cuems-nodeconf's write path needed a separate serialization copy
    because its old builder mutated the object on write; this asserts the
    workaround has nothing left to work around, across repeated calls too."""
    obj = _decoded()
    obj.save(str(tmp_path / "one.xml"))
    obj.save(str(tmp_path / "two.xml"))
    assert obj["node_list"][0]["node"]["node_role"] is NodeRole.controller


# -- atomicity (T038) ----------------------------------------------------------


def test_write_is_atomic_a_concurrent_reader_never_sees_a_truncated_file(tmp_path):
    """``write_tree`` (documents.py) writes a temp file in the same directory
    and ``os.replace``s it into place — this asserts the property that
    machinery gives, for network_map specifically, using a large enough
    payload and enough iterations to make a torn read plausible if the
    machinery ever regressed to a non-atomic write."""
    target = tmp_path / "out.xml"
    obj = _decoded()
    # Inflate the payload so a naive truncate-then-write would have a
    # window to be caught mid-write.
    base_node = dict(obj["node_list"][0]["node"])
    padded = node(**{**base_node, "alias": "x" * 200_000})
    obj["node_list"] = [{"node": padded}] + list(obj["node_list"][1:])
    obj.save(str(target))  # first write, so the file exists for readers

    errors: list[Exception] = []
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            try:
                text = target.read_text()
            except FileNotFoundError:
                continue
            if not (text.startswith("<?xml") and text.rstrip().endswith("</cms:CuemsNetworkMap>")):
                errors.append(AssertionError(f"torn read: {text[:80]!r}...{text[-80:]!r}"))
                return

    def writer():
        for _ in range(10):
            obj.save(str(target))

    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    writer_thread = threading.Thread(target=writer)
    writer_thread.start()
    writer_thread.join()
    stop.set()
    reader_thread.join(timeout=2)

    assert not errors, errors
