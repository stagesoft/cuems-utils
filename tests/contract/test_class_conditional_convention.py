# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T009 — the five authoring rules, against every bundled schema.

Nothing is conditional yet, so each rule is vacuous and the test passes.
A later edit that breaks a rule fails here.

Rule 5 (class uniqueness) binds the containers that replace a
``maxOccurs="1"`` element: ``device`` and ``player``. It does not bind
``Cue`` or ``CueOutput``. A cue list holds many cues of one class, and a
cue holds many outputs of one class. FR-013 names devices, the root
defaults and players.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from tests.support.corpus import REPO_ROOT

XS = "{http://www.w3.org/2001/XMLSchema}"
SCHEMAS = REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas"
_CLASS_TEST = re.compile(r"^@class='([^']+)'$")
_UNIQUE = {
    "device": "count(device) = count(distinct-values(device/@class))",
    "player": "count(player) = count(distinct-values(player/@class))",
}
_REPEATED_ON_PURPOSE = frozenset({"Cue", "CueOutput"})


def _local(type_name: str | None) -> str | None:
    if not type_name:
        return None
    return type_name.split(":")[-1]


def _parent_map(root: ET.Element) -> dict:
    return {child: parent for parent in root.iter() for child in parent}


def _enclosing_type(element: ET.Element, parents: dict) -> ET.Element | None:
    node = element
    while node in parents:
        node = parents[node]
        if node.tag == f"{XS}complexType":
            return node
    return None


def _declared_type(root: ET.Element, name: str | None) -> ET.Element | None:
    if name is None:
        return None
    for node in root.iter(f"{XS}complexType"):
        if node.get("name") == name:
            return node
    return None


def _has_required_class(complex_type: ET.Element | None, root: ET.Element, seen: set) -> bool:
    if complex_type is None or id(complex_type) in seen:
        return False
    seen.add(id(complex_type))
    for attr in complex_type.iter(f"{XS}attribute"):
        if attr.get("name") == "class" and attr.get("use") == "required":
            type_name = _local(attr.get("type")) or ""
            if type_name == "NonEmptyString":
                return True
    extension = complex_type.find(f".//{XS}extension")
    if extension is not None:
        return _has_required_class(
            _declared_type(root, _local(extension.get("base"))), root, seen
        )
    return False


def _content_elements(complex_type: ET.Element) -> list[ET.Element]:
    elements = []
    for node in list(complex_type):
        if node.tag in (f"{XS}sequence", f"{XS}choice", f"{XS}all"):
            elements.extend(child for child in list(node) if child.tag == f"{XS}element")
    return elements


def _normalise(text: str | None) -> str:
    return " ".join((text or "").split())


def test_every_schema_follows_the_class_conditional_convention():
    failures = []
    for path in sorted(SCHEMAS.glob("*.xsd")):
        root = ET.parse(path).getroot()
        parents = _parent_map(root)
        for element in root.iter(f"{XS}element"):
            alternatives = [child for child in list(element) if child.tag == f"{XS}alternative"]
            if not alternatives:
                continue
            name = element.get("name")
            where = f"{path.name}:{name}"
            tests = [alt.get("test") for alt in alternatives]
            if tests[-1] is not None:
                failures.append(f"{where}: the last alternative is not unconditional")
            for test in tests[:-1]:
                if test is None or _CLASS_TEST.fullmatch(test.strip()) is None:
                    failures.append(f"{where}: test {test!r} is not exactly @class='VALUE'")
            declared = _declared_type(root, _local(element.get("type")))
            if not _has_required_class(declared, root, set()):
                failures.append(f"{where}: the base type does not require class as NonEmptyString")
            container = _enclosing_type(element, parents)
            if container is None:
                failures.append(f"{where}: no enclosing complex type")
                continue
            siblings = _content_elements(container)
            singles = [
                sib.get("name")
                for sib in siblings
                if sib.get("maxOccurs") in (None, "1") and sib.get("minOccurs") in (None, "1")
            ]
            repeated = [
                sib.get("name")
                for sib in siblings
                if sib.get("maxOccurs") not in (None, "1")
            ]
            group = next(
                (node for node in list(container) if node.tag in (f"{XS}sequence", f"{XS}choice")),
                None,
            )
            group_repeated = group is not None and group.get("maxOccurs") not in (None, "1")
            if singles and (repeated or group_repeated):
                failures.append(
                    f"{where}: the container mixes single children {singles} with a repeated one"
                )
            asserts = [_normalise(node.get("test")) for node in container.findall(f"{XS}assert")]
            if name in _UNIQUE:
                expected = _UNIQUE[name]
                if expected not in asserts:
                    failures.append(f"{where}: missing uniqueness assert {expected!r}")
            if name in _REPEATED_ON_PURPOSE and any("distinct-values" in test for test in asserts):
                failures.append(f"{where}: a cue list must not assert class uniqueness")
    assert not failures, "\n".join(failures)
