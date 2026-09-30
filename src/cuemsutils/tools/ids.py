# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Node-identity shapes, and the vocabulary for talking about them (feature 012).

Three things live here, and they are here rather than in ``cuemsutils.xml``
because a consumer may not import that package (clarification Q14):

* the **classification** vocabulary — ``converged`` / ``not-converged`` /
  ``not-provisioned`` / ``unrecognised`` (data-model §1.3);
* the **token scanner** that finds every 36-character uuid in a file's bytes and
  says whether it was an element's whole value or embedded in a compound string
  (FR-002, FR-009);
* the **published coercion rule** — the public face of what the library's own
  decoding does with an identity (FR-030).

## "Converged" means uuid4, and only uuid4

The three definitions below are deliberately **three**, not one widened pattern:

.. code-block:: text

    converged ::= uuid4, lowercase, exactly 36 characters
    sentinel  ::= 00000000-0000-0000-0000-000000000000
    admitted  ::= converged | sentinel

The sentinel is *admitted* by the narrowed schemas and is **never** *converged*
(data-model §1.2, FR-021c). Keeping the two words apart is load-bearing rather
than pedantic: :func:`coerce_identity`'s second branch and
:func:`classify`'s ``not-provisioned`` class both give the wrong answer if they
blur, and the three schema types (``ConvergedUuidType``,
``NotProvisionedUuidType``, ``NodeUuidType``) are named after exactly these
three definitions so that a reader can check one against the other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CONVERGED",
    "NOT_CONVERGED",
    "NOT_PROVISIONED_CLASS",
    "UNRECOGNISED",
    "CLASSES",
    "NOT_PROVISIONED_UUID",
    "CONVERGED_PATTERN",
    "SENTINEL_PATTERN",
    "ADMITTED_PATTERN",
    "TokenOccurrence",
    "classify",
    "coerce_identity",
    "is_admitted",
    "is_converged",
    "scan_text",
    "scan_file",
]

# -- the three definitions -------------------------------------------------------------

#: The converged shape: uuid4, lowercase. Length is pinned at 36 by the anchors
#: plus the fixed group widths, and stated again in the schemas as explicit
#: ``minLength``/``maxLength`` facets because a pattern facet in XSD is already
#: anchored and the length is what a reader checks first.
CONVERGED_PATTERN = (
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)

#: The not-provisioned placeholder, as a value. **This is the sentinel
#: constant** the library surface publishes (contract §3): the nil-uuid a node
#: carries as its identity placeholder, which answers "is this node
#: provisioned?". It is *not*
#: :data:`cuemsutils.tools.identity_check.NOT_PROVISIONED`, the human-readable
#: status string the report prints, which answers "what should this line of
#: output say?".
#:
#: Defined here, and ``identity_check.SENTINEL`` is bound to it, so there is one
#: value rather than two that must agree. The published *name* stays where it
#: already was (assumption 7) — nothing a consumer imports moved.
NOT_PROVISIONED_UUID = "00000000-0000-0000-0000-000000000000"

#: The sentinel as a pattern, so the schemas' ``NotProvisionedUuidType`` and
#: this module can be checked against one another by a test rather than by eye.
SENTINEL_PATTERN = re.escape(NOT_PROVISIONED_UUID)

#: What the narrowed schemas accept: the **admitted** set, which is the union of
#: the two above and is not a third, looser shape (assumption 1). No other
#: nil-like value becomes valid by admitting this one.
ADMITTED_PATTERN = f"(?:{CONVERGED_PATTERN})|(?:{SENTINEL_PATTERN})"

_CONVERGED_RE = re.compile(f"^(?:{CONVERGED_PATTERN})$")

# -- the classification ----------------------------------------------------------------

#: uuid4, lowercase. Nothing else.
CONVERGED = "converged"

#: A well-formed uuid of another version, or a uuid4 in upper case. Actionable:
#: run the re-mint.
NOT_CONVERGED = "not-converged"

#: The sentinel. **Not a failure** — feature 011 established it as the coherent
#: state of a freshly installed node — but a different action from
#: :data:`NOT_CONVERGED`, which is why it is reported distinguishably (US1
#: scenario 3).
NOT_PROVISIONED_CLASS = "not-provisioned"

#: Not a uuid at all, or unreadable. Inspect by hand.
UNRECOGNISED = "unrecognised"

#: The four classes, in the order data-model §1.3 lists them. Every identity
#: falls in **exactly one**.
CLASSES = (CONVERGED, NOT_CONVERGED, NOT_PROVISIONED_CLASS, UNRECOGNISED)

#: Any canonically-shaped uuid, of any version and either case. Used by the
#: scanner: a *token* is recognised by shape, and its class is decided
#: afterwards by :func:`classify`. Keeping the two apart is what lets the
#: scanner run on a document carrying a uuid1 — which is the document this
#: feature exists to repair.
_ANY_UUID = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_ANY_UUID_RE = re.compile(_ANY_UUID)


def is_converged(value) -> bool:
    """Whether ``value`` is uuid4, lowercase — and **not** the sentinel."""
    return bool(_CONVERGED_RE.match(str(value))) if value is not None else False


def is_admitted(value) -> bool:
    """Whether the narrowed schemas would accept ``value``.

    Converged **or** the sentinel. This is the set a schema admits, which is a
    different question from whether an identity is converged, and the two are
    asked in different places: a schema asks this one, an operator asks the
    other.
    """
    return is_converged(value) or str(value) == NOT_PROVISIONED_UUID


