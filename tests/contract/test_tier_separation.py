"""FR-024 (T067) — the two tiers report distinguishably.

**T1** is the schema: types, cardinality, enumerations, patterns, `xs:assert`.
Derived, total, and enforced by ``xmlschema``.

**T2** is what remains: rules about relationships between values that XSD
cannot state at all.

The requirement is not that both run. It is that a caller can **tell them
apart** — and that neither absorbs the other. A structurally invalid document
must report its structural failure without the semantic tier masking it, and a
semantically wrong but structurally valid one must name a **rule**, not a
schema constraint.

Why this needs its own test rather than falling out of the others: the natural
implementation runs everything and reports the first thing that breaks, which
satisfies "it failed" and destroys the only distinction a consumer can act on.
"""

from __future__ import annotations

import sys

import pytest

from cuemsutils.errors import SchemaError, ValidationError
from cuemsutils.xml.validators import RULES
from tests.support import invalid_scripts as broken
from tests.support.public_api import assert_no_xml_import


def test_a_semantic_failure_names_a_registered_rule():
    """A canvas region extending past its canvas — T1 cannot express it."""
    report = broken.semantically_invalid().validate()
    semantic = [v for v in report if v.tier == "T2"]
    assert semantic, list(report)
    assert semantic[0].rule in RULES, semantic[0].rule
    assert semantic[0].rule == "canvas_region_containment"


def test_the_semantic_case_is_structurally_valid():
    """Without this, the test above could be measuring a schema failure.

    Every component of the off-canvas region is individually inside ``[0, 1]``,
    so ``UnitFloat``/``PositiveUnitFloat`` accept all four. It is their **sum**
    that is wrong, and no XSD facet spans siblings.
    """
    report = broken.semantically_invalid().validate()
    assert [v for v in report if v.tier == "T1"] == []


def test_a_structural_failure_is_reported_without_a_semantic_tier_finding():
    report = broken.structurally_invalid().validate()
    structural = [v for v in report if v.tier == "T1"]
    assert structural, list(report)
    assert [v for v in report if v.tier == "T2"] == []


def test_the_structural_tier_runs_first():
    """Order is part of the contract, not an implementation detail.

    A structurally broken document makes every semantic finding on it
    unreliable — the values the rules would judge may not be the values the
    document meant. Reporting T1 first is what lets a consumer stop reading.
    """
    report = list(broken.invalid_both_tiers().validate())
    tiers = [v.tier for v in report]
    assert "T1" in tiers and "T2" in tiers, tiers
    assert tiers.index("T1") < tiers.index("T2"), tiers


def test_neither_tier_absorbs_the_other():
    report = broken.invalid_both_tiers().validate()
    assert {v.tier for v in report} == {"T1", "T2"}
    assert len({v.rule for v in report}) >= 2


def test_the_exception_types_distinguish_them_too(tmp_path):
    """The same distinction on the raising path, where a consumer branches."""
    with pytest.raises(SchemaError):
        broken.structurally_invalid().save(tmp_path / "a.xml")

    with pytest.raises(ValidationError) as caught:
        broken.semantically_invalid().save(tmp_path / "b.xml")
    assert not isinstance(caught.value, SchemaError)


def test_a_t1_violation_names_a_schema_constraint_not_a_rule_name():
    """The ``rule`` field means different things per tier, and says so.

    For T2 it is the registered rule name; for T1 it is the schema construct
    that rejected the value. A T1 violation carrying a *registry* name would
    mean the tiers had been conflated somewhere upstream of the report.
    """
    report = broken.structurally_invalid().validate()
    for violation in report:
        if violation.tier == "T1":
            assert violation.rule not in RULES, violation


def test_every_violation_is_addressable(tmp_path):
    """``location`` is a pair so a caller can address either half."""
    for violation in broken.invalid_both_tiers().validate():
        cue_id, field = violation.location
        assert cue_id is None or isinstance(cue_id, str)
        assert field is None or isinstance(field, str)


def test_the_module_under_test_names_nothing_from_the_xml_package():
    """Scoped: ``RULES`` is imported to *check* tier separation, not to use it.

    The registry is internal, and this module is a contract test for the tier
    rather than a consumer — so the exemption is stated rather than silent.
    """
    from tests.support.public_api import imported_modules

    named = imported_modules(sys.modules[__name__])
    roots = {
        ".".join(n.split(".")[:3])
        for n in named
        if n.startswith("cuemsutils.xml")
    }
    assert roots == {"cuemsutils.xml.validators"}, roots


def test_the_public_surface_needs_none_of_it():
    """The consumer-facing half of the same claim, with the sweep applied."""
    import tests.contract.test_validate_report as public_leg

    assert_no_xml_import(public_leg)
