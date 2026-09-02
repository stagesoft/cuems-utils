"""Legacy read compatibility (T066a, T066b) — FR-035a–d, SC-019.

Two obligations, both about documents the library did not write itself.

**Historical documents keep loading** (T066a) — true through feature 007.
``tests/data/corpus/legacy/`` holds earlier revisions of a real script,
recovered from `cuems-engine`'s history. The engine may never reject what
today's parser accepts.

**Feature 008 is a recorded, licensed exception to that guarantee** (D3's
second exception, FR-002): promoting ``Media.duration`` to
``cms:CTimecodeType`` invalidates every on-disk document still carrying the
old bare-string shape, including both ``legacy/`` documents — and this
feature retypes the field precisely because ITEM E's conversion path exists
to carry old documents like these forward again. Until Phase 2 lands, "loads"
is qualified: schema validation now rejects them, for that one recorded
reason, and this file asserts *that* rather than pretending the guarantee is
still unconditional.

**The ``schemaLocation`` attribute does not affect loading** (T066b). Feature
006 changes the written attribute from the writing machine's absolute path to
a relative one (F24). That change is only safe if the read side is indifferent
to the attribute's form — so the evidence is produced *here*, on the code that
exists, rather than assumed there. Exercised below on
``cuems-editor/script_minimal.xml``, unaffected by the duration relaxation.
"""

from __future__ import annotations

import json
import re
import warnings
import xml.etree.ElementTree as ET

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT, documents

LEGACY = documents(category="legacy")
OUTCOMES = json.loads((GOLDEN_ROOT / "outcomes.json").read_text())

SCHEMA_LOCATION_ATTR = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"


def test_the_legacy_tier_is_not_empty():
    """FR-035d — compatibility evidence, not archaeology.

    An empty ``legacy/`` would make every assertion below vacuous.
    """
    assert LEGACY


@pytest.mark.parametrize("doc", LEGACY, ids=[d.relpath for d in LEGACY])
def test_legacy_documents_are_rejected_for_the_recorded_reason(doc):
    """FR-035a, qualified by feature 008's D3 duration relaxation.

    Both documents still carry ``Media.duration`` in the pre-008 bare-string
    shape, which no longer validates against ``script.xsd`` — so the rejection
    happens at T1, before there is a dict to decode. This is the licensed
    exception, not a regression: it is why ``tests/data/corpus/pre-008/``
    exists, and why the D3 relaxation was granted only alongside ITEM E's
    conversion path.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(Exception):
            rt.read_dict(doc)
    assert OUTCOMES[doc.relpath]["read"]["ok"] is False
    assert OUTCOMES[doc.relpath]["read"]["error_type"] == "XMLSchemaValidationError"


@pytest.mark.parametrize("doc", LEGACY, ids=[d.relpath for d in LEGACY])
def test_legacy_documents_fail_at_the_object_layer_too(doc):
    """The object layer never gets the chance to run its own check.

    Through feature 007 these two were compatibility evidence at the dict
    layer only, rejected at the object layer by
    ``CueOutput._classify_output_name`` (their output names predate the
    ``<uuid>_<int>`` convention). Feature 008's T1 rejection now happens
    first — ``read_objects`` decodes internally too, so it surfaces the same
    schema error rather than ever reaching the output-name check.
    """
    assert OUTCOMES[doc.relpath]["to_objects"]["ok"] is False
    assert OUTCOMES[doc.relpath]["to_objects"]["error_type"] == "XMLSchemaValidationError"

    with pytest.raises(Exception), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rt.read_objects(doc)


def test_legacy_documents_are_distinct_from_the_current_one():
    """Otherwise this file would be testing the same bytes three times.

    ``settings.xml`` at ``v0.1.0rc11`` and ``v0.1.0rc14`` validate but are
    byte-identical to the current fixture, which is why they are *not*
    vendored — see ``PROVENANCE.md``.
    """
    hashes = {d.path.read_bytes() for d in LEGACY}
    assert len(hashes) == len(LEGACY)
    current = (
        next(
            d
            for d in DOCUMENTS
            if d.relpath == "cuems-engine/projects/complex_test/script.xml"
        )
        .path.read_bytes()
    )
    assert current not in hashes


# --- the schemaLocation form matrix (T066b, FR-035c, SC-019) --------------


@pytest.fixture(scope="module")
def base_document():
    return next(
        d for d in DOCUMENTS if d.relpath == "cuems-editor/script_minimal.xml"
    )


def _variant(doc, tmp_path, form: str):
    """Rewrite the root's ``schemaLocation`` into one of three forms."""
    tree = ET.parse(doc.path)
    root = tree.getroot()
    namespace = "https://stagelab.coop/cuems/"

    if form == "absent":
        root.attrib.pop(SCHEMA_LOCATION_ATTR, None)
    elif form == "relative":
        root.set(SCHEMA_LOCATION_ATTR, f"{namespace} ../cuems/script.xsd")
    elif form == "absolute":
        root.set(SCHEMA_LOCATION_ATTR, f"{namespace} /opt/cuems/schemas/script.xsd")
    else:  # pragma: no cover - guarded by the parametrisation
        raise AssertionError(form)

    target = tmp_path / f"{form}.xml"
    tree.write(target, encoding="utf-8", xml_declaration=True)
    return target


