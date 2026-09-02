"""Identical internals across entry points — contract C5, FR-007–FR-011 (T010).

This is the measurement feature 005 exists to close, written **first**, against
pre-005 code, so the gap is a number before it is a fix.

The three entry points, all carrying the *same content* so that any difference
can only come from construction:

* **built** — the programmatic path, the descriptor-generated example document
  (``cuemsutils.xml.descriptor.generate_script_example``, feature 008);
* **XML-decoded** — that same document written out and read back;
* **JSON-decoded** — the same object through the editor's payload round-trip.

Measured on pre-005 code (`79632c3`): **44 type differences** against the
XML-decoded object, in four groups. Feature 005 closed 30 of them:

=========================================  =====  =========================
group                                      count  status
=========================================  =====  =========================
``ui_properties``: CuemsDict -> dict           4  closed — BC1 (T028)
region wrapper shape and its cascade          24  closed — BC2 (T024/T026)
``action_target``: str -> Uuid                 2  closed — T037
``ui_properties`` wildcard None -> "None"      6  **open, not in scope**
``DmxCue`` fields left raw (OPAQUE_TYPES)      4  **open, not in scope**
``output_geometry`` scales: int -> float       4  **open, not in scope**
=========================================  =====  =========================

**Built vs JSON-decoded is now exact — zero differences.** Only the XML leg
still diverges, and every remaining difference is a *text* round-trip artefact:
XML has no way to say "this was an int" for content the schema does not
describe, while JSON does.

The three open groups are inherited and deliberate:

* the wildcard ``<warning>None</warning>`` round-trip, which ``mapper.py``
  records as "it reads like a bug, and it is one", deferred by feature 004
  because changing it rewrites editor state for every cue in every project;
* ``Mapper.OPAQUE_TYPES``, which decodes a ``DmxCue`` with ``model(body)`` and
  never recurses, so its ``autoload`` / ``enabled`` / ``timecode`` stay strings;
* ``VideoOutputGeometryType`` is GENERIC-bound — a plain dict with no model
  class, so no adapter table reaches into it. Giving it a class is 006's work.

None is enumerated in FR-019 and none has a task, so **SC-001's "zero type
differences" does not hold as written**; what holds is zero differences in the
enumerated groups. ``test_the_unenumerated_divergence_is_exactly_as_measured``
pins the remainder with exact counts, so it stays a recorded scope question
rather than becoming an inexplicably red gate.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS

#: Any script document — ``write_bytes`` only needs one to resolve the schema.
SCRIPT_DOC = next(d for d in DOCUMENTS if d.schema == "script")


def _json_to_object(payload: dict):
    from cuemsutils.xml.Parsers import CuemsParser

    return CuemsParser({"CuemsScript": payload}).parse()


def type_map(obj, path: str = "", into: dict[str, str] | None = None) -> dict[str, str]:
    """``{field path: type name}`` for every value at every depth.

    A map rather than a pairwise walk, because the two objects being compared
    may *differ in shape* — a wrapped ``{'Region': …}`` on one side and a
    ``Region`` on the other — and a parallel walk would either crash or stop at
    the divergence, which is the one place it must not stop.
    """
    if into is None:
        into = {}
    into[path or "/"] = type(obj).__name__

    if isinstance(obj, dict):
        for key, value in obj.items():
            type_map(value, f"{path}/{key}", into)
    elif isinstance(obj, (list, tuple)):
        for index, item in enumerate(obj):
            type_map(item, f"{path}[{index}]", into)
    return into


def differences(left: dict[str, str], right: dict[str, str]) -> list[tuple[str, str, str]]:
    """``(path, left type, right type)`` for every path where the two disagree."""
    out = []
    for key in sorted(set(left) | set(right)):
        a, b = left.get(key, "<absent>"), right.get(key, "<absent>")
        if a != b:
            out.append((key, a, b))
    return out


def classify(path: str, left: str, right: str) -> str:
    """Which of the four measured groups a difference belongs to."""
    leaf = path.rsplit("/", 1)[-1].split("[")[0]
    if leaf == "ui_properties":
        return "ui_properties"
    if "/ui_properties/" in path:
        return "wildcard_none"  # the <warning>None</warning> round-trip
    if "/regions" in path or "/Region" in path or leaf == "Region":
        return "regions"
    if "/DmxScene" in path or (left, right) in {("bool", "str"), ("int", "str")}:
        return "opaque_dmx"
    if (left, right) in {("int", "float"), ("str", "Uuid")}:
        return "built_uncoerced"
    return "other"


def render(rows) -> str:
    return "\n  ".join(f"{p}: {a} != {b}" for p, a, b in rows)


@pytest.fixture(scope="module")
def three_ways():
    """One document's content, constructed three ways."""
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter

    built = rt.build_generated_script()

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "built.xml"
        path.write_bytes(rt.write_bytes(SCRIPT_DOC, built))
        xml_decoded = XmlReaderWriter(
            schema_name="script", xmlfile=str(path)
        ).read_to_objects()

    json_decoded = _json_to_object(json.loads(json.dumps(built)))
    return built, xml_decoded, json_decoded


