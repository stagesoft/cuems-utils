# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""F2 — a fact is declared in exactly one schema; elsewhere it is referenced.

`specs/planning/etc-cuems-first-install.md` §8.3. The six schemas share one
namespace, so a name declared twice is either a deliberate cross-document
**reference** or an accident waiting to misbind. Audit finding **X14** was the
accident: ``script.xsd`` and what is now ``hardware_outputs.xsd`` both declared
``OutputsType`` with different content, which is the structural half of why the
second schema was never loadable. It was found by reading, years late, and fixed
in rc16.

**This file is that reading, made mechanical.** It is a ratchet, not a clean
sheet: the overlaps that exist today are enumerated below with a verdict each,
and anything *new* fails. Its first run (2026-09-23) turned up two live
X14-class defects. ``NodeType`` was resolved the same day — ``project_mappings``'
became ``NodeMappingType`` — and its entry left this file, which is how a fix is
completed here. ``UuidType`` remains, recorded as debt rather than blessed,
because resolving it invalidates every node identity in the field (§9).

**Declarations are read as authored**, by regex over the source, rather than
through a loaded schema object. Two reasons: most element declarations here are
local rather than global, so a loaded object would need a full walk to see them;
and the collision exists at the level an author writes and can fix. The same
choice is made by ``test_schema_scope.py``'s ``doc_version`` check.

