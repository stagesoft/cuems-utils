# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Feature 014 — the public configuration ingestion (T019, T020, T021).

``ConfigManager.from_json(SchemaName, payload)`` — one public JSON → object
call per configuration domain, symmetric with ``CuemsScript.from_json``. It
closes ``cuems-editor``'s UR-5, whose own T059 is ``xfail(strict=True)``
against this call's absence.

**Why these three tests and not one.** plan.md §9.2's argument is that the
descriptor and the ingestion are two halves of *one* round trip and must agree
on the type of every field — so the loop is asserted (T019), the types at the
far end of it are asserted per schema (T020), and the one assertion that only
makes sense because X1 lands in the same feature is asserted separately (T021).
Written against either change alone, T021 would be wrong.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from cuemsutils.config.mappings import CuemsProjectMappingsType
from cuemsutils.config.network_map import CuemsNetworkMapType
from cuemsutils.config.settings import CuemsProjectSettingsType, CuemsSettingsType
from cuemsutils.errors import IngestError, SchemaError
from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName
from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.mapper import root_spec
from cuemsutils.xml.versioning import CURRENT_VERSION
from cuemsutils.xml.settings import NetworkMap, ProjectMappings, ProjectSettings, Settings

REPO_ROOT_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

#: Mirrors ``test_config_manager_save_accessors.py``'s fixture document —
#: ``tests/data/`` ships no project ``settings.xml``, and the domain needs one.
_PROJECT_SETTINGS_XML = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    '<cms:CuemsProjectSettings xmlns:cms="https://stagelab.coop/cuems/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="https://stagelab.coop/cuems/ project_settings.xsd">'
    "<setting><name>example</name><value>1</value></setting>"
    "</cms:CuemsProjectSettings>"
)

#: ``(SchemaName, reader class, root model class, source document)`` per
#: configuration domain. The source is read, projected, fed back through
#: ``from_json`` and persisted — so the payload is a real document's wire form
#: rather than a hand-written approximation of one.
DOMAINS = {
    "settings": (SchemaName.SETTINGS, Settings, CuemsSettingsType, "settings.xml"),
    "network_map": (
        SchemaName.NETWORK_MAP,
        NetworkMap,
        CuemsNetworkMapType,
        "network_map.xml",
    ),
    "project_mappings": (
        SchemaName.PROJECT_MAPPINGS,
        ProjectMappings,
        CuemsProjectMappingsType,
        "project_mappings.xml",
    ),
    "project_settings": (
        SchemaName.PROJECT_SETTINGS,
        ProjectSettings,
        CuemsProjectSettingsType,
        None,
    ),
}


@pytest.fixture
def conf_dir(tmp_path, monkeypatch):
    """A scratch copy of ``tests/data``, pointed at by ``CUEMS_CONF_PATH``."""
    target = tmp_path / "conf"
    shutil.copytree(REPO_ROOT_DATA, target, ignore=shutil.ignore_patterns("corpus"))
    (target / "project_settings.xml").write_text(_PROJECT_SETTINGS_XML, encoding="utf-8")
    monkeypatch.setenv("CUEMS_CONF_PATH", str(target))
    return target


@pytest.fixture
def manager(conf_dir):
    """``load_all=False`` — the shape ``cuems-editor``'s ``config_save``
    constructs (``ConfigManager(load_all=False)``), so the ingestion is
    exercised on a manager that has not loaded a network map."""
    return ConfigManager(load_all=False)


def _source(conf_dir, domain):
    _, reader, _, filename = DOMAINS[domain]
    if filename is None:
        return reader(str(conf_dir / "project_settings.xml"))
    return reader(str(conf_dir / filename))


def _payload(conf_dir, domain):
    """One domain's document as the **wire** form of its root object.

    This is what a client holds: ``schemaLocation`` and ``doc_version`` are
    both absent from a projection, which is exactly the shape §9.3 says the
    ingestion must not require.
    """
    return _source(conf_dir, domain).xml_dict.to_wire()


