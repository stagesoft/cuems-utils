"""T008 — the corpus is complete, self-contained and covered.

Guards the three properties every other contract test in this feature silently
assumes: that the corpus is what ``PROVENANCE.md`` says it is, that it needs no
sibling checkout (FR-022b, SC-015), and that no document sits in it without a
golden (SC-009, SC-016).
"""

from __future__ import annotations

import json

import pytest

from tests.support.corpus import (
    CORPUS_ROOT,
    DOCUMENTS,
    GOLDEN_ROOT,
    PINNED_COUNTS,
    REPO_ROOT,
    SCHEMAS,
    discovered_xml_relpaths,
    documents,
)


def _outcomes() -> dict:
    return json.loads((GOLDEN_ROOT / "outcomes.json").read_text())


def test_manifest_and_disk_agree():
    """Neither may contain a document the other does not.

    Checked in *both* directions on purpose. A document on disk but not in the
    manifest is silently uncovered; a document in the manifest but not on disk
    turns every test that parametrises over it into a skip nobody notices.
    """
    manifest = sorted(d.relpath for d in DOCUMENTS)
    on_disk = discovered_xml_relpaths()
    assert manifest == on_disk, (
        f"manifest-only: {sorted(set(manifest) - set(on_disk))}\n"
        f"disk-only:     {sorted(set(on_disk) - set(manifest))}"
    )


@pytest.mark.parametrize("directory,expected", sorted(PINNED_COUNTS.items()))
def test_pinned_document_counts(directory, expected):
    """The corpus is a fixed number, not "whatever those directories hold".

    SC-PERF-001's new-suite budget is measured against this count, so a corpus
    that can grow or shrink silently makes that budget meaningless.
    """
    actual = len(documents(category=directory))
    assert actual == expected, (
        f"{directory}/ holds {actual} documents, PROVENANCE.md pins {expected}. "
        f"Adding a document is fine — update PROVENANCE.md and PINNED_COUNTS together."
    )


@pytest.mark.parametrize("schema", SCHEMAS)
def test_every_schema_has_a_document(schema):
    """SC-009 — all six schemas are represented."""
    assert documents(schema=schema), f"no corpus document uses {schema}.xsd"


@pytest.mark.parametrize("schema", SCHEMAS)
def test_every_schema_has_a_loadable_document(schema):
    """SC-009, sharpened: representation is not coverage.

    A schema whose only documents are rejected proves nothing about
    byte-identity — there is no dict and no XML to be identical to. ``outputs``
    is the live case: its sole vendored instance has a namespace typo, and the
    corrected copy in ``cuems-utils/`` is the only thing keeping this green.
    """
    outcomes = _outcomes()
    loadable = [
        d.relpath
        for d in documents(schema=schema)
        if outcomes.get(d.relpath, {}).get("read", {}).get("ok")
    ]
    assert loadable, (
        f"{schema}.xsd has corpus documents but none the library can read. "
        f"Byte-identity for this schema would be asserted against nothing."
    )


def test_every_document_has_a_golden():
    """SC-016 — a newly added document cannot silently go uncovered.

    Every document must appear in ``outcomes.json``; a document the library
    *reads* must additionally have a dict golden. Rejected documents correctly
    have no dict golden — their outcome record is their coverage.
    """
    outcomes = _outcomes()
    missing_outcome = [d.relpath for d in DOCUMENTS if d.relpath not in outcomes]
    assert not missing_outcome, (
        f"no golden outcome recorded for: {missing_outcome}. "
        f"Run `python -m tests.support.capture_goldens`."
    )

    missing_dict = [
        d.relpath
        for d in DOCUMENTS
        if outcomes[d.relpath]["read"]["ok"]
        and not (GOLDEN_ROOT / "dict" / f"{d.slug}.reader.json").exists()
    ]
    assert not missing_dict, f"readable but no dict golden: {missing_dict}"


def test_no_golden_without_a_document():
    """The reverse: a golden whose document was deleted must not linger.

    An orphaned golden is worse than a missing one — it keeps passing while
    covering nothing.
    """
    slugs = {d.slug for d in DOCUMENTS} | {"create_script"}
    # ``outcomes.json``, ``MANIFEST.sha256`` and ``api/`` are per-feature, not
    # per-document: the first records verdicts for the whole corpus, the
    # second (T002) hashes every golden for the immutability guard, the third
    # snapshots the public API surface (T019a). None maps to a slug.
    orphans = [
        str(p.relative_to(GOLDEN_ROOT))
        for p in GOLDEN_ROOT.rglob("*")
        if p.is_file()
        and p.name not in ("outcomes.json", "MANIFEST.sha256")
        and p.parent.name != "api"
        and p.name.split(".")[0] not in slugs
    ]
    assert not orphans, f"goldens with no corpus document: {orphans}"


def test_corpus_is_inside_this_repository():
    """FR-022b, SC-015 — the suite passes on a lone checkout.

    Cross-repo access was a one-time vendoring operation, not a dependency. If
    a document ever resolves outside this tree, the suite stops being runnable
    by anyone who has not checked out all four repositories.
    """
    for doc in DOCUMENTS:
        resolved = doc.path.resolve()
        assert resolved.is_file(), f"missing corpus document: {doc.relpath}"
        assert resolved.is_relative_to(REPO_ROOT.resolve()), (
            f"{doc.relpath} resolves to {resolved}, outside this repository"
        )
        assert resolved.is_relative_to(CORPUS_ROOT.resolve())


def test_provenance_and_negative_readme_exist():
    """FR-022a — a corpus without recorded provenance is a pile of files."""
    assert (CORPUS_ROOT / "PROVENANCE.md").is_file()
    assert (CORPUS_ROOT / "negative" / "README.md").is_file()
