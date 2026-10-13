"""G1 (US1), T012 — a project's configuration document can be saved for the
first time.

``project_path(..., must_exist=False)`` answers with the canonical write
target for a file that does not exist yet (FR-001). Saving a document there
creates it and the document reloads with equal values (acceptance 3); a
target whose **parent directory** is absent still fails at write time
(acceptance 4) — that is a separate, correct failure this feature does not
change.

Extended by US2 (T023) to the full G1+G2 journey once ``project_settings``
has a public read.
"""

from __future__ import annotations

import os
import shutil

import pytest

from cuemsutils.config.settings import CuemsProjectSettingsType
from cuemsutils.tools.ConfigManager import ConfigManager
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


def test_a_projects_first_settings_save_creates_and_reloads_equal(config_manager):
    # The project's own directory exists (as it would once a project is
    # created), but its settings.xml has never been saved.
    project_dir = os.path.join(config_manager.library_path, "projects", "first-save-project")
    os.makedirs(project_dir, exist_ok=True)

    target = config_manager.project_path(
        "first-save-project", "settings.xml", must_exist=False
    )
    assert not os.path.exists(target)

    document = CuemsProjectSettingsType()
    document["setting"] = [{"name": "example", "value": "1"}]
    document.save(target)

    assert os.path.exists(target)
    reloaded = ProjectSettings(target).xml_dict
    assert reloaded["setting"][0]["name"] == "example"
    assert reloaded["setting"][0]["value"] == "1"


def test_the_full_g1_g2_journey_first_save_of_an_edited_project(config_manager):
    """R6's synergy, SC-001/SC-002: a project with no ``settings.xml`` loads
    an empty document (G2), the operator edits it, and G1 supplies the
    tolerated target for its very first save."""
    project_dir = os.path.join(config_manager.library_path, "projects", "never-saved-project")
    os.makedirs(project_dir, exist_ok=True)

    config_manager.load_project_config("never-saved-project")
    assert config_manager.to_wire("project_settings") == {}

    config_manager.project_settings["setting"] = [{"name": "volume", "value": "50"}]

    target = config_manager.project_path(
        "never-saved-project", "settings.xml", must_exist=False
    )
    assert not os.path.exists(target)

    # G1's write target is resolved explicitly and handed to the save
    # accessor: ``save_project_settings``'s own *default*-path resolution is
    # unchanged (it still requires the file to already exist, contract C1's
    # declined "one call that resolves and persists") — a first save passes
    # the tolerated path through the existing ``path`` parameter.
    config_manager.save_project_settings("never-saved-project", target)

    assert os.path.exists(target)
    reloaded = ProjectSettings(target).xml_dict
    assert reloaded["setting"][0]["name"] == "volume"
    assert reloaded["setting"][0]["value"] == "50"


def test_a_target_whose_parent_directory_is_absent_still_fails_at_write_time(config_manager):
    # No directory was ever created for this project.
    target = config_manager.project_path(
        "never-created-project", "settings.xml", must_exist=False
    )
    project_dir = os.path.dirname(target)
    assert not os.path.exists(project_dir)

    document = CuemsProjectSettingsType()
    with pytest.raises(OSError):
        document.save(target)
