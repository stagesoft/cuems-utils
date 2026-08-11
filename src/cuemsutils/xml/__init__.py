"""XML serialization for the CueMS object model.

The public surface is the five names in ``__all__``. Everything else in this
package is internal machinery (Q14).
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
# working, and the package root keeps exporting classes.
#
# Neither import emits a warning: the shims warn on use, never on import.
from . import Settings as _settings_shim  # noqa: F401
from . import XmlReaderWriter as _xml_reader_writer_shim  # noqa: F401
from .settings import NetworkMap, ProjectMappings, ProjectSettings, Settings
from .xml_reader_writer import XmlReaderWriter

__all__ = [
    'NetworkMap',
    'ProjectMappings',
    'ProjectSettings',
    'Settings',
    'XmlReaderWriter',
]
