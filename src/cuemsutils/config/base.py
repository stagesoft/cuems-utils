"""The one base class every configuration model shares (T044).

``CuemsDict`` with one difference, stated in the package docstring and repeated
here because this is where it is implemented: ``from_decoded`` stores values
verbatim rather than running the schema-derived adapter table.
"""

from __future__ import annotations

from ..helpers import CuemsDict


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
        """Build from a decoded document, **without coercing** (FR-018).

        The show model's ``from_decoded`` runs each field's adapter, because a
        cue has two construction paths — built and decoded — and feature 005
        exists to make them agree. Config has one path, so there is nothing to
        reconcile, and running the adapters would not unify anything: it would
        *change* values that consumers across two other repositories already
        read.

        The measured case is ``network_map.xsd``'s ``adopted``/``online``,
        typed ``cms:BoolType``. The show adapter decodes that to Python
        ``bool``; the recorded ``*.config.json`` goldens carry ``"True"``,
        ``NetworkMap.get_nodes_by_adoption`` calls ``strtobool`` on it, and
        ``cuems-engine`` branches on the string. Retyping it here would be a
        behaviour change nothing in this feature enumerates, arriving through a
        base class rather than through a decision.

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
