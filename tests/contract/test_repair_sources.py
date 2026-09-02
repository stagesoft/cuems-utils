"""Every repair traces to the descriptor — zero hand-written fallbacks or
unrepairable-field lists (ITEM E, US7, T114) — FR-045, SC-020.
"""

from __future__ import annotations

import ast
from pathlib import Path

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.xml.descriptor import Repairability, SchemaDescriptor
from cuemsutils.xml.validators import RULES
from tests.support import invalid_scripts as broken
from tests.support.corpus import REPO_ROOT


def test_repair_reads_the_default_from_declared_defaults_not_a_literal_table():
    """``xml.validators.repair`` (the one implementation, ITEM E) resolves a
    substitute value through ``type(node).declared_defaults()`` — the same
    accumulated table the descriptor's own ``default`` field is built from
    (research R5) — never a second, hand-maintained mapping."""
    source = (REPO_ROOT / "src" / "cuemsutils" / "xml" / "validators.py").read_text()
    tree = ast.parse(source)
    repair_fn = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "repair"
    )
    calls = {
        node.func.attr
        for node in ast.walk(repair_fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "declared_defaults" in calls


def test_every_rule_declares_repairable_no_undeclared_rule_exists():
    """FR-031b: ``register()`` requires ``repairable`` with no default, so an
    undeclared rule is a ``TypeError`` at import — already true simply by
    every rule in ``RULES`` having imported successfully."""
    for rule in RULES.values():
        assert isinstance(rule.repairable, bool)


def test_zero_fields_are_unclassified_across_every_schema():
    descriptor = SchemaDescriptor()
    unclassified = 0
    for schema_name in descriptor.schemas:
        for type_descriptor in descriptor.types(schema_name):
            for field in type_descriptor.fields:
                if field.repairability not in (Repairability.REPAIRABLE, Repairability.UNREPAIRABLE):
                    unclassified += 1
    assert unclassified == 0


def test_a_repair_records_default_traceable_to_the_descriptor(tmp_path):
    """The value ``repair()`` substituted is exactly the same value the
    descriptor reports as that field's default — not independently derived."""
    from cuemsutils.xml.registry import get_registry
    from cuemsutils.xml.spec import TypeKey

    script = broken.repairable_violation()
    path = tmp_path / "repairable.xml"
    broken.write_bypassing_validation(script, path)

    _loaded, report = CuemsScript.load_with_report(path)
    record = report.repairs[0]

    descriptor = SchemaDescriptor()
    key = TypeKey("script", "FadeCueType")
    field = next(f for f in descriptor.describe(key).fields if f.name == "action_type")
    assert record.substituted_value == field.default
    assert field.repairability is Repairability.REPAIRABLE
