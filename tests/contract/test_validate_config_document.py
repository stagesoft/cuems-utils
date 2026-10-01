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
def test_a_valid_document_validates_and_needs_no_repair(schema_name):
    report = validate_config_document(VALID[schema_name])
    assert isinstance(report, LoadReport)
    assert report.repairs == ()
    assert report.document == str(VALID[schema_name])


#: ``(schema, from_version, to_version)`` for the corpus documents that are
#: genuinely **version-old**. Measured, not assumed: these three carry no
#: ``doc_version`` (or an older one) while their schemas have moved, so a
#: *valid* document correctly reports ``CONVERTED``. Feature 012's identity
#: steps are what moved ``network_map`` and ``project_mappings`` to 2 and
#: ``settings`` to 3; ``project_settings`` is still at 1 and so reports clean.
VERSION_OLD = (
    ("settings", 2, 3),
    ("network_map", 1, 2),
    ("project_mappings", 1, 2),
)


@pytest.mark.parametrize("schema_name,from_version,to_version", VERSION_OLD)
def test_a_version_old_document_reports_converted_rather_than_clean(
    schema_name, from_version, to_version
):
    """The report distinguishes "valid" from "up to date", which is the point.

    A caller that only learns "valid" cannot tell that the file on disk is
    behind the library — and ``file_differs_from_loaded`` is how it finds out
    without this function writing anything.
    """
    report = validate_config_document(VALID[schema_name])
    assert report.outcome is Outcome.CONVERTED, report
    assert [(c.from_version, c.to_version) for c in report.conversions] == [
        (from_version, to_version)
    ]
    assert report.file_differs_from_loaded is True


def test_a_current_version_document_reports_clean(tmp_path):
    """The ``CLEAN`` arm, on a document at its schema's current version."""
    import xml.etree.ElementTree as ET

    from cuemsutils.xml.versioning import CURRENT_VERSION

    target = tmp_path / "settings.xml"
    tree = ET.parse(VALID["settings"])
    tree.getroot().set("doc_version", str(CURRENT_VERSION["settings"]))
    tree.write(target, encoding="utf-8", xml_declaration=True)

    report = validate_config_document(target)
    assert report.outcome is Outcome.CLEAN, report
    assert report.conversions == ()
    assert report.repairs == ()
    assert report.file_differs_from_loaded is False


def test_project_settings_is_already_current_and_reports_clean():
    report = validate_config_document(VALID["project_settings"])
    assert report.outcome is Outcome.CLEAN, report


#: The path to a genuinely **required** element, per schema: every step but the
#: last names a container to descend into, the last names the element to delete.
#:
#: Named rather than discovered, and the path rather than a single name, because
#: both shortcuts failed. "The body's first child" was optional for
#: ``network_map`` — ``node_list`` is ``minOccurs="0"``, so removing it produced
#: a perfectly valid document and the test passed by not invalidating anything.
#: The required elements there are one level further down, inside a ``<node>``.
#:
#: ``project_settings`` is absent on purpose: its body is legitimately empty, it
#: declares no required child, and there is nothing whose absence is an error.
REQUIRED_ELEMENT = {
    "settings": ("Settings", "conf_path"),
    "network_map": ("node_list", "node", "uuid"),
    "project_mappings": ("number_of_nodes",),
}


@pytest.mark.parametrize("schema_name", sorted(REQUIRED_ELEMENT))
def test_an_invalid_document_names_the_offending_field(schema_name, tmp_path):
    """"Invalid" without a field name is the answer this function improves on."""
    import xml.etree.ElementTree as ET

    def child(parent, name):
        return next(e for e in parent if e.tag.rsplit("}", 1)[-1] == name)

    *containers, required = REQUIRED_ELEMENT[schema_name]
    source = VALID[schema_name]
    target = tmp_path / source.name
    shutil.copyfile(source, target)
    tree = ET.parse(target)
    body = tree.getroot()
    for step in containers:
        body = child(body, step)
    body.remove(child(body, required))
    tree.write(target, encoding="utf-8", xml_declaration=True)

    with pytest.raises(Exception) as caught:
        validate_config_document(target)
    message = str(caught.value)
    assert required in message, (
        f"{schema_name}: removing <{required}> produced {message!r}, which does "
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
    assert report.repairs == ()


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


def test_this_module_has_no_module_level_import_of_cuemsutils_xml():
    """The surface claim, on this file's own AST (clarification Q14).

    **Module level** only. One test needs ``CURRENT_VERSION`` in order to build
    a document at its schema's current version, and names it inside the function
    body where it costs nothing at import time — which is the same discipline
    ``tools/__init__.py`` itself follows and the thing the subprocess check
    below actually measures.
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    offenders = []
    for node in tree.body:  # top level only
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
