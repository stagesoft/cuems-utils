"""Deprecated import path — use :mod:`cuemsutils.tools.TimeoutLoop`.

Kept so that ``cuems-nodeconf``'s pre-existing import
(``from cuemsutils.timeoutloop import Timeoutloop``) keeps resolving. Removed
in ``v0.1.1``.

**Importing this module is silent; using what it exports is not.** A
module-level re-export cannot satisfy "warn on every use" — an import warns
at most once, and in a long-running daemon that imported at startup it never
warns again, which is precisely when a consumer most needs telling. So
``Timeoutloop`` is a warning alias that fires on every instantiation, at the
*caller's* line — see :func:`cuemsutils._deprecation.deprecated_alias`.

Renamed, not just relocated: the class is ``TimeoutLoop`` at the new path,
matching what ``README.md`` already documented before the code did.
``Timeoutloop`` (the old spelling) is this alias's name in *this* module's
namespace only; the class it wraps is named ``TimeoutLoop`` everywhere else,
including in its own ``repr()``.

Nothing in this library imports from here.
"""

from ._deprecation import deprecated_alias
from .tools.TimeoutLoop import TimeoutLoop as _TimeoutLoop

_NEW = "cuemsutils.tools.TimeoutLoop"

Timeoutloop = deprecated_alias(_TimeoutLoop, f"{_NEW}.TimeoutLoop")

__all__ = ["Timeoutloop"]