@pytest.mark.xfail(
    strict=True,
    reason="US1 not landed, and two measured groups (wildcard None, "
    "OPAQUE_TYPES) are outside FR-019's enumeration entirely.",
)
def test_built_and_xml_decoded_have_identical_internal_types(three_ways):
    """SC-001 — zero type differences between the built and loaded object."""
    built, xml_decoded, _ = three_ways
    found = differences(type_map(built), type_map(xml_decoded))
    assert not found, "built vs XML-decoded:\n  " + render(found)


def test_built_and_json_decoded_have_identical_internal_types(three_ways):
    """The JSON leg, after the two payloads became one projection.

    **This assertion was unqualified until feature 006, and the change is
    deliberate.** Feature 005 could say "zero differences" here because the
    JSON payload was a *different, richer* encoding from the one
    ``project_load`` carried: ``__json__`` emitted the object's own Python
    values, so ``int`` and ``None`` survived a JSON round-trip that XML
    flattens to text.

    That richness was the defect (F21). The editor received two mutually
    inconsistent encodings of the same document — ``true`` on one path and
    ``"True"`` on the other, ``ui_properties`` integers on one and strings on
    the other — and 006 collapses them onto the single schema-faithful
    projection. The cost is exactly this: the JSON leg now reproduces the XML
    leg's type behaviour, because it *is* the XML leg's projection.

    So the enumerated groups are still zero (that is
    ``test_the_enumerated_divergence_is_closed``), and what remains is the
    wildcard/opaque residual the XML leg has always had, now shared. Pinning
    it by group rather than deleting the test keeps the change visible.
    """
    built, _, json_decoded = three_ways
    found = differences(type_map(built), type_map(json_decoded))
    unexpected = [r for r in found if classify(*r) not in ALIGNED_PAYLOAD_GROUPS]
    assert not unexpected, "built vs JSON-decoded:\n  " + render(unexpected)


#: The groups the aligned payload inherits from the XML projection — wildcard
#: ``ui_properties`` content stringified (X10's documented fallback) and
#: ``OPAQUE_TYPES`` members never recursed into. Neither is new; both were
#: already the ``project_load`` behaviour before this feature made
#: ``initial_template`` match it.
ALIGNED_PAYLOAD_GROUPS = {"wildcard_none", "opaque_dmx"}


def test_the_json_leg_now_matches_the_xml_leg_group_for_group(three_ways):
    """The positive form of the change above: one projection, one behaviour.

    Without this, relaxing the assertion above would be indistinguishable from
    giving up on it. The claim is not "some differences are tolerated" but
    "the two payloads have stopped disagreeing" — which is checkable, and is
    what SC-003 is about.
    """
    built, xml_decoded, json_decoded = three_ways
    xml_groups = {classify(*r) for r in differences(type_map(built), type_map(xml_decoded))}
    json_groups = {classify(*r) for r in differences(type_map(built), type_map(json_decoded))}
    assert json_groups <= xml_groups, (
        f"the JSON leg diverges in groups the XML leg does not: "
        f"{sorted(json_groups - xml_groups)}"
    )


def test_ui_properties_is_the_same_wrapper_type_everywhere(three_ways):
    """FR-008, named explicitly so the failure reads as a requirement."""
    built, xml_decoded, json_decoded = three_ways

    def by_path(obj):
        return {
            path: name
            for path, name in type_map(obj).items()
            if path.endswith("/ui_properties")
        }

    # Per path, not per object: each object carries a *mix* of ui_properties
    # types, and comparing the mixes as sets passes while every individual
    # field still disagrees.
    reference = by_path(built)
    assert reference, "no ui_properties field was found to compare"
    for label, obj in (("xml", xml_decoded), ("json", json_decoded)):
        found = differences(reference, by_path(obj))
        assert not found, f"built vs {label}:\n  " + render(found)


