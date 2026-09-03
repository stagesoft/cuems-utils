"""``DmxUniverse.set_dmx_channels`` (DmxCue.py:372-396) — untested.

Its broad ``except Exception`` fallback resembles the shape of defect feature
005 removed elsewhere (``DmxSceneCompatibility``, see
``tests/contract/test_dmx_failure_path.py``'s docstring): on *any* failure
converting *any* one entry, the whole raw, un-normalized ``channels`` value is
stored as ``dmx_channels`` instead — silently, with no exception raised to the
caller. These tests **characterize the current behaviour** (pin what it does
today, including the fallback), they do not assert it is correct; fixing it
would be a behaviour change out of scope here.
"""

from __future__ import annotations

from cuemsutils.cues.DmxCue import DmxChannel, DmxUniverse


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
    stored via the ``isinstance`` branch — the *original* list object, not a
    freshly built one."""
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


# --- the exception-swallow fallback ------------------------------------------


def test_a_malformed_dict_entry_falls_back_to_storing_the_raw_input():
    """No ``'DmxChannel'`` key: indexing raises ``KeyError`` inside the loop,
    caught by the blanket ``except Exception`` — the raw list is stored as-is,
    still plain ``dict``, not converted, and no exception reaches the
    caller."""
    raw = [{"not_dmxchannel_key": 1}]
    u = DmxUniverse()

    u.dmx_channels = raw

    assert u.dmx_channels == raw
    assert not isinstance(u.dmx_channels[0], DmxChannel)


def test_a_non_subscriptable_entry_falls_back_to_storing_the_raw_input():
    """An ``int`` entry raises ``TypeError`` on ``r['DmxChannel']`` — same
    fallback as the ``KeyError`` case, different exception type, because the
    ``except`` clause is unqualified."""
    raw = [5]
    u = DmxUniverse()

    u.dmx_channels = raw

    assert u.dmx_channels == raw


def test_one_bad_entry_discards_conversion_of_every_good_entry_in_the_batch():
    """The defect's sharp edge: the exception aborts the loop entirely, so
    entries *before* the bad one — already logically valid — are stored
    unconverted too, not just the offending entry."""
    raw = [
        {"DmxChannel": {"channel": 1, "value": 1}},
        {"bad": 1},
        {"DmxChannel": {"channel": 2, "value": 2}},
    ]
    u = DmxUniverse()

    u.dmx_channels = raw

    assert u.dmx_channels == raw
    assert all(not isinstance(c, DmxChannel) for c in u.dmx_channels)
