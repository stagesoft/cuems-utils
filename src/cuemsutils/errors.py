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
