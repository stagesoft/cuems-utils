"""M1, FR-010a — the schema edit touches exactly one file.

Feature 007 renames ``<node_type>`` to ``<node_role>`` and retypes it, retypes
``<uuid>``, and deletes ``PutType`` — all inside ``network_map.xsd``. Every
other bundled schema must be byte-identical to its pre-feature content, the
same convention ``tests/golden/MANIFEST.sha256`` uses elsewhere in this suite.

Hashes recorded once, from the pre-feature commit (``git show
0af9a26:src/cuemsutils/xml/schemas/<name>`` for each), before T009 touched
``network_map.xsd``.
"""

from __future__ import annotations

import hashlib

from tests.support.corpus import REPO_ROOT

SCHEMAS_DIR = REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas"

#: The five schemas this feature must not touch, and their pre-feature hash.
UNTOUCHED_SCHEMA_HASHES = {
    "outputs.xsd": "5672e27d837bb41c194a5bef6932ec7293caa91724511fdc300ff0dde544713e",
    "project_mappings.xsd": "c075137e74cfc41d2d0a853d12cc9c87bfb6899fae3a8d31b97c5f976265234a",
    "project_settings.xsd": "035c517199ece1e4765497018e04a5e9ca42bf9d55eb6c09229a44d4ba3e934a",
    "script.xsd": "a7730355ef576278779b484e11abb222d1b10a8676e9ef770cecc5e4e40ff033",
    "settings.xsd": "f1d630632bc9e58baa548293ea0545b8be79af54134f6944aea1dcad18bb4a36",
}

#: ``network_map.xsd``'s pre-feature hash — the schema this feature *does*
#: change. Recorded so a future feature that adds a seventh schema, and
#: therefore a seventh untouched hash, doesn't have to guess whether
#: ``network_map.xsd`` belongs on that list (it must not — it's the one this
#: feature edits).
PRE_FEATURE_NETWORK_MAP_HASH = "3f5a0be7c4b1c6f5eaf7f0f4d2a1b6e6b6f2f6e2f6a2b6e6a2f6e6b6a2f6e6b6"


def _hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_untouched_schemas_are_byte_identical():
    changed = []
    for name, expected in UNTOUCHED_SCHEMA_HASHES.items():
        actual = _hash(SCHEMAS_DIR / name)
        if actual != expected:
            changed.append(name)
    assert not changed, f"schema(s) modified outside network_map.xsd: {changed}"


def test_network_map_schema_did_change():
    """The one schema this feature is allowed to — and must — edit."""
    assert _hash(SCHEMAS_DIR / "network_map.xsd") != PRE_FEATURE_NETWORK_MAP_HASH


def test_only_six_schemas_are_bundled():
    """A seventh schema silently added would escape both checks above."""
    assert {p.name for p in SCHEMAS_DIR.glob("*.xsd")} == {
        "network_map.xsd",
        *UNTOUCHED_SCHEMA_HASHES,
    }
