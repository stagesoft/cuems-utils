"""The T2 semantic tier (T055) — rules the schema cannot express (FR-017).

Two tiers of validation, kept explicitly separate:

**T1** is the schema. Types, cardinality, enumerations, patterns, and the
``xs:assert`` constraints XSD 1.1 allows. Derived, total, and enforced by
``xmlschema`` — nothing in this module duplicates it.

**T2** is what remains: rules about relationships between values that XSD
cannot state at all. There are three, and the list is closed by design — a T2
tier that grows freely becomes a second schema maintained in Python, which is
exactly the duplication this feature exists to remove.

Each rule below was previously inline in the class that happened to need it.
Naming them makes the boundary checkable: anything here is a rule XSD *cannot*
express, and anything XSD *can* express does not belong here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

#: Absorbs float round-trip noise. Mirrors ``cues.CueOutput._CONTAINMENT_EPS``:
#: a region written as ``0.5`` and read back as ``0.5000000000000001`` must not
#: fail a ``<= 1`` check it passed on the way out.
CONTAINMENT_EPS = 1e-6


def check_canvas_region_containment(region: dict, node_uuid: str) -> None:
    """A canvas region must fit inside the canvas.

    XSD constrains each component to ``[0, 1]`` individually (T1), which cannot
    express that their **sums** must also be bounded: ``x=0.9, width=0.9`` is
    two valid components describing a region that runs off the canvas.

    XSD 1.1's ``xs:assert`` could in principle state this, but the constraint
    spans sibling elements inside a repeated structure and the schema is frozen
    in this feature (FR-023, D3). It stays in T2.
    """
    x = float(region.get("x", 0))
    y = float(region.get("y", 0))
    width = float(region.get("width", 0))
    height = float(region.get("height", 0))

    if x + width > 1.0 + CONTAINMENT_EPS:
        raise ValueError(
            f"Node {node_uuid} canvas_region x+width must be <= 1, got {x + width}"
        )
    if y + height > 1.0 + CONTAINMENT_EPS:
        raise ValueError(
            f"Node {node_uuid} canvas_region y+height must be <= 1, got {y + height}"
        )


def check_one_custom_template_per_node(count: int, node_uuid: str) -> None:
    """At most one custom template — an entry carrying a ``canvas_region``.

    A **V1 product constraint**, not a structural one: the format could hold
    several and the editor's output-picker currently exposes one. See
    ``docs/canvas_region.md`` (Deferred — Multiple customs per cue / per node)
    for the lift path.

    Recorded here rather than in the schema precisely because it is expected to
    be lifted; encoding a temporary product decision in the XSD would make
    relaxing it a breaking schema change.
    """
    if count > 1:
        raise ValueError(
            f"Node {node_uuid} has {count} custom templates "
            f"(canvas_region entries); at most 1 is allowed"
        )


def validate_custom_templates(processed: dict) -> None:
    """Both video-output rules, over a processed project-mappings dict.

    Note the scope, which is easy to misread: ``canvas_region`` at the mappings
    level is a **UI template hint** — it offers the editor's output-picker a
    default starting rectangle for a named custom slot. It does not describe
    physical monitor layout (that comes from videocomposer's DRM detection) and
    it is not a per-cue output region (those live in ``script.xsd``'s
    ``VideoCueOutput.canvas_region``).
    """
    for section in ("nodes", "new_nodes"):
        for node_wrapper in processed.get(section, []) or []:
            node = node_wrapper.get("node") if isinstance(node_wrapper, dict) else None
            if not node:
                continue
            video = node.get("video")
            if not video:
                continue

            node_uuid = node.get("uuid", "<unknown>")
            template_count = 0
            for video_group in video:
                if not isinstance(video_group, dict):
                    continue
                for output_wrapper in video_group.get("outputs", []) or []:
                    output = (
                        output_wrapper.get("output")
                        if isinstance(output_wrapper, dict)
                        else None
                    )
                    if not output:
                        continue
                    region = output.get("canvas_region")
                    if region is None:
                        continue
                    check_canvas_region_containment(region, node_uuid)
                    template_count += 1

            check_one_custom_template_per_node(template_count, node_uuid)


#: The closed list. ``test_config_parity`` and the coherence test read this to
#: assert the tier has not grown silently.
SEMANTIC_RULES = (
    "canvas_region containment",
    "at most one custom template per node",
    "media duration",
)


# --- what validation *reports* (T023) --------------------------------------
#
# ``Violation`` and ``ValidationReport`` are what ``validate()`` returns, not
# names a consumer imports: a caller inspects the report it is handed and never
# constructs one. So they stay **internal** — no entry in ``__all__``, no entry
# in the API golden — and live here, beside the ``run_rules`` that produces
# them. ``CuemsScript.validate()``'s docstring is where their shape is
# published, because an internal type gets no documentation page of its own.


@dataclass(frozen=True)
class Violation:
    """One thing wrong with a document, in a form a caller can act on.

    ``frozen`` so a report can be compared, hashed and de-duplicated — and so
    the violation ``save()`` carries on its exception is the same value
    ``validate()`` reports rather than a look-alike (FR-034b).
    """

    #: ``"T1"`` structural or ``"T2"`` semantic — so the two tiers are
    #: distinguishable and neither absorbs the other.
    tier: str

    #: The registered rule name for T2; the schema constraint for T1.
    rule: str

    #: ``(cue_id, field)`` for a cue-scoped rule, ``(None, field)`` for a
    #: document-scoped one. A **pair**, deliberately, so a caller can address
    #: either half without parsing a string.
    location: tuple[str | None, str | None]

    #: The rule's own message, preserved where it is already actionable.
    message: str

    def __str__(self) -> str:
        cue_id, field = self.location
        where = "/".join(str(p) for p in (cue_id, field) if p is not None)
        return f"[{self.tier}] {self.rule}" + (f" at {where}" if where else "") + \
            f": {self.message}"


class ValidationReport:
    """Every violation found, or none — what ``validate()`` returns.

    Falsy when empty, so ``if script.validate():`` reads as *"there are
    violations"*. Iterates its violations and reports ``len()``.
    """

    __slots__ = ("_violations",)

    def __init__(self, violations=()):
        self._violations: tuple[Violation, ...] = tuple(violations)

    @property
    def violations(self) -> tuple[Violation, ...]:
        return self._violations

    def __bool__(self) -> bool:
        return bool(self._violations)

    def __len__(self) -> int:
        return len(self._violations)

    def __iter__(self) -> Iterator[Violation]:
        return iter(self._violations)

    def __repr__(self) -> str:
        if not self._violations:
            return "<ValidationReport: valid>"
        return "<ValidationReport: {} violation(s)>\n  {}".format(
            len(self._violations), "\n  ".join(str(v) for v in self._violations)
        )


def violation_from_schema_error(error) -> Violation:
    """One ``xmlschema`` validation error, as a T1 ``Violation``.

    The rule name is the schema construct that rejected the value — the XSD
    type where there is one, the validator's own name otherwise — because
    "the schema constraint for T1" is what a caller needs to look up. The
    element name is the ``field`` half of the location; the cue is not
    recoverable from an ``xmlschema`` error without re-walking the tree, so
    the ``cue_id`` half stays ``None`` and the message carries the path.
    """
    element = getattr(error, "elem", None)
    field = getattr(element, "tag", None)
    if isinstance(field, str) and field.startswith("{"):
        field = field.rsplit("}", 1)[-1]

    validator = getattr(error, "validator", None)
    rule = getattr(validator, "name", None) or getattr(
        validator, "local_name", None
    )
    if rule is None:
        rule = type(validator).__name__ if validator is not None else "schema"

    path = getattr(error, "path", None)
    reason = getattr(error, "reason", None) or str(error).strip().splitlines()[0]
    message = f"{reason}" + (f" (at {path})" if path else "")
    return Violation("T1", str(rule), (None, field), message)


# --- the T2 seam (T023b) ---------------------------------------------------


def _cue_id(cue) -> str | None:
    identifier = cue.get("id") if hasattr(cue, "get") else None
    return None if identifier is None else str(identifier)


def _walk(obj, cue_type: type, cue_id: str | None = None):
    """Every model object below ``obj``, paired with its **enclosing cue** id.

    A plain recursive walk rather than a schema-driven one: T2 rules are about
    *values*, and the tier must not acquire a second opinion about structure —
    that is T1's, derived, and total.

    The id is taken only when the node is a cue. Taking it from any node
    carrying an ``id`` would relabel a violation on ``Media.duration`` with the
    *media's* id, and a caller told to look at ``(media_id, "duration")`` has
    nowhere to look: the editor addresses cues.
    """
    if hasattr(obj, "keys"):
        if isinstance(obj, cue_type):
            cue_id = _cue_id(obj) or cue_id
        yield cue_id, obj
        for value in obj.values():
            yield from _walk(value, cue_type, cue_id)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from _walk(item, cue_type, cue_id)


def _check_media_duration(media, cue_id: str | None):
    """``Media.duration`` parses as a timecode — the rule ``set_duration`` holds.

    XSD constrains the *lexical shape* (``TimecodeType`` is a pattern), which
    cannot express that ``CTimecode`` can actually parse it, nor reject a value
    of the wrong Python type on an object never written to a document.
    """
    from ..tools.CTimecode import CTimecode

    duration = media.get("duration")
    if duration is None:
        return
    if isinstance(duration, CTimecode):
        return
    if not isinstance(duration, str):
        yield Violation(
            "T2",
            "media_duration",
            (cue_id, "duration"),
            f"media duration must be a str, CTimecode or None, got "
            f"{type(duration).__name__}",
        )
        return
    try:
        CTimecode(duration)
    except Exception as exc:  # noqa: BLE001 - any parse failure is the finding
        yield Violation(
            "T2",
            "media_duration",
            (cue_id, "duration"),
            f"Invalid media duration {duration!r}: {exc}",
        )


def _check_output_canvas_region(output, cue_id: str | None):
    """A video output's canvas region fits inside the canvas."""
    region = output.get("canvas_region")
    if not isinstance(region, dict):
        return
    try:
        check_canvas_region_containment(region, cue_id or "<unknown>")
    except ValueError as exc:
        yield Violation(
            "T2",
            "canvas_region_containment",
            (cue_id, "canvas_region"),
            str(exc),
        )


def run_rules(obj) -> list[Violation]:
    """Every T2 violation in ``obj`` — **the seam**, not yet the registry.

    ``save()`` and ``validate()`` bind to this signature (T027/T028) two phases
    before the named-rule registry exists (T072). Building the seam first is
    what keeps US1 from calling a function no task creates, and what lets T072
    *fill* it rather than introduce it — so the signature the public surface
    depends on never changes.

    Until then it wraps the rules this module already holds:
    ``check_canvas_region_containment`` over each video output's region, and
    ``Media.set_duration``'s parse rule over each media duration.
    ``check_one_custom_template_per_node`` is document-scoped over
    *project mappings*, not over a script, and is reached through
    ``validate_custom_templates`` from the config path.
    """
    from ..cues.Cue import Cue
    from ..cues.CueOutput import VideoCueOutput
    from ..cues.MediaCue import Media

    violations: list[Violation] = []
    for cue_id, node in _walk(obj, Cue):
        if isinstance(node, Media):
            violations.extend(_check_media_duration(node, cue_id))
        elif isinstance(node, VideoCueOutput):
            violations.extend(_check_output_canvas_region(node, cue_id))
    return violations
