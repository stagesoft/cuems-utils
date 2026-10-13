"""Contract C1 (G1, T009/T010) — a write target for a file that does not
exist yet.

``ConfigBase.conf_path`` and ``ConfigManager.project_path`` both gain a
keyword-only ``must_exist`` parameter. The default (``True``) is today's
behaviour, unchanged, for every in-package call site and every consumer
(FR-002); passing ``must_exist=False`` tolerates an absent file and returns
the canonical path anyway (FR-001, FR-004). The tolerance is reachable only
by keyword, never positionally (FR-003).
"""

from __future__ import annotations

import os
import shutil

import pytest

from cuemsutils.tools.ConfigManager import ConfigManager

REPO_ROOT_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.fixture
def config_manager(tmp_path, monkeypatch):
    conf_dir = tmp_path / "conf"
    shutil.copytree(REPO_ROOT_DATA, conf_dir, ignore=shutil.ignore_patterns("corpus"))
    monkeypatch.setenv("CUEMS_CONF_PATH", str(conf_dir))
    return ConfigManager()


# --- ConfigBase.conf_path ---------------------------------------------------


def test_conf_path_tolerates_an_absent_file_when_asked(config_manager):
    target = config_manager.conf_path("never_written.xml", must_exist=False)
    assert target == os.path.join(config_manager.config_dir, "never_written.xml")
    assert not os.path.exists(target)


def test_conf_path_still_returns_the_path_when_the_file_exists(config_manager):
    target = config_manager.conf_path("settings.xml", must_exist=False)
    assert target == config_manager.conf_path("settings.xml")


def test_conf_path_default_still_raises_on_an_absent_file(config_manager):
    with pytest.raises(FileNotFoundError, match="never_written.xml"):
        config_manager.conf_path("never_written.xml")


def test_conf_path_must_exist_true_explicit_still_raises(config_manager):
    with pytest.raises(FileNotFoundError):
        config_manager.conf_path("never_written.xml", must_exist=True)


def test_conf_path_tolerance_is_not_reachable_positionally(config_manager):
    with pytest.raises(TypeError):
        config_manager.conf_path("never_written.xml", False)  # type: ignore[call-arg]


# --- ConfigManager.project_path ---------------------------------------------


def test_project_path_tolerates_an_absent_file_when_asked(config_manager):
    target = config_manager.project_path("new-project", "settings.xml", must_exist=False)
    assert target == os.path.join(
        config_manager.library_path, "projects", "new-project", "settings.xml"
    )
    assert not os.path.exists(target)


def test_project_path_default_still_raises_on_an_absent_project(config_manager):
    with pytest.raises(FileNotFoundError, match="settings.xml"):
        config_manager.project_path("new-project", "settings.xml")


def test_project_path_tolerance_is_not_reachable_positionally(config_manager):
    with pytest.raises(TypeError):
        config_manager.project_path("new-project", "settings.xml", False)  # type: ignore[call-arg]
