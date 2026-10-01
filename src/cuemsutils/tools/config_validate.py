# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``validate_config_document`` — ask whether a configuration document is valid.

UR-5's second half (feature 013, FR-036, T060). Before this there was no way to
answer that question without constructing a ``ConfigManager``, which wants a
whole installation: a ``settings.xml`` to find, a library path to resolve, a
node identity to recognise. ``CuemsScript.validate`` exists for show documents
and cannot help — it builds a show document.

**The consumer imports the façade**, ``from cuemsutils.tools import
validate_config_document``, and never names this module. The re-export in
``tools/__init__.py`` is lazy for the reason that package's docstring gives: a
top-level import here would make ``import cuemsutils.tools.CTimecode`` pull the
whole schema layer.

**It reports rather than merely refusing.** The answer is feature 008's existing
``LoadReport``/``Outcome``/``RepairRecord``/``ConversionRecord`` — the same
vocabulary a show document reports through — so a caller learns *what* is wrong
and not only *that* something is, and no second report type exists to drift from
the first. No new exception type either: the error postures are
``ConfigBase.load_config_document``'s, deliberately, so a document validated here
and the same document loaded by ``ConfigManager`` fail the same way.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from os import PathLike

from ..errors import LoadReport, Outcome, SchemaError

#: The four schemas this function accepts, each with the reader that decodes it.
#: Resolved lazily inside :func:`validate_config_document` — naming the classes
#: here would defeat the laziness the façade's re-export exists for.
_CONFIG_SCHEMAS = ("settings", "network_map", "project_mappings", "project_settings")


def _reader_for(schema_name: str):
    from ..xml.settings import NetworkMap, ProjectMappings, ProjectSettings, Settings

    return {
        "settings": Settings,
        "network_map": NetworkMap,
        "project_mappings": ProjectMappings,
        "project_settings": ProjectSettings,
    }[schema_name]


def _schema_name_for(path) -> str:
    """Which schema ``path`` belongs to, from its **root element**.

    Not from ``xsi:schemaLocation``: that hint is never resolved for validation
    either (``mapper.build_document``'s docstring), and a self-reported,
    possibly stale value is not ground truth for what a document is. Same rule
    ``cuems-convert-documents`` and ``cuems-reshape-devices`` apply, so the three
    agree on what they are looking at.
    """
    from ..xml.schema import SCHEMA_ROOTS

    if not os.path.exists(path):
        # ``FileNotFoundError`` rather than a parse error, and unwrapped: every
        # consumer already handles ``OSError``, and wrapping it would force
        # them to unwrap to find out what actually happened (FR-035).
        raise FileNotFoundError(f"No such file: {path}")
    try:
        root = ET.parse(os.fspath(path)).getroot()
    except ET.ParseError as exc:
        raise SchemaError(f"{path} is not well-formed XML: {exc}") from exc

    local = root.tag.rsplit("}", 1)[-1]
    for schema_name, root_tag in SCHEMA_ROOTS.items():
        if root_tag == local:
            if schema_name in _CONFIG_SCHEMAS:
                return schema_name
            # A show schema reached a configuration validator. Saying "not a
            # configuration document" and stopping would leave the caller with
            # nowhere to go, which is the defect FR-036's first half fixes in
            # the deprecation advice — so this message names the right target
            # too.
            target = (
                "cuemsutils.cues.CuemsScript.CuemsScript.validate"
                if schema_name == "script"
                else "the schema directly; it has no configuration accessor"
            )
            raise SchemaError(
                f"{path} is a {schema_name} document, which is not one of the "
                f"four configuration schemas "
                f"({', '.join(_CONFIG_SCHEMAS)}). Validate it with {target}."
            )
    raise SchemaError(
        f"{path} has root element <{local}>, which no bundled schema declares. "
        f"The configuration roots are: "
        + ", ".join(f"<{SCHEMA_ROOTS[name]}>" for name in _CONFIG_SCHEMAS)
        + "."
    )


def validate_config_document(path: str | PathLike) -> LoadReport:
    """Validate one configuration document, with no installation involved.

    Runs the same T1 (structural) and T2 (semantic) passes the accessor runs,
    on the same engine, and reports the outcome.

    Args:
        path: a ``settings``, ``network_map``, ``project_mappings`` or
            ``project_settings`` document. The schema is read from the root
            element, not from the filename and not from ``xsi:schemaLocation``.

    Returns:
        LoadReport: ``outcome`` is ``CLEAN``, ``CONVERTED`` when a registered
        version conversion ran **in memory**, or ``REPAIRED`` when a repairable
        T2 violation was repaired in the decoded object.
        ``file_differs_from_loaded`` says whether the file on disk is now stale
        with respect to what was loaded — this function never writes, so it is
        a statement about the document, not about an action taken.

    Raises:
        OSError: the file does not exist, unwrapped (FR-035).
        SchemaError: the document is not well-formed, its root element belongs
            to no bundled schema, it belongs to a schema that is not a
            configuration schema, or it fails T1. The message names the
            offending element.
        ValidationError: a version newer than this library, or an
            **unrepairable** T2 violation — the same distinction a show
            document gets (feature 008, FR-037). ``project_mappings``'
            ``one_custom_template_per_node`` is the one registered
            configuration T2 rule and is ``repairable=False``.
    """
    from .ConfigBase import load_config_document

    schema_name = _schema_name_for(path)
    reader = load_config_document(_reader_for(schema_name), os.fspath(path), schema_name)

    # T2, on the decoded object, exactly as ``CuemsScript.load_with_report``
    # does for a show document. ``repair`` raises on the first unrepairable
    # violation (FR-044), which is what turns a semantic failure into a
    # ``ValidationError`` rather than a report nobody reads.
    from ..errors import ConversionRecord
    from ..xml.validators import repair

    repairs = repair(reader.get_dict())

    conversions = tuple(
        ConversionRecord(
            step.from_version, step.to_version, step.description, step.dropped_elements
        )
        for step in getattr(reader, "document_conversions", ())
    )

    if repairs:
        outcome = Outcome.REPAIRED
    elif conversions:
        outcome = Outcome.CONVERTED
    else:
        outcome = Outcome.CLEAN

    return LoadReport(
        document=str(path),
        outcome=outcome,
        conversions=conversions,
        repairs=tuple(repairs),
        file_differs_from_loaded=outcome is not Outcome.CLEAN,
    )
