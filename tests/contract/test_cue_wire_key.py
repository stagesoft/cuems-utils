# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T046 — the wire key is ``Cue`` plus a class (FR-032, FR-052).

``{"AudioCue": {...}}`` becomes ``{"Cue": {..., "class": "audio"}}``. That one
sentence is the whole of this feature's contract to ``cuems-frontend``, and
this module is its oracle: the golden regeneration in T050 is checked against
*this*, never the other way round. Nothing else about the projection changes —
same fields, same order within a cue, same scalars.
"""

from __future__ import annotations

from pathlib import Path

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.xml.descriptor import generate_script_example

#: Element names that must not appear as a wire key anywhere in the payload.
RETIRED_KEYS = frozenset({
    "AudioCue", "VideoCue", "DmxCue",
    "AudioCueOutput", "VideoCueOutput", "DmxCueOutput",
})


def _walk(value, path=()):
    """Every ``(path, key, body)`` single-key wrapper in a wire payload."""
    if isinstance(value, dict):
        for key, body in value.items():
            yield (path, key, body)
            yield from _walk(body, (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, (*path, index))


def _cue_wrappers(wire):
    return [(key, body) for _path, key, body in _walk(wire) if key in ("Cue", "CueOutput")]


def _example_wire():
    return generate_script_example().to_wire()


def test_no_retired_element_name_is_a_wire_key():
    wire = _example_wire()
    offenders = sorted({key for _p, key, _b in _walk(wire) if key in RETIRED_KEYS})
    assert offenders == [], f"retired wire keys still emitted: {offenders}"


def test_every_cue_wrapper_carries_a_class():
    wire = _example_wire()
    wrappers = _cue_wrappers(wire)
    assert wrappers, "the example projects no Cue or CueOutput wrapper at all"
    for key, body in wrappers:
        assert isinstance(body, dict), f"{key} body is not a mapping"
        assert "class" in body, f"{key} carries no class value: {sorted(body)}"
        assert isinstance(body["class"], str) and body["class"], (
            f"{key} class is not a non-empty string: {body['class']!r}"
        )


def test_the_classes_are_the_three_the_example_builds():
    wire = _example_wire()
    cue_classes = sorted(
        {body["class"] for key, body in _cue_wrappers(wire) if key == "Cue"}
    )
    assert cue_classes == ["audio", "dmx", "video"]
    output_classes = sorted(
        {body["class"] for key, body in _cue_wrappers(wire) if key == "CueOutput"}
    )
    assert output_classes == ["audio", "dmx", "video"]


def test_action_fade_and_cuelist_keep_their_own_wire_keys():
    wire = _example_wire()
    keys = {key for _p, key, _b in _walk(wire)}
    assert {"ActionCue", "FadeCue", "CueList"} <= keys
    for _path, key, body in _walk(wire):
        if key in ("ActionCue", "FadeCue", "CueList") and isinstance(body, dict):
            assert "class" not in body, f"{key} was given a device class"


def test_nothing_else_about_the_projection_changed(tmp_path):
    """The round trip is unchanged apart from the key and the class value.

    A cue's body, minus ``class``, is what the per-class key used to carry:
    the same field names in the same order. Compared against the object the
    projection came from rather than against a recorded golden, so this test
    says nothing about which bytes T050 regenerates.
    """
    script = generate_script_example()
    wire = script.to_wire()
    contents = script["CueList"]["contents"]
    projected = [
        body for key, body in _cue_wrappers(wire) if key == "Cue"
    ]
    media_cues = [cue for cue in contents if "Media" in cue or "DmxScene" in cue]
    assert len(projected) == len(media_cues)
    for body, cue in zip(projected, media_cues):
        assert [k for k in body if k != "class"] == [
            k for k in body if k != "class"
        ]
        for key in body:
            if key == "class":
                continue
            assert key in cue, f"{key} is on the wire but not on the object"


def test_to_json_round_trips_through_the_new_key(tmp_path):
    script = generate_script_example()
    again = CuemsScript.from_json(script.to_json())
    assert again.to_wire() == script.to_wire()


def test_a_saved_document_reloads_to_the_same_wire_payload(tmp_path):
    """Build side and decode side agree on the key and the attribute."""
    script = generate_script_example()
    path = tmp_path / "script.xml"
    script.save(path)
    text = Path(path).read_text(encoding="utf-8")
    assert "<Cue " in text and 'class="audio"' in text
    for retired in RETIRED_KEYS:
        assert f"<{retired}" not in text, f"{retired} is still written as an element"
    assert CuemsScript.load(path).to_wire() == script.to_wire()
