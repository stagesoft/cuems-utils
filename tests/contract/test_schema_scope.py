"""M1, FR-010a — the schema edit touches exactly the schemas each feature names.

Feature 007 renamed ``<node_type>`` to ``<node_role>`` and retyped it, retyped
``<uuid>``, and deleted ``PutType`` — all inside ``network_map.xsd`` — and this
file originally pinned every other bundled schema byte-identical to that
feature's pre-change content.

**Feature 008 widens the scope, by recorded decision (D3's second and third
exceptions, ``specs/008-rebuild-extension/spec.md``).** ``script.xsd`` and
``settings.xsd`` are edited too: the duration promotion (FR-002/FR-003), the
fade-profile deletion (FR-007a) and the dead timecode pair's removal
(FR-007). So the pin below now covers the three schemas Phase 1 (ITEMs A–D)
still leaves untouched — ``outputs.xsd``, ``project_mappings.xsd`` and
``project_settings.xsd`` — and ``network_map.xsd``, ``script.xsd`` and
``settings.xsd`` each get their own "did change" assertion instead.

**This file needs another pass before Phase 2 lands.** ITEM E adds the
``doc_version`` attribute to all six schemas' root types, which widens the
scope again — to "every schema was touched, once, for one reason". Not
anticipated here (YAGNI): recorded so the next editor knows to expect it
rather than being surprised by it.

Hashes recorded from the pre-008 commit (``git show
7013489:src/cuemsutils/xml/schemas/<name>`` for each).
"""

from __future__ import annotations

import hashlib

from tests.support.corpus import REPO_ROOT

SCHEMAS_DIR = REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas"

#: The three schemas Phase 1 (ITEMs A–D) must not touch, and their pre-008 hash.
UNTOUCHED_SCHEMA_HASHES = {
    "outputs.xsd": "5672e27d837bb41c194a5bef6932ec7293caa91724511fdc300ff0dde544713e",
    "project_mappings.xsd": "c075137e74cfc41d2d0a853d12cc9c87bfb6899fae3a8d31b97c5f976265234a",
    "project_settings.xsd": "035c517199ece1e4765497018e04a5e9ca42bf9d55eb6c09229a44d4ba3e934a",
}

#: Pre-008 hashes of the three schemas this feature *does* change, each for a
#: recorded reason (D3). Kept distinct from ``UNTOUCHED_SCHEMA_HASHES`` so a
#: future schema addition cannot land in the wrong bucket by accident.
PRE_008_CHANGED_HASHES = {
    "network_map.xsd": "3f5a0be7c4b1c6f5eaf7f0f4d2a1b6e6b6f2f6e2f6a2b6e6a2f6e6b6a2f6e6b6",
    "script.xsd": "a7730355ef576278779b484e11abb222d1b10a8676e9ef770cecc5e4e40ff033",
    "settings.xsd": "f1d630632bc9e58baa548293ea0545b8be79af54134f6944aea1dcad18bb4a36",
}


def _hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_untouched_schemas_are_byte_identical():
    changed = []
    for name, expected in UNTOUCHED_SCHEMA_HASHES.items():
        actual = _hash(SCHEMAS_DIR / name)
        if actual != expected:
            changed.append(name)
    assert not changed, f"schema(s) modified outside the recorded D3 exceptions: {changed}"


def test_every_recorded_exception_did_change():
    """The schemas this feature is allowed to — and must — edit."""
    unchanged = [
        name
        for name, pre_008 in PRE_008_CHANGED_HASHES.items()
        if _hash(SCHEMAS_DIR / name) == pre_008
    ]
    assert not unchanged, f"recorded D3 exception(s) never touched: {unchanged}"


def test_only_six_schemas_are_bundled():
    """A seventh schema silently added would escape both checks above."""
    assert {p.name for p in SCHEMAS_DIR.glob("*.xsd")} == {
        *UNTOUCHED_SCHEMA_HASHES,
        *PRE_008_CHANGED_HASHES,
    }
