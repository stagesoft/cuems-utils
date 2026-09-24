# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""M1 — the bundled schemas are pinned, and changing one is a deliberate act.

**Re-based 2026-09-23** (`specs/planning/etc-cuems-first-install.md` §11). What
this file pins has changed; what it is *for* has not.

Until now it pinned each schema's **Phase-1-end content** and asserted that
feature 008 ITEM E's ``doc_version`` attribute was the only textual difference
since. That was right for 008, when the schemas were meant to hold still, and it
did its job. The current work inverts the premise: leaving the XML in a clean,
durable state is the whole point, so sanctioned schema edits are the norm. Two
had already landed — ``hardware_outputs.xsd``'s rename and
``project_mappings.xsd``'s ``NodeMappingType`` — each handled by dropping the
schema from the asserted set, which had taken it to four pinned and two
excluded. A third would have left it guarding almost nothing.

So the baseline is re-based on **current** content, with a meaning of its own:

    These are the schemas as the rebuild left them. A change to any of them is
    a deliberate act that updates this file in the same commit.

The pin does not prevent change — it makes change **visible and attributable**,
which is the property worth keeping. A schema edit nobody meant to make fails
here; one that was meant fails here too, and is answered by updating the hash
beside the edit, in the same commit, where a reviewer sees both.

The pre-008 and Phase-1-end hashes are not carried forward. They were never
asserted — only their keys were used, to build the set of schema names — and git
history holds them.

**Why a hash and not a golden copy.** A byte comparison against a checked-in
duplicate of each schema would pin the same thing while creating a second copy
to keep in step, which is the duplication ``test_schema_name_overlap.py`` exists
to catch elsewhere.
"""

from __future__ import annotations

import hashlib
import re

from tests.support.corpus import REPO_ROOT

SCHEMAS_DIR = REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas"

#: Each bundled schema's content, as of the re-base. **Update an entry in the
#: same commit as the schema edit it describes**, with the reason in the commit
#: message — that pairing is the whole mechanism.
#:
#: Recorded 2026-09-23, after: ``outputs.xsd`` -> ``hardware_outputs.xsd`` with
#: its root element and type renamed (``CuemsHardwareOutputs``,
#: ``HardwareOutputsType``); ``project_mappings.xsd``'s ``NodeType`` ->
#: ``NodeMappingType``; and rc16's F3/F4 element drops —
#: ``settings.xsd`` loses ``audio_cards``/``universes``, ``hardware_outputs.xsd``
#: loses ``default_video_output``/``default_audio_output``, each with a
#: conversion registered for its version step.
#:
#: Updated 2026-09-24 for ``settings.xsd`` and ``hardware_outputs.xsd``: both
#: carried a ``doc_version`` comment reading *"this schema stays at version 1"*
#: while sitting at version **2**, which F3/F4 had moved them to. A comment, so
#: no document on disk is affected — but it is precisely the drift this pin
#: exists to surface, and the two hashes moving beside the correction is the
#: mechanism working rather than an inconvenience.
CURRENT_SCHEMA_HASHES = {
    "hardware_outputs.xsd": "fccbe9d8f6adbb122e46334ebf1c7548755ca27d95b07e8328beacd899b63cad",
    "network_map.xsd": "4411c7a23f71dc712bdf278c6629c0df9635d857ad62d58f9a378ada51865b67",
    "project_mappings.xsd": "b8446d7f5c21ea511ae2092d608fc1f62aa42a183ffa1a9dc2ec77c29708380d",
    "project_settings.xsd": "26a607758210057e11b79b1b2b023e6bc6086a0e250fb6b53bfb5ffadb897ac9",
    "script.xsd": "3912e37113d2783c610b449881c6ee1931312baaa486f7744d92270dd845e818",
    "settings.xsd": "a51a85a9a13262387470570d3dd8540b6ae258a6baae2b7d3bb514864967cea6",
}

ALL_SCHEMA_NAMES = set(CURRENT_SCHEMA_HASHES)

#: The one line ITEM E added to every root complex type (data-model.md §1). A
#: regex rather than an exact string: each schema's existing indentation differs
#: (two spaces vs four), and the line's *whitespace* is not what this pins.
_DOC_VERSION_ATTRIBUTE_RE = re.compile(
    r'[ \t]*<xs:attribute name="doc_version" type="xs:positiveInteger" use="optional"\s*/>\n?'
)


def _hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_every_schema_matches_its_recorded_hash():
    """A schema changed without this file changing with it.

    The failure names the schema and nothing else, deliberately: the question a
    reader needs answered is *which* one moved, and the diff is in the same
    commit.
    """
    mismatched = sorted(
        name
        for name, expected in CURRENT_SCHEMA_HASHES.items()
        if _hash(SCHEMAS_DIR / name) != expected
    )
    assert not mismatched, (
        f"schema(s) whose content no longer matches CURRENT_SCHEMA_HASHES: {mismatched}. "
        "If the edit was intended, update the hash in this commit. If it was not, this "
        "is the change nobody meant to make."
    )


def test_every_schema_declares_doc_version_exactly_once():
    """Independent of any baseline, which is why it survives the re-base intact.

    ITEM E's version marker is what makes convert-on-read possible at all; a
    schema that loses it, or grows a second one, breaks the version probe before
    any conversion is reached.
    """
    missing_or_duplicated = []
    for name in sorted(ALL_SCHEMA_NAMES):
        text = (SCHEMAS_DIR / name).read_text()
        if len(_DOC_VERSION_ATTRIBUTE_RE.findall(text)) != 1:
            missing_or_duplicated.append(name)
    assert not missing_or_duplicated, (
        f"schema(s) without exactly one doc_version attribute: {missing_or_duplicated}"
    )


def test_only_six_schemas_are_bundled():
    """A seventh schema silently added would escape every check above."""
    assert {p.name for p in SCHEMAS_DIR.glob("*.xsd")} == ALL_SCHEMA_NAMES


def test_the_pin_covers_every_bundled_schema():
    """The two sets above are the same set, stated positively.

    ``test_only_six_schemas_are_bundled`` compares the directory against
    ``ALL_SCHEMA_NAMES``, which is *derived from* the hash table — so a schema
    dropped from the table and from the directory together would pass both.
    This is the assertion that does not.
    """
    assert len(CURRENT_SCHEMA_HASHES) == 6
    assert {p.name for p in SCHEMAS_DIR.glob("*.xsd")} == set(CURRENT_SCHEMA_HASHES)
