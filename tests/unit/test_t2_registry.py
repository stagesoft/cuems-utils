"""The T2 rule registry (T066) — FR-024, FR-024c, SC-015.

Before this feature each rule existed inside the property setter that happened
to need it. That is not a duplicate — it is *no name at all*, which is why "how
many semantic rules are there?" could only be answered by reading fourteen
setters and hoping none had been missed. The registry gives each one a name, a
``(type, field)`` binding, and **one definition invoked from two call sites**:
the setter (immediate, programmatic) and the write/validate tier.

Each rule below is run against one violating and one satisfying input, because
a registry of rules that never fire is a list, not a tier.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.validators import RULES, SEMANTIC_RULES, Rule, enforce, register

#: The three rules ``validators.py`` held before the registry existed. Named
#: individually so the tier cannot lose one silently.
SEEDED = ("canvas_region_containment", "one_custom_template_per_node", "media_duration")

#: The value-rejecting setter rules, relocated by T073. Nine of the original
#: fourteen survive feature 008's fade-profile deletion (FR-007a) — the five
#: ``fade_profile_*`` rules are gone along with the surface they validated.
RELOCATED = (
    "action_target_required",
    "fade_action_type",
    "fade_curve_type",
    "fade_duration_positive",
    "fade_target_value_range",
    "output_name_shape",
    "canvas_region_containment",
    "media_duration",
    "cuelist_shape",
)

#: ``(rule name, violating value, satisfying value, object)``.
#:
#: The object matters for three rules and is ``None`` for the rest: a canvas
#: region's legality depends on its output's ``output_name``, and a fade
#: profile's on its siblings.
_CUSTOM = "3d2b8f1a-1c4e-4a7b-9f2d-0a1b2c3d4e5f_custom_1"
_ALIAS = "3d2b8f1a-1c4e-4a7b-9f2d-0a1b2c3d4e5f_0"
_REGION = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
_OFF_CANVAS = {"x": 0.9, "y": 0.0, "width": 0.9, "height": 0.5}

CASES = [
    ("action_target_required", None, "any-target", None),
    ("fade_action_type", "play", "fade_action", None),
    ("fade_curve_type", "corkscrew", "linear", None),
    ("fade_duration_positive", "00:00:00.000", "00:00:02.000", None),
    ("fade_target_value_range", 101, 50, None),
    (
        "canvas_region_containment",
        _OFF_CANVAS,
        _REGION,
        {"output_name": _CUSTOM},
    ),
    ("output_name_shape", "VideoOut1", _ALIAS, None),
    ("media_duration", "not a timecode", "00:00:30.000", None),
    ("cuelist_shape", 7, {"contents": []}, None),
]

CASE_IDS = [case[0] for case in CASES]


def test_the_registry_is_not_empty():
    """10 rules survive feature 008 (FR-007a deletes five fade-profile ones)."""
    assert len(RULES) >= 10, sorted(RULES)


@pytest.mark.parametrize("name", sorted(set(SEEDED)))
def test_the_seeded_rules_are_registered(name):
    """The three ``validators.py`` already held, by name."""
    assert name in RULES


@pytest.mark.parametrize("name", sorted(set(RELOCATED)))
def test_every_relocated_setter_rule_is_registered(name):
    assert name in RULES


def test_every_rule_names_what_it_applies_to():
    for name, rule in RULES.items():
        assert isinstance(rule, Rule)
        assert rule.applies_to, f"{name} is bound to nothing"
        for entry in rule.applies_to:
            assert len(entry) == 2, entry
            assert all(isinstance(part, str) for part in entry), entry


def test_every_rule_has_exactly_one_definition():
    """FR-024c, SC-015 — asserted on **function identity**.

    Two rules sharing a name is impossible (``register`` raises). What this
    catches is the other direction: two *entries* wrapping what is really one
    check, or one entry wrapping a lambda that delegates elsewhere. Distinct
    function objects with distinct qualnames is what "one definition per rule"
    looks like from the outside.
    """
    checks = [rule.check for rule in RULES.values()]
    assert len({id(check) for check in checks}) == len(checks)
    names = [getattr(check, "__qualname__", None) for check in checks]
    assert len(set(names)) == len(names), names


def test_registering_the_same_name_twice_is_refused():
    """The registry is an inventory; two entries under one name is not one."""
    with pytest.raises(ValueError):

        @register("media_duration", [("Media", "duration")], repairable=False)
        def _shadow(value, obj=None):  # pragma: no cover - never called
            pass


@pytest.mark.parametrize("name,bad,good,obj", CASES, ids=CASE_IDS)
def test_each_rule_fires_on_a_violation(name, bad, good, obj):
    with pytest.raises((ValueError, TypeError)):
        enforce(name, bad, obj)


@pytest.mark.parametrize("name,bad,good,obj", CASES, ids=CASE_IDS)
def test_each_rule_passes_on_a_satisfying_value(name, bad, good, obj):
    enforce(name, good, obj)


# --- T072a: one inventory, not two ----------------------------------------


def test_semantic_rules_is_derived_from_the_registry():
    """``SEMANTIC_RULES`` used to be a hand-written tuple of three prose names.

    Keeping both once ``RULES`` existed would have been **two inventories of
    one thing** — FR-024c's prohibition one level up, and the mechanism behind
    F15's three incompatible shapes. It is derived now, and this asserts the
    derivation rather than the contents.
    """
    assert tuple(SEMANTIC_RULES) == tuple(sorted(RULES))


def test_the_name_form_changed_from_prose_to_identifiers():
    """Recorded, because the two readers of the list had to be updated with it.

    Rule *messages* — what users see — are unchanged; the names are new.
    """
    for name in SEMANTIC_RULES:
        assert " " not in name, name
        assert name.isidentifier(), name


def test_the_three_original_prose_names_are_gone():
    assert "canvas_region containment" not in SEMANTIC_RULES
    assert "at most one custom template per node" not in SEMANTIC_RULES
    assert "media duration" not in SEMANTIC_RULES
