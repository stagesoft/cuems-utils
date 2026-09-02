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