def test_regions_are_region_objects_everywhere(three_ways):
    """FR-009, SC-006 — the raw ``{'Region': …}`` wrapper is what fails today."""
    for label, obj in zip(("built", "xml", "json"), three_ways):
        region_types = {
            name
            for path, name in type_map(obj).items()
            if "/regions[" in path and path.endswith("]")
        }
        assert region_types <= {"Region"}, f"{label}: regions are {region_types}"


# --- the measurement itself, asserted positively --------------------------
#
# These pass today and must keep passing until US1 lands. They are what make
# the xfails above meaningful: without them, a harness that compared nothing
# would xfail just as convincingly.


def test_the_probe_actually_compares_something(three_ways):
    built, xml_decoded, _ = three_ways
    assert differences(type_map(built), type_map(xml_decoded)), (
        "the harness found no differences — it is comparing nothing"
    )


def test_the_enumerated_divergence_is_closed(three_ways):
    """FR-019 rows 1 and 2 — **zero** remaining differences in either group.

    The fail-then-pass evidence for BC1 and BC2 at the level the feature claims:
    not "regions look better" but "no path anywhere reports a region or a
    ui_properties type difference".
    """
    built, xml_decoded, json_decoded = three_ways
    for label, obj in (("xml", xml_decoded), ("json", json_decoded)):
        rows = differences(type_map(built), type_map(obj))
        offending = [r for r in rows if classify(*r) in {"ui_properties", "regions"}]
        assert not offending, f"built vs {label}:\n  " + render(offending)


def test_the_unenumerated_divergence_is_exactly_as_measured(three_ways):
    """**A recorded scope question, not a pass.**

    Pre-005 (`79632c3`) this harness measured **44** type differences in four
    groups. BC1, BC2 and T037 closed 30 of them. The remaining **14** are in
    three groups that FR-019 does not enumerate and no task closes:

    ``wildcard_none`` (6)
        ``ui_properties`` wildcard content round-trips ``None`` and ``int`` as
        the strings ``"None"`` / ``"0"``. ``mapper.py`` records this as a known
        defect deferred by feature 004 — *"it reads like a bug, and it is one"*
        — because fixing it rewrites editor state for every cue in every
        project.

    ``opaque_dmx`` (4)
        ``Mapper.OPAQUE_TYPES`` decodes a ``DmxCue`` with ``model(body)`` and
        never recurses, so its ``autoload``, ``enabled``, ``timecode`` and scene
        ``id`` stay the strings ``xmlschema`` produced.

    ``built_uncoerced`` (4)
        the **built** side is the less typed one: ``output_geometry/x_scale``
        and ``y_scale`` are ``int`` where decode yields ``float``. All four sit
        inside ``VideoOutputGeometryType``, which is GENERIC-bound — a plain
        dict with no model class, so no adapter table reaches into it. Closing
        them means giving that type a class, which is feature 006's work.

        This group was **6** until T037: ``action_target`` was a ``str`` on the
        built side and a ``Uuid`` on the decoded one. Those two closed when the
        uuid-bearing setters started delegating to the adapter, which is the
        same table decode uses — the feature working as designed, on a field
        the enumeration did not call out.

    All three groups are structural rather than oversights, and none is
    reachable without widening this feature. **SC-001's "zero type differences"
    is therefore not satisfied as written**; what holds is zero differences in
    the groups FR-019 enumerates. Pinned with exact counts so the remainder is
    a recorded scope question rather than an inexplicably red gate.
    """
    built, xml_decoded, _ = three_ways
    rows = differences(type_map(built), type_map(xml_decoded))

    counts: dict[str, int] = {}
    for row in rows:
        counts[classify(*row)] = counts.get(classify(*row), 0) + 1

    assert counts.get("other", 0) == 0, (
        "unclassified type differences — the measured groups no longer "
        "describe the divergence:\n  "
        + render([r for r in rows if classify(*r) == "other"])
    )
    assert counts.get("ui_properties", 0) == 0, "BC1 regressed"
    assert counts.get("regions", 0) == 0, "BC2 regressed"
    assert counts.get("wildcard_none") == 6, counts
    assert counts.get("opaque_dmx") == 4, counts
    assert counts.get("built_uncoerced") == 4, counts
    assert sum(counts.values()) == 14, counts
