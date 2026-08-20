"""The configuration object model (T044) — structure derived, naming by hand.

The rule, applied mechanically (data-model.md §1):

> **Structure is derived. Naming, ergonomics and semantics are hand-written.**

So every class here declares only its *field set*, and every field set comes
from the XSD. What an accessor is called, which mapping counts as "video", and
whether a region fits its canvas are decided in ``tools/ConfigBase.py``,
``tools/ConfigManager.py`` and ``xml/validators.py`` — not here.

The failure mode this exists to prevent is measured rather than hypothetical:
F14's five-level nested walk and F15's three mutually incompatible shapes for
one piece of data, two of them fossilised behind an unconditional
``return super().check_mappings()``. That is what hand-maintained structure
decays into.

## Why these classes do not coerce

``ConfigDict`` overrides ``from_decoded`` to store values **verbatim**, without
running the schema-derived adapter table. That is the opposite of what the show
model does, and the reason is a real difference between the two domains rather
than an inconsistency:

* A cue can be *built in Python* and *decoded from a document*, and feature 005
  exists because those two paths produced differently-typed objects. The
  adapter table is what makes them one object.
* A config object has exactly **one** construction path — decode. There is no
  second path to reconcile, so there is nothing for a coercion table to unify.
* Running the table anyway would **change values**. ``network_map.xsd`` types
  ``adopted`` and ``online`` as ``cms:BoolType``, which the show adapter turns
  into Python ``bool``; the recorded config goldens carry the strings
  ``"True"``/``"False"``, ``NetworkMap.get_nodes_by_adoption`` calls
  ``strtobool`` on them, and ``cuems-engine`` reads them as strings. FR-018
  freezes accessor *meaning*, and silently retyping two fields across a
  repository boundary is not a naming change.

The projection is unaffected: ``to_wire()`` runs the same adapters as the show
path, and every one of them is the identity on an already-correct value
(``_Bool.to_wire("True") == "True"``), which is what keeps SC-017's "one
implementation" true without importing the coercion difference into it.

## Why the decoded shape is preserved

Repeated content in a config document decodes as ``[{"node": {...}}, ...]`` —
the same single-key wrapper shape the show path produces for ``contents``. The
show model *collapses* that wrapper (``CueList.contents`` is a list of cues);
the config layer **keeps** it, because `cuems-engine` and `cuems-editor` read
it and this feature does not edit consumer repositories (FR-UX-001). Feature
008 executes the migration guide; until then the shape is a contract.

So `Mapper.decode_config` substitutes classes and changes nothing else. See its
docstring for the symmetry with ``decode``.
"""

from .base import ConfigDict

__all__ = ["ConfigDict"]
