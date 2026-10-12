# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T027 — what a fresh, unconfigured node's ``default_mappings.xml`` means to
``ConfigManager`` (feature 011, research R12): it loads, the six defaults are
empty, and the node entry claims no hardware.

**Measured, not assumed**: ``get_video_output_id('default')`` and
``get_audio_output_id('default')`` read ``node_conf['default_*_output']`` — keys
``settings.xsd`` has never declared — so they raise ``KeyError`` on *every*
node today, fresh or not. They have zero callers; the fossil is feature 014's
to back with a real document or delete. This file pins the measured behaviour
rather than changing an accessor 011 does not own."""

from __future__ import annotations

import pytest

from cuemsutils.tools.ConfigManager import ConfigManager
from cuemsutils.xml import make_defaults


@pytest.fixture
def fresh(tmp_path):
    make_defaults.generate(tmp_path)
    return ConfigManager(config_dir=str(tmp_path), load_all=True)


def test_a_fresh_node_loads_with_empty_defaults(fresh):
    for field in ("default_audio_input", "default_audio_output", "default_video_input",
                  "default_video_output", "default_dmx_input", "default_dmx_output"):
        assert fresh.mappings.get(field) in (None, ""), field
    assert fresh.mappings["number_of_nodes"] == 1
    assert fresh.node_mappings["uuid"] == fresh.node_conf["uuid"]
    assert all(not v for v in fresh.node_hw_outputs.values()), fresh.node_hw_outputs


def test_the_fossil_accessors_raise_as_measured(fresh):
    """Recorded, not repaired: feature 014's (research R12, plan)."""
    with pytest.raises(KeyError):
        fresh.get_video_output_id("default")
    with pytest.raises(KeyError):
        fresh.get_audio_output_id("default")
