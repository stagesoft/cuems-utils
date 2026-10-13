"""The repairability/default invariance check (T008, SC-005a).

G3 seeds every field of a descriptor's ``instance`` with a value satisfying
its type — but a seed is not a ``FieldDescriptor.default``, and it must not
move a single field's repairability classification (FR-026a; data-model.md
§3 invariant 6). This module makes that a one-call check rather than a
by-hand diff of two snapshot files.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from cuemsutils.xml.descriptor import SchemaDescriptor

#: A callable default's ``repr`` carries its process's memory address
#: (``<function new_uuid at 0x7f...>``), which differs on every run and would
#: make every callable-default field read as "changed" against a snapshot
#: captured in a previous process. Stripped so the comparison is about
#: *identity of meaning* (still a callable, same qualified name), not address.
_FUNCTION_ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+>$")


def _normalize(default_repr: str) -> str:
    return _FUNCTION_ADDRESS.sub(">", default_repr)

#: The six schemas, in the order `quickstart.md` §5 and T003 snapshot them.
SCHEMAS = (
    "script",
    "settings",
    "network_map",
    "project_mappings",
    "project_settings",
    "hardware_outputs",
)


def current_rows() -> list[tuple]:
    """``(schema, type name, field name, repairability value, repr(default))``
    for every field across all six schemas — the exact shape T003 wrote to
    ``snapshots/repairability-before.txt``."""
    sd = SchemaDescriptor()
    rows = [
        (schema, td.key.name, field.name, field.repairability.value, repr(field.default))
        for schema in SCHEMAS
        for td in sd.types(schema)
        for field in td.fields
    ]
    return sorted(rows)


def load_snapshot(path: Path) -> list[tuple]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        rows.append(ast.literal_eval(line))
    return rows


def diff_against_snapshot(path: Path) -> list[tuple[tuple, tuple]]:
    """Rows present in both the snapshot and today, paired up, where they
    differ. Returns ``[]`` when nothing changed — SC-005a's "zero" (FR-026a).

    Rows that exist only on one side (a field added or removed by some other
    requirement) are **not** reported here: this check is scoped to whether an
    *existing* field's classification moved, not to schema growth.
    """
    before = {(s, t, f): (r, _normalize(d)) for s, t, f, r, d in load_snapshot(path)}
    after = {(s, t, f): (r, _normalize(d)) for s, t, f, r, d in current_rows()}

    changed = []
    for key, before_value in before.items():
        after_value = after.get(key)
        if after_value is not None and after_value != before_value:
            changed.append((key + before_value, key + after_value))
    return changed
