"""T015 / FR-025 — a named, tested public equivalent per internal import.

Feature 010, US3. `cuems-nodeconf` reaches into `cuemsutils.xml` today
(`CuemsNodeConf.py:22-23`), which Q14 forbids and which no feature had recorded
as a violation until C4. This feature ends it, and FR-025 says how: **each**
internal import acquires a *named, tested* public equivalent, and where one
already exists the guide names it rather than the library adding a synonym.

"Tested" means what FR-025 says it means: a test asserts the public equivalent
returns a result **equal to** the internal import's for the same input, so an
equivalent that merely resolves is distinguishable from one that preserves
behaviour.

**Measured 2026-09-04, and it changes the shape of the task**: of the three names
imported, only one has a call site. `Mapper` and `read_config_document` appear
exactly once each in that repository — on the import line itself. Their migration
target is **deletion**, not replacement, and a "public equivalent" for them would
be a synonym invented for nobody.
"""

from __future__ import annotations

from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parents[1] / "data"


def _network_map_path() -> Path:
    candidate = CORPUS / "network_map.xml"
    if not candidate.is_file():
        pytest.skip(f"no network_map fixture at {candidate}")
    return candidate


def test_the_network_map_reader_has_an_equal_public_equivalent():
    """``cuemsutils.xml.settings.NetworkMap`` (internal, used at
    ``CuemsNodeConf.py:567``) against ``ConfigManager.network_map``.

    The assertion is **equality of result**, not merely that both run.
    """
    from cuemsutils.tools.ConfigManager import ConfigManager
    from cuemsutils.xml.settings import NetworkMap as InternalReader

    path = _network_map_path()

    internal = InternalReader(str(path)).get_dict()

    manager = ConfigManager(config_dir=str(path.parent), load_all=False)
    manager.load_network_map()
    public = manager.network_map

    assert public == internal.get("CuemsNetworkMap", internal), (
        "the public path must return what the internal reader returns, "
        "or it is a different reader wearing a public name"
    )


def test_the_two_unused_imports_have_no_call_site_to_replace():
    """``Mapper`` and ``read_config_document`` are imported by
    ``cuems-nodeconf`` and never called.

    Asserted here as a **property of this library**, not of that repository —
    a test cannot reach a sibling checkout. What it pins is the claim the
    migration guide makes about them: they are internal, and nothing in
    ``cuemsutils``' own public surface exposes or needs them, so "delete the
    import" is a complete migration rather than a deferred one.
    """
    import cuemsutils.xml as xml_package
    from cuemsutils.tools.ConfigManager import ConfigManager

    assert not hasattr(xml_package, "Mapper")
    assert not hasattr(xml_package, "read_config_document")
    assert not hasattr(ConfigManager, "Mapper")
