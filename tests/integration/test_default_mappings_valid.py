# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

from pathlib import Path

import pytest

from cuemsutils.xml import XmlReaderWriter

# This module exercises the deprecated XML surface (XmlReaderWriter / Parsers /
# XmlBuilder) on purpose. v0.1.2 deletes that surface, and this module with it or ported:
# specs/planning/deprecated-surface-removal-v0-1-2.md (R10). Feature 017, FR-029b.
pytestmark = pytest.mark.expects_deprecation


def test_default_mappings_validates_against_schema():
    # validate() raises xmlschema.XMLSchemaValidationError on drift.
    # We use validate() rather than read() because we only need the
    # pass/fail signal, not the parsed dict.
    fixture = Path(__file__).parent.parent / "data" / "default_mappings.xml"
    reader = XmlReaderWriter(
        schema_name="project_mappings",
        xmlfile=str(fixture),
    )
    reader.validate()