def _type_map(value, path=()):
    """Every scalar's ``(path, type name)``, for comparing two decodes.

    The instrument T020's second half needs: *"the other three schemas'
    scalars are still ``str``"* is only checkable against what ``load_*``
    itself produces, because some of those scalars were never ``str`` —
    ``xmlschema`` decodes ``xs:int`` to ``int`` with no adapter involved, and
    feature 012's per-**field** opt-in makes ``settings``' own ``node/uuid`` a
    ``Uuid``. So the assertion is *identical types*, not *all strings*.
    """
    out = {}
    if isinstance(value, dict):
        for key, child in value.items():
            out.update(_type_map(child, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            out.update(_type_map(child, (*path, index)))
    else:
        out[path] = type(value).__name__
    return out


# --- T019: the loop §9.2 describes -------------------------------------------


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_descriptor_instance_names_exactly_the_fields_the_ingestion_accepts(domain):
    """The descriptor's root ``instance`` is the ingestion's accepted shape.

    The first half of §9.2's loop, and the half that cannot be asserted by a
    round trip: the client does not invent a document, it fills the one the
    descriptor handed it. If the two disagreed on a key the loop would close
    only for documents that never came from the descriptor.
    """
    schema = DOMAINS[domain][0]
    spec = root_spec(schema.value)
    roots = [t for t in SchemaDescriptor().types(schema.value) if t.key == spec.key]

    assert len(roots) == 1, f"{domain} has no single descriptor for its root type"
    assert set(roots[0].instance) == {f.name for f in spec.fields}


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_from_json_round_trips_a_document_through_save_and_load(manager, conf_dir, domain):
    """``from_json`` → persist → read back equals what went in.

    Persisted through the **root object's own** ``save(path)`` rather than
    through ``manager.save_<domain>()``: ``save_*`` writes what the manager
    *holds*, and two of the four domains keep that on a private attribute
    (``_settings_document``, ``_project_settings_document``). The object
    ``from_json`` returns is the same one ``save_*`` would have written, which
    is UR-5's own wording, and ``.save(path)`` is the public surface it already
    carries. Recorded in the migration guide so a consumer does not go looking
    for an installer.
    """
    schema, reader, root_class, _ = DOMAINS[domain]
    payload = _payload(conf_dir, domain)

    obj = manager.from_json(schema, payload)

    assert type(obj) is root_class

    target = conf_dir / f"{domain}-round-trip.xml"
    obj.save(str(target))

    assert reader(str(target)).xml_dict.to_wire() == payload


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_from_json_accepts_all_three_payload_forms(manager, conf_dir, domain):
    """A JSON ``str``, UTF-8 ``bytes`` and an already-decoded ``Mapping``.

    ``CuemsScript.from_json``'s contract (contracts §C0), carried across
    verbatim — the three are asserted to produce **equal objects**, not merely
    to be accepted.
    """
    schema = DOMAINS[domain][0]
    payload = _payload(conf_dir, domain)
    text = json.dumps(payload, default=str)

    from_mapping = manager.from_json(schema, payload)
    from_text = manager.from_json(schema, text)
    from_bytes = manager.from_json(schema, text.encode("utf-8"))

    assert from_text == from_mapping
    assert from_bytes == from_mapping


def test_from_json_reaches_load_network_map(manager, conf_dir):
    """The one domain whose ``load_*`` answers with the root object itself.

    ``load_network_map`` assigns ``netmap.get_dict()`` — which for
    ``network_map`` (``main_key`` is ``''``) is the root — so this closes
    T019's loop through the accessor the task names, not only through a
    re-read.
    """
    payload = _payload(conf_dir, "network_map")

    manager.from_json(SchemaName.NETWORK_MAP, payload).save(
        str(conf_dir / "network_map.xml")
    )
    manager.load_network_map()

    assert manager.network_map.to_wire() == payload


def test_from_json_reaches_load_base_settings(manager, conf_dir):
    """The same, for ``settings`` — compared one level down.

    ``Settings.main_key`` is ``'Settings'``, so ``ConfigBase.settings`` is the
    root's ``Settings`` **field**, not the root. That asymmetry is pre-existing
    and is why ``ConfigManager.to_wire('settings')`` projects one level deeper
    than the document the ingestion takes.
    """
    payload = _payload(conf_dir, "settings")

    manager.from_json(SchemaName.SETTINGS, payload).save(str(conf_dir / "settings.xml"))
    manager.load_base_settings(str(conf_dir))

    assert manager.settings.to_wire() == payload["Settings"]


# --- T020: the types at the far end, per schema -------------------------------


def test_network_map_ingestion_produces_typed_values(manager, conf_dir):
    """``adopted`` a ``bool``, ``node_role`` a ``NodeRole``, ``uuid`` a ``Uuid``.

    ``network_map`` is the one configuration schema that runs the adapter table
    (feature 007, research R1), and plan.md §9.1's table is the argument for
    doing UR-5 *with* X1: it is also the only configuration schema carrying a
    boolean, and the only one 014 retypes.
    """
    payload = _payload(conf_dir, "network_map")

    obj = manager.from_json(SchemaName.NETWORK_MAP, payload)
    node = obj["node_list"][0]["node"]

    assert type(node["adopted"]) is bool
    assert type(node["online"]) is bool
    assert isinstance(node["node_role"], NodeRole)
    assert isinstance(node["uuid"], Uuid)


@pytest.mark.parametrize("domain", ["settings", "project_mappings", "project_settings"])
def test_other_schemas_keep_the_types_their_load_path_produces(manager, conf_dir, domain):
    """The half that catches an ingestion that "helpfully" coerces everywhere.

    Feature 007 measured and pinned the guarantee that ``settings``,
    ``project_mappings`` and ``project_settings`` decode every scalar untouched
    (SC-010a), and normalising the per-schema asymmetry here would retire it
    silently. So the ingestion's types are compared against the **load path's
    own**, scalar by scalar, rather than against an assumption about which
    ones are strings.
    """
    schema = DOMAINS[domain][0]
    payload = _payload(conf_dir, domain)

    loaded = _source(conf_dir, domain).xml_dict
    ingested = manager.from_json(schema, payload)

    loaded_types = _type_map(dict(loaded))
    # ``schemaLocation`` is in the document and never in a projection, so it
    # cannot be in the ingested object. Everything else must match.
    loaded_types.pop(("schemaLocation",), None)
    loaded_types.pop(("doc_version",), None)

    assert _type_map(dict(ingested)) == loaded_types
    assert "bool" not in set(_type_map(dict(ingested)).values())


# --- T021: the assertion that only exists because both changes land together ---


def test_network_map_ingestion_takes_the_json_boolean(manager, conf_dir):
    """``"adopted": true`` — X1's form, and the only one a client now sends."""
    payload = _payload(conf_dir, "network_map")
    payload["node_list"][0]["node"]["adopted"] = True
    payload["node_list"][0]["node"]["online"] = False

    obj = manager.from_json(SchemaName.NETWORK_MAP, payload)
    node = obj["node_list"][0]["node"]

    assert node["adopted"] is True
    assert node["online"] is False


def test_network_map_ingestion_refuses_the_retired_string_boolean(manager, conf_dir):
    """``"adopted": "True"`` is **refused**, by ``_Bool.decode``'s table.

    Written against X1 alone this assertion would be about a document; written
    against UR-5 alone it would have had to *accept* the string, because that
    is what the pre-014 descriptor told a client to send (plan.md §9.2). It is
    correct only because the two land together.
    """
    payload = _payload(conf_dir, "network_map")
    payload["node_list"][0]["node"]["adopted"] = "True"

    with pytest.raises(SchemaError) as excinfo:
        manager.from_json(SchemaName.NETWORK_MAP, payload)

    assert "True" in str(excinfo.value)


# --- the refusals §9.3 says stay refusals -------------------------------------


@pytest.mark.parametrize(
    "schema, expected",
    [
        (SchemaName.SCRIPT, "CuemsScript.from_json"),
        (SchemaName.HARDWARE_OUTPUTS, "hardware_outputs"),
    ],
)
def test_from_json_refuses_the_two_non_configuration_schemas(manager, conf_dir, schema, expected):
    """``script`` is ``CuemsScript.from_json``'s; ``hardware_outputs`` has no
    model bindings until feature 015. The editor already refuses both with
    those reasons and this call does not widen them."""
    with pytest.raises(ValueError) as excinfo:
        manager.from_json(schema, {})

    assert expected in str(excinfo.value)


def test_from_json_takes_a_schema_name_not_a_string(manager, conf_dir):
    """``get_schema_descriptor``'s posture (FR-028a), carried across: accepting
    both would reintroduce the stringly-typed surface the enum removes."""
    with pytest.raises(TypeError) as excinfo:
        manager.from_json("settings", {})

    assert "SchemaName" in str(excinfo.value)


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff\xfe not utf-8",
        "{not json",
        [1, 2, 3],
        42,
        {"nothing_the_root_declares": 1},
    ],
)
def test_from_json_refuses_what_is_not_a_document(manager, conf_dir, payload):
    """Every refusal here is *"this is not a ``settings`` document"* — nothing
    was validated because there was nothing of the right shape to validate,
    which is why they are ``IngestError`` rather than ``SchemaError``
    (``CuemsScript._ingest``'s distinction, unchanged)."""
    with pytest.raises(IngestError):
        manager.from_json(SchemaName.SETTINGS, payload)


