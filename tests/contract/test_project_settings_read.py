"""Contract C2 (G2) — the public read for a project's settings (T020-T022a).

``ConfigManager.project_settings`` answers with the document object, whether
``load_project_settings`` found a file or not; ``to_wire('project_settings')``
reaches it through the **same** projection body every other section uses.
"""

from __future__ import annotations

import pytest

from cuemsutils.config.settings import CuemsProjectSettingsType
from tests.support.config_inventory import build_config_manager


@pytest.fixture
def manager():
    return build_config_manager(load_project=False)


def test_a_project_with_no_settings_file_projects_empty(manager):
    """FR-015 — not ``{"setting": []}``, and identical to a file that holds
    no settings: the repeated field is omitted when empty, the projection's
    existing rule."""
    manager.load_project_config("a-project-with-no-settings-file")

    assert manager.to_wire("project_settings") == {}


def test_a_never_loaded_project_still_raises_not_loaded(manager):
    """FR-015a — "no file" and "never loaded" must stay distinguishable: a
    manager that never called ``load_project_config`` still raises the
    existing failure, not an empty projection."""
    with pytest.raises(AttributeError):
        manager.to_wire("project_settings")


def test_the_projection_reaches_the_same_body_as_every_other_section(manager):
    """FR-011/FR-014 — asserted structurally, not by comparing output: the
    section resolver calls ``getattr(self, section).to_wire()``, the same
    path every other projectable section takes. A second, bespoke
    implementation for this one section would satisfy every behavioural test
    here while violating the "one projection body" requirement."""
    from cuemsutils.helpers import CuemsDict

    manager.load_project_config("structural-check-project")
    value = manager.project_settings

    assert type(value).to_wire is CuemsDict.to_wire


def test_the_accessor_answers_with_the_document_object_not_a_dict(manager):
    """T022a — the shape two tests depend on: ``to_wire`` calls ``.to_wire()``
    on whatever ``getattr`` finds, so a raw ``dict``-returning property would
    raise instead of projecting."""
    manager.load_project_config("object-not-dict-project")

    value = manager.project_settings
    assert isinstance(value, CuemsProjectSettingsType)
    assert type(value) is not dict
