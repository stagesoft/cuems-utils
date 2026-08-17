"""Contract C3a (T015a) — semantic round-trip: ``load(save(x)) == load(x)``.

The durable guarantee, and the one that survives things byte-identity cannot:
reformatting, minification, or a storage layer that rewrites the XML without
changing its meaning.

**C3a does not replace C1.** Object equality is *blind* to element order within
order-free (`xs:all`) content models — a reordered ``CuemsScript`` root loads to
an equal object, which is exactly the defect research R2 identified and FR-001b
corrected. That blindness is asserted below rather than described, so nobody
later mistakes C3a for sufficient evidence and drops C1.

Scope: **loaded-vs-loaded** only, and that exclusion is now lifted elsewhere
rather than still open. The built-vs-loaded comparison this file deferred as
F18's territory landed in feature 005 (T031): it lives in
``tests/integration/test_d14_chain.py`` — the chain that already owns the
built object — and its full measurement, including the three groups of type
difference that fall outside FR-019's enumeration, is pinned in
``tests/integration/test_construction_parity.py``. This file stays
loaded-vs-loaded because that is what makes it a *semantic* round-trip test;
duplicating the comparison here would give two owners to one guarantee.
"""

from __future__ import annotations

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

WRITABLE = [d for d in DOCUMENTS if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()]
IDS = [d.relpath for d in WRITABLE]


@pytest.mark.parametrize("doc", WRITABLE, ids=IDS)
def test_load_save_load_is_object_equal(doc, tmp_path):
    original = rt.read_objects(doc)
    written = tmp_path / "saved.xml"
    written.write_bytes(rt.write_bytes(doc, original))
    assert rt.read_objects(doc, source=written) == original


@pytest.mark.parametrize("doc", WRITABLE, ids=IDS)
def test_object_equality_is_blind_to_order_free_reordering(doc, tmp_path):
    """Why C1 cannot be retired in favour of this contract.

    Permuting the children of the ``xs:all`` ``CuemsScript`` root produces a
    document that is a different sequence of bytes and an *equal* object. If
    C3a were the only gate, a mapper that reordered every script root on disk
    would pass it.
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(doc.path)
    root = tree.getroot()
    script_el = root[0]
    if len(script_el) < 2:
        pytest.skip("root has too few children to permute")

    children = list(script_el)
    script_el[:] = list(reversed(children))
    shuffled = tmp_path / "shuffled.xml"
    tree.write(shuffled, encoding="utf-8", xml_declaration=True)

    assert shuffled.read_bytes() != doc.path.read_bytes()
    assert rt.read_objects(doc, source=shuffled) == rt.read_objects(doc)
