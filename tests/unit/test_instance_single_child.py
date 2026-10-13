"""G3, T065 — the two-shape element lookup resolves an anonymous single
complex child by path (R1).

``CuemsSettings/Settings`` and ``CuemsProject/CuemsScript`` are the two
measured sites: the root's single field has no qname to key it by
(``field.child is None`` and ``field.xsd_type is None``), so the anonymous
child is resolved by ``derive_path``, reusing the guard conditions of
``Mapper._anonymous_child``/``_child_spec_for`` verbatim.
"""

from __future__ import annotations

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.spec import TypeKey, derive


def test_the_root_fields_are_genuinely_anonymous():
    """The premise research R1 measured, pinned so a schema change that
    makes this unnecessary is visible rather than silently making the fix
    inert."""
    for schema_name, root_path in (
        ("settings", "CuemsSettings"),
        ("script", "CuemsProject"),
    ):
        spec = derive(TypeKey(schema_name, root_path, is_path=True))
        assert len(spec.fields) == 1
        field = spec.fields[0]
        assert field.child is None and field.xsd_type is None, (
            schema_name,
            field,
        )


def test_settings_root_expands_to_the_full_settings_instance():
    descriptor = SchemaDescriptor()
    td = descriptor.describe(TypeKey("settings", "CuemsSettings", is_path=True))
    assert isinstance(td.instance, dict)
    assert "Settings" in td.instance
    assert isinstance(td.instance["Settings"], dict)
    assert "node" in td.instance["Settings"]


def test_script_root_expands_to_the_full_script_instance():
    descriptor = SchemaDescriptor()
    td = descriptor.describe(TypeKey("script", "CuemsProject", is_path=True))
    assert isinstance(td.instance, dict)
    assert "CuemsScript" in td.instance
    assert isinstance(td.instance["CuemsScript"], dict)
    assert "CueList" in td.instance["CuemsScript"]


def test_neither_root_reports_null_for_its_single_child():
    """FR-022 — the defect this fixes: today (pre-G3) both reported
    ``null`` instead of expanding."""
    descriptor = SchemaDescriptor()
    settings_td = descriptor.describe(TypeKey("settings", "CuemsSettings", is_path=True))
    script_td = descriptor.describe(TypeKey("script", "CuemsProject", is_path=True))
    assert settings_td.instance["Settings"] is not None
    assert script_td.instance["CuemsScript"] is not None
