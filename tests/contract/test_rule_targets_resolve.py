# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every registered T2 rule targets a class that exists.

``validators.register`` binds a rule to ``(class-name, field)`` pairs, and
``Rule.fields_for`` matches those names against an object's MRO
(``validators.py:128,174``) — **by string**, deliberately, so the registry does
not have to import every model. The cost of that choice is that a target naming
a class which no longer exists is not an error. It is silence: the rule is
registered, reported as registered, and never fires.

This file is the check that makes it an error instead.

**It exists because of a near miss.** Renaming ``project_mappings.xsd``'s
``NodeType`` to ``NodeMappingType`` (rc16, closing an X14 recorded by
``test_schema_name_overlap.py``) had to update the key of
``one_custom_template_per_node`` along with the schema, the registry binding and
the model class. Every one of those *except the rule key* is covered by an
existing test — ``test_registry_totality`` compares bound names against the
schema's complex types, ``test_coherence`` resolves the model. The rule key was
the single site where getting it wrong stayed green, and it is the site whose
live enforcement path (``ProjectMappings.validate_custom_templates``) does not
go through the registry, so the product constraint would still *appear* enforced
while the registered rule was dead.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.validators import RULES

#: The schemas whose types carry model classes — the same set
#: ``tests/unit/test_coherence.py`` walks, and for the same reason: a rule can
#: only target a class that some registry binds.
_SCHEMAS = ("script", "settings", "project_settings", "project_mappings", "network_map")


def _known_models() -> dict[str, type]:
    """Every model class reachable through the registries, keyed by ``__name__``.

    Keyed on the name the way :meth:`validators.Rule.fields_for` matches — a
    class name off an object's MRO — rather than on the registry's *type* name,
    because the two are not always the same string.

    **Both binding kinds are walked.** A registry binds by type name *and* by
    element path (``bind_path``), and the document roots are path-bound because
    their types are anonymous (research R3). Walking only ``bound_type_names``
    would report ``CuemsScript`` — bound at ``CuemsProject/CuemsScript``, and the
    target of ``cuelist_shape`` — as a class nothing binds, which would be a
    defect in the check rather than in the rule.

    **Generic bindings are skipped.** ``Binding.model`` is the sentinel *string*
    ``"GENERIC"`` for a type bound to the generic container rather than to a
    class, so the filter is ``isinstance(model, type)`` and not a ``None``
    check — a distinction worth stating, because getting it wrong raises
    ``AttributeError: 'str' object has no attribute '__name__'`` from inside
    every parametrised case at once.
    """
    models: dict[str, type] = {}
    for schema_name in _SCHEMAS:
        registry = get_registry(schema_name)
        bindings = [registry.binding_for(n) for n in registry.bound_type_names]
        bindings += [registry.binding_for_path(p) for p in registry.bound_path_names]
        for binding in bindings:
            if binding is not None and isinstance(binding.model, type):
                models.setdefault(binding.model.__name__, binding.model)
    return models


def _known_class_names() -> set[str]:
    return set(_known_models())


@pytest.mark.parametrize("rule_name", sorted(RULES))
def test_every_rule_target_names_a_class_that_exists(rule_name):
    known = _known_class_names()
    unresolved = sorted(
        {cls for cls, _field in RULES[rule_name].applies_to if cls not in known}
    )
    assert not unresolved, (
        f"rule {rule_name!r} targets class name(s) no registry binds: "
        f"{unresolved}. A target is matched by string against an object's MRO, "
        "so a stale name does not raise -- the rule simply never fires. If a "
        "class was renamed, update the rule's applies_to with it."
    )


def test_every_rule_target_names_a_field_the_class_declares():
    """The other half of the same silence.

    A target whose *class* resolves but whose *field* does not is equally inert,
    and equally quiet. Checked together because a rename that moves a field
    between types fails this rather than the one above.
    """
    models = _known_models()

    broken = []
    for rule_name, rule in sorted(RULES.items()):
        for cls, field in rule.applies_to:
            model = models.get(cls)
            if model is None:
                continue  # covered by the test above
            declared = set(model.declared_fields())
            if field not in declared:
                broken.append(f"{rule_name}: {cls}.{field}")

    assert not broken, (
        "rule target(s) naming a field the class does not declare: "
        f"{broken}. The rule is registered and will never fire."
    )


def test_the_renamed_mappings_type_is_the_one_carrying_the_rule():
    """rc16's rename, pinned where it was nearly missed.

    ``one_custom_template_per_node`` is the only registered T2 rule on the
    configuration side (CLAUDE.md), and its target moved with the type. Named
    explicitly rather than left to the generic checks above, because this is the
    pair whose divergence the generic checks were written after.
    """
    rule = RULES["one_custom_template_per_node"]
    assert rule.applies_to == (("NodeMappingType", "video"),)
    assert rule.repairable is False

    mappings = get_registry("project_mappings")
    assert mappings.model_for("NodeMappingType") is not None
    assert mappings.model_for("NodeType") is None, (
        "project_mappings still binds 'NodeType' -- the rc16 rename is "
        "incomplete, and the X14 it resolved is back."
    )

    # network_map keeps the plain name: identity is the older, broader meaning.
    assert get_registry("network_map").model_for("NodeType") is not None
