# Feature Specification: MediaCue Parametric Fades

**Feature Branch**: `001-mediacue-fading-function`  
**Created**: 2026-03-20  
**Status**: Draft  
**Input**: User description: "extend MediaCue so it can store and handle fading effects based on a parametrized function. Extend also required information on xmlschemas"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Fade Behavior in a Media Cue (Priority: P1)

As a script author, I want to define fade behavior on a media cue using a
parameterized function so that playback transitions can match artistic intent.

**Why this priority**: This is the core capability requested and delivers direct
value even without other enhancements.

**Independent Test**: Create a media cue with one fade function definition, save
it, load it, and confirm the same fade data is preserved and applied.

**Acceptance Scenarios**:

1. **Given** a media cue without a fade definition, **When** the author adds a
   fade function with valid parameters, **Then** the cue stores the fade
   definition and uses it during fade-related actions.
2. **Given** a media cue with a fade definition, **When** the cue is serialized
   and loaded again, **Then** the fade definition is preserved without loss.

---

### User Story 2 - Validate Fade Data Through XML Schema (Priority: P2)

As a script validator, I want the XML schema to describe required fade-function
fields so that invalid scripts are rejected before runtime.

**Why this priority**: Schema validation prevents malformed fade definitions from
causing late failures.

**Independent Test**: Validate one XML script with correct fade-function data
and one with missing/invalid fade-function fields, then verify pass/fail
results are deterministic.

**Acceptance Scenarios**:

1. **Given** a script containing valid media-cue fade-function data, **When**
   schema validation runs, **Then** validation succeeds.
2. **Given** a script missing required fade-function fields, **When** schema
   validation runs, **Then** validation fails with a clear field-level reason.

---

### User Story 3 - Preserve Backward Compatibility for Existing Scripts (Priority: P3)

As a maintainer, I want existing scripts without parametric fades to remain
usable so that the feature rollout does not break current shows.

**Why this priority**: Compatibility reduces migration risk and avoids service
disruption for current users.

**Independent Test**: Load and validate a script created before this feature,
execute media cues, and confirm behavior remains unchanged when no fade function
is defined.

**Acceptance Scenarios**:

1. **Given** a script with legacy media cues and no parametric fade data,
   **When** the script is loaded and run, **Then** it behaves as before this
   feature.

### Edge Cases

- Fade function parameters are incomplete, out of bounds, or non-numeric.
- Fade duration is zero or exceeds available cue playback duration.
- Multiple fade definitions are provided where only one is allowed.
- Fade definition exists but action requests no fade execution.
- Only one direction (`fade_in` or `fade_out`) is defined while the other is
  missing for a workflow that requires both.
- Legacy media cue payloads omit all new fade-function fields.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a media cue to store one parameterized fade
  function definition.
- **FR-002**: The fade function definition MUST include all required parameters
  needed to evaluate fade progression over time.
- **FR-002A**: The system MUST allow selecting a predefined system fade function
  that requires no user-provided fade parameters.
- **FR-002B**: The system MUST accept zero, one, or two `MediaCueFadeProfile`
  entries on `MediaCue`, using profile `type` values `in` and `out`, with at
  most one profile per type.
- **FR-003**: The system MUST apply the `fade_in` or `fade_out` definition that
  matches the requested fade operation for that media cue.
- **FR-004**: The system MUST serialize and deserialize media-cue fade-function
  data without changing semantic meaning.
- **FR-005**: The XML schema MUST define and enforce required fade-function
  fields for media cues.
- **FR-006**: XML validation MUST fail when required fade-function fields are
  missing or invalid.
- **FR-007**: Existing scripts without fade-function data MUST remain valid and
  executable with unchanged baseline behavior.
- **FR-UX-001**: User-facing wording, prompts, and defaults MUST match
  established project conventions or include a documented migration plan.
- **FR-PERF-001**: Feature MUST define measurable performance budgets and how
  they will be validated.

### Key Entities *(include if feature involves data)*

- **MediaCueFadeProfile**: Fade metadata attached to a media cue profile `type`
  (`in` or `out`), including function mode and function parameters.
- **FadeFunctionParameters**: Named values that control fade curve behavior and
  timing.
- **MediaCueXmlFadeBlock**: XML representation of fade profile data used for
  schema validation and interchange.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of media cues with valid fade-function data round-trip
  through save/load with no data loss in validation tests.
- **SC-002**: 100% of XML samples missing required fade-function fields are
  rejected by schema validation.
- **SC-003**: At least 95% of fade-enabled cue executions produce expected fade
  progression values in acceptance tests.
- **SC-003A**: 100% of acceptance tests that request `fade_in` and `fade_out`
  select and apply the matching directional fade function.
- **SC-004**: 100% of regression samples for legacy scripts (without fade data)
  load and run without behavior change.
- **SC-QUALITY-001**: No new lint/type warnings are introduced in changed files.
- **SC-TEST-001**: Required unit/integration/schema tests fail before and pass
  after implementation.

## Assumptions

- Up to two typed fade profiles (`in` and `out`) are sufficient for this
  increment.
- Fade-function parameters are represented as structured key-value data.
- Legacy scripts without fade data use existing default fade behavior.
- Validation errors can identify missing/invalid fade fields at a user-meaningful
  level.
