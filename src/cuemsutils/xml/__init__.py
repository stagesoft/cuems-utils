"""XML serialization for the CueMS object model — **internal machinery**.

``__all__`` is empty (FR-019). This package exports nothing, and everything in
it is machinery behind two public entry points:

``cuemsutils.cues.CuemsScript.CuemsScript``
    show data — ``load``, ``save``, ``validate``, ``from_json``, ``to_json``,
    ``to_wire``.
``cuemsutils.tools.ConfigManager.ConfigManager``
    configuration.

**Dotted access still works this release, and is unsupported** (FR-019a).
``from cuemsutils.xml import XmlReaderWriter`` resolves and warns; it is gone in
``v0.1.1``. Keeping it functional is not an oversight — the deprecation shims
below *resolve through it*, so emptying ``__all__`` and making the names
unreachable are different changes. Genuine lockdown is feature 008's, together
with the consumer migration the shims exist to buy time for.

This docstring used to open *"The public surface is the five names in
``__all__``"*. That sentence and the ``__all__`` below would now contradict each
other, and a module whose docstring disagrees with its own exports is the first
thing a maintainer reads.
"""

# Import the deprecated-path shims FIRST, and do not remove these two lines.
#
# ``Settings.py`` and ``XmlReaderWriter.py`` are real submodules, so the *first*
# import of either makes Python set it as an attribute of this package —
# clobbering the class of the same name that the lines below bind. Whichever
# happens last wins, and before this import was made explicit the winner
# depended on whether some consumer had already imported the old path: the
# public ``from cuemsutils.xml import Settings`` then handed back a *module*,
# and calling it raised ``TypeError: 'module' object is not callable``.
#
# Importing them here forces that attribute assignment to happen before the
# class bindings, so the classes win permanently — Python sets the parent
# attribute only on a submodule's initial import. The old import paths keep
# working, and the package root keeps binding classes.
#
# Neither import emits a warning: the shims warn on use, never on import.
from . import Settings as _settings_shim  # noqa: F401
from . import XmlReaderWriter as _xml_reader_writer_shim  # noqa: F401
from ._deprecation import deprecated_alias
from .Parsers import CuemsParser as _CuemsParser
from .settings import NetworkMap as _NetworkMap
from .settings import ProjectMappings as _ProjectMappings
from .settings import ProjectSettings as _ProjectSettings
from .settings import Settings as _Settings
from .xml_reader_writer import XmlReaderWriter as _XmlReaderWriter

#: Where each retired entry point's traffic goes (T061, D2's migration map).
_SCRIPT = "cuemsutils.cues.CuemsScript.CuemsScript"
_CONFIG = "cuemsutils.tools.ConfigManager.ConfigManager"

#: The one per-method note in the whole feature (D2a).
#:
#: ``read()`` returns the reader dict; its replacement returns the projection,
#: and the two differ by the ``schemaLocation`` key — an XML artifact with no
#: meaning to a consumer. A caller told only "use ``to_wire`` instead" would
#: find that out by diffing payloads in production.
_READ_NOTE = "the returned dict no longer contains the schemaLocation key"

# The six supported entry points this feature retires (contract C3). Five were
# in ``__all__``; ``CuemsParser`` never was, and is the sixth because feature
# 004 made it a supported path deliberately — it is `cuems-editor`'s primary
# JSON -> object route. The library stopped calling it in T061a, which is what
# lets it carry a warning without tripping contract C8 on itself.
XmlReaderWriter = deprecated_alias(
    _XmlReaderWriter, _SCRIPT, notes={"read": _READ_NOTE}
)
CuemsParser = deprecated_alias(_CuemsParser, f"{_SCRIPT}.from_json")
Settings = deprecated_alias(_Settings, _CONFIG)
NetworkMap = deprecated_alias(_NetworkMap, _CONFIG)
ProjectMappings = deprecated_alias(_ProjectMappings, _CONFIG)
ProjectSettings = deprecated_alias(_ProjectSettings, _CONFIG)

#: Empty, and that is the surface statement (FR-019, SC-005).
#:
#: ``from cuemsutils.xml import *`` binds nothing. The names above remain
#: reachable by dotted access for one release and warn on use.
__all__: list[str] = []
