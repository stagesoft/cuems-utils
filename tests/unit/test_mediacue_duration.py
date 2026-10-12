"""``Media.duration`` accepts everything ``format_timecode`` does (T007) — FR-002.

The setter collapsed from a three-branch (``str``/``CTimecode``/``None``)
dispatch to a direct call to the shared helper (T014), the same one
``FadeCue.duration`` and every other ``CTimecodeType`` field uses. This pins
that the four supply shapes produce the *same* object, not four subtly
different ones.
"""

from __future__ import annotations

from cuemsutils.cues.MediaCue import Media
from cuemsutils.tools.CTimecode import CTimecode


def test_str_int_dict_and_ctimecode_all_produce_the_same_object():
    expected = CTimecode("00:00:10.000")

    from_str = Media()
    from_str.duration = "00:00:10.000"

    from_int = Media()
    from_int.duration = 10

    from_dict = Media()
    from_dict.duration = {"CTimecode": "00:00:10.000"}

    from_ctimecode = Media()
    from_ctimecode.duration = CTimecode("00:00:10.000")

    for media in (from_str, from_int, from_dict, from_ctimecode):
        assert media.duration == expected
        assert type(media.duration) is CTimecode


def test_the_shared_helper_is_format_timecode():
    """Named directly, so a future setter cannot quietly reintroduce a
    second, slightly different implementation of "parse a timecode"."""
    import inspect

    assert "format_timecode" in inspect.getsource(Media)
