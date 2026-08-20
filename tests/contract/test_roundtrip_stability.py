"""Contract C3 (T015) — round-trip stability, not input fidelity.

The property asserted is::

    save(load(save(load(x)))) == save(load(x))

and **not** ``save(load(x)) == x``, which is false today and cannot be made true
here. Hand-authored corpus files are indented, some declare ``version="1.1"``,
and the serializer normalizes both; the first save reformats. Idempotence holds
from the first save onward (research R10, and the restated FR-012/SC-003).

``test_first_cycle_is_not_identity`` exists to keep that honest: if the first
cycle ever *did* become identity, the weaker property asserted here would be
silently weaker than necessary, and someone should notice.
"""

from __future__ import annotations

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

WRITABLE = [d for d in DOCUMENTS if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()]
IDS = [d.relpath for d in WRITABLE]


def _cycle(doc, source, tmp_path, tag):
    """One ``save(load(...))``, returning the path written."""
    obj = rt.read_objects(doc, source=source)
    target = tmp_path / f"{tag}.xml"
    target.write_bytes(rt.write_bytes(doc, obj))
    return target


@pytest.mark.parametrize("doc", WRITABLE, ids=IDS)
def test_second_cycle_is_identical_to_first(doc, tmp_path):
    once = _cycle(doc, doc.path, tmp_path, "once")
    twice = _cycle(doc, once, tmp_path, "twice")
    assert twice.read_bytes() == once.read_bytes()


@pytest.mark.parametrize("doc", WRITABLE, ids=IDS)
def test_stability_holds_for_a_third_cycle(doc, tmp_path):
    """Two cycles could coincide; three is evidence of a fixed point.

    Cheap, and it distinguishes "stable" from "alternating", which two cycles
    cannot.
    """
    once = _cycle(doc, doc.path, tmp_path, "once")
    twice = _cycle(doc, once, tmp_path, "twice")
    thrice = _cycle(doc, twice, tmp_path, "thrice")
    assert thrice.read_bytes() == twice.read_bytes()


#: The two documents authored for feature 006 (T003b, T003c) were written in
#: the serializer's own output form — one line, no indentation, canonical
#: element order. Every other corpus document is hand-authored or vendored and
#: is indented, so its first save reformats it.
#:
#: Until T037 even these two changed on the first cycle, because the writer
#: replaced their ``schemaLocation`` with the writing machine's absolute path
#: to the ``.xsd``. Writing the bare filename removed the last difference, so
#: for them ``save(load(x)) == x`` now holds outright. That is the strengthening
#: this file's docstring asks someone to notice, so it is asserted rather than
#: excluded.
FIRST_CYCLE_IS_IDENTITY = {
    "cuems-utils/fade_showcase.xml",
    "cuems-utils/unicode_showcase.xml",
}

REFORMATTED = [d for d in WRITABLE if d.relpath not in FIRST_CYCLE_IS_IDENTITY]
CANONICAL = [d for d in WRITABLE if d.relpath in FIRST_CYCLE_IS_IDENTITY]


@pytest.mark.parametrize("doc", REFORMATTED, ids=[d.relpath for d in REFORMATTED])
def test_first_cycle_is_not_identity(doc, tmp_path):
    """The measured falsehood, pinned as such.

    Recorded so that C3's weaker form is visibly *necessary* rather than merely
    convenient. If this ever fails for a **hand-authored** document, the
    serializer has started preserving its input and SC-003 should be
    strengthened — a good outcome, but one that must be a decision rather than
    a drift.
    """
    once = _cycle(doc, doc.path, tmp_path, "once")
    assert once.read_bytes() != doc.path.read_bytes()


@pytest.mark.parametrize("doc", CANONICAL, ids=[d.relpath for d in CANONICAL])
def test_a_canonically_authored_document_survives_the_first_cycle_unchanged(
    doc, tmp_path
):
    """``save(load(x)) == x``, for a document already in canonical form.

    The stronger property, now reachable for the first time because T037
    stopped the writer stamping a machine-local path into the root element.
    Asserting it here is what keeps the split above honest: without it,
    "excluded from the not-identity check" would be indistinguishable from
    "untested".
    """
    once = _cycle(doc, doc.path, tmp_path, "once")
    assert once.read_bytes() == doc.path.read_bytes()
