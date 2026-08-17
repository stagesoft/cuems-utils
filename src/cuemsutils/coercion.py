"""Per-class coercion tables — the model's single coercion site (FR-001).

Feature 005's premise is that an object's internal types must not depend on how
it was made. Today they do: property setters coerce, so a value assigned through
``script.id = …`` becomes a ``Uuid`` while the same value written by the decoder's
raw ``dict.__setitem__`` stays a string. Moving coercion here — behind one table
per class, resolved from the schema — is what makes the built, XML-decoded and
JSON-decoded objects the same object (FR-007).

**Why a resolver rather than a declaration.** The obvious alternative is to name
an adapter per field in ``REQ_ITEMS``. That would be a second source of truth for
a field's type, which D2 forbids: the XSD already states it. Here the type still
comes from the schema via ``TypeSpec``; only the lookup direction is new.

**Why this module sits at the package root** rather than under ``xml/``. The
import direction is one-way today — ``xml/`` imports ``cues/`` and ``cues/``
imports nothing from ``xml/``. The model layer needs the adapters, so a
module-scope import from ``cues/`` would close the cycle. The imports inside
``_resolve`` are therefore **function-local**, and that placement is what keeps
the direction one-way; by the time any model object is constructed, both packages
are importable (research R1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at runtime
    from .xml.adapters import Adapter

#: Resolved tables, keyed on the **exact** class.
#:
#: Deliberately a module-level dict rather than an attribute set on the class.
#: ``cls._table = …`` would be inherited through the MRO by every subclass, so
#: the first cue type constructed would hand its adapters to all the others —
#: ``AudioCue`` coercing ``VideoCue``'s fields, silently and only for the fields
#: the two happen not to share. A dict keyed on the class object cannot do that.
_TABLES: dict[type, dict[str, "Adapter"]] = {}


class AmbiguousBindingError(RuntimeError):
    """A model class is bound in more than one schema registry.

    Registries are **per schema** on purpose (research R4): ``script.xsd`` and
    ``outputs.xsd`` both declare ``OutputsType`` with different content. So
    "which adapters does this class use?" has a well-defined answer only while a
    class is bound in exactly one registry.

    It is, today. The five configuration registries bind every type to
    ``GENERIC`` (``registry.py``), so no model class resolves in them at all.
    That stops being true in **feature 006**, which gives configuration
    documents model classes — at which point ``coercion_table()`` needs a schema
    argument and every call site changes. This error is what makes that arrive
    as a named failure rather than as objects silently coerced by whichever
    registry happened to resolve first.
    """

    def __init__(self, cls: type, schema_names: list[str]):
        self.cls = cls
        self.schema_names = schema_names
        super().__init__(
            f"{cls.__module__}.{cls.__qualname__} is bound in "
            f"{len(schema_names)} registries ({', '.join(sorted(schema_names))}), "
            f"so its coercion table is ambiguous. Registries are per schema "
            f"(research R4); adapter_table() takes no schema argument because "
            f"every model class was bound in exactly one. Give the resolver a "
            f"schema argument, or bind the class in one registry."
        )


def adapter_table(cls: type) -> dict[str, "Adapter"]:
    """The ``{field name: Adapter}`` table for ``cls``, built once.

    A field with no entry is **not** an error: it means the schema declares no
    type this module has a codec for, and the value is left exactly as it
    arrived. Call sites read the table with ``.get(name, PASSTHROUGH)``, which is
    also what a class with no registry binding gets for every field — an empty
    table, and therefore no coercion at all.

    Built once per class and cached for the process. The cache is what keeps
    SC-PERF-003 true: the table is resolved per *class*, never per object, so a
    1000-cue script does 19 resolutions, not 1000.
    """
    table = _TABLES.get(cls)
    if table is None:
        table = _TABLES[cls] = _resolve(cls)
    return table


def _resolve(cls: type) -> dict[str, "Adapter"]:
    # Function-local, and that is the load-bearing detail — see the module
    # docstring. Moving these to module scope closes the import cycle.
    from .xml.adapters import adapter_for
    from .xml.registry import all_registries

    found = [
        (schema_name, spec)
        for schema_name, registry in all_registries().items()
        if (spec := registry.spec_for_model(cls)) is not None
    ]

    if len(found) > 1:
        raise AmbiguousBindingError(cls, [name for name, _ in found])
    if not found:
        return {}

    _, spec = found[0]
    # The wildcard field spec carries an empty name (``UiPropertiesType``'s
    # ``xs:any``); it describes no field, so it gets no entry.
    return {
        field.name: adapter_for(field.xsd_type) for field in spec.fields if field.name
    }


def clear_cache() -> None:
    """Drop every resolved table. For tests that rebuild registries."""
    _TABLES.clear()
