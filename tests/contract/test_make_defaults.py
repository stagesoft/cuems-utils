# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T026 — the three default documents, generated at build (feature 011, D2/D3;
research R2, R12). Determinism, the sentinel, schema validity with nothing to
repair, the current version marker, and the two-way completeness guarantee."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cuemsutils.xml import make_defaults, seed_values
from cuemsutils.xml.seed_values import SeedValueError
from cuemsutils.xml.versioning import CURRENT_VERSION, read_version

SENTINEL = "00000000-0000-0000-0000-000000000000"
DOCUMENTS = {"settings.xml": "settings", "network_map.xml": "network_map", "default_mappings.xml": "project_mappings"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("defaults")
    make_defaults.generate(out)
    return out


def test_two_generations_are_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    make_defaults.generate(a)
    make_defaults.generate(b)
    for name in DOCUMENTS:
        assert _sha(a / name) == _sha(b / name), name


def test_every_document_carries_the_sentinel_and_no_other_uuid(generated):
    import re

    for name in DOCUMENTS:
        text = (generated / name).read_text(encoding="utf-8")
        assert SENTINEL in text, name
        others = set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)) - {SENTINEL}
        assert not others, f"{name} carries a non-sentinel uuid: {others}"
        assert "000000000000" in text, f"{name} lacks the sentinel MAC"


def test_every_document_validates_with_nothing_to_repair(generated):
    from cuemsutils.xml.settings import NetworkMap, ProjectMappings, Settings
    from cuemsutils.xml.validators import repair

    readers = {"settings.xml": Settings, "network_map.xml": NetworkMap, "default_mappings.xml": ProjectMappings}
    for name, reader in readers.items():
        document = reader(str(generated / name)).get_dict()  # T1 (and T2 where registered)
        assert repair(document) == [], f"{name} needed repair"


def test_every_document_carries_the_current_version(generated):
    for name, schema in DOCUMENTS.items():
        tree = ET.parse(generated / name)
        assert read_version(tree) == CURRENT_VERSION[schema], name


def test_the_network_map_has_exactly_one_firstrun_row(generated):
    root = ET.parse(generated / "network_map.xml").getroot()
    rows = root.findall(".//node")
    assert len(rows) == 1
    row = rows[0]
    assert row.findtext("uuid") == SENTINEL
    assert row.findtext("mac") == "000000000000"
    assert row.findtext("name") == "unprovisioned"
    assert row.findtext("ip") == "0.0.0.0"
    assert row.findtext("node_role") == "firstrun"


def test_the_default_mappings_claim_no_hardware(generated):
    root = ET.parse(generated / "default_mappings.xml").getroot()
    assert root.findtext("number_of_nodes") == "1"
    defaults = root.find("defaults")
    assert defaults is not None and list(defaults) == []
    nodes = root.findall("./nodes/node")
    assert len(nodes) == 1 and nodes[0].findtext("uuid") == SENTINEL
    assert nodes[0].find("devices") is None
    assert root.find("new_nodes") is not None and len(root.find("new_nodes")) == 0


def test_a_fresh_triple_loads_through_config_manager(generated):
    """A8 — the sentinel triple is coherent, so the degraded fallback loads."""
    from cuemsutils.tools.ConfigManager import ConfigManager

    manager = ConfigManager(config_dir=str(generated), load_all=True)
    assert manager.node_conf["uuid"] == SENTINEL


def test_completeness_holds_in_both_directions(tmp_path):
    """FR-010: a missing required entry and a stale key each fail naming themselves."""
    tables = seed_values.load_seed_values()
    del tables["network_map"]["NodeType"]["ip"]
    with pytest.raises(SeedValueError, match=r"NodeType\.ip"):
        make_defaults.generate(tmp_path / "missing", tables=tables)
    tables = seed_values.load_seed_values()
    tables["project_mappings"]["CuemsProjectMappingsType"]["gone_field"] = 1
    with pytest.raises(SeedValueError, match=r"gone_field"):
        make_defaults.generate(tmp_path / "stale", tables=tables)


def test_the_module_refuses_a_non_deterministic_generation(tmp_path, monkeypatch):
    """The build-time guard: two generations that differ abort the install."""
    calls = {"n": 0}
    real = make_defaults._build_documents

    def flaky(tables, identity=None):
        calls["n"] += 1
        docs = real(tables, identity)
        if calls["n"] == 2:
            docs["network_map.xml"]["node_list"][0]["node"]["ip"] = "1.2.3.4"
        return docs

    monkeypatch.setattr(make_defaults, "_build_documents", flaky)
    with pytest.raises(RuntimeError, match=r"not deterministic"):
        make_defaults.main(["--out", str(tmp_path / "out")])