def test_from_json_ingests_this_librarys_own_settings_projection(conf_dir):
    """``ConfigManager.to_wire('settings')`` is accepted (T023).

    This is the payload ``cuems-editor``'s T059 actually sends — its test does
    ``manager.to_wire('settings')`` and hands the result to ``config_save`` —
    and it is **one level deeper** than the ``settings`` document, because
    ``Settings.main_key`` is ``'Settings'`` and ``ConfigBase.settings`` is the
    root's field rather than the root.

    Pinned here as its own test rather than folded into the round trip,
    because it is the only reason the tolerance in ``from_json`` exists and a
    future reader deleting the tolerance should be told by a named failure.
    """
    manager = ConfigManager()
    section = manager.to_wire("settings")

    assert "Settings" not in section, "to_wire('settings') projects the field, not the root"

    obj = manager.from_json(SchemaName.SETTINGS, section)

    assert type(obj) is CuemsSettingsType
    assert obj["Settings"].to_wire() == section


def test_from_json_does_not_require_doc_version(manager, conf_dir):
    """``doc_version`` is excluded from every wire projection, so no client
    payload carries it — and the writer emits the **current** version anyway.

    Asserted against ``CURRENT_VERSION`` rather than a literal: ``settings`` is
    at 3 (feature 012 stepped it), ``network_map`` and ``project_mappings`` at
    2, ``project_settings`` at 1, and a literal here would be a second place
    those have to be kept in step.
    """
    payload = _payload(conf_dir, "settings")

    assert "doc_version" not in payload

    target = conf_dir / "settings-written.xml"
    manager.from_json(SchemaName.SETTINGS, payload).save(str(target))

    assert Settings(str(target)).document_version == CURRENT_VERSION["settings"]
