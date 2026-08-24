"""Accessor parity for the configuration classes (T051).

``Settings``, ``NetworkMap``, ``ProjectMappings`` and ``ProjectSettings`` are
the four public classes that read configuration documents. Routing them through
the engine (T053) must not change a single value any of them returns.

Their public surface is asserted here rather than only through the dict
goldens, because a consumer calls ``get_node`` or ``get_dict`` — not
``xml_dict`` — and a refactor that kept the dict intact while breaking an
accessor would pass C2 and still break `cuems-engine` at startup.
"""

from __future__ import annotations

import json
import warnings

import pytest

from cuemsutils.xml import NetworkMap, ProjectMappings, ProjectSettings, Settings
from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT, documents

CONFIG_CLASSES = {
    "Settings": Settings,
    "NetworkMap": NetworkMap,
    "ProjectMappings": ProjectMappings,
    "ProjectSettings": ProjectSettings,
}

READABLE_CONFIG = [
    d
    for d in DOCUMENTS
    if d.config_class and (GOLDEN_ROOT / "dict" / f"{d.slug}.config.json").exists()
]
IDS = [d.relpath for d in READABLE_CONFIG]


def _load(doc):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return CONFIG_CLASSES[doc.config_class](str(doc.path))


def _golden_as_decoded(value):
    """A ``*.config.json`` golden's value, typed as the live decode now types it.

    Identity for every schema except ``network_map`` (feature 007, research
    R1): its ``node_role`` field decodes to a ``NodeRole`` where the JSON
    golden necessarily records the enum's ``.value`` string. ``bool`` fields
    need no conversion — ``json.loads`` already gives ``True``/``False`` for
    the JSON literal, matching the live decode directly.
    """
    from cuemsutils.tools.NodeList import NodeRole

    if isinstance(value, dict):
        out = {k: _golden_as_decoded(v) for k, v in value.items()}
        if "node_role" in out and isinstance(out["node_role"], str):
            out["node_role"] = NodeRole(out["node_role"])
        return out
    if isinstance(value, list):
        return [_golden_as_decoded(v) for v in value]
    return value


# --- feature 006 addition (T042, FR-016) ----------------------------------
#
# The compensations are gone. This is the assertion that they were
# compensations rather than logic: every accessor returns the **same values**
# after their deletion, against the goldens captured before it.


def _manager():
    from tests.support.config_inventory import build_config_manager

    return build_config_manager()


def test_every_accessor_value_survives_the_deleted_compensations():
    """The three compensations deleted by T050-T052 changed no value.

    Compared against the recorded ``*.config.json`` goldens through the
    accessors, not through ``xml_dict`` — a refactor that kept the dict intact
    while breaking an accessor would pass C2 and still break `cuems-engine` at
    startup, which is the whole reason this file exists.
    """
    manager = _manager()
    settings_golden = json.loads(
        rt.golden_json("dict/cuems-utils__settings.config.json")
    )["Settings"]

    assert rt.as_plain(manager.settings) == settings_golden
    assert rt.as_plain(manager.node_conf) == settings_golden["node"]
    assert manager.library_path == settings_golden["library_path"]
    assert manager.node_uuid == settings_golden["node"]["uuid"]

    network_golden = json.loads(
        rt.golden_json("dict/cuems-utils__network_map.config.json")
    )
    # network_map is the one schema that opts into the adapter table (feature
    # 007, research R1). That divergence from the golden's raw JSON shape is
    # FR-011a working as designed, not a value the T050-T052 compensations
    # could have changed — see _golden_as_decoded.
    assert rt.as_plain(manager.network_map)["node_list"] == _golden_as_decoded(
        network_golden
    )["node_list"]


def test_node_hw_outputs_is_unchanged_by_the_deleted_five_level_walk():
    """Compensation #2's *output*, not its code.

    ``load_net_and_node_mappings`` built ``node_hw_outputs`` by rediscovering
    the nesting at five levels; it now addresses each level by the name the
    schema gives it. The values it produces are what the engine actually
    consumes, so they are what is pinned.
    """
    manager = _manager()
    outputs = manager.node_hw_outputs

    assert set(outputs) == {
        "audio_inputs",
        "audio_outputs",
        "video_inputs",
        "video_outputs",
        "dmx_inputs",
        "dmx_outputs",
    }
    assert outputs["audio_outputs"], "the walk produced no audio outputs at all"
    assert all(isinstance(name, str) for names in outputs.values() for name in names)

    # The measured content of the vendored fixture, so a silently emptied walk
    # cannot pass. ``mapped_to`` wins over ``name``; ``name`` is the fallback.
    assert "system:playback_1" in outputs["audio_outputs"]
    assert "system:capture_1" in outputs["audio_inputs"]


