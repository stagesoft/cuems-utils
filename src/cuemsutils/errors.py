"""The exception hierarchy consumers catch (T023a) — contract C5, FR-034.

**The one new public module this feature adds**, and the justification is
specific. A *returned* type can stay internal because the caller only inspects
what it is handed — that is why ``ValidationReport`` lives in
``xml/validators.py``. An *exception* is different: one the caller cannot name
is one the caller cannot catch, and the alternative consumers reach for is
matching on message strings.

Four types shipped with feature 006, and a fifth joined in feature 009 — the shape of the tree is
still the contract:

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

``DmxChannelDecodeError`` (feature 009)
    a DMX channel entry could not be converted. Deliberately a direct
    ``CuemsError`` subclass, not a ``ValidationError``: this is unreachable
    from a schema-valid document (T1 already rejects the malformed shape), so
    it is never a *document* validation outcome — only a payload that bypassed
    schema validation entirely (``CuemsScript.from_json``, direct
    construction) can trigger it.

**I/O failures are not wrapped** (FR-035). A missing or unreadable file raises
the standard library's ``OSError``/``FileNotFoundError``, which every consumer
already handles. Wrapping it would force callers to unwrap it to find out what
actually happened.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "CuemsError",
    "DmxChannelDecodeError",
    "IngestError",
    "SchemaError",
    "ValidationError",
    "ConversionRecord",
    "LoadReport",
    "Outcome",
    "RepairRecord",
]


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


class DmxChannelDecodeError(CuemsError):
    """A DMX channel entry could not be converted to a ``DmxChannel`` (FR-001).

    Raised by ``DmxUniverse.set_dmx_channels`` (feature 009) in place of that
    method's former swallow-and-log fallback, which stored the raw,
    unconverted ``channels`` argument on any single entry's ``KeyError``/
    ``TypeError`` — silently corrupting every entry in the batch, not just the
    offending one. Unreachable from a schema-valid ``script.xml`` (T1 already
    rejects a malformed ``<DmxChannel>``); reachable from ``CuemsScript.from_json``
    or direct/programmatic construction (FR-007).

    Carries **identifiers only, never the object repr** (FR-002, FR-UX-001),
    mirroring ``DmxSceneWriteError``'s (``xml/mapper.py``) precedent: the
    universe, the failing entry's index, and the failing entry itself (for
    programmatic inspection only — never rendered into the message, which
    names only the entry's type).
    """

    def __init__(self, universe, index: int, entry: object):
        self.universe = universe
        self.index = index
        self.entry = entry

        try:
            universe_num = universe.universe_num
        except Exception:  # noqa: BLE001 - a broken universe must still name itself
            universe_num = "<universe_num unknown>"

        super().__init__(
            f"DMX channel entry at index {index} in universe {universe_num!r} "
            f"could not be converted to a DmxChannel (entry: {type(entry).__name__})."
        )


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


def project_mappings_semantic_message(exc: Exception) -> str | None:
    """Whether ``exc`` is ``project_mappings``' one T2 (semantic) violation.

    ``ProjectMappings._validate_custom_templates`` delegates to
    ``xml.validators.check_canvas_region_containment`` /
    ``check_one_custom_template_per_node`` — the same two checks the
    registered ``one_custom_template_per_node`` T2 rule delegates to (feature
    008, ITEM D) — and both raise a plain ``ValueError``. Recognised by
    message shape, matching the pattern this module already uses for
    ``network_map``'s two known failure modes, so ``load_config_document`` can
    tell a **semantic** (T2) violation from a **structural** (T1) one and
    raise the right exception type (feature 008, FR-037).
    """
    # Matched against the **exact** wording ``check_canvas_region_containment``
    # / ``check_one_custom_template_per_node`` raise (``xml/validators.py``),
    # not a loose substring — an auto-generated ``xmlschema`` structural (T1)
    # message can legitimately name the ``canvas_region`` *element* too (e.g.
    # "Unexpected child with tag 'canvas_region'"), and that must stay a
    # ``SchemaError``, not be reclassified as this rule's ``ValidationError``.
    message = str(exc)
    if "canvas_region" in message and "must be <= 1, got" in message:
        return message
    if "custom templates (canvas_region entries); at most" in message:
        return message
    return None


# ---------------------------------------------------------------------------
# The repair report (feature 008, ITEM E, US7) — data-model.md §4.
#
# Public, joining ``ValidationError``/``SchemaError``/``IngestError`` on 006's
# precedent: a repair the caller cannot inspect is one it cannot surface.
# ---------------------------------------------------------------------------


class Outcome(Enum):
    """What a load did, beyond returning an object (FR-046)."""

    CLEAN = "clean"
    CONVERTED = "converted"
    REPAIRED = "repaired"


@dataclass(frozen=True)
class RepairRecord:
    """One field, repaired to its descriptor default on load (FR-043, FR-045).

    ``field_path`` is the enclosing cue's id and the field name, joined the
    same way ``Violation.__str__`` joins its location — ``"<cue_id>/<field>"``,
    or bare ``"<field>"`` for a document-scoped field with no enclosing cue.
    """

    field_path: str
    previous_value: object
    substituted_value: object
    rule_name: str


@dataclass(frozen=True)
class ConversionRecord:
    """One version step applied on load (FR-046, data-model.md §1.1).

    ``dropped_elements`` names what a **lossy** step discarded — empty for
    every step that only reshapes or remaps. FR-051c's fade-profile drop is
    the one case in this feature that populates it; reporting it is what
    makes that drop permissible rather than a silent loss (SC-016e).
    """

    from_version: int
    to_version: int
    description: str
    dropped_elements: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoadReport:
    """What a load did beyond returning an object (data-model.md §4).

    Answers FR-046's five questions from data alone: which document
    (:attr:`document`), which fields were repaired and what replaced what
    (:attr:`repairs`), which conversions ran (:attr:`conversions`), and
    whether the file on disk is now stale (:attr:`file_differs_from_loaded`).

    A clean load returns ``outcome == Outcome.CLEAN`` with both tuples empty
    — **never** ``None`` — so a caller never branches on presence before
    reading (contracts §1).
    """

    document: str
    outcome: Outcome
    conversions: tuple[ConversionRecord, ...] = ()
    repairs: tuple[RepairRecord, ...] = ()
    file_differs_from_loaded: bool = False


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
