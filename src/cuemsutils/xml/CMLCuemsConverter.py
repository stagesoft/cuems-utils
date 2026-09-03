"""Deprecated import path — use :mod:`cuemsutils.xml.converter`.

Kept so that any consumer import written before this feature keeps resolving
(FR-026a, contract C9). Removed in ``v0.1.1``.

Importing is silent; using what it exports is not — see the note in
:mod:`cuemsutils.xml.XmlReaderWriter`, which this module mirrors.

The replacement, :class:`cuemsutils.xml.converter.CuemsConverter`, is not a
rename: the class published here was a **fork** of ``XMLSchemaConverter`` with
both ``element_decode`` and ``element_encode`` copied from an older
``xmlschema`` and then edited, and it imported
``xmlschema.validators.wildcards.Xsd11AnyElement`` — a non-public path.
``CuemsConverter`` overrides one method, rebuilds one block inside it, and
imports only public API (D5, research R11). Decoded output is byte-identical
across the whole corpus in both reader configurations.
"""

from .._deprecation import deprecated_alias
from .converter import CuemsConverter as _CuemsConverter

_NEW = "cuemsutils.xml.converter"

CMLCuemsConverter = deprecated_alias(_CuemsConverter, f"{_NEW}.CuemsConverter")

__all__ = ["CMLCuemsConverter"]
