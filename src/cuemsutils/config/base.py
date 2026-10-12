"""The one base class every configuration model shares (T044).

``CuemsDict`` with one difference, stated in the package docstring and repeated
here because this is where it is implemented: ``from_decoded`` stores values
verbatim rather than running the schema-derived adapter table.
"""

from __future__ import annotations

from os import PathLike

from ..helpers import CuemsDict


def save_document(obj, schema_name: str, path: "str | PathLike") -> None:
    """Validate (T1), then write atomically (feature 008, research R6).

    The one body every config domain's ``save()`` calls — ``settings``,
    ``project_settings``, ``project_mappings`` and the landed
    ``network_map`` all share this rather than repeating
    ``CuemsNetworkMapType.save``'s four lines four times (FR-013's symmetry
    requirement, answered by factoring a landed pattern rather than
    reinventing it per domain).

    Configuration schemas declare no ``xs:assert``, so there is one
    validation tier here (T2 is a ``script.xsd`` concept) — the first
    structural violation raises and nothing is written. Does not mutate
    ``obj``: ``build_tree`` reads declared fields through the adapters'
    ``to_lexical``/``to_wire`` and never writes back (FR-015). Atomicity is
    ``write_tree``'s: a temp file in the destination directory, then
    ``os.replace`` — a concurrent reader sees the whole old file or the whole
    new one, never a truncated document (FR-017).

    Args:
        obj: the root config object (a ``ConfigDict`` instance).
        schema_name: which bundled schema to validate and build against.
        path: where to write.

    Raises:
        SchemaError: ``obj`` does not match ``{schema_name}.xsd`` — carries
            the violation.
        OSError: propagated unwrapped, exactly as ``CuemsScript.save``.
    """
    from ..errors import SchemaError
    from ..xml.documents import build_tree, iter_schema_errors, write_tree
    from ..xml.validators import violation_from_schema_error

    tree = build_tree(obj, schema_name)
    for error in iter_schema_errors(schema_name, tree):
        violation = violation_from_schema_error(error)
        raise SchemaError(str(violation), violation=violation)
    write_tree(tree, path)


class ConfigDict(CuemsDict):
    """A declared-field model object for a configuration document.

    Inherits everything that matters — ``declared_fields``, ``items()``,
    ``to_wire()``, ``to_json()``, equality, copy — so config objects and show
    objects are the same kind of thing to every consumer that is not looking at
    their contents. The projection in particular is *the same method body*
    (``helpers.CuemsDict.to_wire``), which is what makes SC-017's "one
    implementation" a fact about the code (FR-014a).
    """

    #: An optional element that is **present and empty** stays in the payload.
    #:
    #: The show model materialises declared defaults for fields its document
    #: omitted (``fade_profiles`` becomes ``None``), so the projection has to
    #: drop optional-and-empty fields or it would emit elements the document
    #: never carried. Config declares **every** field :data:`Unset`, so an
    #: object holds exactly the keys its document had — and dropping one would
    #: lose information rather than restore it. ``project_mappings.xml``'s
    #: ``<dmx />`` is the measured case: present, empty, and recorded as
    #: ``"dmx": null`` in the config golden.
    OMIT_EMPTY_OPTIONAL = False

    @classmethod
    def from_decoded(cls, mapping: dict):
        """Build from a decoded document — **this method itself never coerces**.

        The show model's ``from_decoded`` runs each field's adapter, because a
        cue has two construction paths — built and decoded — and feature 005
        exists to make them agree. Config has one path, so there is nothing
        for *this method* to reconcile: it stores ``mapping``'s values
        verbatim, whatever they already are by the time they arrive here.

        **Whether they arrived coerced is decided earlier, per schema.**
        ``Mapper._decode_config_value`` (research R1) runs the adapter table
        on a scalar field only when its schema's registry has
        ``runs_adapter_table`` set — ``network_map`` only, as of feature 007.
        So ``node``'s ``mapping`` already carries a ``NodeRole`` for
        ``node_role`` and a ``bool`` for ``adopted``/``online`` by the time it
        reaches this method; ``Settings``'/``ProjectMappings``'/
        ``ProjectSettings``' mappings still carry the raw strings
        ``read_config_document`` produced, unchanged, because their schemas
        did not opt in. Retyping *those* here would be a behaviour change
        nothing in this feature enumerates, arriving through a base class
        rather than through a decision — which is exactly why the opt-in
        lives on the registry (one flag to audit) and not in this method.

        Undeclared keys are kept rather than dropped — the leaked
        ``schemaLocation`` at a config root is the only one — matching what the
        raw dicts carried. They are filtered at ``items()`` and at the
        projection, exactly as everywhere else.
        """
        obj = cls.__new__(cls)
        dict.__init__(obj)
        obj._init_runtime()

        for key, value in mapping.items():
            dict.__setitem__(obj, key, value)

        for key, default in cls.declared_defaults().items():
            if key in obj:
                continue
            from ..helpers import Unset

            if default is Unset:
                continue
            dict.__setitem__(obj, key, default() if callable(default) else default)

        return obj
