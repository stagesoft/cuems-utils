# Canvas Region

Custom video regions authored in normalized coordinates, used alongside monitor aliases.

## Overview

A `canvas_region` is a rectangle on a node's video canvas expressed in normalized floats in `[0, 1]`, top-left origin. The feature distinguishes two kinds of video output:

- **Monitor alias** — output backed by a physical display. Coordinates are resolved at runtime by `cuems-videocomposer` from the monitor's reported geometry. Authored once in [project_mappings.xml](../tests/data/default_mappings.xml); no `canvas_region` attached.
- **Custom** — output authored by the user as an arbitrary rectangle on the canvas. Unlike aliases, the coordinates are stored explicitly.

## Coordinate model

- Normalized floats `x`, `y` in `[0, 1]` and `width`, `height` in `(0, 1]`.
- Top-left origin: `x` grows right, `y` grows down.
- On-canvas only: `x + width ≤ 1` and `y + height ≤ 1`.
- Canvas is **node-scoped** — one canvas per node, distinct from any other node's canvas.
- Schema types: `UnitFloat` (for `x`, `y`) and `PositiveUnitFloat` (for `width`, `height`), defined in both [project_mappings.xsd](../src/cuemsutils/xml/schemas/project_mappings.xsd) and [script.xsd](../src/cuemsutils/xml/schemas/script.xsd).

Component ranges are enforced by XSD. Containment (`x+w ≤ 1`, `y+h ≤ 1`) cannot be expressed in XSD 1.0 and is enforced in Python (`VideoCueOutput` for cue paths, `ProjectMappings._validate_custom_templates` for mappings paths) with a small epsilon (`1e-6`) to absorb float round-trip noise.

## Two locations

### Project mappings — template slot

A `canvas_region` on a `VideoPutType` entry in `project_mappings` marks that entry as a **custom template**: a named slot on the node that the cue editor lists alongside monitor aliases. Its stored values also serve as the UI's default when a cue first instantiates a custom.

```xml
<output>
    <id>2</id>
    <name>custom</name>
    <canvas_region>
        <x>0.0</x>
        <y>0.0</y>
        <width>1.0</width>
        <height>1.0</height>
    </canvas_region>
    <mappings>
        <mapped_to>custom</mapped_to>
    </mappings>
</output>
```

Rule:
- `canvas_region` present ⇒ custom template.
- `canvas_region` absent ⇒ monitor alias resolved by composer.

### VideoCueOutput — per-cue instance

A `canvas_region` on a `VideoCueOutput` in `script.xsd` is the actual rectangle the user drew for a single cue. Required when the `output_name` matches `_custom_<n>`; rejected otherwise.

```json
{
    "VideoCueOutput": {
        "output_name": "<uuid>_custom_0",
        "canvas_region": { "x": 0.25, "y": 0.1, "width": 0.5, "height": 0.4 },
        "output_geometry": { ... }
    }
}
```

## `output_name` convention

- **Alias**: `<node_uuid>_<output.id>` — unchanged from prior behavior.
- **Custom**: `<node_uuid>_custom_<n>`, `n` zero-based. V1 emits only `_custom_0`; the numbered suffix reserves capacity for future customs without schema surgery.

