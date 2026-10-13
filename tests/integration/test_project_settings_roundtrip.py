"""G2 (US2), T019 — the full ``project_settings`` round trip (contract C2).

``to_wire('project_settings')`` -> ``from_json(SchemaName.PROJECT_SETTINGS, …)``
-> ``save(path)`` -> reload compares **equal**.
"""

from __future__ import annotations

import os
import shutil

import pytest

from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName
from cuemsutils.xml.settings import ProjectSettings

REPO_ROOT_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _point_library_path_at(conf_dir) -> None:
    settings_path = conf_dir / "settings.xml"
    text = settings_path.read_text(encoding="utf-8")
    text = text.replace(
        "<library_path>/opt/cuems_library</library_path>",
        f"<library_path>{conf_dir}</library_path>",
    )
    settings_path.write_text(text, encoding="utf-8")


@pytest.fixture
def config_manager(tmp_path, monkeypatch):
    conf_dir = tmp_path / "conf"
    shutil.copytree(REPO_ROOT_DATA, conf_dir, ignore=shutil.ignore_patterns("corpus"))
    _point_library_path_at(conf_dir)
    monkeypatch.setenv("CUEMS_CONF_PATH", str(conf_dir))
    return ConfigManager()


def test_project_settings_round_trips_through_wire_and_back(config_manager):
    project_dir = os.path.join(config_manager.library_path, "projects", "roundtrip-project")
    os.makedirs(project_dir, exist_ok=True)
    settings_xml = os.path.join(project_dir, "settings.xml")
    with open(settings_xml, "w", encoding="utf-8") as f:
        f.write(
            "<?xml version='1.0' encoding='utf-8'?>\n"
            '<cms:CuemsProjectSettings xmlns:cms="https://stagelab.coop/cuems/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="https://stagelab.coop/cuems/ project_settings.xsd">'
            "<setting><name>brightness</name><value>75</value></setting>"
            "</cms:CuemsProjectSettings>"
        )

    config_manager.load_project_config("roundtrip-project")
    payload = config_manager.to_wire("project_settings")
    assert payload["setting"][0]["SettingType"]["name"] == "brightness"

    document = config_manager.from_json(SchemaName.PROJECT_SETTINGS, payload)

    target = config_manager.project_path(
        "roundtrip-project-2", "settings.xml", must_exist=False
    )
    os.makedirs(os.path.dirname(target), exist_ok=True)
    document.save(target)

    reloaded = ProjectSettings(target).xml_dict
    assert reloaded["setting"][0]["name"] == "brightness"
    assert reloaded["setting"][0]["value"] == "75"
