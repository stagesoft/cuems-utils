"""Coercion-table resolution (T005).

The table is where feature 005 puts coercion, so a defect here does not raise —
it produces objects whose internal types depend on how they were made, which is
precisely the condition the feature exists to remove. Every assertion below
guards a failure that is silent by nature.

Asserted through ``cls.coercion_table()`` rather than
``coercion.adapter_table(cls)``: the classmethod is what production calls, and
testing the resolver while the model calls the classmethod tests the wrong
thing.
"""

from __future__ import annotations

import pytest

from cuemsutils import coercion
from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.CueList import CueList
from cuemsutils.cues.CueOutput import AudioCueOutput, DmxCueOutput, VideoCueOutput
from cuemsutils.cues.DmxCue import DmxChannel, DmxCue, DmxScene, DmxUniverse
from cuemsutils.cues.FadeCue import FadeCue
from cuemsutils.cues.FadeProfile import FadeFunctionParameter, FadeProfile
from cuemsutils.cues.MediaCue import Media, MediaCue, Region
from cuemsutils.cues.VideoCue import VideoCue
from cuemsutils.helpers import CuemsDict
from cuemsutils.xml.adapters import PASSTHROUGH
from cuemsutils.xml.registry import get_registry

#: Every model class bound in the script registry, except ``CuemsScript`` —
#: which is not a ``CuemsDict`` until T017 and so has no classmethod to call
#: yet. It is covered by ``test_the_script_root_resolves_through_its_path_binding``.
BOUND_MODELS = [
    Cue,
    CueList,
    AudioCue,
    VideoCue,
    MediaCue,
    ActionCue,
    FadeCue,
    DmxCue,
    Media,
    Region,
    AudioCueOutput,
    VideoCueOutput,
    DmxCueOutput,
    DmxScene,
    DmxUniverse,
    DmxChannel,
    FadeProfile,
    FadeFunctionParameter,
]


@pytest.mark.parametrize("model", BOUND_MODELS, ids=lambda m: m.__name__)
def test_every_bound_model_resolves_a_table_from_the_schema(model):
    """The table's keys are the schema's field names, not a hand-written list."""
    spec = get_registry("script").spec_for_model(model)
    assert spec is not None, f"{model.__name__} has no registry binding"

    table = model.coercion_table()
    declared = {field.name for field in spec.fields if field.name}
    assert set(table) == declared


@pytest.mark.parametrize("model", BOUND_MODELS, ids=lambda m: m.__name__)
def test_the_table_is_built_once_per_class(model):
    """SC-PERF-003 — per class, never per object.

    Identity, not equality: a table rebuilt on every construction would compare
    equal and cost a schema resolution per object, which is the difference
    between 19 resolutions and one per cue in a 1000-cue script.
    """
    assert model.coercion_table() is model.coercion_table()


def test_sibling_subclasses_get_distinct_tables():
    """The MRO-inheritance trap (T004).

    Caching the table as ``cls._table = …`` would put it on whichever class was
    constructed first and hand it to every sibling through the MRO —
    ``AudioCue``'s adapters coercing ``VideoCue``'s fields, silently, and only
    for the fields the two do not share. A dict keyed on the class object cannot
    do that, and this is the assertion that says so.
    """
    audio, video = AudioCue.coercion_table(), VideoCue.coercion_table()
    assert audio is not video

    # Not merely distinct objects — distinct *content*, so the test fails on a
    # cache that hands out equal-but-copied tables. The two share 16 of 17
    # fields, which is what makes the MRO trap survivable long enough to ship:
    # only ``master_vol`` and ``opacity`` would misresolve.
    assert "master_vol" in audio and "master_vol" not in video
    assert "opacity" in video and "opacity" not in audio


def test_a_class_with_no_binding_gets_an_empty_table():
    """An unbound class coerces nothing, rather than raising.

    ``CuemsDict`` itself is the case: it is the base, not a bound type. Call
    sites read the table with ``.get(name, PASSTHROUGH)``, so an empty table
    means every field passes through untouched — today's behaviour for anything
    the registry does not describe.
    """
    table = CuemsDict.coercion_table()
    assert table == {}
    assert table.get("anything", PASSTHROUGH) is PASSTHROUGH


def test_the_script_root_resolves_through_its_path_binding():
    """``CuemsScript`` is bound by **path**, not by type qname (research R3).

    A resolver scanning only ``bound_type_names`` returns ``None`` here, and the
    root would get an empty table — its ``id``, ``created`` and ``modified``
    silently uncoerced while every cue below it coerced correctly. That is the
    hole T004a's two-map scan closes, and it is invisible to every other test
    because the root is never a list member on the encode path.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    table = coercion.adapter_table(CuemsScript)
    assert table, "the script root resolved no adapters"
    assert type(table["id"]).__name__ == "_UuidAdapter"


def test_media_duration_is_not_coerced():
    """FR-009b — ``MediaType.duration`` is a string, and stays one.

    Two different fields share the name: ``FadeCueType.duration`` is a
    ``CTimecodeType`` emitted as a wrapped child, while ``MediaType.duration``
    is a ``TimecodeType`` — a restricted string — emitted as bare text, whose
    getter contract is ``str`` (``test_media_duration.py``). Coercing it would
    change the emitted element for every media document.

    The schema-derived table gets this right with no special case, because
    ``TimecodeType`` binds to a passthrough-decoding adapter. This test pins
    that it stays that way.
    """
    duration = Media.coercion_table()["duration"]
    assert duration.decode("00:00:01.000") == "00:00:01.000"
    assert isinstance(duration.decode("00:00:01.000"), str)

    fade = FadeCue.coercion_table()["duration"]
    assert type(fade).__name__ == "_CTimecodeAdapter"


def test_a_class_bound_in_two_registries_raises(monkeypatch):
    """The guard that fails loudly in 006 (T004).

    ``adapter_table`` takes no schema argument, which is correct only while
    every model class is bound in exactly one registry. The five configuration
    registries bind everything to ``GENERIC`` today, so nothing resolves in
    them; feature 006 gives configuration documents model classes and the
    assumption dies. Resolving to whichever registry cached first would coerce
    objects with another schema's adapters — a wrong-but-plausible result, the
    worst kind. It raises instead, naming both schemas.
    """

    class Doubly(CuemsDict):
        pass

    spec = get_registry("script").spec_for_model(AudioCue)

    def fake_spec_for_model(self, model):
        return spec if model is Doubly else None

    from cuemsutils.xml import registry as registry_module

    monkeypatch.setattr(
        registry_module.SchemaRegistry, "spec_for_model", fake_spec_for_model
    )
    coercion.clear_cache()

    with pytest.raises(coercion.AmbiguousBindingError) as excinfo:
        Doubly.coercion_table()

    message = str(excinfo.value)
    assert "Doubly" in message
    # Both schemas named — "it is ambiguous" without saying between what is not
    # an actionable error.
    assert "script" in message and "project_mappings" in message

    coercion.clear_cache()
