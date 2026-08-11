"""One message format for every deprecation in this package (FR-027).

**A message template, not a mechanism.** The mechanism is `deprecated==1.2.18`,
already a dependency and already used for `XmlReader`/`XmlWriter` since 0.0.7.
It supplies per-call emission, `extra_stacklevel` and class support natively;
none of that is reimplemented here, and this module must not grow into a second
warning system.

The one thing it cannot supply is FR-027a. Its ``version=`` renders as
*"Deprecated since version X"* (`deprecated/classic.py:71-72,151-153`) — that is
"deprecated since", not "removed in", so passing ``v0.1.1`` there would emit a
false statement on a shim that ships in ``v0.1.0``. The removal release and the
replacement pointer therefore live in ``reason=``, and fixing that string once
here is what makes FR-027's "one message format" true by construction rather
than by review across ~20 sites.
"""

import inspect

from deprecated import deprecated

#: The release that removes these shims (FR-027a). ``v0.1.0`` ships them with
#: warnings intact; they are gone in ``v0.1.1``.
REMOVAL_RELEASE = "v0.1.1"


def deprecation_reason(replacement: str) -> str:
    """The single message body: what to use instead, and when this goes away."""
    return f"use {replacement} instead; removed in {REMOVAL_RELEASE}"


def deprecated_symbol(replacement: str, extra_stacklevel: int = 0):
    """Decorator for a deprecated function or class.

    Warns on **every** call rather than once per import (FR-027b), and reports
    the caller's line rather than the shim's.
    """
    return deprecated(
        reason=deprecation_reason(replacement),
        category=DeprecationWarning,
        extra_stacklevel=extra_stacklevel,
    )


def deprecated_alias(target: type, replacement: str) -> type:
    """Build a warning stand-in for ``target`` to publish at its old path.

    A bare module-level re-export cannot satisfy FR-027b — importing a name
    twice warns at most once, and never at all in a long-running process that
    imported it at startup. So the alias is a subclass whose instantiation and
    whose public methods each warn at the caller's line.

    Subclassing rather than decorating ``target`` in place is deliberate: the
    decorator mutates the class it is given, so applying it to the real class
    would make the *new* import path warn too, and the shim would deprecate its
    own replacement.

    Instances remain ``isinstance`` of ``target``, so code that mixes old and
    new import paths keeps working — which is the entire point of shipping a
    shim rather than a breaking change.
    """
    namespace = {
        "__module__": target.__module__,
        "__doc__": (
            f"Deprecated alias for :class:`{target.__module__}.{target.__name__}`. "
            f"{deprecation_reason(replacement)}."
        ),
    }
    for name in dir(target):
        if name.startswith("_"):
            continue
        member = inspect.getattr_static(target, name, None)
        if not inspect.isfunction(member):
            continue
        namespace[name] = deprecated_symbol(f"{replacement}.{name}")(member)

    alias = type(target.__name__, (target,), namespace)
    return deprecated_symbol(replacement)(alias)