**Content is compared whitespace-normalised.** ``script.xsd`` indents with two
spaces and the rest with four, and indentation is not what this pins.
"""

from __future__ import annotations

import collections
import re

import pytest

from tests.support.corpus import REPO_ROOT

SCHEMAS_DIR = REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas"

#: Element names that legitimately appear in several schemas because they are
#: **references by join key**, which is what F2 prescribes rather than forbids.
#: The node ``uuid`` is the cluster-wide key; a port ``id`` is the key within a
#: node's inventory. A document that needs to point at one of these says its
#: name — that is the reference working as designed.
JOIN_KEYS = frozenset({
    "uuid",
    "mac",
    "node",
    "id",
    "output",
})

#: Element names that collide only as *words*. Different meaning in each schema,
#: no shared fact, nothing to de-duplicate. Allowlisted so the report stays
#: readable — a check that cries wolf on ``name`` gets muted by its readers.
GENERIC_ELEMENT_NAMES = frozenset({
    "name",
    "value",
    "x",
    "y",
    "width",
    "height",
    "outputs",
    "canvas_region",
    "default_audio_output",
    "default_video_output",
})

#: Named types declared in several schemas with **identical** content.
#:
#: Not defects today, and not harmless either: nothing keeps them in step, so
#: the first one to gain a facet becomes an X14 silently. That is what
#: :func:`test_known_identical_duplicates_have_not_diverged` is for — these may
#: stay duplicated, but they may not *drift*.
KNOWN_IDENTICAL_DUPLICATES = {
    "CanvasRegionType": ("project_mappings", "script"),
    "BoolType": ("network_map", "script", "settings"),
    "DateType": ("script", "settings"),
    "NonEmptyString": ("network_map", "project_mappings", "project_settings", "settings"),
    "PositiveUnitFloat": ("project_mappings", "script"),
    "UnitFloat": ("project_mappings", "script"),
}

#: Named types declared in several schemas with **different** content — the X14
#: pattern, live. Recorded with the verdict so the debt is enumerated rather
#: than blessed; see §8.5 for the order these are resolved in.
#:
#: Removing an entry here is how a fix is *completed*: while a name is listed,
#: :func:`test_the_allowlist_has_no_stale_entries` requires it to still collide.
KNOWN_DIVERGENT_DECLARATIONS = {
    "UuidType": {
        "schemas": ("network_map", "script"),
        "verdict": (
            "network_map's accepts ANY uuid version, case-insensitive, shape "
            "only -- deliberately, per feature 007 research R2. script's "
            "requires uuid4 specifically (version nibble 4, variant [89ab]), "
            "lowercase, exactly 36 characters. The divergence is semantic, not "
            "cosmetic: production node identities are uuid1 (MAC-derived) and "
            "uuid5, which the first accepts and the second would reject. "
            "RESOLUTION DECIDED 2026-09-23: uuid4 project-wide, so script's is "
            "the surviving definition and network_map's narrows to match. That "
            "narrowing invalidates every node identity in the field, so it is a "
            "rule-4 file-format migration and CANNOT land before cuems-init-node "
            "exists to perform the cross-document re-mint -- see planning "
            "section 9. This entry stays until it does."
        ),
    },
}

_DECL_PATTERNS = {
    "complexType": re.compile(r'<xs:complexType name="([^"]+)">(.*?)</xs:complexType>', re.S),
    "simpleType": re.compile(r'<xs:simpleType name="([^"]+)">(.*?)</xs:simpleType>', re.S),
}
_ELEMENT_DECL = re.compile(r'<xs:element name="([^"]+)"')


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _named_type_declarations() -> dict[str, dict[str, str]]:
    """``type name -> {schema: normalised body}``, complex and simple alike.

    Both kinds share one symbol space in XSD, so a complex type and a simple
    type of the same name would collide too; they are collected together for
    that reason rather than kept apart for tidiness.
    """
    found: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for path in sorted(SCHEMAS_DIR.glob("*.xsd")):
        text = path.read_text()
        for pattern in _DECL_PATTERNS.values():
            for match in pattern.finditer(text):
                found[match.group(1)][path.stem] = _normalise(match.group(2))
    return found


def _element_declarations() -> dict[str, set[str]]:
    found: dict[str, set[str]] = collections.defaultdict(set)
    for path in sorted(SCHEMAS_DIR.glob("*.xsd")):
        for name in _ELEMENT_DECL.findall(path.read_text()):
            found[name].add(path.stem)
    return found


def test_no_unrecorded_type_name_is_declared_in_two_schemas():
    """The X14 check. A new name in two schemas fails here, at the commit that
    introduces it, rather than years later by reading."""
    recorded = set(KNOWN_IDENTICAL_DUPLICATES) | set(KNOWN_DIVERGENT_DECLARATIONS)
    unrecorded = {
        name: sorted(per_schema)
        for name, per_schema in _named_type_declarations().items()
        if len(per_schema) > 1 and name not in recorded
    }
    assert not unrecorded, (
        "type name(s) declared in more than one schema and not recorded in this "
        f"file: {unrecorded}. Either it is a genuine reference -- then say so "
        "here -- or it is an X14: same name, same namespace, different content."
    )


def test_no_unrecorded_element_name_is_declared_in_two_schemas():
    allowed = JOIN_KEYS | GENERIC_ELEMENT_NAMES
    unrecorded = {
        name: sorted(schemas)
        for name, schemas in _element_declarations().items()
        if len(schemas) > 1 and name not in allowed
    }
    assert not unrecorded, (
        f"element name(s) declared in more than one schema: {unrecorded}. Add to "
        "JOIN_KEYS if it is a reference by key, to GENERIC_ELEMENT_NAMES if the "
        "collision is only a word, or de-duplicate the fact."
    )


@pytest.mark.parametrize("type_name", sorted(KNOWN_IDENTICAL_DUPLICATES))
def test_known_identical_duplicates_have_not_diverged(type_name):
    """Duplication is tolerated here; **drift** is not.

    Nothing keeps these copies in step, so the moment one gains a facet the pair
    becomes an X14 with no announcement. This is the announcement.
    """
    per_schema = _named_type_declarations()[type_name]
    bodies = set(per_schema.values())
    assert len(bodies) == 1, (
        f"{type_name} is declared in {sorted(per_schema)} and the copies have "
        "DIVERGED -- same name, same namespace, different content. That is a new "
        "X14. Either re-converge them or move the entry to "
        "KNOWN_DIVERGENT_DECLARATIONS with a verdict."
    )


@pytest.mark.parametrize("type_name", sorted(KNOWN_DIVERGENT_DECLARATIONS))
def test_known_divergent_declarations_are_still_divergent(type_name):
    """Debt is enumerated, not certified.

    A fix is complete when its entry leaves this file. While the entry is here
    the collision must still be real -- otherwise the allowlist would quietly
    keep asserting a defect that no longer exists, which is how a suite ends up
    green *because* it pins the wrong thing.
    """
    recorded = KNOWN_DIVERGENT_DECLARATIONS[type_name]
    per_schema = _named_type_declarations()[type_name]

    assert sorted(per_schema) == sorted(recorded["schemas"]), (
        f"{type_name} is now declared in {sorted(per_schema)}, not "
        f"{sorted(recorded['schemas'])} as recorded. Update the entry."
    )
    assert len(set(per_schema.values())) > 1, (
        f"{type_name}'s declarations no longer differ -- the collision is "
        "resolved. Remove its entry from KNOWN_DIVERGENT_DECLARATIONS (and, if "
        "the name is still shared deliberately, record it as an identical "
        "duplicate instead)."
    )


def test_the_allowlist_has_no_stale_entries():
    """Every recorded name must still be declared in more than one schema.

    An entry for a name that no longer overlaps is an instruction to a future
    reader that is simply false, and it hides the fact that the overlap was
    already dealt with.
    """
    overlapping = {
        name for name, per_schema in _named_type_declarations().items() if len(per_schema) > 1
    }
    stale = (set(KNOWN_IDENTICAL_DUPLICATES) | set(KNOWN_DIVERGENT_DECLARATIONS)) - overlapping
    assert not stale, (
        f"recorded name(s) that no longer overlap: {sorted(stale)}. Remove the "
        "entries -- the overlap they describe is gone."
    )
