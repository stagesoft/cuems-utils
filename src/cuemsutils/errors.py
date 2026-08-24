"""The exception hierarchy consumers catch (T023a) — contract C5, FR-034.

**The one new public module this feature adds**, and the justification is
specific. A *returned* type can stay internal because the caller only inspects
what it is handed — that is why ``ValidationReport`` lives in
``xml/validators.py``. An *exception* is different: one the caller cannot name
is one the caller cannot catch, and the alternative consumers reach for is
matching on message strings.

Four types, and the shape of the tree is the contract:

``CuemsError``
    the base. Lets a consumer catch everything this library raises without
    also catching its own bugs.

``ValidationError``
    a document failed validation. Carries the **first** violation, in the same
    form ``validate()`` reports it (FR-034b) — implementing the type is not
    enough, because the failure mode is a consumer catching the exception and
    finding nothing on it to show a user.

``SchemaError``
    a **structural** (T1) failure specifically. A subclass of
    ``ValidationError`` on purpose: "does not match the schema" is a kind of
    "failed validation", so a caller that only cares about the distinction can
    make it and one that does not can ignore it.

``IngestError``
    the payload is not a script at all. Deliberately **not** a
    ``ValidationError``: nothing was validated, because there was nothing of
    the right shape to validate.

**I/O failures are not wrapped** (FR-035). A missing or unreadable file raises
the standard library's ``OSError``/``FileNotFoundError``, which every consumer
already handles. Wrapping it would force callers to unwrap it to find out what
actually happened.
"""

from __future__ import annotations

__all__ = ["CuemsError", "IngestError", "SchemaError", "ValidationError"]


class CuemsError(Exception):
    """Base class for every error this library raises deliberately."""


class ValidationError(CuemsError):
    """A document or object failed validation.

    Args:
        message: what went wrong, in the rule's own words.
        violation: the ``Violation`` that produced it — the **first** one, when
            the raising call site stops early (``save()``). ``None`` only when
            the failure has no single locus.
    """

    def __init__(self, message: str, violation=None):
        super().__init__(message)
        self.violation = violation


class SchemaError(ValidationError):
    """A structural (T1) failure: the document does not match its schema."""


class IngestError(CuemsError):
    """The payload is not a script at all.

    Raised by ``CuemsScript.from_json`` for a JSON array or scalar, a mapping
    whose root nothing recognises, malformed JSON, and bytes that are not valid
    UTF-8. The message names **what was expected** rather than surfacing a
    structural error from inside the machinery.
    """


# ---------------------------------------------------------------------------
# network_map migration diagnostics (feature 007, FR-011c, FR-011h-i, C8)
#
# ``tools/ConfigBase.py``'s ``load_config_document`` wraps every non-OSError
# read failure in ``SchemaError`` with a generic message. For network_map's
# two known failure modes — a document still carrying the retired
# ``<node_type>`` element, and a ``<node_role>`` value outside the enumeration
# — that generic wrap is upgraded to name the node, the offending value, the
# accepted values, and the remedy, rather than leaving a reader to parse an
# ``xmlschema`` stack trace to find out "run the conversion" is the answer.
# ---------------------------------------------------------------------------

#: Mirrors ``specs/007-node-model-migration/cuems_migrate_network_map.py``'s
#: mapping. Duplicated rather than imported — that script is stdlib-only,
#: lives outside ``src/`` for this pass, and must not import ``cuemsutils``
#: either way (the shared-venv rule).
_NETWORK_MAP_LEGACY_ROLE_VALUES = {
    "NodeType.master": "controller",
    "master": "controller",
    "NodeType.slave": "node",
    "slave": "node",
    "NodeType.firstrun": "firstrun",
    "firstrun": "firstrun",
}

#: ``network_map.xsd``'s ``NodeRoleType`` enumeration, spelled out here so the
#: message can name the accepted values without importing the schema loader
#: into this module.
NETWORK_MAP_ACCEPTED_ROLES = ("controller", "node", "firstrun")


def network_map_node_type_message(xmlfile: str, exc: Exception) -> str | None:
    """A migration-naming message for a document still carrying ``<node_type>``.

    Returns ``None`` when ``exc`` is not recognisably this failure, so the
    caller falls through to the generic wrap for every other schema error.
    """
    if getattr(exc, "invalid_tag", None) != "node_type":
        return None
    elem = getattr(exc, "elem", None)
    uuid_el = elem.find("uuid") if elem is not None else None
    node_type_el = elem.find("node_type") if elem is not None else None
    uuid = uuid_el.text if uuid_el is not None else "<uuid unknown>"
    value = node_type_el.text if node_type_el is not None else "<value unknown>"

    message = (
        f"{xmlfile}: node {uuid} still carries the retired <node_type> "
        f"element (value {value!r}) — network_map.xsd now requires "
        f"<node_role>, one of {list(NETWORK_MAP_ACCEPTED_ROLES)}. Run the "
        "network_map conversion (cuems-migrate-network-map) and retry."
    )
    replacement = _NETWORK_MAP_LEGACY_ROLE_VALUES.get(value)
    if replacement is not None:
        message += f" note: {value!r} is the retired spelling for {replacement!r}."
    return message


def network_map_role_enum_message(xmlfile: str, exc: Exception) -> str | None:
    """A message naming the field and accepted values for an out-of-vocabulary
    ``<node_role>``. Returns ``None`` when ``exc`` is not this failure."""
    elem = getattr(exc, "elem", None)
    if elem is None or getattr(elem, "tag", None) != "node_role":
        return None
    value = getattr(exc, "obj", None)
    return (
        f"{xmlfile}: <node_role>{value}</node_role> is not one of the "
        f"accepted values {list(NETWORK_MAP_ACCEPTED_ROLES)}. Edit the "
        "document to one of the accepted values and retry."
    )
