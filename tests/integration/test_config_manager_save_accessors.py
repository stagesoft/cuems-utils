"""``ConfigManager``'s ``save_*`` accessors, called directly rather than only
their underlying model classes.

``tests/integration/test_config_save.py`` (ITEM B) exercises ``NetworkMap``/
``Settings``/``ProjectSettings``/``ProjectMappings``'s own ``.save()`` methods
and checks the ``ConfigManager`` accessors' *signatures* by reflection
(``test_every_domain_save_has_the_same_argument_shape_and_default_path_behaviour``),
but never actually calls ``manager.save_network_map()`` /
``manager.save_settings()`` / ``manager.save_project_settings()`` /
``manager.save_project_mappings()``. A bug in the accessor itself — the wrong
attribute, the wrong default path — would pass that suite untouched. This
closes that gap.
"""

from __future__ import annotations

import os
import shutil

import pytest

from cuemsutils.tools.ConfigManager import ConfigManager
from cuemsutils.xml.settings import NetworkMap, ProjectMappings, ProjectSettings, Settings

REPO_ROOT_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

_PROJECT_SETTINGS_XML = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    '<cms:CuemsProjectSettings xmlns:cms="https://stagelab.coop/cuems/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="https://stagelab.coop/cuems/ project_settings.xsd">'
    "<setting><name>example</name><value>1</value></setting>"
    "</cms:CuemsProjectSettings>"
)


@pytest.fixture
def config_manager(tmp_path, monkeypatch):
    """A ``ConfigManager`` rooted at a scratch copy of ``tests/data`` — every
    ``save_*`` call in this file lands under ``tmp_path``, never in the real
    fixtures under version control."""
    conf_dir = tmp_path / "conf"
    shutil.copytree(REPO_ROOT_DATA, conf_dir, ignore=shutil.ignore_patterns("corpus"))
    monkeypatch.setenv("CUEMS_CONF_PATH", str(conf_dir))
    return ConfigManager()


@pytest.fixture
def partial_config_manager(tmp_path, monkeypatch):
    """Constructed with ``load_all=False`` — ``network_map`` never becomes a
    document, so it can pin the pre-load ``AttributeError`` the docstring
    documents."""
    conf_dir = tmp_path / "conf"
    shutil.copytree(REPO_ROOT_DATA, conf_dir, ignore=shutil.ignore_patterns("corpus"))
    monkeypatch.setenv("CUEMS_CONF_PATH", str(conf_dir))
    return ConfigManager(load_all=False)


@pytest.fixture
def project_config_manager(config_manager, tmp_path, monkeypatch):
    """``config_manager`` with a real project directory behind it, so
    ``load_project_config``/``save_project_settings``/``save_project_mappings``
    have something concrete to round-trip rather than falling back to
    defaults (``project_path`` raising ``FileNotFoundError``, per
    ``ConfigManager.load_project_mappings``'s except branch)."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "settings.xml").write_text(_PROJECT_SETTINGS_XML, encoding="utf-8")
    shutil.copyfile(
        os.path.join(REPO_ROOT_DATA, "project_mappings.xml"),
        project_dir / "mappings.xml",
    )

    def _project_path(project_uname, file_name):
        return str(project_dir / file_name)

    monkeypatch.setattr(config_manager, "project_path", _project_path)
    config_manager.load_project_config("test_project")
    return config_manager


# --- save_network_map --------------------------------------------------------


def test_save_network_map_default_path_round_trips(config_manager):
    config_manager.node_network_map["alias"] = "renamed-via-save-network-map"
    config_manager.save_network_map()

    reloaded = NetworkMap(config_manager.conf_path("network_map.xml")).xml_dict
    assert reloaded["node_list"][0]["node"]["alias"] == "renamed-via-save-network-map"


def test_save_network_map_explicit_path(config_manager, tmp_path):
    target = tmp_path / "elsewhere" / "network_map.xml"
    target.parent.mkdir()

    config_manager.save_network_map(str(target))

    assert NetworkMap(str(target)).xml_dict == config_manager.network_map


def test_save_network_map_before_load_raises(partial_config_manager, tmp_path):
    with pytest.raises(AttributeError):
        partial_config_manager.save_network_map(str(tmp_path / "unused.xml"))


# --- save_settings ------------------------------------------------------------


def test_save_settings_default_path_round_trips(config_manager):
    config_manager.node_conf["mac"] = "aa:bb:cc:dd:ee:ff"
    config_manager.save_settings()

    reloaded = Settings(config_manager.conf_path("settings.xml")).get_dict()
    assert reloaded["node"]["mac"] == "aa:bb:cc:dd:ee:ff"


def test_save_settings_explicit_path(config_manager, tmp_path):
    target = tmp_path / "elsewhere" / "settings.xml"
    target.parent.mkdir()

    config_manager.save_settings(str(target))

    assert Settings(str(target)).get_dict() == config_manager.settings


# --- save_project_settings -----------------------------------------------------


def test_save_project_settings_default_path_round_trips(project_config_manager):
    project_config_manager.project_conf  # loaded, per load_project_settings
    project_config_manager._project_settings_document["setting"][0]["value"] = "42"
    project_config_manager.save_project_settings("test_project")

    reloaded = ProjectSettings(
        project_config_manager.project_path("test_project", "settings.xml")
    ).xml_dict
    assert reloaded["setting"][0]["value"] == "42"


def test_save_project_settings_explicit_path(project_config_manager, tmp_path):
    target = tmp_path / "elsewhere" / "settings.xml"
    target.parent.mkdir()

    project_config_manager.save_project_settings("test_project", str(target))

    assert ProjectSettings(str(target)).xml_dict == project_config_manager._project_settings_document


def test_save_project_settings_before_load_raises(config_manager, tmp_path):
    with pytest.raises(AttributeError):
        config_manager.save_project_settings("never-loaded", str(tmp_path / "unused.xml"))


# --- save_project_mappings ------------------------------------------------------


def test_save_project_mappings_default_path_round_trips(project_config_manager):
    project_config_manager.project_mappings["default_audio_input"] = "renamed-input"
    project_config_manager.save_project_mappings("test_project")

    reloaded = ProjectMappings(
        project_config_manager.project_path("test_project", "mappings.xml")
    ).processed
    assert reloaded["default_audio_input"] == "renamed-input"


def test_save_project_mappings_explicit_path(project_config_manager, tmp_path):
    """Compared field-by-field, not by object equality against the pre-save
    in-memory value — ``doc_version`` (present only once written) and the
    dropped ``schemaLocation`` wire artefact make a strict ``==`` brittle for
    reasons unrelated to what this test checks; see
    ``test_config_save.py``'s own note on comparing against the writer's own
    output form."""
    target = tmp_path / "elsewhere" / "mappings.xml"
    target.parent.mkdir()

    project_config_manager.save_project_mappings("test_project", str(target))

    reloaded = ProjectMappings(str(target)).processed
    assert reloaded["number_of_nodes"] == project_config_manager.project_mappings["number_of_nodes"]
    assert reloaded["default_audio_input"] == project_config_manager.project_mappings["default_audio_input"]
    assert len(reloaded["nodes"]) == len(project_config_manager.project_mappings["nodes"])


def test_save_project_mappings_before_load_raises(config_manager, tmp_path):
    with pytest.raises(AttributeError):
        config_manager.save_project_mappings("never-loaded", str(tmp_path / "unused.xml"))
