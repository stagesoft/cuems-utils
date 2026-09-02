"""The document-version marker and the conversion registry (ITEM E, US6).

Two mechanisms, kept in one module because they are two halves of one idea
(data-model.md §1): a document states what version it was written by, and a
registry says how to bring an old one forward.

**The marker is a document property, never a domain field** (research R1). It
is read here by a **pre-validation** probe — stdlib ``ElementTree``, root
attribute only, no schema (research R2) — because an old document does not
validate against the current schema by definition, and a probe that ran
validation first would be circular.

**The registry is a step-by-step walk, not a bespoke old-to-current jump**
(data-model.md §1.1). ``(schema_name, from_version) -> Conversion``, so a
document three versions old runs three conversions in order. An unregistered
step is a valid **identity** step (FR-051d, research R9): the version
increments, the document is untouched, nothing is reported dropped.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable

#: The unqualified attribute name (research R1). Declared ``use="optional"``
#: on every schema's root complex type; absent means version 1 (FR-050).
DOC_VERSION_ATTR = "doc_version"

#: Each schema's current version (data-model.md §1). Only ``script`` moves in
#: this feature — the other five stay at 1, and that independence is measured
#: rather than assumed (FR-048b, SC-023b, T099a).
CURRENT_VERSION: dict[str, int] = {
    "script": 2,
    "settings": 1,
    "network_map": 1,
    "project_mappings": 1,
    "project_settings": 1,
    "outputs": 1,
}


class DocumentTooNewError(Exception):
    """A document's marker exceeds this library's current version (FR-052).

    Raised by the read path before any schema decode is attempted — a document
    from a newer library may use elements this one's schema does not even
    declare, so validating it first would produce a confusing "unexpected
    element" failure instead of a diagnosis of the real cause. Call sites
    translate this to a distinguishable ``ValidationError`` (contracts §1: an
    exception the caller cannot name is one it cannot catch).
    """

    def __init__(self, schema_name: str, version: int, current: int):
        self.schema_name = schema_name
        self.version = version
        self.current = current
        super().__init__(
            f"{schema_name} document is version {version}, newer than this "
            f"library's current version {current} for {schema_name}.xsd — "
            f"upgrade cuemsutils to read it"
        )


def read_version(source: ET.ElementTree | ET.Element) -> int:
    """The document's declared version, or 1 if it declares none (FR-050).

    ``source`` is already parsed with stdlib ``ElementTree`` — this reads
    ``root.attrib`` only, consulting no schema (research R2), so it can run on
    a document that would not validate against the current schema at all,
    which is precisely the document an old-version marker describes.
    """
    root = source.getroot() if hasattr(source, "getroot") else source
    raw = root.attrib.get(DOC_VERSION_ATTR)
    return int(raw) if raw is not None else 1


@dataclass(frozen=True)
class Conversion:
    """One version step's transformation (research R9).

    ``apply`` mutates ``root`` (the document's root ``Element``) in place and
    returns identifiers for anything it dropped — empty for a step that only
    reshapes or remaps. There is no ``None``/identity variant of this class:
    the identity step is represented by the **absence** of a registry entry
    (see :func:`convert`), so "no conversion" and "a conversion that happens
    to do nothing" cannot be confused.
    """

    description: str
    apply: Callable[[ET.Element], list[str]]


@dataclass(frozen=True)
class ConversionStep:
    """One version increment as it was actually applied — what a
    ``ConversionRecord`` (``cuemsutils.errors``) is built from."""

    from_version: int
    to_version: int
    description: str
    dropped_elements: tuple[str, ...] = ()


#: ``(schema_name, from_version) -> Conversion``. No entry for a step means
#: identity (FR-051d): the version increments, the document is untouched.
_CONVERSIONS: dict[tuple[str, int], Conversion] = {}


def register_conversion(schema_name: str, from_version: int, conversion: Conversion) -> None:
    """Register ``conversion`` as the ``schema_name`` step from ``from_version``."""
    _CONVERSIONS[(schema_name, from_version)] = conversion


def convert(
    schema_name: str, tree: ET.ElementTree | ET.Element, from_version: int, to_version: int
) -> list[ConversionStep]:
    """Walk every version step from ``from_version`` to ``to_version``, in order.

    Mutates ``tree`` in place, step by step — a document three versions old
    runs three conversions in sequence rather than one bespoke old-to-current
    jump (data-model.md §1.1). Returns the steps actually applied, in order,
    for the caller to build ``ConversionRecord``s from.
    """
    root = tree.getroot() if hasattr(tree, "getroot") else tree
    steps: list[ConversionStep] = []
    version = from_version
    while version < to_version:
        conversion = _CONVERSIONS.get((schema_name, version))
        if conversion is None:
            steps.append(
                ConversionStep(
                    version,
                    version + 1,
                    "identity — purely additive schema growth (FR-051d)",
                    (),
                )
            )
        else:
            dropped = conversion.apply(root)
            steps.append(
                ConversionStep(version, version + 1, conversion.description, tuple(dropped))
            )
        version += 1
    return steps


# --- script 1 -> 2: three transformations, one version step (FR-051b) ------
#
# Document elements are unprefixed in every CueMS document this library reads
# or writes (``mapper.build_document``/``Mapper._fill`` emit every descendant
# with a bare tag — only the root carries the ``cms:`` namespace prefix), so
# these walk by bare tag name, never by qualified name.


def _script_1_to_2(root: ET.Element) -> list[str]:
    """``script`` 1 -> 2 (data-model.md §1.1): the duration reshape, the
    ``fade_in``/``fade_out`` remap, and the ``fade_profiles`` drop — in one
    step, which is what demonstrates the registry composes (FR-051b)."""
    dropped: list[str] = []

    # 1. <duration>TC</duration> -> <duration><CTimecode>TC</CTimecode></duration> (FR-051, ITEM A)
    for media in root.iter("Media"):
        duration = media.find("duration")
        if duration is None or duration.find("CTimecode") is not None:
            continue
        text = duration.text
        duration.text = None
        ET.SubElement(duration, "CTimecode").text = text

    # 2. action_type: fade_in -> play, fade_out -> stop (FR-051a, ITEM D) —
    #    behaviour-preserving: ``cuems-engine`` already dispatches both as
    #    never-implemented stubs treated exactly as play/stop.
    for action_type in root.iter("action_type"):
        if action_type.text == "fade_in":
            action_type.text = "play"
        elif action_type.text == "fade_out":
            action_type.text = "stop"

    # 3. fade_profiles dropped, each drop reported (FR-051c, ITEM A) — a data
    #    drop is permissible only because it is reported (SC-016e).
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "fade_profiles":
                identifier = _enclosing_id(parent) or "<cue with no id>"
                dropped.append(f"fade_profiles removed from cue {identifier}")
                parent.remove(child)

    return dropped


def _enclosing_id(element: ET.Element) -> str | None:
    id_element = element.find("id")
    return id_element.text if id_element is not None else None


register_conversion(
    "script",
    1,
    Conversion(
        description=(
            "duration reshape (bare text -> <CTimecode> wrapper); "
            "action_type fade_in/fade_out -> play/stop; fade_profiles dropped"
        ),
        apply=_script_1_to_2,
    ),
)
