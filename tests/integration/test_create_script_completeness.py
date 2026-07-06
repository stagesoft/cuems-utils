# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

import cuemsutils.cues  # noqa: F401 — forces every public cue module to
                        # be imported so Cue.__subclasses__() sees them.
from cuemsutils.cues import CueList
from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.MediaCue import MediaCue
from cuemsutils.create_script import create_script


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


def test_create_script_covers_every_cue_subclass():
    # Exempt: intermediate/container types that should not appear as
    # leaf cues in the template.
    #   - CueList is the container, not a leaf cue.
    #   - MediaCue is abstract-by-convention; concrete media cues
    #     (AudioCue, VideoCue) extend it and appear instead.
    #     (It is not exported from cuemsutils/cues/__init__.py.)
    exempt = {CueList, MediaCue}

    expected = _collect_cue_subclasses(Cue) - exempt

    script = create_script()
    present = {type(c) for c in _walk_cuelist(script['CueList'])}

    missing = expected - present
    assert not missing, (
        f"create_script() is missing representative(s) for: "
        f"{sorted(c.__name__ for c in missing)}. "
        f"Add an instance to create_script.py so the frontend's "
        f"initial_template payload stays complete. New cue classes "
        f"must also be wired into cuemsutils/cues/__init__.py for "
        f"this test to see them."
    )
