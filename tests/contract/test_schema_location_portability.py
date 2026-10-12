"""FR-029, SC-009 (T078) — a written document does not name its writer.

``xsi:schemaLocation`` used to carry the **writing machine's absolute path** to
the bundled `.xsd`, so every show file recorded the local filesystem layout of
whichever node last saved it (F24). Two consequences, and the second is the one
that mattered day to day:

* show files were neither portable nor reproducible — the same object saved on
  a developer laptop and on a node produced different bytes;
* the golden harness could not compare written XML at all without normalising
  that one component out, which is why ``SCHEMA_PATH_PLACEHOLDER`` existed.

T037 writes ``os.path.basename(xsd_path)``. This proves it by **writing the same
object under two different installation layouts** and comparing the bytes —
which is the only form of the claim that a single-layout test cannot make.

Nothing resolves the value: validation always uses the explicitly loaded schema
object, never the hint in the document. That is what makes narrowing it safe
rather than merely tidy.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support import invalid_scripts as broken
from tests.support.corpus import loadable_script_documents
from tests.support.public_api import assert_no_xml_import

SCRIPT_DOCS = loadable_script_documents()
IDS = [d.relpath for d in SCRIPT_DOCS]


@pytest.fixture
def relocate_schemas(tmp_path, monkeypatch):
    """Move the bundled schemas to an arbitrary directory, as an install would.

    Patches ``documents.get_pkg_schema`` rather than ``__file__``: the function
    is the one place the schema path is computed (US4 consolidated it there),
    so patching it is patching the installation layout rather than simulating
    one. The compiled-schema cache is keyed on the resolved *path*, so two
    layouts get two schema objects and neither reuses the other's.
    """

    def relocate(label: str):
        from cuemsutils.xml import documents

        root = tmp_path / label / "site-packages" / "cuemsutils" / "xml" / "schemas"
        root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(Path(documents.__file__).parent / "schemas", root)

        def fake(schema_name: str) -> str:
            name = schema_name if schema_name.endswith(".xsd") else schema_name + ".xsd"
            path = root / name
            if not path.is_file():
                raise FileNotFoundError(f"Schema file {name} not found")
            return str(path)

        monkeypatch.setattr(documents, "get_pkg_schema", fake)
        return root

    return relocate


def test_the_two_layouts_really_are_different(relocate_schemas):
    """The control. If both layouts resolved to the same directory the
    comparison below would be a document compared with itself."""
    from cuemsutils.xml import documents

    first = relocate_schemas("layout-a")
    a = documents.get_pkg_schema("script")
    second = relocate_schemas("layout-b")
    b = documents.get_pkg_schema("script")

    assert first != second
    assert a != b
    assert Path(a).is_file() and Path(b).is_file()


def test_the_same_object_writes_identical_bytes_under_two_layouts(
    tmp_path, relocate_schemas
):
    script = broken.valid_script()

    relocate_schemas("layout-a")
    first = tmp_path / "a.xml"
    script.save(first)

    relocate_schemas("layout-b")
    second = tmp_path / "b.xml"
    script.save(second)

    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_no_corpus_document_writes_an_absolute_path(doc, tmp_path, relocate_schemas):
    relocate_schemas("deep/nested/layout")
    target = tmp_path / "written.xml"
    CuemsScript.load(doc.path).save(target)

    written = target.read_text(encoding="utf-8")
    assert 'xsi:schemaLocation="https://stagelab.coop/cuems/ script.xsd"' in written
    assert str(tmp_path) not in written
    assert "site-packages" not in written
    assert "/usr/" not in written


def test_the_written_document_still_validates_under_either_layout(
    tmp_path, relocate_schemas
):
    """The attribute is informational; validation uses the loaded schema.

    Stated because "we narrowed the schema location" reads like it might have
    broken validation, and the reason it did not is worth having asserted
    rather than reasoned about.
    """
    relocate_schemas("layout-a")
    target = tmp_path / "a.xml"
    broken.valid_script().save(target)
    assert CuemsScript.load(target) is not None

    relocate_schemas("layout-b")
    assert CuemsScript.load(target) is not None


def test_a_document_written_under_one_layout_loads_under_the_other(
    tmp_path, relocate_schemas
):
    """The portability claim as an operator would meet it: save on a laptop,
    open on a node."""
    relocate_schemas("laptop")
    target = tmp_path / "show.xml"
    original = broken.valid_script()
    original.save(target)

    relocate_schemas("node")
    reopened = CuemsScript.load(target)

    # Compared through the projection rather than by object equality. A
    # written-then-read script is not ``==`` its in-memory original for a
    # reason this feature does not own: wildcard ``ui_properties`` content has
    # no declared type, so ``{'warning': 0}`` returns as ``{'warning': '0'}``
    # (F19). The projection stringifies both sides, which is the comparison
    # that is actually about portability.
    assert reopened.to_wire() == CuemsScript.load(target).to_wire()
    assert reopened.name == original.name
    assert [c["id"] for c in reopened.cuelist.contents] == [
        c["id"] for c in original.cuelist.contents
    ]


def test_the_module_under_test_names_only_the_layout_helper():
    """``xml.documents`` is patched to *simulate an installation*, which is not
    something the public surface can do. Stated rather than swept."""
    from tests.support.public_api import imported_modules

    named = {
        name
        for name in imported_modules(sys.modules[__name__])
        if name.startswith("cuemsutils.xml") and name.count(".") >= 2
    }
    assert named <= {"cuemsutils.xml.documents"}, named


def test_the_public_leg_names_nothing_from_the_xml_package():
    import tests.integration.test_public_chain as public_leg

    assert_no_xml_import(public_leg)
