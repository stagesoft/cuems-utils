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
