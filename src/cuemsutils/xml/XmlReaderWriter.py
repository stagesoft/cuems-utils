"""Deprecated import path — use :mod:`cuemsutils.xml.xml_reader_writer`.

Kept so that every consumer import written before the D9 rename keeps resolving
(FR-026a, contract C9). Removed in ``v0.1.1``.

**Importing this module is silent; using what it exports is not.** A
module-level re-export cannot satisfy FR-027b — an import warns at most once,
and in a long-running process that imported at startup it never warns again,
which is precisely when a consumer most needs telling. So each symbol is a
warning alias that fires on every instantiation and every public method call, at
the *caller's* line.

Nothing in this library imports from here. That is asserted by contract C8.
"""

from .._deprecation import deprecated_alias, deprecated_symbol
from .xml_reader_writer import CuemsXml as _CuemsXml
from .xml_reader_writer import XmlReader as _XmlReader
from .xml_reader_writer import XmlReaderWriter as _XmlReaderWriter
from .xml_reader_writer import XmlWriter as _XmlWriter
from .xml_reader_writer import get_pkg_schema as _get_pkg_schema

_NEW = "cuemsutils.xml.xml_reader_writer"

CuemsXml = deprecated_alias(_CuemsXml, f"{_NEW}.CuemsXml")
XmlReaderWriter = deprecated_alias(_XmlReaderWriter, f"{_NEW}.XmlReaderWriter")
get_pkg_schema = deprecated_symbol(f"{_NEW}.get_pkg_schema")(_get_pkg_schema)

# Deprecated twice over: by 0.0.7 in favour of ``XmlReaderWriter``, and again by
# the D9 rename. They are aliased from the new module rather than redeclared —
# redeclaring would create *different* classes at the two paths, so an
# ``isinstance`` check would depend on which import the caller happened to use.
XmlWriter = deprecated_alias(_XmlWriter, f"{_NEW}.XmlReaderWriter")
XmlReader = deprecated_alias(_XmlReader, f"{_NEW}.XmlReaderWriter")


__all__ = [
    "CuemsXml",
    "XmlReader",
    "XmlReaderWriter",
    "XmlWriter",
    "get_pkg_schema",
]