`MediaCue.get_all_output_names()` splits `output_name` at positions `[:36]` / `[37:]` (UUID + separator). For customs the second element is `"custom_0"` — downstream consumers (notably the engine) must tolerate this non-integer form. See [Open questions → Engine-side routing](#engine-side-routing-of-custom_0).

## V1 caps

- One custom template per node (mappings), enforced in `ProjectMappings._validate_custom_templates`.
- One custom instance per cue (UI-side).

Both caps are explicit and bypassable by relaxing Python checks (schema already permits `_custom_1`, `_custom_2`, …).

## Validation rules

| Layer | Checks |
|---|---|
| XSD (both schemas) | Component ranges via `UnitFloat` / `PositiveUnitFloat`. Presence/cardinality (`minOccurs="0"` everywhere). |
| Python — `VideoCueOutput` | `output_name` matches alias or custom regex; `canvas_region` presence matches the detected kind; containment sums; property setters re-validate post-init. |
| Python — `ProjectMappings` | Containment sums on template entries; at most one template per node. |

## Deferred — wait-for-driver

Work intentionally not in V1. Each has a concrete trigger for when to do it.

### Aspect ratio handling

**Question:** a 16:9 source plays into a 4:3 custom region — letterbox, stretch, or crop?

**Likely shape:** a per-cue policy field on `VideoCueOutput`, e.g. `fit: "contain" | "cover" | "stretch"`. Orthogonal to the coordinate encoding; adding it is a small schema change and a property on `VideoCueOutput`.

**Why deferred:** no default is obvious without real usage. Different customers will have different expectations (conference: letterbox; exhibit: cover). V1 has no policy field — behavior is whatever the composer does today for misaligned geometry on aliases, extended to customs.

**Trigger:** first customer that places a cue on a custom region whose aspect differs from the source. Ask them what they expect; that answer becomes the default.

### Z-order

**Question:** when two cues' video outputs overlap on the same canvas region, which one is visible?

**Today:** document order in the cuelist implicitly decides. Reordering layering means moving cues around.

**Likely shape:** an explicit `order: xs:int` on `VideoCueOutput`, defaulting to `0`. Higher `order` wins. Decouples visual layering from cue order.

**Why deferred:** not a problem until customers actually overlap cues and complain about fragility.

**Trigger:** a layering complaint from a customer, or a design that inherently layers (e.g. lower third on top of background video).

### Off-canvas regions

**Question:** can a region spill past `[0, 1]` (negative `x`, or `x + width > 1`)?

**Use cases:** LED walls with physical bezels ignored by content; projection spill-over beyond the intended surface; pre-calibration authoring against a rough canvas.

**Shape change required:** replace `UnitFloat` / `PositiveUnitFloat` with unbounded floats; drop the containment sum check or make it a soft warning; document the new invariant.

**Why deferred:** niche. Most customers map content to visible surfaces. The on-canvas-only rule catches common authoring mistakes (accidental overflow), which is valuable in V1.

**Trigger:** a venue whose physical setup genuinely needs it.

### Multiple customs per cue / per node

**Schema readiness:** complete. Alias and custom `_custom_<n>` allow unlimited `n`. The V1 caps are Python-side only:
- `ProjectMappings._validate_custom_templates` raises if a node has more than one entry with `canvas_region`.
- UI caps the cue-side count at one (not enforced in code here; UI contract).

**To lift:**
- Remove the per-node template cap in `ProjectMappings._validate_custom_templates`.
- Remove the UI single-custom constraint.
- Consider a `name` field per template to disambiguate in the picker (already present via `<name>` in the mappings entry).

**Why deferred:** no customer has asked. Multi-custom adds UX weight (which custom did I pick? how do I tell them apart?) that should be informed by real usage.

**Trigger:** a customer asking for two custom regions in the same cue (e.g. "show the logo top-left AND the timer bottom-right").

### Visual drag/resize editor

**Shape:** a canvas widget where users drag/resize the region instead of typing numeric fields. Snap to common fractions (0.5, 0.25, …), multi-select, align-to-edge, etc.

**Why deferred:** V1 ships with numeric fields only — enough to unblock the backend. The visual editor is a UX win, not a correctness one.

**Trigger:** numeric-fields UI has shipped, users have complained about the friction, and the product team has capacity.

## Open questions

### Composer destination label

**Status:** ambiguous. V1 proceeds with Option A as the working assumption; confirmation pending.

The mappings template entry has `<mapped_to>custom</mapped_to>`. When cue A and cue B on the same node both pick `_custom_0`, which label reaches the composer?

- **Option A (default for V1): inherit the template's `mapped_to`.** Both cues target the same composer surface. If only one custom cue is "live" at a time, this is fine. If they overlap in time, last writer wins.
- **Option B: generate a unique per-instance label** like `<cue_uuid>_custom_<n>`. Avoids collisions; requires the composer to accept new names dynamically.

Decide with the composer team. If A is acceptable, no code change is needed. If B is required, update the engine-side resolution path.

### Engine-side routing of `custom_0`

**Risk:** the engine may not yet route `("uuid", "custom_0")` correctly.

`MediaCue.get_all_output_names()` returns this tuple shape for custom outputs; monitor aliases continue to return `("uuid", "<integer>")`. Engine code that assumes the second element is integer-coerceable will fail at playback. This is invisible from `cuems-utils` tests — everything validates and roundtrips — but manifests at show time.

**Action required outside this repo:** inspect `cuems-engine` for consumers of `get_all_output_names` and the `output_name[:36] / [37:]` split. Either (a) make consumers tolerate string suffixes, or (b) route `custom_*` through a separate resolution path that reads the cue's inline `canvas_region` directly rather than looking up a mappings entry by integer id.

Until this is verified, custom outputs should not be used in production cuelists.

---

## Related files

- Schemas: [project_mappings.xsd](../src/cuemsutils/xml/schemas/project_mappings.xsd), [script.xsd](../src/cuemsutils/xml/schemas/script.xsd)
- Python models: [CueOutput.py](../src/cuemsutils/cues/CueOutput.py), [Settings.py](../src/cuemsutils/xml/Settings.py)
- Tests: [test_cue_output.py](../tests/test_cue_output.py), [test_project_mappings.py](../tests/test_project_mappings.py), [test_canvas_region_roundtrip.py](../tests/test_canvas_region_roundtrip.py)
- Fixtures: [default_mappings.xml](../tests/data/default_mappings.xml), [project_mappings.xml](../tests/data/project_mappings.xml)
- Video composer (sibling repo): resolves monitor aliases to pixel rectangles on its own canvas.
