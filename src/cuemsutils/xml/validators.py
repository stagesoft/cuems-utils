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


# --- the named-rule registry (T072) ----------------------------------------
#
# One definition per rule, registered by name and bound to the ``(type, field)``
# pairs it applies to, invoked from **two** call sites: the property setter
# (immediate, programmatic) and the write/validate tier.
#
# Before this, each rule existed once inside the setter that happened to need
# it. That is not a second copy — it is *no* name at all, which is why the tier
# could only be enumerated by reading fourteen setters and hoping none had been
# missed. Naming them is what makes "which rules are there?" a question with an
# answer.
#
# ``applies_to`` is keyed on **class-name strings**, not classes. Importing
# ``cues/`` at this module's scope would close the import cycle the whole
# package is arranged to keep open, and a rule that has to wait for its class
# to exist cannot be registered at import time. Matching walks the object's MRO
# names, so a rule bound to ``VideoCueOutput`` does not fire on an
# ``AudioCueOutput`` and one bound to a base does fire on its subclasses.


@dataclass(frozen=True)
class Rule:
    """One semantic rule: a name, what it applies to, and the check itself."""

    name: str

    #: ``(class name, field name)`` pairs. A rule may apply to more than one —
    #: ``canvas_region_containment`` governs both a per-cue video output and a
    #: project-mappings video port.
    applies_to: tuple[tuple[str, str], ...]

    #: ``check(value, obj) -> None``. Raises ``ValueError`` with the message
    #: the user sees. Messages are **preserved unchanged** from the setters
    #: they came from: the rule names are new, the wording is not.
    check: object

    def fields_for(self, class_names: frozenset[str]) -> tuple[str, ...]:
        return tuple(
            field for cls, field in self.applies_to if cls in class_names
        )


#: Every registered rule, by name. **The tier's inventory**, and the only one.
RULES: dict[str, Rule] = {}


def register(name: str, applies_to):
    """Register a rule under ``name``, bound to ``(type, field)`` pairs.

    Returns the undecorated function, so the setter that used to hold the body
    can call it directly and the registry and the setter cannot drift — which
    is the whole content of FR-024c. Two call sites, one function object.
    """

    def decorator(fn):
        if name in RULES:
            raise ValueError(f"rule {name!r} is already registered")
        RULES[name] = Rule(name, tuple(applies_to), fn)
        return fn

    return decorator


def enforce(name: str, value, obj=None) -> None:
    """Run one rule by name — **the setter's call site**.

    Raises whatever the rule raises, which is a ``ValueError`` carrying the
    message that setter has always produced. Programmatic assignment therefore
    still fails immediately and with the same words (FR-024c, T071).
    """
    RULES[name].check(value, obj)


#: The closed list. ``test_config_parity`` and the coherence test read this to
#: assert the tier has not grown silently.
#:
#: **Derived from ``RULES``, not maintained beside it** (T072a). It used to be a
#: hand-written tuple of three prose names — ``"canvas_region containment"``,
#: ``"at most one custom template per node"``, ``"media duration"``. Once the
#: registry existed, keeping both would have been two inventories of one thing:
#: FR-024c's prohibition one level up, and precisely the mechanism behind F15's
#: three incompatible shapes.
#:
#: The name **form** changed with it — prose with spaces became identifiers —
#: and its two readers were updated. Rule *messages*, which are what users see,
#: are unchanged.
def _semantic_rules() -> tuple[str, ...]:
    return tuple(sorted(RULES))


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


def run_rules(obj) -> list[Violation]:
    """Every T2 violation in ``obj`` — **the seam, now filled** (T072).

    ``save()`` and ``validate()`` bound to this signature two phases before the
    registry existed (T023b). Building the seam first is what kept US1 from
    calling a function no task created, and what lets this task *fill* it
    rather than introduce it — so the signature the public surface depends on
    never changed.

    The walk asks the **registry**, not a list of special cases: for every
    object below ``obj``, every rule bound to one of its MRO names and to a
    field it actually carries is run, and a ``ValueError`` becomes a
    ``Violation``. Adding a rule therefore extends this without editing it,
    which is the difference between a tier and an archaeology exercise.

    Rules are run in **registration order** so a document with several
    violations reports them in a stable order rather than a dict-iteration one.
    """
    from ..cues.Cue import Cue

    violations: list[Violation] = []
    for cue_id, node in _walk(obj, Cue):
        class_names = frozenset(cls.__name__ for cls in type(node).__mro__)
        for rule in RULES.values():
            for field in rule.fields_for(class_names):
                if field not in node:
                    continue
                try:
                    rule.check(node[field], node)
                except (ValueError, TypeError) as exc:
                    # ``TypeError`` is here for one rule: ``media_duration``
                    # rejects a wrong *type* with a ``TypeError`` because that
                    # is what its setter has always raised, and T071 keeps the
                    # setter's behaviour. A report is a report either way.
                    violations.append(
                        Violation("T2", rule.name, (cue_id, field), str(exc))
                    )
    return violations


# --- the rules themselves (T073) -------------------------------------------
#
# Each body came from the property setter that used to hold it, and each
# **message is preserved verbatim** — the rule names are new, the words a user
# reads are not (T072a).
#
# Every one takes ``(value, obj)``. Most ignore ``obj``; the three that do not
# need the object to answer at all — a canvas region's legality depends on the
# output's ``output_name``, and a fade profile's on its siblings.