@pytest.mark.parametrize("form", ["absolute", "relative", "absent"])
def test_every_schema_location_form_loads(base_document, tmp_path, form):
    """FR-035c — the attribute's form must not affect loading."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert rt.read_dict(base_document, source=_variant(base_document, tmp_path, form))


def test_all_three_forms_decode_equally(base_document, tmp_path):
    """SC-019 — equal results, not merely three successful loads.

    This is the assertion feature 006 actually needs. Changing the written
    attribute from an absolute path to a relative one is safe **iff** the read
    side cannot tell the difference; three loads that succeed but decode
    differently would not establish that.

    Compared with the attribute itself removed from the result, because it is
    leaked into the payload (F23) and is legitimately different in each variant
    — the point is that nothing *else* changes.
    """
    results = {}
    for form in ("absolute", "relative", "absent"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            decoded = rt.read_dict(
                base_document, source=_variant(base_document, tmp_path, form)
            )
        decoded.pop(SCHEMA_LOCATION_ATTR, None)
        results[form] = rt.json_dumps(decoded)

    assert results["absolute"] == results["relative"] == results["absent"]


def test_the_attribute_is_the_only_difference(base_document, tmp_path):
    """The control: the variants must actually differ on disk.

    If ``_variant`` silently produced three identical files, the test above
    would pass while proving nothing.
    """
    bodies = {
        form: _variant(base_document, tmp_path, form).read_bytes()
        for form in ("absolute", "relative", "absent")
    }
    assert len(set(bodies.values())) == 3

    # The ``xmlns:xsi`` declaration goes with the attribute: ElementTree emits
    # a namespace declaration only when something uses it, so removing the
    # attribute removes the declaration too. Both are stripped, or the
    # "absent" variant would differ for a second, uninteresting reason.
    def strip(body: bytes) -> bytes:
        body = re.sub(rb'\s*xsi:schemaLocation="[^"]*"', b"", body)
        body = re.sub(rb'\s*xmlns:xsi="[^"]*"', b"", body)
        return body

    assert len({strip(body) for body in bodies.values()}) == 1


# --- feature 006 addition (T079, FR-030, SC-009) --------------------------
#
# The write side narrowed (T037): ``xsi:schemaLocation`` now carries the bare
# schema filename. **Files already on disk are unaffected**, and that is the
# half a portability test cannot show — it writes new documents.
#
# The three-form matrix above proves the *reader* is indifferent. These extend
# it to the public surface, to a fourth form the matrix does not cover, and to
# equality of the resulting objects rather than equality of decoded dicts.


@pytest.mark.parametrize("form", ["absolute", "relative", "absent"])
def test_every_form_loads_through_the_public_api(base_document, tmp_path, form):
    from cuemsutils.cues.CuemsScript import CuemsScript

    assert CuemsScript.load(_variant(base_document, tmp_path, form)) is not None


def test_all_three_forms_load_to_equal_objects(base_document, tmp_path):
    """Equality of **objects**, which is what a consumer holds.

    ``test_all_three_forms_decode_equally`` compares decoded dicts. That was
    the right assertion while the reader was the surface; now that
    ``CuemsScript.load`` is, the claim has to be made where the guarantee is
    given — and declared-field equality (feature 006) is a stricter comparison
    than the dict one, so it can fail where that passes.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    scripts = {
        form: CuemsScript.load(_variant(base_document, tmp_path, form))
        for form in ("absolute", "relative", "absent")
    }
    assert scripts["absolute"] == scripts["relative"] == scripts["absent"]


def test_a_document_pointing_at_a_path_that_does_not_exist_still_loads(
    base_document, tmp_path
):
    """FR-030's sharpest case, and the one the matrix omits.

    An absolute path to a machine that no longer exists is not hypothetical: it
    is what every show file written before this feature carries, once the node
    that wrote it is reimaged or the package moves. If anything resolved the
    hint, those files would stop opening — which is exactly the failure the
    narrowing is meant to prevent, arriving from the other direction.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    tree = ET.parse(base_document.path)
    tree.getroot().set(
        SCHEMA_LOCATION_ATTR,
        "https://stagelab.coop/cuems/ /nonexistent/machine/schemas/script.xsd",
    )
    target = tmp_path / "stale.xml"
    tree.write(target, encoding="utf-8", xml_declaration=True)

    assert CuemsScript.load(target) is not None


def test_an_old_document_rewrites_to_the_new_form(base_document, tmp_path):
    """The migration path, such as it is: open and save.

    No conversion tool is needed and none is provided. A document carrying the
    old absolute path loads, and the next ``save()`` writes the bare filename —
    so files migrate as they are edited, and files that are never edited keep
    working indefinitely.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    source = _variant(base_document, tmp_path, "absolute")
    assert b"/opt/cuems/schemas/script.xsd" in source.read_bytes()

    target = tmp_path / "rewritten.xml"
    CuemsScript.load(source).save(target)

    written = target.read_text(encoding="utf-8")
    assert 'xsi:schemaLocation="https://stagelab.coop/cuems/ script.xsd"' in written
    assert "/opt/cuems" not in written
