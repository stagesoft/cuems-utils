# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T069 — the deprecation advice names the right target per schema (FR-036, SC-015).

UR-5, first half. ``XmlReaderWriter.validate_object``'s warning sends every
caller at ``CuemsScript.validate``, which **cannot validate a configuration
document** — it builds a show document. So a consumer following the advice on a
``settings.xml`` is sent somewhere that will not work, which is worse than no
advice: they have no reason to doubt it.

Asserted on the **message text**, for all six schemas, because that text is the
whole deliverable. The alias is one class for every schema, so the
schema-specific part has to come from ``schema_name`` at the call rather than
from a second alias.
"""

from __future__ import annotations

import warnings

import pytest

from cuemsutils.xml import XmlReaderWriter

#: The four configuration schemas, which must be sent at the config validator.
CONFIG_SCHEMAS = ("settings", "network_map", "project_mappings", "project_settings")
#: The show schemas. ``hardware_outputs`` is a show schema used by the editor's
#: output picker, not a configuration document ``ConfigManager`` reads — stated
#: here because its classification is the one a reader is most likely to guess
#: wrong.
SCRIPT_SCHEMAS = ("script", "hardware_outputs")


def _advice(schema_name: str, tmp_path) -> str:
    """The ``validate_object`` deprecation message for ``schema_name``."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        writer = XmlReaderWriter(
            schema_name=schema_name, xmlfile=str(tmp_path / "doc.xml")
        )
        try:
            writer.validate_object(None)
        except Exception:
            # The call itself is expected to fail — ``None`` is not a document.
            # The warning is emitted before the work, which is the point.
            pass
    messages = [str(w.message) for w in caught if w.category is DeprecationWarning]
    advice = [m for m in messages if "validate" in m]
    assert advice, f"no validate advice emitted for {schema_name}: {messages}"
    return advice[-1]


@pytest.mark.parametrize("schema_name", CONFIG_SCHEMAS)
def test_a_configuration_document_is_sent_at_the_config_validator(schema_name, tmp_path):
    message = _advice(schema_name, tmp_path)
    assert "validate_config_document" in message, (
        f"{schema_name} is advised {message!r}; a configuration document cannot "
        f"be validated through CuemsScript"
    )


@pytest.mark.parametrize("schema_name", CONFIG_SCHEMAS)
def test_a_configuration_document_is_not_sent_at_cuemsscript_validate(
    schema_name, tmp_path
):
    """The negative half, stated separately so it cannot be satisfied by
    mentioning both targets in one message."""
    message = _advice(schema_name, tmp_path)
    assert "CuemsScript.validate" not in message, (
        f"{schema_name} is still advised to use CuemsScript.validate: {message!r}"
    )


@pytest.mark.parametrize("schema_name", SCRIPT_SCHEMAS)
def test_a_show_document_is_still_sent_at_cuemsscript_validate(schema_name, tmp_path):
    message = _advice(schema_name, tmp_path)
    assert "CuemsScript.validate" in message, (
        f"{schema_name} is advised {message!r}; a show document's validator did "
        f"not change"
    )


@pytest.mark.parametrize("schema_name", CONFIG_SCHEMAS + SCRIPT_SCHEMAS)
def test_every_schema_still_names_the_removal_release(schema_name, tmp_path):
    """One message format for every deprecation (FR-027a) still holds.

    The per-schema target is a change to *what* the message points at, not a
    second message format — which is the rule ``_deprecation.py``'s docstring
    exists to keep.
    """
    assert "removed in v0.1.1" in _advice(schema_name, tmp_path)