@register("action_target_required", [("ActionCue", "action_target")])
def _action_target_required(value, obj=None) -> None:
    """An action cue must name what it acts on."""
    if value is None:
        raise ValueError("action_target is required")


@register("fade_action_type", [("FadeCue", "action_type")])
def _fade_action_type(value, obj=None) -> None:
    if value != "fade_action":
        raise ValueError(
            f"action_type must be 'fade_action' for FadeCue, got '{value}'"
        )


@register("fade_curve_type", [("FadeCue", "curve_type")])
def _fade_curve_type(value, obj=None) -> None:
    from ..cues.FadeCue import FadeCurveType

    if isinstance(value, FadeCurveType):
        return
    try:
        FadeCurveType(value)
    except ValueError:
        valid = [member.value for member in FadeCurveType]
        raise ValueError(f"curve_type must be one of {valid}, got '{value}'")


@register("fade_duration_positive", [("FadeCue", "duration")])
def _fade_duration_positive(value, obj=None) -> None:
    """``None`` is accepted — it means "not set yet", not "zero"."""
    from ..cues.FadeCue import _ZERO_TC
    from ..helpers import format_timecode

    if value is None:
        return
    if format_timecode(value) <= _ZERO_TC:
        raise ValueError("duration must be positive and non-zero")


@register("fade_target_value_range", [("FadeCue", "target_value")])
def _fade_target_value_range(value, obj=None) -> None:
    number = int(value)
    if not (0 <= number <= 100):
        raise ValueError(f"target_value must be between 0 and 100, got {number}")


@register("output_name_shape", [("VideoCueOutput", "output_name")])
def _output_name_shape(value, obj=None) -> None:
    """A video output name is an alias or a custom slot, and nothing else."""
    from ..cues.CueOutput import _classify_output_name

    _classify_output_name(value)


@register("canvas_region_containment", [("VideoCueOutput", "canvas_region")])
def _canvas_region_containment(value, obj=None) -> None:
    """The region fits the canvas, **and** matches the output's mode.

    Two clauses, one rule, because they are the same question asked of the same
    field: an alias output must not carry a region, a custom one must, and a
    region that is present must fit. Splitting them would put the mode check
    somewhere a caller reading "canvas_region" would not look.
    """
    from ..cues.CueOutput import _classify_output_name, _validate_canvas_region

    output_name = obj.get("output_name") if obj is not None else None
    kind = None
    if isinstance(output_name, str):
        try:
            kind = _classify_output_name(output_name)
        except ValueError:
            kind = None  # reported by ``output_name_shape``, not twice here

    if value is None:
        if kind == "custom":
            raise ValueError(
                f"canvas_region is required for custom output_name {output_name!r}"
            )
        return

    if kind == "alias":
        raise ValueError(
            f"canvas_region must be absent for alias output_name {output_name!r}"
        )
    _validate_canvas_region(value)


@register("media_duration", [("Media", "duration")])
def _media_duration(value, obj=None) -> None:
    """``Media.duration`` parses as a timecode (feature 008, FR-005).

    ``Media.duration`` is now ``cms:CTimecodeType`` — the same type and the
    same ``format_timecode`` machinery every other time-carrying element
    uses, so this rule delegates to it exactly as ``fade_duration_positive``
    does for ``FadeCue.duration``. The ``str`` branch this rule used to carry
    (parsing a value already known to be ``str``, with its own ``TypeError``
    for anything else) is gone: it existed because the field used to *store*
    a string, and a T2 rule only ever sees a stored value. It now stores a
    ``CTimecode`` exactly as every other such field does, so that branch is
    unreachable rather than merely redundant.
    """
    from ..helpers import format_timecode

    if value is None:
        return
    format_timecode(value)


@register("cuelist_shape", [("CuemsScript", "CueList")])
def _cuelist_shape(value, obj=None) -> None:
    from ..cues.CueList import CueList

    if isinstance(value, CueList):
        return
    try:
        CueList(value)
    except Exception as exc:  # noqa: BLE001 - the constructor is the check
        raise ValueError(
            f"CueList {value} is not a CueList object or a valid dict"
        ) from exc


@register("one_custom_template_per_node", [("NodeType", "video")])
def _one_custom_template_per_node(value, obj=None) -> None:
    """At most one custom template — an entry carrying a ``canvas_region``.

    A **V1 product constraint**, not a structural one, and document-scoped over
    *project mappings* rather than over a script. Registered against the
    mappings ``NodeType`` so ``run_rules`` reaches it if a config object is
    ever validated; the live call site remains ``validate_custom_templates``,
    which ``ProjectMappings`` runs on read.
    """
    if not value:
        return
    node_uuid = obj.get("uuid", "<unknown>") if obj is not None else "<unknown>"
    count = 0
    for group in value if isinstance(value, list) else [value]:
        if not hasattr(group, "keys"):
            continue
        for wrapper in group.get("outputs") or []:
            output = _unwrap_single(wrapper)
            if output is None:
                continue
            region = output.get("canvas_region")
            if region is None:
                continue
            check_canvas_region_containment(region, node_uuid)
            count += 1
    check_one_custom_template_per_node(count, node_uuid)


def _unwrap_single(wrapper):
    if hasattr(wrapper, "keys") and len(wrapper) == 1:
        only = next(iter(wrapper.values()))
        if hasattr(only, "keys"):
            return only
    return wrapper if hasattr(wrapper, "keys") else None


#: Derived, never hand-maintained — see ``_semantic_rules``.
SEMANTIC_RULES = _semantic_rules()
