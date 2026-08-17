# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

import cuemsutils.cues  # noqa: F401 — forces every public cue module to
from cuemsutils.create_script import create_script

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


# --- feature 005 addition (T038, FR-022) ----------------------------------
#
# Additive only: no assertion above changes.


def test_the_returned_template_ships_with_its_identifiers_cleared():
    """Change 3's consumer-visible delta (FR-019 row 3, FR-022, SC-009).

    ``create_script`` clears the script and cue-list ids on its way out, and
    they used to come back **random**: ``Uuid(None)`` mints a uuid4 for any
    falsy argument, so "clear this field" assigned a fresh id instead. Three of
    the five cue identifiers already arrived empty; these two now match.

    This is the one change in feature 005 that alters a payload the Angular UI
    renders. ``project_load`` is untouched — that contract is
    ``test_ui_payload_contract.py``.
    """
    from cuemsutils.create_script import create_script

    template = create_script()

    assert template["id"] is None
    assert template["CueList"]["id"] is None
    for index, cue in enumerate(template["CueList"]["contents"]):
        assert cue["id"] is None, f"contents[{index}] kept an id"


def test_clearing_the_template_leaves_everything_else_intact():
    """The delta is *exactly* the identifiers, and nothing else (SC-009)."""
    from cuemsutils.create_script import create_script

    template = create_script()

    assert template["name"] == "Test Script"
    assert template["description"] == "This is a test script"
    assert len(template["CueList"]["contents"]) == 5
    assert template["ui_properties"] == {"warning": 0}

    # Media ids are *not* cleared — they are content, not template identity.
    media = [c["Media"] for c in template["CueList"]["contents"] if "Media" in c]
    assert media, "the template carries no media to check"
    assert all(m["id"] is not None for m in media)


def test_the_generated_golden_is_insulated_from_the_change(tmp_path):
    """Research R8, verified rather than trusted.

    ``capture_goldens._make_template_writable`` restamps the ids
    ``create_script`` clears, *before* serialization — the template cannot be
    written otherwise, because ``script.xsd`` requires uuid4 ids. So change 3
    leaves ``tests/golden/generated/create_script.xml`` byte-identical, which
    is what lets FR-020's "zero goldens change" hold through a change that
    alters generated content.
    """
    from tests.support import roundtrip as rt
    from tests.support.corpus import DOCUMENTS

    doc = next(d for d in DOCUMENTS if d.schema == "script")
    produced = rt.normalize_uuids(rt.write_bytes(doc, rt.build_generated_script()))
    assert produced == rt.golden_bytes("generated/create_script.xml")