def classify(value) -> str:
    """Which of the four :data:`CLASSES` ``value`` falls in.

    ``None``, an empty value and anything unparseable are
    :data:`UNRECOGNISED` — the class whose action is "inspect by hand", which
    is the honest answer for a value nothing here can name.

    The sentinel is checked **before** the uuid shape, because it *is* a
    canonically-shaped uuid and would otherwise be reported as
    :data:`NOT_CONVERGED` — sending an operator to the re-mint for a node that
    was simply never provisioned.
    """
    if value is None:
        return UNRECOGNISED
    text = str(value)
    if text == NOT_PROVISIONED_UUID:
        return NOT_PROVISIONED_CLASS
    if _CONVERGED_RE.match(text):
        return CONVERGED
    if re.fullmatch(_ANY_UUID, text):
        return NOT_CONVERGED
    return UNRECOGNISED


# -- the published coercion rule (FR-030) ----------------------------------------------


def coerce_identity(raw):
    """The library's own decoding leniency, published (contract §2).

    ==========================================  ==========================
    Input                                       Output
    ==========================================  ==========================
    a **converged** value (uuid4, lowercase)    :class:`~cuemsutils.tools.Uuid.Uuid`
    any other non-empty string, **including
    the sentinel**                              unchanged, as a ``str``
    empty (``None`` or ``""``)                  ``None``
    ==========================================  ==========================

    The sentinel falls through the second branch, which is the intended result
    and not an exception to the rule: it is admitted by the schemas but is not
    converged, and a consumer receiving the published constant as a plain string
    is what makes **one comparison** enough to recognise an unprovisioned node
    (M-d).

    One consumer has mirrored this rule by hand (M-c). Publishing it is what
    lets that copy be deleted rather than left to drift — so this function and
    ``xml/adapters.py``'s ``_UuidAdapter.decode`` must agree on every input, and
    ``tests/contract/test_published_coercion.py`` is where that is asserted
    rather than assumed.
    """
    from .Uuid import Uuid

    if raw is None or raw == "":
        return None
    if isinstance(raw, Uuid):
        return raw
    text = str(raw)
    if is_converged(text):
        return Uuid(text)
    return raw


# -- the token scanner (FR-002, FR-009) ------------------------------------------------


@dataclass(frozen=True)
class TokenOccurrence:
    """One 36-character uuid token, and enough about where it sat to act on it.

    ``embedded`` is the field that matters: it is the distinction that makes a
    *structural* rewrite wrong (design §10.2). A bare ``<uuid>`` element would
    be updated by any tool that understood the schema; a
    ``<identity>_<output>`` prefix inside an ``<output_name>`` would not, and it
    stays schema-valid while stale, because ``output_name`` is a
    ``NameStringType`` and remains one (data-model §1.1a).
    """

    #: The token exactly as found, case included.
    value: str

    #: Byte offset of the token's first character within the file's text.
    offset: int

    #: The enclosing element's local name, or ``None`` when the token sits
    #: somewhere no element tag precedes it (an attribute value, a comment, a
    #: file that is not XML at all). Reported rather than guessed.
    element: str | None

    #: ``False`` when the token is the element's **whole** value, whitespace
    #: aside; ``True`` when it is part of a longer string.
    embedded: bool

    #: The element's full text when ``embedded``, so a report can show the
    #: compound form an operator will recognise. Equal to ``value`` otherwise.
    context: str

    @property
    def classification(self) -> str:
        return classify(self.value)


#: Tags and tokens in **one** alternation, so :func:`scan_text` is a single
#: left-to-right pass. Scanning backwards for the enclosing tag per token would
#: be quadratic, which on the 4 MB ``remint_200`` fixture is the difference
#: between the throughput floor and missing it by orders of magnitude — and it
#: would be invisible on any small fixture.
_TAG_OR_TOKEN = re.compile(rf"(?P<tag><[^<>]*>)|(?P<uuid>{_ANY_UUID})")

_OPEN_TAG_NAME = re.compile(r"^<([A-Za-z_][\w.:-]*)")


def scan_text(text: str) -> list[TokenOccurrence]:
    """Every uuid-shaped token in ``text``, in the order it appears.

    Tokens are found by **shape**, of any uuid version and either case, because
    the whole point is to find the identities that are *not* converged.

    Read from the raw text rather than from a parsed tree **on purpose**: every
    caller is a path that must survive a document the schema refuses, and after
    the narrowing that is every document the re-mint exists to repair
    (FR-006a). A parse would be the one step that could fail.
    """
    found: list[TokenOccurrence] = []
    element: str | None = None
    after_tag = -1
    for match in _TAG_OR_TOKEN.finditer(text):
        tag = match.group("tag")
        if tag is not None:
            name = _OPEN_TAG_NAME.match(tag)
            if name is None or tag.endswith("/>"):
                element, after_tag = None, -1
            else:
                element, after_tag = name.group(1).rsplit(":", 1)[-1], match.end()
            continue
        start, end = match.span()
        close = text.find("<", end)
        if after_tag == -1 or close == -1:
            found.append(TokenOccurrence(match.group(0), start, element, True, match.group(0)))
            continue
        body = text[after_tag:close].strip()
        found.append(
            TokenOccurrence(match.group(0), start, element, body != match.group(0), body)
        )
    return found


def scan_file(path) -> list[TokenOccurrence]:
    """:func:`scan_text` over a file, decoded as UTF-8 with surrogate escapes.

    ``errors="surrogateescape"`` rather than ``"strict"``: a file this scanner
    cannot decode is still a file that may carry an identity, and refusing to
    look at it would make the survey's coverage depend on an unrelated encoding
    accident.
    """
    return scan_text(Path(path).read_text(encoding="utf-8", errors="surrogateescape"))
