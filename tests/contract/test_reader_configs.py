"""Both reader configurations, differences included (T052) — FR-013.

The library reads XML two ways, and they do not agree:

============  ==========================  ===============================
              ``XmlReaderWriter.read``    the config classes' ``read``
============  ==========================  ===============================
namespaces    ``strip_namespaces=False``  ``strip_namespaces=True``
containers    converter defaults          explicit ``dict`` / ``list``
attributes    converter default           ``attr_prefix=''``
============  ==========================  ===============================

FR-013 requires **both** to be preserved — including the places they differ
from each other. That second clause is the one worth testing: a refactor that
unified them would look like a simplification, produce one consistent output,
and change what every consumer of the other configuration receives.

Feature 006 may unify them. It would be a wire change, so it is not this
feature's to make.
"""

from __future__ import annotations

import json
import warnings

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

BOTH_CONFIGS = [
    d
    for d in DOCUMENTS
    if (GOLDEN_ROOT / "dict" / f"{d.slug}.reader.json").exists()
    and (GOLDEN_ROOT / "dict" / f"{d.slug}.config.json").exists()
]
IDS = [d.relpath for d in BOTH_CONFIGS]

SCHEMA_LOCATION_KEY = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"


def _reader(doc):
    return json.loads(rt.golden_json(f"dict/{doc.slug}.reader.json"))


def _config(doc):
    return json.loads(rt.golden_json(f"dict/{doc.slug}.config.json"))


@pytest.mark.parametrize("doc", BOTH_CONFIGS, ids=IDS)
def test_configuration_a_is_byte_identical(doc):
    assert rt.json_dumps(rt.read_dict(doc)) == rt.golden_json(
        f"dict/{doc.slug}.reader.json"
    )


@pytest.mark.parametrize("doc", BOTH_CONFIGS, ids=IDS)
def test_configuration_b_is_byte_identical(doc):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        produced = rt.json_dumps(rt.read_config_dict(doc))
    assert produced == rt.golden_json(f"dict/{doc.slug}.config.json")


@pytest.mark.parametrize("doc", BOTH_CONFIGS, ids=IDS)
def test_the_two_configurations_still_differ(doc):
    """The clause that makes FR-013 more than "keep it working".

    If these ever became equal, one configuration would have silently adopted
    the other's behaviour — and every consumer of the changed one would be
    receiving something new. Asserting the *difference* is what catches a
    well-intentioned unification.
    """
    assert rt.json_dumps(_reader(doc)) != rt.json_dumps(_config(doc))


@pytest.mark.parametrize("doc", BOTH_CONFIGS, ids=IDS)
def test_only_configuration_a_carries_the_namespaced_schema_location(doc):
    """Where the difference actually lives, named.

    With ``strip_namespaces=False`` the leaked attribute keeps its full
    ``{…XMLSchema-instance}`` qname; with stripping on it becomes a bare
    ``schemaLocation``. Same leak (F23), two spellings, and consumers of each
    configuration have been reading one of them for years.
    """
    assert SCHEMA_LOCATION_KEY in _reader(doc)
    assert SCHEMA_LOCATION_KEY not in _config(doc)
    assert "schemaLocation" in _config(doc)


@pytest.mark.parametrize("doc", BOTH_CONFIGS, ids=IDS)
def test_content_agrees_where_namespaces_are_not_involved(doc):
    """The difference is confined to namespace handling, and nothing else.

    Without this, "they differ" would be satisfied by any divergence at all,
    including a real content bug.
    """
    reader = {k: v for k, v in _reader(doc).items() if not k.startswith("{")}
    config = {k: v for k, v in _config(doc).items() if k != "schemaLocation"}
    assert reader == config


@pytest.mark.parametrize("doc", BOTH_CONFIGS, ids=IDS)
def test_configuration_b_uses_plain_containers(doc):
    """``dict_class=dict``, ``list_class=list`` — asserted structurally.

    The config classes pass plain builtins explicitly. A converter returning
    its own mapping subclass would still compare equal and would still
    serialize the same, and would break ``isinstance(x, dict)`` checks in
    consumer code.
    """

    def check(node):
        if isinstance(node, dict):
            assert type(node) is dict
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            assert type(node) is list
            for item in node:
                check(item)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        check(rt.read_config_dict(doc))


def test_both_configurations_are_exercised_by_the_corpus():
    """Neither configuration may lose its last covered document."""
    assert BOTH_CONFIGS
    assert {d.schema for d in BOTH_CONFIGS} >= {
        "settings",
        "network_map",
        "project_mappings",
        "project_settings",
    }
