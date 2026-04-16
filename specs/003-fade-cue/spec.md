# Feature Specification: FadeCue Class

**Feature Branch**: `003-fade-cue`  
**Created**: 2026-04-15  
**Status**: Draft  
**Input**: User description: "Create a new class FadeCue as a child class of ActionCue to handle and store Fade events (fade_in, fade_out) to target cues. Class should have its own xml representation and be included into create_script method."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a Fade-to-Level Cue on a Target (Priority: P1)

A show operator defines a FadeCue that, when triggered, smoothly transitions a target cue's level to a specified value over a given duration, following a chosen curve shape. The FadeCue carries all the information needed — target identifier, destination level, duration, and curve type — so the show engine can execute the transition without any further input.

**Why this priority**: Core purpose of the feature. A FadeCue that can be stored, validated, and serialized delivers the complete data contract the engine needs.

**Independent Test**: Can be fully tested by creating a FadeCue with a target cue identifier, a `target_value`, a `duration`, and a `curve_type`, then verifying all properties are stored correctly and the object serializes to valid XML.

**Acceptance Scenarios**:

1. **Given** a valid target cue identifier, a target level (0–100), a duration, and a curve type, **When** a FadeCue is created, **Then** all four properties are stored correctly and the object passes schema validation.
2. **Given** a fully populated FadeCue, **When** serialized to XML, **Then** the output is valid against the project's XML schema and contains all required elements.
3. **Given** a FadeCue serialized to XML, **When** deserialized back, **Then** all properties are restored to their original values (round-trip fidelity).

---

### User Story 2 - Validate Fade Parameters at Definition Time (Priority: P2)

When a show operator sets an invalid value — a target level outside the 0–100 range, a zero or negative duration, or an unrecognised curve type — the system rejects it immediately with a clear error, preventing a malformed cue from entering the script.

**Why this priority**: Bad data caught at definition time avoids silent failures at showtime.

**Independent Test**: Can be fully tested by attempting to construct or assign invalid values and confirming a descriptive error is raised in each case.

**Acceptance Scenarios**:

1. **Given** a FadeCue under construction, **When** `target_value` is set outside 0–100, **Then** a descriptive validation error is raised.
2. **Given** a FadeCue under construction, **When** `duration` is zero or negative, **Then** a descriptive validation error is raised.
3. **Given** a FadeCue under construction, **When** `curve_type` is not one of the allowed values, **Then** a descriptive validation error is raised.

---

### User Story 3 - Include FadeCue in Sample Script (Priority: P3)

The `create_script` utility generates a minimal sample script demonstrating all available cue types. A FadeCue instance must appear in that sample so integrators and testers have a complete, valid working example.

**Why this priority**: Ensures the class is wired into the existing demonstration and validation pipeline, catching integration issues early.

**Independent Test**: Can be fully tested by running `create_script` and confirming that a FadeCue node appears in the resulting XML, and that the full script validates against schema.

**Acceptance Scenarios**:

1. **Given** the `create_script` method, **When** called, **Then** the returned script contains at least one FadeCue element.
2. **Given** the script produced by `create_script`, **When** validated against the XML schema, **Then** validation passes with no errors and no regressions in other cue types.

---

### Edge Cases

