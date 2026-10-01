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

import functools
import inspect
import warnings

from deprecated import deprecated

#: The release that removes these shims (FR-027a). ``v0.1.0`` ships them with
#: warnings intact; they are gone in ``v0.1.1``.
REMOVAL_RELEASE = "v0.1.1"


def deprecation_reason(replacement: str, note: str | None = None) -> str:
    """The single message body: what to use instead, and when this goes away.

    ``note`` appends one clause, and exists for exactly one message (D2a):
    ``XmlReaderWriter.read`` is replaced by ``CuemsScript.to_wire()``, whose
    output differs from ``read()``'s by one key — the ``schemaLocation``
    artifact. A consumer told only "use ``to_wire`` instead" would find that
    out by comparing payloads in production.

    Still **one** function producing every message, so the standing "no second
    warning system" rule holds. Every message without a note renders
    byte-identically to what it rendered before this parameter existed.
    """
    body = f"use {replacement} instead; removed in {REMOVAL_RELEASE}"
    return f"{body}; note: {note}" if note else body


def deprecated_symbol(
    replacement: str, extra_stacklevel: int = 0, note: str | None = None
):
    """Decorator for a deprecated function or class.

    Warns on **every** call rather than once per import (FR-027b), and reports
    the caller's line rather than the shim's.
    """
    return deprecated(
        reason=deprecation_reason(replacement, note),
        category=DeprecationWarning,
        extra_stacklevel=extra_stacklevel,
    )


def _per_instance_deprecated(method, advice_for, note: str | None = None):
    """A deprecated method whose **replacement is decided at the call**.

    ``deprecated`` bakes the message when the class is built, which is right
    whenever the replacement is a property of the method. It is wrong when the
    replacement depends on the *instance*: ``XmlReaderWriter`` is one class for
    all six schemas, and ``validate_object``'s correct target depends on which
    schema the instance was constructed for (feature 013, FR-036) — a
    configuration document cannot be validated through ``CuemsScript``.

    ``advice_for`` receives ``self.schema_name`` and returns the replacement.
    The message body still comes from :func:`deprecation_reason`, so this stays
    one message format rather than becoming a second warning system — the rule
    this module's docstring exists to keep.

    ``stacklevel=2`` reports the caller's line, matching what
    ``extra_stacklevel`` buys on the baked path.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        warnings.warn(
            deprecation_reason(advice_for(getattr(self, "schema_name", None)), note),
            category=DeprecationWarning,
            stacklevel=2,
        )
        return method(self, *args, **kwargs)

    return wrapper


def deprecated_alias(
    target: type,
    replacement: str,
    notes: dict[str, str] | None = None,
    replacements: dict[str, str] | None = None,
    per_instance: dict | None = None,
) -> type:
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

    ``notes`` attaches a per-method clause, keyed by method name. One method
    needs it (D2a): ``read``'s replacement returns a payload that differs from
    ``read()``'s by the ``schemaLocation`` key, and a consumer told only the
    replacement's name would discover that in production.

    ``replacements`` overrides the **name** a method is pointed at. Without it
    the message is composed mechanically as ``f"{replacement}.{name}"``, which
    is right when the method keeps its name and wrong when it does not:
    ``XmlReaderWriter.read`` would be reported as *"use CuemsScript.read"* — a
    method that does not exist. D2's migration map renames four of them
    (``read`` -> ``to_wire``, ``read_to_objects`` -> ``load``,
    ``write_from_object`` -> ``save``, ``validate_object`` -> ``validate``),
    and a deprecation warning that names a nonexistent replacement is worse
    than one that names none.

    ``per_instance`` maps a method name to a callable taking the instance's
    ``schema_name`` and returning the replacement, for the one case where the
    right target is not knowable when the class is built — see
    :func:`_per_instance_deprecated`. It takes precedence over ``replacements``
    for that method.
    """
    notes = notes or {}
    replacements = replacements or {}
    per_instance = per_instance or {}
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
        if name in per_instance:
            namespace[name] = _per_instance_deprecated(
                member, per_instance[name], note=notes.get(name)
            )
            continue
        namespace[name] = deprecated_symbol(
            replacements.get(name, f"{replacement}.{name}"), note=notes.get(name)
        )(member)

    alias = type(target.__name__, (target,), namespace)
    return deprecated_symbol(replacement)(alias)
