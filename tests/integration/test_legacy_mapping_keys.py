# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T025 — the old spellings answer from the reshaped document (FR-012a)."""

from __future__ import annotations

from pathlib import Path

from cuemsutils.xml.settings import ProjectMappings

_DOCUMENT = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "cuems-utils" / "project_mappings.xml"
)


def test_each_legacy_spelling_answers():
    loaded = ProjectMappings(str(_DOCUMENT)).processed
    assert loaded["default_audio_input"] == "2cf05d21cca3 system:capture_1"
    assert loaded["default_audio_output"] == "2cf05d21cca3 system:playback_1"
    assert loaded["default_video_output"] == "2cf05d21cca3 0"
    assert loaded["default_video_input"] == ""
    assert loaded["default_dmx_input"] == ""
    assert loaded["default_dmx_output"] == ""

    node = loaded["nodes"][0]["node"]
    assert node["audio"]["class"] == "audio"
    assert node["video"]["class"] == "video"
    assert node["dmx"]["class"] == "dmx"
    assert node.get("audio")["class"] == "audio"
    assert node.get("lighting") is None