- What happens when `target_value` is set to exactly 0 or 100? (Both are valid boundary values and MUST be accepted.)
- What happens when `duration` is zero or negative? (MUST raise a validation error.)
- What happens when `curve_type` receives an unrecognised string? (MUST raise a validation error.)
- What happens when `action_target` is missing or None? (MUST raise a validation error, consistent with ActionCue behaviour.)
- What happens when a FadeCue referencing a non-existent target cue ID is serialized? (MUST serialize without error; target existence is a runtime engine concern.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: FadeCue MUST extend ActionCue and inherit all standard cue properties (id, name, enabled, timecode, target, prewait, postwait, post_go, etc.).
- **FR-002**: FadeCue MUST fix `action_type` to the value `fade_action`; this value MUST be added to the `ActionType` enumeration in the XML schema and MUST NOT be overridable by the caller.
- **FR-003**: FadeCue uses the inherited `action_target` property from ActionCue to identify the target cue. No rename or wrapper is introduced; `target_cue` is a documentation-only label.
- **FR-004**: FadeCue MUST include a `curve_type` property whose value is one of a fixed enumeration: `linear`, `exponential`, `logarithmic`, `sigmoid`. Any other value MUST be rejected at construction or assignment.
- **FR-005**: FadeCue MUST include a `duration` property representing the total time of the fade, expressed as a timecode value in `hh:mm:ss.milliseconds` format. The property MUST accept both a timecode-formatted string and a CTimecode object; the XML representation MUST store it as a timecode string. A zero or negative duration MUST be rejected.
- **FR-006**: FadeCue MUST include a `target_value` integer property in the range 0–100 (inclusive) representing the destination level the engine will fade to. Values outside this range MUST be rejected.
- **FR-007**: The starting level of the fade is NOT stored on FadeCue; the show engine recovers it from the live value at runtime.
- **FR-008**: FadeCue MUST serialize to and deserialize from the project XML format, producing output that validates against the project XML schema.
- **FR-009**: FadeCue MUST be registered in the `CueListContentsType` of the XML schema, allowing it to appear within a cue list.
- **FR-010**: The `create_script` function MUST include at least one FadeCue instance in the sample script it produces.
- **FR-011**: FadeCue MUST be exported from the `cues` package so it is importable at the same level as AudioCue, VideoCue, and ActionCue.
- **FR-UX-001**: Property names, default values, and XML element names MUST follow the established naming conventions used by ActionCue and DmxCue (snake_case properties, matching XML element names).
- **FR-PERF-001**: FadeCue construction, serialization, and deserialization MUST complete in the same order of magnitude as equivalent operations on ActionCue (no significant overhead introduced).

### Key Entities

- **FadeCue**: A specialization of ActionCue that stores the complete description of a fade transition — target cue, destination level, duration, and curve shape. At rest it is a data container; actual execution is handled by the show engine at runtime.
- **target_cue**: The identifier of the cue on which the fade is applied (inherited from ActionCue).
- **curve_type**: Enumerated fade curve shape — one of `linear`, `exponential`, `logarithmic`, `sigmoid`. Determines how the engine interpolates the level over time.
- **duration**: Time span of the fade, stored as a timecode string (`hh:mm:ss.milliseconds`). Must be positive and non-zero.
- **target_value**: Integer destination level (0–100 inclusive). The engine fades from the live current value to this target.
- **action_type**: Fixed to `fade_action` for all FadeCue instances.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A FadeCue can be instantiated, fully populated, serialized to XML, and deserialized back with 100% property fidelity (round-trip parity).
- **SC-002**: All three invalid-input scenarios (bad `target_value`, bad `duration`, bad `curve_type`) raise descriptive errors 100% of the time.
- **SC-003**: The XML output of a FadeCue passes the project schema validator with zero errors.
- **SC-004**: `create_script` produces a valid script containing at least one FadeCue without any regression in existing cue examples.
- **SC-005**: `action_type` on any FadeCue instance always returns `fade_action` regardless of how the object was constructed.
- **SC-QUALITY-001**: No new lint or type warnings are introduced by the FadeCue implementation.
- **SC-TEST-001**: Unit tests for FadeCue construction, validation, and XML round-trip fail before implementation and pass after.

## Assumptions

- The XML schema (`script.xsd`) will be extended with a new `FadeCueType` that extends `ActionCueType`, adding `curve_type`, `duration`, and `target_value` as required elements.
- `fade_action` will be added as a new enumeration value to `ActionType` in the schema.
- The enum identifiers stored in XML are the lowercase English spellings: `linear`, `exponential`, `logarithmic`, `sigmoid`.
- No parametric curve customisation (e.g. sigmoid steepness, exponential base) is in scope; the four named curves are treated as presets resolved by the engine.
- The starting level of a fade is always recovered from the live runtime state; FadeCue does not store an initial value.
- Target validation (confirming the referenced cue exists) is the show engine's responsibility, not FadeCue's.
