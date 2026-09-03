"""``DmxUniverse.set_dmx_channels`` (DmxCue.py:372-396) — conversion behavior.

Originally characterized a broad ``except Exception`` fallback that resembled the
shape of defect feature 005 removed elsewhere (``DmxSceneCompatibility``, see
``tests/contract/test_dmx_failure_path.py``'s docstring): on *any* failure
converting *any* one entry, the whole raw, un-normalized ``channels`` value was
stored as ``dmx_channels`` instead — silently, with no exception raised to the
caller.

Feature 009 replaces that swallow with a raise (``DmxChannelDecodeError``,
``cuemsutils.errors``) — see ``specs/009-fix-dmx-channel-conversion/``. The
"exception-swallow fallback" tests below now pin the *new* behavior: a
conversion failure raises instead of silently storing raw data. The
"well-formed path" tests are unchanged — they are this feature's regression
guard (FR-004/FR-008). A new test also pins the mixed-batch case (FR-004a):
today's original code silently dropped one side of a batch mixing
already-``DmxChannel`` instances with still-raw-but-valid entries, and this
feature's unified conversion loop resolves that rather than preserving it.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.DmxCue import DmxChannel, DmxUniverse
from cuemsutils.errors import DmxChannelDecodeError

# --- the well-formed path -----------------------------------------------------


def test_default_dmx_channels_is_none():
    assert DmxUniverse().dmx_channels is None


def test_wrapped_dict_entries_convert_to_dmxchannel_instances():
    u = DmxUniverse()
    u.dmx_channels = [{"DmxChannel": {"channel": 3, "value": 200}}]

    assert len(u.dmx_channels) == 1
    channel = u.dmx_channels[0]
    assert isinstance(channel, DmxChannel)
    assert channel.channel == 3
    assert channel.value == 200


def test_a_single_dmxchannel_instance_is_wrapped_into_a_list_unconverted():
    """Not a list, and already a ``DmxChannel``: wrapped as ``[channels]`` and
    appended as-is — the *same object*, not a freshly converted one."""
    ch = DmxChannel({"channel": 1, "value": 10})
    u = DmxUniverse()

    u.dmx_channels = ch

    assert u.dmx_channels == [ch]
    assert u.dmx_channels[0] is ch


def test_a_list_of_dmxchannel_instances_passes_through_unconverted():
    ch = DmxChannel({"channel": 1, "value": 10})
    u = DmxUniverse()

    u.dmx_channels = [ch]

    assert u.dmx_channels == [ch]
    assert u.dmx_channels[0] is ch


def test_none_entries_are_skipped_without_disturbing_valid_ones():
    u = DmxUniverse()

    u.dmx_channels = [None, {"DmxChannel": {"channel": 2, "value": 1}}]

    assert len(u.dmx_channels) == 1
    assert u.dmx_channels[0].channel == 2


def test_a_batch_mixing_already_converted_and_raw_entries_converts_both():
    """FR-004a: today's original two-branch code silently dropped one side of
    a mixed batch, order-dependently. The unified conversion loop resolves
    every entry to a proper ``DmxChannel`` — already-converted instances
    appended as-is, raw-but-valid dicts converted and appended — with none
    dropped."""
    already = DmxChannel({"channel": 1, "value": 10})
    u = DmxUniverse()

    u.dmx_channels = [already, {"DmxChannel": {"channel": 2, "value": 20}}]

    assert len(u.dmx_channels) == 2
    assert u.dmx_channels[0] is already
    assert isinstance(u.dmx_channels[1], DmxChannel)
    assert u.dmx_channels[1].channel == 2
    assert u.dmx_channels[1].value == 20


# --- the conversion-failure path ----------------------------------------------


def test_a_malformed_dict_entry_raises_dmx_channel_decode_error():
    """No ``'DmxChannel'`` key: indexing raises ``KeyError``, now wrapped and
    re-raised as ``DmxChannelDecodeError`` instead of silently falling back to
    the raw input."""
    u = DmxUniverse()

    with pytest.raises(DmxChannelDecodeError):
        u.dmx_channels = [{"not_dmxchannel_key": 1}]

    assert u.dmx_channels is None


def test_a_non_subscriptable_entry_raises_dmx_channel_decode_error():
    """An ``int`` entry raises ``TypeError`` on ``entry['DmxChannel']`` — same
    error type as the ``KeyError`` case (FR-005)."""
    u = DmxUniverse()

    with pytest.raises(DmxChannelDecodeError):
        u.dmx_channels = [5]

    assert u.dmx_channels is None


def test_one_bad_entry_aborts_conversion_of_the_whole_batch():
    """FR-003: the whole call fails on the first bad entry — ``dmx_channels``
    is left at its prior value (unset, for a fresh universe), not populated
    with a mix of converted and raw entries."""
    raw = [
        {"DmxChannel": {"channel": 1, "value": 1}},
        {"bad": 1},
        {"DmxChannel": {"channel": 2, "value": 2}},
    ]
    u = DmxUniverse()

    with pytest.raises(DmxChannelDecodeError) as excinfo:
        u.dmx_channels = raw

    assert excinfo.value.index == 1
    assert u.dmx_channels is None
