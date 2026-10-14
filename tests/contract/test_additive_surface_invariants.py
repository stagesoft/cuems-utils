# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Feature 015 is additive: nothing it did changes what an existing call means.

T120a — no schema version moved and no conversion was added or removed.
T120b — every public call the feature touched keeps its default behaviour and
exception type. The new keyword (``must_exist``) defaults to the old behaviour,
and the two raised types are still the ones a caller already catches.
"""

from __future__ import annotations

import inspect

import pytest

from cuemsutils.xml import versioning

#: The registry at the 015 branch point (``75a958e``), literal on purpose — a
#: constant imported from the module under test would move with it.
BRANCH_POINT_VERSIONS = {
    "script": 2,
    "settings": 3,
    "network_map": 2,
    "project_mappings": 2,
    "project_settings": 1,
    "hardware_outputs": 2,
}
BRANCH_POINT_CONVERSIONS = {
    ("hardware_outputs", 1),
    ("network_map", 1),
    ("script", 1),
    ("settings", 1),
}
#: Steps that are identity *by absence* (feature 012); see test_version_marker.py.
BRANCH_POINT_IDENTITY_STEPS = {("project_mappings", 1), ("settings", 2)}


def test_no_schema_version_moved():
    assert versioning.CURRENT_VERSION == BRANCH_POINT_VERSIONS


def test_the_conversion_registry_is_unchanged():
    assert set(versioning._CONVERSIONS) == BRANCH_POINT_CONVERSIONS


def test_the_deliberate_identity_steps_are_unchanged():
    from tests.contract.test_version_marker import DELIBERATE_IDENTITY_STEPS

    assert set(DELIBERATE_IDENTITY_STEPS) == BRANCH_POINT_IDENTITY_STEPS


# --- T120b -----------------------------------------------------------------


@pytest.fixture
def manager(tmp_path, monkeypatch):
    from tests.support.config_inventory import build_config_manager

    return build_config_manager(load_project=False)


def test_must_exist_defaults_to_the_old_behaviour(manager):
    from cuemsutils.tools.ConfigManager import ConfigManager

    for fn in (ConfigManager.conf_path, ConfigManager.project_path):
        parameter = inspect.signature(fn).parameters["must_exist"]
        assert parameter.default is True
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_a_missing_file_still_raises_file_not_found_by_default(manager):
    with pytest.raises(FileNotFoundError):
        manager.conf_path("no-such-document.xml")
    with pytest.raises(FileNotFoundError):
        manager.project_path("no-such-project", "settings.xml")


def test_the_tolerant_form_answers_instead_of_raising(manager):
    assert manager.conf_path("no-such-document.xml", must_exist=False).endswith(
        "no-such-document.xml"
    )


def test_an_existing_file_resolves_identically_in_both_forms(manager):
    assert manager.conf_path("settings.xml") == manager.conf_path(
        "settings.xml", must_exist=False
    )


def test_to_wire_keeps_its_default_section_and_its_error_type(manager):
    assert inspect.signature(type(manager).to_wire).parameters["section"].default == "settings"
    with pytest.raises(ValueError):
        manager.to_wire("not-a-real-section")


def test_the_new_error_is_a_validation_error():
    """A caller catching ``ValidationError`` around a load still catches it."""
    from cuemsutils.errors import NodeIdentityCollisionError, ValidationError

    assert issubclass(NodeIdentityCollisionError, ValidationError)
