"""G1, T011 — resolving a tolerated write target has no side effects
(FR-005). ``must_exist=False`` answers a question; it must not also act on
the answer by creating the file or any directory in its path.
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


def test_tolerated_conf_path_creates_nothing(config_manager):
    target = config_manager.conf_path("never_written.xml", must_exist=False)

    assert not os.path.exists(target)
    assert not os.path.exists(os.path.dirname(target)) or os.path.dirname(target) == config_manager.config_dir


def test_tolerated_project_path_creates_no_project_directory(config_manager):
    project_dir = os.path.join(config_manager.library_path, "projects", "brand-new-project")
    # Precondition: this project has never been touched.
    assert not os.path.exists(project_dir)

    target = config_manager.project_path("brand-new-project", "settings.xml", must_exist=False)

    assert not os.path.exists(target)
    assert not os.path.exists(project_dir)


def test_resolving_a_tolerated_target_twice_is_idempotent(config_manager):
    first = config_manager.conf_path("never_written.xml", must_exist=False)
    second = config_manager.conf_path("never_written.xml", must_exist=False)

    assert first == second
    assert not os.path.exists(first)
