"""DMX channel conversion failure raises — the read-side sibling of
``test_dmx_failure_path.py``'s write-side contract (feature 005,
``DmxSceneWriteError``), landed by feature 009.

``DmxUniverse.set_dmx_channels`` (``cues/DmxCue.py``) used to wrap its whole
per-entry conversion loop in one ``except Exception``: on any single entry's
``KeyError``/``TypeError``, it silently stored the raw, unconverted
``channels`` argument as ``dmx_channels`` — corrupting every entry in the
batch, not just the offending one, with only a log line as any trace. See
``specs/planning/dmx-universe-channel-conversion-defect.md`` for the full
characterization and ``specs/009-fix-dmx-channel-conversion/`` for this
feature's spec.

What changed, precisely:

* the swallow is **deleted** — a conversion failure now raises
  ``DmxChannelDecodeError`` (``cuemsutils.errors``), naming the universe and
  the failing entry (identifiers only — FR-002, FR-UX-001, mirroring
  ``DmxSceneWriteError``'s "no object repr" rule);
* this is unreachable from a schema-valid ``script.xml`` — T1 already rejects
  a malformed ``<DmxChannel>`` before this code ever runs on XML-sourced
  content (confirmed by investigation during ``/speckit.specify``) — but *is*
  reachable from ``CuemsScript.from_json``, which runs no schema validation
  (FR-007);
* a batch mixing already-``DmxChannel`` instances with still-raw-but-valid
  entries now converts **both** sides correctly (FR-004a) — today's original
  code silently dropped one side, order-dependently.
"""

from __future__ import annotations

import json

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.DmxCue import DmxChannel, DmxCue, DmxUniverse
from cuemsutils.errors import DmxChannelDecodeError
from tests.support.capture_goldens import build_generated_script


def _universe_with(dmx_channels):
    u = DmxUniverse()
    u.universe_num = 7
    u.dmx_channels = dmx_channels
    return u


# --- the change: it raises --------------------------------------------------


def test_a_malformed_entry_raises_dmx_channel_decode_error():
    with pytest.raises(DmxChannelDecodeError):
        _universe_with([{"not_dmxchannel_key": 1}])


def test_the_error_identifies_the_universe_by_universe_num():
    u = DmxUniverse()
    u.universe_num = 42
    with pytest.raises(DmxChannelDecodeError) as excinfo:
        u.dmx_channels = [{"not_dmxchannel_key": 1}]
    assert "42" in str(excinfo.value)


def test_the_error_identifies_the_failing_entrys_index_and_type():
    u = DmxUniverse()
    with pytest.raises(DmxChannelDecodeError) as excinfo:
        u.dmx_channels = [
            {"DmxChannel": {"channel": 1, "value": 1}},
            {"not_dmxchannel_key": 1},
        ]
    assert excinfo.value.index == 1
    assert "1" in str(excinfo.value)
    assert "dict" in str(excinfo.value)


def test_the_original_keyerror_is_preserved_as_the_cause():
    u = DmxUniverse()
    with pytest.raises(DmxChannelDecodeError) as excinfo:
        u.dmx_channels = [{"not_dmxchannel_key": 1}]
    assert isinstance(excinfo.value.__cause__, KeyError)


def test_the_original_typeerror_is_preserved_as_the_cause():
    u = DmxUniverse()
    with pytest.raises(DmxChannelDecodeError) as excinfo:
        u.dmx_channels = [5]
    assert isinstance(excinfo.value.__cause__, TypeError)


def test_the_error_carries_no_object_repr():
    """FR-002 — identifiers only. Entry content stays out of the message."""
    u = DmxUniverse()
    secret_marker = "SHOW_CONTENT_SHOULD_NOT_LEAK"
    with pytest.raises(DmxChannelDecodeError) as excinfo:
        u.dmx_channels = [{"not_dmxchannel_key": secret_marker}]
    assert secret_marker not in str(excinfo.value)


# --- the control cases -------------------------------------------------------


def test_a_healthy_universe_still_converts():
    """Without this, always-raising would pass every test above."""
    u = _universe_with([{"DmxChannel": {"channel": 3, "value": 200}}])
    assert len(u.dmx_channels) == 1
    assert isinstance(u.dmx_channels[0], DmxChannel)


def test_a_mixed_batch_converts_both_sides():
    """FR-004a — the case today's original code silently corrupted."""
    already = DmxChannel({"channel": 1, "value": 10})
    u = _universe_with([already, {"DmxChannel": {"channel": 2, "value": 20}}])

    assert len(u.dmx_channels) == 2
    assert u.dmx_channels[0] is already
    assert isinstance(u.dmx_channels[1], DmxChannel)
    assert u.dmx_channels[1].channel == 2


# --- reachable from CuemsScript.from_json, not from script.xml load ---------


def test_from_json_reaches_the_same_error():
    """FR-007 — a payload that bypassed schema validation entirely (here, a
    JSON round trip) reaches ``set_dmx_channels`` through ``DmxCue``'s opaque,
    non-recursive construction and raises the same error."""
    script = build_generated_script()
    data = json.loads(script.to_json())

    contents = data["CuemsScript"]["CueList"]["contents"]
    dmx_cue = next(c for c in contents if "DmxCue" in c)
    dmx_cue["DmxCue"]["DmxScene"]["DmxUniverse"]["dmx_channels"] = [
        {"not_dmxchannel_key": 1}
    ]

    with pytest.raises(DmxChannelDecodeError):
        CuemsScript.from_json(data)


def test_a_healthy_from_json_round_trip_is_unaffected():
    """Control case: the unmodified generated script's real DMX scene still
    round-trips through ``from_json`` without raising."""
    script = build_generated_script()
    data = json.loads(script.to_json())

    result = CuemsScript.from_json(data)

    contents = result["CueList"]["contents"]
    dmx_cue = next(c for c in contents if isinstance(c, DmxCue))
    universe = dmx_cue["DmxScene"]["DmxUniverse"]
    assert all(isinstance(c, DmxChannel) for c in universe.dmx_channels)
