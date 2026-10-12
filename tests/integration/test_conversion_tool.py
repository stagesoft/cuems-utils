"""The standalone conversion tool (ITEM E, US6, T098) — contracts §5, FR-042.

``cuems-convert-documents`` shares the **one** conversion registry the load
path consults (SC-019) — this file exercises the tool's own obligations on
top of that: a backup before every rewrite, a fatal-for-that-document-only
backup failure, and idempotence.
"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET

from cuemsutils.xml.convert_documents import ConversionOutcome, convert_file, main
from cuemsutils.xml.versioning import DOC_VERSION_ATTR
from tests.support.corpus import REPO_ROOT

PRE_008 = REPO_ROOT / "tests" / "data" / "corpus" / "pre-008"
ALL_TRANSFORMS = PRE_008 / "script_v1_all_transforms.xml"


def test_backs_up_before_rewriting_and_converts(tmp_path):
    target = tmp_path / "doc.xml"
    shutil.copy2(ALL_TRANSFORMS, target)

    status = convert_file(target)

    assert status == ConversionOutcome.CONVERTED
    backups = list(tmp_path.glob("doc.xml.*.bak"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == ALL_TRANSFORMS.read_bytes()

    tree = ET.parse(target)
    assert tree.getroot().attrib.get(DOC_VERSION_ATTR) == "2"


def test_a_current_document_is_left_untouched_and_reported_current(tmp_path):
    target = tmp_path / "doc.xml"
    shutil.copy2(ALL_TRANSFORMS, target)
    convert_file(target)  # first pass: converts
    before = target.read_bytes()

    status = convert_file(target)

    assert status == ConversionOutcome.CURRENT
    assert target.read_bytes() == before, "a current document must not be rewritten"


def test_idempotent_a_second_run_changes_no_bytes(tmp_path):
    target = tmp_path / "doc.xml"
    shutil.copy2(ALL_TRANSFORMS, target)

    convert_file(target)
    once = target.read_bytes()
    convert_file(target)
    twice = target.read_bytes()

    assert once == twice


def test_backup_failure_is_fatal_only_for_that_document(tmp_path, monkeypatch):
    """FR-042: a backup failure skips and reports the offending document, and
    does not abort the rest of the batch."""
    good = tmp_path / "good.xml"
    bad = tmp_path / "bad.xml"
    shutil.copy2(ALL_TRANSFORMS, good)
    shutil.copy2(ALL_TRANSFORMS, bad)

    import shutil as shutil_module

    original_copy2 = shutil_module.copy2

    def _fail_for_bad(src, dst, *a, **kw):
        if str(src) == str(bad):
            raise OSError("simulated backup failure")
        return original_copy2(src, dst, *a, **kw)

    monkeypatch.setattr("cuemsutils.xml.convert_documents.shutil.copy2", _fail_for_bad)

    bad_before = bad.read_bytes()
    exit_code = main([str(good), str(bad)])

    assert exit_code == 1, "a skipped document must be reflected in the exit code"
    assert bad.read_bytes() == bad_before, "the unbackupable document must not be rewritten"
    good_tree = ET.parse(good)
    assert good_tree.getroot().attrib.get(DOC_VERSION_ATTR) == "2", (
        "the rest of the batch must still be converted"
    )


def test_never_rewrites_without_a_successful_backup_first(tmp_path, monkeypatch):
    target = tmp_path / "doc.xml"
    shutil.copy2(ALL_TRANSFORMS, target)
    before = target.read_bytes()

    monkeypatch.setattr(
        "cuemsutils.xml.convert_documents.shutil.copy2",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("no backup possible")),
    )

    status = convert_file(target)

    assert status == ConversionOutcome.BACKUP_FAILED
    assert target.read_bytes() == before


def test_an_unrecognised_document_is_skipped_not_crashed(tmp_path):
    target = tmp_path / "not_cuems.xml"
    target.write_text("<?xml version='1.0'?><SomethingElse/>")

    status = convert_file(target)

    assert status == ConversionOutcome.UNRECOGNISED
