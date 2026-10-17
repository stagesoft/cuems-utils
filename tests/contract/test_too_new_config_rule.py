# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T037c — a too-new configuration document carries the show path's rule id (FR-049e).

A document newer than the library is its own outcome, and the recovery for it
is to upgrade the reader, never to repair the document. A consumer must be able
to tell it from an unrepairable document by a structured field. The show path
already gives one (``violation.rule == "document_version_too_new"``,
``tests/integration/test_conversion.py``); until this test, the configuration
path raised the same public ``ValidationError`` with **no** violation, so the
only way to tell was the sentence (the pattern ``cuems-editor`` UR-4 retired).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cuemsutils.errors import ValidationError
from cuemsutils.tools import validate_config_document
from cuemsutils.xml.versioning import CURRENT_VERSION, DOC_VERSION_ATTR

CORPUS = Path(__file__).resolve().parents[1] / "data" / "corpus"
VALID = {
    "settings": CORPUS / "cuems-utils" / "settings.xml",
    "network_map": CORPUS / "cuems-utils" / "network_map.xml",
    "project_mappings": CORPUS / "cuems-utils" / "project_mappings.xml",
    "project_settings": CORPUS / "cuems-engine" / "project_settings.xml",
}


def _too_new(tmp_path: Path, schema_name: str) -> Path:
    tree = ET.parse(VALID[schema_name])
    tree.getroot().set(DOC_VERSION_ATTR, str(CURRENT_VERSION[schema_name] + 1))
    target = tmp_path / VALID[schema_name].name
    tree.write(target, encoding="utf-8", xml_declaration=True)
    return target


@pytest.mark.parametrize("schema_name", sorted(VALID))
def test_a_too_new_configuration_document_names_its_rule(tmp_path, schema_name):
    with pytest.raises(ValidationError) as excinfo:
        validate_config_document(_too_new(tmp_path, schema_name))
    violation = excinfo.value.violation
    assert violation is not None, "the outcome must be structured, not only a sentence"
    assert violation.rule == "document_version_too_new"
    assert violation.tier == "T1"
