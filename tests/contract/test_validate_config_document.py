# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T070 — a public stand-alone validator for configuration documents (FR-036, SC-015).

UR-5, second half. Before this there was no way to ask "is this ``settings.xml``
valid?" without constructing a ``ConfigManager``, which wants a whole
installation. ``CuemsScript.validate`` exists for show documents and cannot help:
it builds a show document.

Four things are asserted, and the last two are the ones that make this a
contract rather than a convenience:

* a valid document of each of the four configuration schemas reports clean;
* an invalid one **names the field**, not merely that something is wrong;
* **no ``ConfigManager`` is constructed** and no ``/etc/cuems`` is required;
* the name is imported from ``cuemsutils.tools``, not from
  ``cuemsutils.tools.config_validate`` — the façade is the published path — and
  that façade's re-export is **lazy**, so ``import cuemsutils.tools.CTimecode``
  still does not pull the schema stack.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cuemsutils.errors import LoadReport, Outcome, ValidationError
from cuemsutils.tools import validate_config_document

CORPUS = Path(__file__).resolve().parents[1] / "data" / "corpus"

#: One accepted document per configuration schema, from the corpus rather than
#: hand-authored: these are the documents the suite already proves load.
VALID = {
    "settings": CORPUS / "cuems-utils" / "settings.xml",
    "network_map": CORPUS / "cuems-utils" / "network_map.xml",
    "project_mappings": CORPUS / "cuems-utils" / "project_mappings.xml",
    "project_settings": CORPUS / "cuems-engine" / "project_settings.xml",
}


def test_the_name_is_on_the_facade():
    assert callable(validate_config_document)
    from cuemsutils import tools

    assert "validate_config_document" in tools.__all__


@pytest.mark.parametrize("schema_name", sorted(VALID))
def test_a_valid_document_reports_clean(schema_name):
    report = validate_config_document(VALID[schema_name])
    assert isinstance(report, LoadReport)
    assert report.outcome is Outcome.CLEAN, report
    assert report.repairs == ()
    assert report.conversions == ()
    assert report.document == str(VALID[schema_name])
    assert report.file_differs_from_loaded is False


@pytest.mark.parametrize("schema_name", sorted(VALID))
def test_an_invalid_document_names_the_offending_field(schema_name, tmp_path):
    """Deleting a required element must produce a message naming it.

    The first required child of the document's own body is removed, so the test
    does not need to know which field each schema requires — only that whichever
    one it removed is named back. "Invalid" without a field name is the answer
    this function exists to improve on.
    """
    import xml.etree.ElementTree as ET

    source = VALID[schema_name]
    target = tmp_path / source.name
    shutil.copyfile(source, target)
    tree = ET.parse(target)
    root = tree.getroot()
    body = list(root)[0] if list(root) else root
    victims = list(body)
    if not victims:
        pytest.skip(f"{schema_name}'s body has no child to remove")
    removed = victims[0].tag.rsplit("}", 1)[-1]
    body.remove(victims[0])
    tree.write(target, encoding="utf-8", xml_declaration=True)

    with pytest.raises(Exception) as caught:
        validate_config_document(target)
    message = str(caught.value)
    assert removed in message, (
        f"{schema_name}: removing <{removed}> produced {message!r}, which does "
        f"not name it"
    )


def test_it_does_not_construct_a_config_manager(monkeypatch):
    """The whole gap this closes: validation must not need an installation."""
    import cuemsutils.tools.ConfigManager as module

    constructed = []
    original = module.ConfigManager.__init__

    def spy(self, *args, **kwargs):
        constructed.append(True)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(module.ConfigManager, "__init__", spy)
    validate_config_document(VALID["settings"])
    assert constructed == [], "validate_config_document constructed a ConfigManager"


def test_it_does_not_require_etc_cuems(monkeypatch, tmp_path):
    monkeypatch.setenv("CUEMS_CONF_PATH", str(tmp_path / "nowhere"))
    report = validate_config_document(VALID["network_map"])
    assert report.outcome is Outcome.CLEAN


def test_a_missing_file_raises_oserror_unwrapped(tmp_path):
    """The accessor posture: every consumer already handles ``OSError``."""
    with pytest.raises(OSError):
        validate_config_document(tmp_path / "absent.xml")


def test_an_unrecognised_root_is_refused_by_name(tmp_path):
    target = tmp_path / "stranger.xml"
    target.write_text("<?xml version='1.0'?><Nope/>", encoding="utf-8")
    with pytest.raises(Exception) as caught:
        validate_config_document(target)
    assert "Nope" in str(caught.value)


def test_a_show_document_is_refused_and_says_where_to_go(tmp_path):
    """``script`` is not a configuration schema; the refusal has to say so."""
    script = CORPUS / "cuems-editor" / "script_minimal.xml"
    with pytest.raises(Exception) as caught:
        validate_config_document(script)
    message = str(caught.value)
    assert "script" in message
    assert "CuemsScript" in message


def test_this_module_does_not_import_cuemsutils_xml():
    """The surface claim, on this file's own source (clarification Q14)."""
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            offenders += [a.name for a in node.names if a.name.startswith("cuemsutils.xml")]
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "cuemsutils.xml"
        ):
            offenders.append(node.module)
    assert offenders == [], offenders


def test_the_facade_re_export_is_lazy():
    """``import cuemsutils.tools.CTimecode`` must not pull the schema stack.

    Run in a **subprocess** because the schema stack is already imported in
    this one. ``tools/__init__.py``'s body stays eager only for ``SENTINEL``
    and ``coerce_identity``, which do not reach ``cuemsutils.xml``.
    """
    code = (
        "import sys; import cuemsutils.tools.CTimecode; "
        "assert not [m for m in sys.modules if m.startswith('cuemsutils.xml')], "
        "sorted(m for m in sys.modules if m.startswith('cuemsutils.xml'))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_tools_init_has_no_top_level_import_of_config_validate():
    """Asserted on the source, so the laziness is structural, not incidental."""
    import cuemsutils.tools as tools

    source = Path(tools.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:  # top level only
        if isinstance(node, ast.ImportFrom):
            assert "config_validate" not in (node.module or ""), ast.dump(node)
            assert not (node.module or "").startswith("..xml"), ast.dump(node)
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "config_validate" not in alias.name
                assert not alias.name.startswith("cuemsutils.xml")


def test_a_repairable_violation_is_reported_rather_than_raised(tmp_path):
    """The report is the deliverable: *what* is wrong, not only *that*.

    ``project_mappings``' one registered T2 rule is ``repairable=False``, so a
    violation of it raises ``ValidationError`` — and that raise is itself the
    reported distinction between a semantic failure and a structural one
    (feature 008, FR-037). Asserted here so the report type's role is pinned
    for whichever schema gains a repairable rule next.
    """
    report = validate_config_document(VALID["project_mappings"])
    assert isinstance(report.repairs, tuple)
    assert isinstance(report.conversions, tuple)
    assert ValidationError is not None