def test_check_project_mappings_accepts_a_correct_project():
    """The rewritten compensation #3 runs, and passes on valid mappings.

    Worth asserting positively: the previous body was guarded by
    ``isinstance(contents, dict)`` over a value that is a *list*, so its inner
    loops never executed and nothing was ever checked. A rewrite that made the
    check wrong would now fail here rather than continuing to pass by never
    running.
    """
    manager = _manager()
    assert manager.check_project_mappings() is True


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_xml_dict_matches_its_golden(doc):
    assert rt.json_dumps(_load(doc).xml_dict) == rt.golden_json(
        f"dict/{doc.slug}.config.json"
    )


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_get_dict_is_stable(doc):
    """``get_dict`` unwraps ``main_key``, which differs per class.

    ``Settings`` uses ``'Settings'``, ``ProjectSettings`` uses
    ``'CuemsProjectSettings'``, and the other two use ``''`` — meaning the
    whole document. Getting that wrong returns an empty dict rather than an
    error, so it is asserted rather than assumed.
    """
    obj = _load(doc)
    result = obj.get_dict()
    assert isinstance(result, dict)
    golden = _golden_as_decoded(json.loads(rt.golden_json(f"dict/{doc.slug}.config.json")))

    # ``rt.as_plain`` from feature 006: the accessor now returns a
    # ``ConfigDict`` (FR-014), and declared-field equality on a model object is
    # deliberately **not** dict equality — it compares by class, so a config
    # object is never equal to a bare mapping. The claim under test is about
    # *contents*, so the classes are stripped before comparing. What the object
    # layer changed is the type; what it must not change is the value, and that
    # is exactly what this now says.
    plain = rt.as_plain(result)
    if obj.main_key == "":
        assert plain == golden
    else:
        assert plain == golden.get(obj.main_key, {}) or plain == {
            obj.main_key: golden.get(obj.main_key)
        }


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_loaded_flag_is_set(doc):
    assert _load(doc).loaded is True


def test_network_map_get_node_returns_the_named_node():
    doc = next(d for d in documents(schema="network_map") if d.category == "cuems-utils")
    network = _load(doc)
    node_list = network.get_dict()["node_list"]
    uuid = node_list[0]["node"]["uuid"]
    assert network.get_node(uuid)["uuid"] == uuid


def test_network_map_get_node_raises_for_an_unknown_uuid():
    """The failure path, pinned with the success path.

    A lookup that silently returned ``None`` for a missing node would let a
    misconfigured cluster start up and fail much later.
    """
    doc = next(d for d in documents(schema="network_map") if d.category == "cuems-utils")
    with pytest.raises(ValueError, match="not found"):
        _load(doc).get_node("00000000-0000-4000-8000-000000000000")


def test_network_map_nodes_by_adoption_splits_and_coerces():
    """``online``/``adopted`` are ``"True"``/``"False"`` strings in the dict.

    ``get_nodes_by_adoption`` converts them with ``strtobool`` and partitions
    on the result — one of the few places a config accessor does more than
    look something up.
    """
    doc = next(d for d in documents(schema="network_map") if d.category == "cuems-utils")
    nodes, new_nodes = NetworkMap.get_nodes_by_adoption(_load(doc).get_dict())
    assert isinstance(nodes, list) and isinstance(new_nodes, list)
    for entry in nodes + new_nodes:
        assert isinstance(entry["node"]["online"], bool)
        assert isinstance(entry["node"]["adopted"], bool)


def test_project_mappings_processed_is_populated():
    doc = next(
        d
        for d in documents(schema="project_mappings")
        if d.relpath == "cuems-utils/project_mappings.xml"
    )
    mappings = _load(doc)
    assert mappings.processed
    assert "nodes" in mappings.processed


def test_project_mappings_get_node_returns_the_named_node():
    doc = next(
        d
        for d in documents(schema="project_mappings")
        if d.relpath == "cuems-utils/project_mappings.xml"
    )
    mappings = _load(doc)
    uuid = mappings.processed["nodes"][0]["node"]["uuid"]
    assert mappings.get_node(uuid)["uuid"] == uuid


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_reading_twice_gives_the_same_result(doc):
    """Idempotence at the accessor level.

    The schema cache is shared across instances, so a cache that leaked state
    between reads would show up here and nowhere else.
    """
    assert rt.json_dumps(_load(doc).xml_dict) == rt.json_dumps(_load(doc).xml_dict)


def test_every_config_class_is_covered():
    """The parametrisation must not quietly shrink to three classes."""
    covered = {d.config_class for d in READABLE_CONFIG}
    assert covered == set(CONFIG_CLASSES)
