"""T004 — the pre-008 corpus is retained and still well-formed.

Load-bearing, not pedantry. After T013, T018 and T066, the documents under
``tests/data/corpus/pre-008/`` are **deliberately invalid** against the current
schemas: they carry the old-shape ``<duration>TC</duration>`` text, the deleted
fade-profile surface, and (once fixtures are added) the retired ``fade_in``/
``fade_out`` action types. A guard that ran schema **validation** here would go
red for exactly the reason this corpus exists (FR-011) — so this test asserts
only well-formedness, via stdlib ``ElementTree``, never ``xmlschema``.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from tests.support.corpus import PRE_008_ROOT


def _pre008_xml_files() -> list:
    return sorted(PRE_008_ROOT.rglob("*.xml"))


def test_pre008_corpus_is_non_empty():
    assert _pre008_xml_files(), (
        f"{PRE_008_ROOT} holds no documents — the retained originals (T003) "
        f"are missing or were removed"
    )


def test_pre008_documents_are_well_formed():
    """Parses, and never validates — see the module docstring."""
    failures = []
    for path in _pre008_xml_files():
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            failures.append(f"{path.relative_to(PRE_008_ROOT)}: {exc}")
    assert not failures, "malformed pre-008 fixture(s):\n" + "\n".join(failures)
