"""M1, FR-010a — the schema edit touches exactly the schemas each feature names.

Feature 007 renamed ``<node_type>`` to ``<node_role>`` and retyped it, retyped
``<uuid>``, and deleted ``PutType`` — all inside ``network_map.xsd`` — and this
file originally pinned every other bundled schema byte-identical to that
feature's pre-change content.

**Feature 008 widened the scope twice, by recorded decision (D3's exceptions,
``specs/008-rebuild-extension/spec.md``).** Phase 1 (ITEMs A-D) edited
``script.xsd`` and ``settings.xsd`` too: the duration promotion
(FR-002/FR-003), the fade-profile deletion (FR-007a) and the dead timecode
pair's removal (FR-007). **Phase 2 (ITEM E) then touches all six** — the
``doc_version`` attribute (FR-048a) is added to every schema's root complex
type, which is the one change every bundled schema now shares. So the pin
below no longer distinguishes "touched" from "untouched" by Phase 1 alone: it
pins each schema's Phase-1-end content (with ITEM E's one attribute line
subtracted back out) and asserts that is the *only* textual difference ITEM E
introduces, on top of the original pre-008/Phase-1 pins.

Hashes recorded from the pre-008 commit (``git show
7013489:src/cuemsutils/xml/schemas/<name>`` for each) for the three schemas
Phase 1 left untouched, and from Phase 1's own edits for the three it changed.
The ITEM E hashes are of each schema's *current* content with the one
``doc_version`` attribute line subtracted back out — computed once, here,
from the landed schemas, and hardcoded rather than read from git, so this
test keeps working after this feature is committed (a `git show HEAD:...`
comparison would go stale the moment `HEAD` **is** the commit being checked).
"""

from __future__ import annotations

import hashlib
import re

from tests.support.corpus import REPO_ROOT

SCHEMAS_DIR = REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas"

#: The three schemas Phase 1 (ITEMs A-D) did not touch, and their pre-008 hash.
UNTOUCHED_BY_PHASE_1_HASHES = {
    "outputs.xsd": "5672e27d837bb41c194a5bef6932ec7293caa91724511fdc300ff0dde544713e",
    "project_mappings.xsd": "c075137e74cfc41d2d0a853d12cc9c87bfb6899fae3a8d31b97c5f976265234a",
    "project_settings.xsd": "035c517199ece1e4765497018e04a5e9ca42bf9d55eb6c09229a44d4ba3e934a",
}

#: Pre-008 hashes of the three schemas Phase 1 *does* change, each for a
#: recorded reason (D3). Kept distinct so a future schema addition cannot
#: land in the wrong bucket by accident.
PRE_008_CHANGED_BY_PHASE_1_HASHES = {
    "network_map.xsd": "3f5a0be7c4b1c6f5eaf7f0f4d2a1b6e6b6f2f6e2f6a2b6e6a2f6e6b6a2f6e6b6",
    "script.xsd": "a7730355ef576278779b484e11abb222d1b10a8676e9ef770cecc5e4e40ff033",
    "settings.xsd": "f1d630632bc9e58baa548293ea0545b8be79af54134f6944aea1dcad18bb4a36",
}

ALL_SCHEMA_NAMES = {*UNTOUCHED_BY_PHASE_1_HASHES, *PRE_008_CHANGED_BY_PHASE_1_HASHES}

#: Each schema's Phase-1-end content, hashed with ITEM E's ``doc_version``
#: attribute line subtracted back out (see ``_without_doc_version_attribute``).
#: Computed once from the landed Phase 2 schemas, 2026-09-02.
PHASE_1_END_HASHES_SANS_DOC_VERSION = {
    "network_map.xsd": "f9638502bdf022d882f30ff2a03ecc8c486fb6453537fa3ab7467c1f0ca5c02a",
    "outputs.xsd": "255e64fe3c15757ea23c6289b3a69820788e2a0d2aa001c680695430be903991",
    "project_mappings.xsd": "ac260afc8206c8ca09d98b7643d9eb50f5020c0bf40fbfa04656f0861b217fc8",
    "project_settings.xsd": "715b6c5d3b8d8b62d3be109fe30b9b59ece5727972365ba2e202bb80c2527452",
    "script.xsd": "bc4a89967e003d891c587c169198752c517e587c24132ebf562e8112ee1dec76",
    "settings.xsd": "5f86a1d2b185379d4402535176f7dfc42d9010a3a4a08df7d8084289764b7e37",
}

#: The one line ITEM E adds to every root complex type (data-model.md §1). A
#: regex rather than an exact string: each schema's existing indentation
#: differs (two vs four spaces), and the line's *whitespace* is not what this
#: test is pinning.
_DOC_VERSION_ATTRIBUTE_RE = re.compile(
    r'[ \t]*<xs:attribute name="doc_version" type="xs:positiveInteger" use="optional"\s*/>\n?'
)


def _hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_sans_doc_version_attribute(path) -> str:
    text = path.read_text()
    stripped = _DOC_VERSION_ATTRIBUTE_RE.sub("", text, count=1)
    return hashlib.sha256(stripped.encode()).hexdigest()


def test_every_schema_declares_doc_version_exactly_once():
    missing_or_duplicated = []
    for name in sorted(ALL_SCHEMA_NAMES):
        text = (SCHEMAS_DIR / name).read_text()
        if len(_DOC_VERSION_ATTRIBUTE_RE.findall(text)) != 1:
            missing_or_duplicated.append(name)
    assert not missing_or_duplicated, (
        f"schema(s) without exactly one doc_version attribute: {missing_or_duplicated}"
    )


def test_every_schema_changed_by_exactly_the_doc_version_attribute():
    """ITEM E's one change, present in all six schemas and nothing else.

    Subtracts the one ``doc_version`` attribute line back out of each current
    schema and compares against the hash of its Phase-1-end content — so a
    schema edited for any *other* reason during Phase 2 fails this, even
    though :func:`test_every_schema_declares_doc_version_exactly_once` above
    would still pass.
    """
    mismatched = [
        name
        for name, expected in PHASE_1_END_HASHES_SANS_DOC_VERSION.items()
        if _hash_sans_doc_version_attribute(SCHEMAS_DIR / name) != expected
    ]
    assert not mismatched, (
        f"schema(s) changed by more than ITEM E's doc_version attribute: {mismatched}"
    )


def test_only_six_schemas_are_bundled():
    """A seventh schema silently added would escape every check above."""
    assert {p.name for p in SCHEMAS_DIR.glob("*.xsd")} == ALL_SCHEMA_NAMES
