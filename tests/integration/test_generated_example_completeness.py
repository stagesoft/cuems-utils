# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

"""Completeness of the descriptor-generated example script (feature 008, T074).

Ported from the retired script-template function's own completeness tests, kept as an
*independent* check rather than trusting
``descriptor._assert_every_choice_member_has_a_builder``'s own internal
guard — a generator that quietly stopped enforcing its own completeness
should still be caught here.
"""

import cuemsutils.cues  # noqa: F401 — forces every public cue module to
from cuemsutils.xml.descriptor import generate_script_example

# be imported so Cue.__subclasses__() sees them.
from cuemsutils.cues import CueList
from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.MediaCue import MediaCue


def _collect_cue_subclasses(root):
    seen = set()
    stack = [root]
    while stack:
        cls = stack.pop()
        for sub in cls.__subclasses__():
            if sub not in seen:
                seen.add(sub)
                stack.append(sub)
    return seen


def _walk_cuelist(cuelist):
    for item in cuelist['contents']:
        yield item
        if isinstance(item, CueList):
            yield from _walk_cuelist(item)


def test_generated_example_covers_every_cue_subclass():
    # Exempt: intermediate/container types that should not appear as
    # leaf cues in the example.
    #   - CueList is the container, not a leaf cue.
    #   - MediaCue is abstract-by-convention; concrete media cues
    #     (AudioCue, VideoCue) extend it and appear instead.
    #     (It is not exported from cuemsutils/cues/__init__.py.)
    exempt = {CueList, MediaCue}

    expected = _collect_cue_subclasses(Cue) - exempt

    script = generate_script_example()
    present = {type(c) for c in _walk_cuelist(script['CueList'])}

    missing = expected - present
    assert not missing, (
        f"generate_script_example() is missing representative(s) for: "
        f"{sorted(c.__name__ for c in missing)}. "
        f"Add a builder to descriptor._script_cue_builders. New cue classes "
        f"must also be wired into cuemsutils/cues/__init__.py for "
        f"this test to see them."
    )


def test_generated_example_carries_real_content():
    """No blanking step exists to undo (FR-033) — every identifier the
    generator sets is populated as returned, including the script and
    cue-list ids that the retired hand-written function used to clear on
    the way out."""
    script = generate_script_example()

    assert script["name"]
    assert script["id"] is not None
    assert script["CueList"]["id"] is not None
    assert script["CueList"]["contents"]
    for index, cue in enumerate(script["CueList"]["contents"]):
        assert cue["id"] is not None, f"contents[{index}] carries no id"

    media = [c["Media"] for c in script["CueList"]["contents"] if "Media" in c]
    assert media, "the example carries no media to check"
    assert all(m["id"] is not None for m in media)
