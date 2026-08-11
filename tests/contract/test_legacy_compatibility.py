"""Legacy read compatibility (T066a, T066b) — FR-035a–d, SC-019.

Two obligations, both about documents the library did not write itself.

**Historical documents keep loading** (T066a). ``tests/data/corpus/legacy/``
holds earlier revisions of a real script, recovered from `cuems-engine`'s
history. The engine may never reject what today's parser accepts.

**The ``schemaLocation`` attribute does not affect loading** (T066b). Feature
006 changes the written attribute from the writing machine's absolute path to
a relative one (F24). That change is only safe if the read side is indifferent
to the attribute's form — so the evidence is produced *here*, on the code that
exists, rather than assumed there.
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
def test_legacy_documents_still_validate_and_decode(doc):
    """FR-035a — the engine rejects nothing today's parser accepts."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        decoded = rt.read_dict(doc)
    assert decoded
    assert OUTCOMES[doc.relpath]["read"]["ok"] is True


@pytest.mark.parametrize("doc", LEGACY, ids=[d.relpath for d in LEGACY])
def test_legacy_documents_decode_byte_identically(doc):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        produced = rt.json_dumps(rt.read_dict(doc))
    assert produced == rt.golden_json(f"dict/{doc.slug}.reader.json")


@pytest.mark.parametrize("doc", LEGACY, ids=[d.relpath for d in LEGACY])
def test_legacy_documents_fail_at_the_object_layer_as_before(doc):
    """The distinction that makes "they load" precise.

    Both legacy scripts pass schema validation and fail in
    ``CueOutput._classify_output_name``: their output names predate the
    ``<uuid>_<int>`` convention. So they are compatibility evidence at the
    dict layer and not at the object layer, and FR-035a's guarantee is about
    what today's parser accepts — which is the dict.
    """
    assert OUTCOMES[doc.relpath]["to_objects"]["ok"] is False
    assert OUTCOMES[doc.relpath]["to_objects"]["error_type"] == "ValueError"

    with pytest.raises(ValueError), warnings.catch_warnings():
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
