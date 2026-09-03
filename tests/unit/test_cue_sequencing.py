"""The auto-follow / next-cue sequencing surface — untested until now.

``Cue._next_enabled``/``Cue.get_next_cue`` (the target-chain walk, including
its infinite-loop guard) and ``CueList.find``/``get_media``/``get_next_cue``/
``times`` (recursive traversal over ``contents``) have no test anywhere in
this suite despite being the mechanism ``cuems-engine`` relies on to decide
what plays next. This is playback-sequencing logic, not incidental getters.
"""

from __future__ import annotations

from cuemsutils.cues import AudioCue, CueList
from cuemsutils.cues.Cue import Cue
from cuemsutils.helpers import new_uuid


def _linked(*cues, post_go="pause"):
    """Wire ``cues`` into a target chain: each points at the next.

    ``target``/``_target_object`` are set independently (``target`` carries
    no coercion — see ``Cue.set_target``), so both are set explicitly rather
    than relying on one to imply the other, exactly as the production code
    reads them (``_next_enabled`` reads ``self.target`` as a truthiness gate
    and ``self._target_object`` as the actual link).
    """
    for cue, nxt in zip(cues, cues[1:]):
        cue.post_go = post_go
        cue.target = "linked"
        cue.target_object(nxt)
    return cues


# --- Cue._next_enabled / Cue.get_next_cue ------------------------------------


def test_next_enabled_is_none_with_no_target():
    c = Cue()
    assert c._next_enabled() is None
    assert c.get_next_cue() is None


def test_next_enabled_returns_the_immediate_target_when_enabled():
    a, b = Cue(), Cue()
    _linked(a, b)
    assert a._next_enabled() is b


def test_next_enabled_skips_disabled_cues_in_the_chain():
    a, b, c, d = Cue(), Cue(), Cue(), Cue()
    _linked(a, b, c, d)
    b.enabled = False
    c.enabled = False
    assert a._next_enabled() is d


def test_next_enabled_returns_none_past_the_depth_guard():
    """50 disabled links exceed the guard (``depth > 50``); the walk gives up
    rather than looping forever on a chain that never reaches an enabled
    cue."""
    chain = [Cue() for _ in range(60)]
    _linked(*chain)
    for cue in chain[1:]:
        cue.enabled = False

    assert chain[0]._next_enabled() is None


def test_get_next_cue_returns_the_immediate_next_when_post_go_is_pause():
    a, b = Cue(), Cue()
    _linked(a, b, post_go="pause")
    assert a.get_next_cue() is b


def test_get_next_cue_recurses_when_post_go_is_not_pause():
    """The recursion is driven by the *caller's own* ``post_go``, not the
    target's: ``a.get_next_cue()`` recurses because ``a.post_go`` is
    ``'continue'``, delegating to ``b.get_next_cue()`` — which then returns
    directly because ``b.post_go`` is ``'pause'``."""
    a, b, c = Cue(), Cue(), Cue()
    _linked(a, b, c, post_go="pause")
    a.post_go = "continue"  # a -> b (continue) -> c (pause)
    assert a.get_next_cue() is c


# --- CueList.find --------------------------------------------------------------


def test_find_returns_self_when_the_uuid_matches_the_list_itself():
    cl = CueList()
    assert cl.find(cl.id) is cl


def test_find_returns_none_on_an_empty_list_for_an_unmatched_uuid():
    cl = CueList()
    assert cl.find(new_uuid()) is None


def test_find_returns_a_direct_child():
    child = Cue()
    cl = CueList({"contents": [child]})
    assert cl.find(child.id) is child


def test_find_recurses_into_a_nested_cuelist():
    grandchild = Cue()
    inner = CueList({"contents": [grandchild]})
    outer = CueList({"contents": [inner]})
    assert outer.find(grandchild.id) is grandchild


def test_find_returns_none_when_the_uuid_is_nowhere_in_the_tree():
    inner = CueList({"contents": [Cue()]})
    outer = CueList({"contents": [inner, Cue()]})
    assert outer.find(new_uuid()) is None


# --- CueList.get_media ----------------------------------------------------------


def _audio_cue_with_media(file_name):
    ac = AudioCue()
    ac.media = {"file_name": file_name, "id": new_uuid()}
    return ac


def test_get_media_is_empty_on_a_list_with_no_contents():
    assert CueList().get_media() == {}


def test_get_media_collects_media_cues_by_id():
    ac = _audio_cue_with_media("one.wav")
    cl = CueList({"contents": [ac]})

    media = cl.get_media()

    assert media == {str(ac.id): {str(ac.media.id): "one.wav"}}


def test_get_media_ignores_plain_cues_without_media():
    ac = _audio_cue_with_media("one.wav")
    cl = CueList({"contents": [Cue(), ac]})

    media = cl.get_media()

    assert list(media) == [str(ac.id)]


def test_get_media_recurses_into_nested_cuelists():
    inner_ac = _audio_cue_with_media("nested.wav")
    inner = CueList({"contents": [inner_ac]})
    outer_ac = _audio_cue_with_media("top.wav")
    outer = CueList({"contents": [inner, outer_ac]})

    media = outer.get_media()

    assert set(media) == {str(inner_ac.id), str(outer_ac.id)}


# --- CueList.get_next_cue --------------------------------------------------------


def test_cuelist_get_next_cue_falls_back_to_its_own_target_when_empty():
    cl = CueList()
    other = Cue()
    cl.target = "linked"
    cl.target_object(other)
    cl.post_go = "pause"

    assert cl.get_next_cue() is other


def test_cuelist_get_next_cue_falls_back_when_every_content_is_disabled():
    disabled = Cue()
    disabled.enabled = False
    cl = CueList({"contents": [disabled]})
    other = Cue()
    cl.target = "linked"
    cl.target_object(other)
    cl.post_go = "pause"

    assert cl.get_next_cue() is other


def test_cuelist_get_next_cue_follows_the_first_enabled_cues_own_chain():
    """When ``post_go == 'pause'`` on the first enabled content cue, the
    result is *that cue's* ``_next_enabled()`` — its own target chain, not
    "the next item in ``contents``"."""
    first, first_target = Cue(), Cue()
    _linked(first, first_target, post_go="pause")
    cl = CueList({"contents": [first, Cue()]})

    assert cl.get_next_cue() is first_target


def test_cuelist_get_next_cue_recurses_through_the_first_cues_chain():
    """``first.post_go == 'continue'`` is what routes through
    ``first.get_next_cue()`` instead of returning ``first._next_enabled()``
    directly; the recursion then bottoms out at ``mid`` (``post_go ==
    'pause'``), which returns ``end``."""
    first, mid, end = Cue(), Cue(), Cue()
    _linked(first, mid, end, post_go="pause")
    first.post_go = "continue"
    cl = CueList({"contents": [first]})

    assert cl.get_next_cue() is end


def test_cuelist_get_next_cue_falls_back_when_the_first_cue_has_no_target():
    first = Cue()  # enabled, but no target of its own
    cl = CueList({"contents": [first]})
    other = Cue()
    cl.target = "linked"
    cl.target_object(other)
    cl.post_go = "pause"

    assert cl.get_next_cue() is other


# --- CueList.times ---------------------------------------------------------------


def test_times_is_empty_for_a_list_with_no_contents():
    assert CueList().times() == []


def test_times_returns_each_contents_offset_in_order():
    a, b = Cue(), Cue()
    a.offset = "00:00:05:00"
    b.offset = "00:00:10:00"
    cl = CueList({"contents": [a, b]})

    assert cl.times() == [a.offset, b.offset]
