# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T046 — the package's own build-time generation still succeeds (SC-008, M-f).

The measurement behind FR-021's sentinel exception. ``xml/make_defaults.py``
runs at **build time**, through the just-built venv's interpreter, and produces
the three documents ``postinst`` installs on a freshly configured node. Every one
of them carries the sentinel identity.

If the tightened pattern did not admit it, the ``.deb`` would fail to build —
or worse, build and install documents no node could load, which is the failure
feature 011 exists to prevent. So this is the test that keeps the exception
honest: it is not an exception for its own sake, it is the one value the base
package of the stack ships.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools import ids
from cuemsutils.xml.make_defaults import generate
from cuemsutils.xml.schema import get_schema

SCHEMA_OF = {
    "settings.xml": "settings",
    "network_map.xml": "network_map",
    "default_mappings.xml": "project_mappings",
}


@pytest.fixture
def generated(tmp_path):
    generate(tmp_path)
    return tmp_path


def test_generation_succeeds(generated):
    for name in SCHEMA_OF:
        assert (generated / name).is_file()


@pytest.mark.parametrize("name", sorted(SCHEMA_OF))
def test_each_generated_document_still_validates(generated, name):
    get_schema(SCHEMA_OF[name]).validate(str(generated / name))


@pytest.mark.parametrize("name", sorted(SCHEMA_OF))
def test_each_generated_document_carries_the_sentinel(generated, name):
    """The premise, restated as an assertion on the actual bytes. If this ever
    stops holding, the narrowing design changes rather than this test being
    updated (quickstart, "Verifying the sentinel premise")."""
    assert ids.NOT_PROVISIONED_UUID in (generated / name).read_text()


def test_a_generated_node_is_classified_not_provisioned_rather_than_broken(generated):
    """Feature 011 established the sentinel as the **coherent** state of a
    freshly installed node. The classification has to agree, or every new node
    would be reported as needing a cluster-wide re-mint."""
    import xml.etree.ElementTree as ET

    identity = ET.parse(generated / "settings.xml").getroot().findtext(".//uuid")
    assert ids.classify(identity) == ids.NOT_PROVISIONED_CLASS


def test_the_generated_documents_are_byte_identical_across_runs(tmp_path):
    """Determinism is feature 011's D-level requirement for these, and the
    narrowing must not have introduced a reason for them to move."""
    first, second = tmp_path / "a", tmp_path / "b"
    generate(first)
    generate(second)
    for name in SCHEMA_OF:
        assert (first / name).read_bytes() == (second / name).read_bytes()
