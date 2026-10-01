# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T038 — no tuple, list, set or enum of device-class names (FR-010, SC-003).

The names below are the vocabulary this ratchet hunts. They live in the test,
not in the library. A collection that carries two or more of them is a class
list.

Exempt, by name: schema files (this walk is Python only; an ``.xsd`` is not a
Python collection), and the migration tool's tables of **old element names**
in ``reshape_devices.py``. Those spellings are being deleted. A further
exemption is a review item and has to be named here, not added quietly.

Not exempt, and worth stating because it looks like it should be: a single
element name such as ``Cue`` or ``CueOutput`` is not a device class and never
appears in ``_CLASS_NAMES``. ``cues/DmxCue.py``'s ``CUE_OUTPUT_ELEMENT`` is
one of those — one schema element name, which is the opposite of a class
list.
"""

from __future__ import annotations

import ast
from pathlib import Path

import cuemsutils

_CLASS_NAMES = frozenset({"audio", "video", "dmx"})

#: (filename, assignment target). Old element names, not a supported vocabulary.
_EXEMPT = frozenset({
    ("reshape_devices.py", "_OLD_DEFAULTS"),
    ("reshape_devices.py", "_OLD_DEFAULT_NAMES"),
    ("reshape_devices.py", "_OLD_DEVICE_ELEMENTS"),
    # Axis D's four tables, same status as the three above: each pairs an old
    # element name with the class that name *becomes*. The element names are
    # being deleted; the class values are there to be written into the
    # documents being rewritten, not to be consulted when reading one. Listed
    # individually rather than exempting the file, so a genuine class list
    # added to this module would still be caught.
    ("reshape_devices.py", "_OLD_CUES"),
    ("reshape_devices.py", "_OLD_CUE_OUTPUTS"),
    ("reshape_devices.py", "_OLD_OUTPUT_GROUPS"),
    ("reshape_devices.py", "_OLD_OUTPUT_GROUP_NAMES"),
})


def _string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _class_names_in(node: ast.AST) -> set[str]:
    found: set[str] = set()
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            value = _string(elt)
            if value in _CLASS_NAMES:
                found.add(value)
            elif isinstance(elt, (ast.List, ast.Tuple, ast.Set)):
                found |= _class_names_in(elt)
    elif isinstance(node, ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name in {"set", "frozenset", "list", "tuple"} and node.args:
            found |= _class_names_in(node.args[0])
    return found


def _is_enum(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "Enum":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Enum":
            return True
    return False


def _assigned_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def test_no_python_collection_enumerates_device_classes():
    root = Path(cuemsutils.__file__).parent
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            value = None
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                name = _assigned_name(node)
                if (path.name, name) in _EXEMPT:
                    continue
                value = node.value
            elif isinstance(node, ast.ClassDef) and _is_enum(node):
                names: set[str] = set()
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign) and stmt.value is not None:
                        constant = _string(stmt.value)
                        if constant in _CLASS_NAMES:
                            names.add(constant)
                        names |= _class_names_in(stmt.value)
                if len(names) >= 2:
                    offenders.append(f"{path.name}:{node.lineno} enum {node.name}")
                continue
            if value is None:
                continue
            found = _class_names_in(value)
            if len(found) >= 2:
                offenders.append(f"{path.name}:{node.lineno} {sorted(found)}")
    assert not offenders, "\n".join(offenders)
