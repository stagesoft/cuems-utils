"""Deprecated import path — use :mod:`cuemsutils.xml.settings`.

Kept so that every consumer import written before the D9 rename keeps resolving
(FR-026a, contract C9). Removed in ``v0.1.1``.

Importing is silent; using what it exports is not — see the note in
:mod:`cuemsutils.xml.XmlReaderWriter`, which this module mirrors exactly.

Note that ``cuemsutils.xml.Settings`` resolves to the ``Settings`` *class*, not
to this module: the package's ``__init__`` re-exports it, and that binding wins.
Reaching this module requires ``import cuemsutils.xml.Settings as ...`` or
``from cuemsutils.xml.Settings import ...``, which is exactly what pre-rename
consumer code does. The collision is why the implementation moved to
``settings.py``.
"""

from ._deprecation import deprecated_alias
from .settings import NetworkMap as _NetworkMap
from .settings import ProjectMappings as _ProjectMappings
from .settings import ProjectSettings as _ProjectSettings
from .settings import Settings as _Settings

_NEW = "cuemsutils.xml.settings"

Settings = deprecated_alias(_Settings, f"{_NEW}.Settings")
NetworkMap = deprecated_alias(_NetworkMap, f"{_NEW}.NetworkMap")
ProjectMappings = deprecated_alias(_ProjectMappings, f"{_NEW}.ProjectMappings")
ProjectSettings = deprecated_alias(_ProjectSettings, f"{_NEW}.ProjectSettings")

__all__ = [
    "NetworkMap",
    "ProjectMappings",
    "ProjectSettings",
    "Settings",
]
