"""Deliberately broken scripts, built once and used by five US1 tests.

Every one of them is built by writing **past** the property setters with
``dict.__setitem__`` or ``from_decoded``. That is not a trick to defeat the
model: it is the only way to reach the state the validation tier exists for.
The setters reject these values on assignment, so a script that carries one has
either been decoded from a document (where FR-026 keeps the semantic tier off)
or assembled key-by-key — which is what ``cuems-editor`` does.

Each helper returns a script that is broken in exactly **one** stated way, so a
test asserting "this violation is reported" cannot pass on a different one.

The valid base is ``build_generated_script()``, a fully-populated,
already-valid document (``descriptor.generate_script_example()``, T070) — not
a partially-built object of our own, since a test proving "invalid scripts
are rejected" against a base that was never valid proves nothing.
"""

from __future__ import annotations

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.CueOutput import VideoCueOutput
from cuemsutils.cues.VideoCue import VideoCue
from tests.support.capture_goldens import build_generated_script

#: A uuid whose *shape* the schema rejects — ``UuidType`` demands the uuid4
#: pattern. Structural (T1), and the cheapest violation to reach.
BAD_UUID = "not-a-uuid"

#: A canvas region every component of which is individually inside ``[0, 1]``
#: — so T1 passes — describing a rectangle that runs off the right edge.
#: Semantic (T2), and unreachable by any schema constraint: ``xs:assert``
#: cannot state a bound on the *sum* of two sibling elements.
OFF_CANVAS_REGION = {"x": 0.9, "y": 0.0, "width": 0.9, "height": 0.5}

CUSTOM_OUTPUT_NAME = "3d2b8f1a-1c4e-4a7b-9f2d-0a1b2c3d4e5f_custom_1"


def valid_script() -> CuemsScript:
    """The generated show, unmodified — the control for every case below."""
    return build_generated_script()


def structurally_invalid() -> CuemsScript:
    """One T1 violation: the script id is not a uuid4."""
    script = build_generated_script()
    dict.__setitem__(script, "id", BAD_UUID)
    return script


def structurally_invalid_three_ways() -> CuemsScript:
    """Three distinct T1 violations, on three different elements."""
    script = build_generated_script()
    dict.__setitem__(script, "id", BAD_UUID)
    dict.__setitem__(script.cuelist, "id", BAD_UUID)
    dict.__setitem__(script.cuelist.contents[0], "id", BAD_UUID)
    return script


def custom_video_output(script: CuemsScript) -> VideoCueOutput:
    """The generated show's one custom-mode video output.

    The generator already builds both modes — an alias output and a custom
    one carrying a valid ``canvas_region`` — so the semantic case below only
    has to move the region, not assemble an output from scratch.
    """
    video = next(c for c in script.cuelist.contents if isinstance(c, VideoCue))
    return next(o for o in video.outputs if "canvas_region" in o)


def semantically_invalid() -> CuemsScript:
    """One T2 violation: a video output whose canvas region leaves the canvas.

    Written with ``dict.__setitem__`` because both ``VideoCueOutput.__init__``
    and its setters run the containment check themselves — the *constructor*
    call is what pins two legacy corpus documents as ``to_objects: error``
    (FR-024d), and it must keep doing so.
    """
    script = build_generated_script()
    dict.__setitem__(custom_video_output(script), "canvas_region", dict(OFF_CANVAS_REGION))
    return script


def invalid_both_tiers() -> CuemsScript:
    """Two T1 violations and one T2 violation — for FR-004's ``>= 3``."""
    script = semantically_invalid()
    dict.__setitem__(script, "id", BAD_UUID)
    dict.__setitem__(script.cuelist, "id", BAD_UUID)
    return script


def repairable_violation() -> CuemsScript:
    """One T2 violation the descriptor classifies **repairable** (feature 008,
    ITEM E, US7) — a fade cue whose ``action_type`` is a valid enum member
    for *some* cue type but not for ``FadeCue`` specifically.

    ``fade_action_type`` is registered ``repairable=True``:
    ``FadeCue.REQ_ITEMS['action_type']`` is ``'fade_action'``, the one value
    the rule accepts, so substituting it *is* the repair. Deliberately not a
    ``target_value``/``curve_type`` violation: both of those are *also*
    constrained at the schema (T1) level by the same enumeration/range the T2
    rule checks, so a value that violates either would already fail T1 during
    decode and never reach this rule — a document on disk cannot demonstrate
    it. ``action_type`` is different: ``cms:ActionType`` is shared across
    every action-carrying cue type and permits values (``'play'``, ``'stop'``,
    ...) that are perfectly valid **XML**, just not valid **for a FadeCue** —
    which is exactly the cross-field constraint XSD cannot express and T2
    exists for.

    Contrasts with :func:`semantically_invalid`, whose
    ``canvas_region_containment`` violation is ``repairable=False`` — between
    the two, a test exercises both sides of FR-043/FR-044's boundary on the
    same load path (SC-020a) rather than assuming one implies the other.
    """
    from cuemsutils.cues.FadeCue import FadeCue

    script = build_generated_script()
    fade = next(c for c in script.cuelist.contents if isinstance(c, FadeCue))
    dict.__setitem__(fade, "action_type", "play")
    return script


def unrepairable_violation_reaching_the_t2_tier() -> CuemsScript:
    """One T2 violation the descriptor classifies **unrepairable**, that
    still reaches ``xml.validators.repair`` rather than failing at *decode*
    time (feature 008, ITEM E, US7).

    :func:`semantically_invalid`'s ``canvas_region_containment`` violation
    does not serve here: ``VideoCueOutputsType`` is an ``OPAQUE_TYPE``, so
    decoding it calls ``VideoCueOutput.__init__``, which runs the same
    containment check itself, *before* the object exists for ``repair`` to
    walk (FR-024d — the same reason ``test_semantic_not_on_read.py`` does not
    use it either). An action cue with no target is different: ``TargetType``
    accepts the empty string and decodes it to ``None`` without complaint
    (``_UuidAdapter.decode``), so the document decodes cleanly and it is
    ``action_target_required`` (``repairable=False`` — its own default *is*
    ``None``, the exact value it rejects) that catches it, downstream, on the
    load path this feature adds.
    """
    from cuemsutils.cues.ActionCue import ActionCue

    script = build_generated_script()
    action = next(c for c in script.cuelist.contents if isinstance(c, ActionCue))
    dict.__setitem__(action, "action_target", None)
    return script


def write_bypassing_validation(script: CuemsScript, path) -> None:
    """Write ``script`` to ``path`` **without** going through ``save()``'s own
    T1/T2 check, which would refuse every fixture in this module by design.

    Every fixture above is invalid on purpose, so it has to reach disk by the
    same tree-building machinery ``save()`` itself uses (``build_tree`` /
    ``write_tree``), stopping one step short of the validation ``save()``
    layers on top.
    """
    from cuemsutils.xml.documents import build_tree, write_tree

    write_tree(build_tree(script, "script"), path)
