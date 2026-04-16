# Research: MediaCue Parametric Fades

## Decision 1: Typed fade profiles in `MediaCue`

- **Decision**: Store fade data as zero, one, or two `fade_profile` entries on
  `MediaCue`, each with required `type` (`in` or `out`) plus:
  - function mode (`preset` or `parametric`)
  - function identifier
  - optional parameter collection
- **Rationale**: One field supports both FR-002 (parameterized functions) and
  FR-002A (predefined system function without user parameters), while typed
  entries satisfy FR-002B (`fade_in` and `fade_out`) without separate XML field
  names.
- **Alternatives considered**:
  - Separate XML elements (`fade_in_profile`, `fade_out_profile`): rejected, too
    rigid and duplicates schema shape.
  - Unbounded profiles without uniqueness by type: rejected, ambiguous runtime
    selection and harder validation.

## Decision 2: XML schema compatibility strategy

- **Decision**: Add optional repeatable `fade_profile` under `MediaCueType` and
  enforce:
  - required `type` (`in` or `out`)
  - max one profile per `type`
  - strict internal validation for required subfields by mode
- **Rationale**: Optional envelope preserves legacy scripts (FR-007) while
  giving strict validation for new scripts (FR-005/FR-006).
- **Alternatives considered**:
  - Make fade fields required in `MediaCueType`: rejected, breaks existing
    scripts.
  - Put fade data in action cues only: rejected, fades are media behavior and
    must remain colocated with media configuration.

## Decision 3: Parameter representation in XML

- **Decision**: Represent parameters as a list of named numeric values
  (`parameter_name`, `parameter_value`) inside each typed fade profile.
- **Rationale**: XML Schema validates this structure deterministically and it
  maps cleanly to Python dictionaries.
- **Alternatives considered**:
  - Free-form mixed content: rejected, weak validation and poor error messages.
  - Fixed parameter fields per function: rejected, hard to extend as new
    function types are added.

## Decision 4: Parsing and serialization path

- **Decision**: Keep generic parser flow for nested XML objects and add explicit
  `MediaCue` normalization in cue model setters so fade profile data is always
  represented in one normalized in-memory shape.
- **Rationale**: Reuses existing parser architecture and minimizes parser-class
  sprawl while ensuring stable model semantics.
- **Alternatives considered**:
  - Dedicated `fade_profileParser` class only: rejected for now, unnecessary if
    generic parser + model normalization is sufficient.

## Decision 5: Performance validation method

- **Decision**: Validate the <=5% overhead budget by comparing median
  parse+serialize time for representative scripts before and after fade-profile
  support, with and without fade data present.
- **Rationale**: Measures user-relevant overhead and detects regressions in both
  legacy and new script paths.
- **Alternatives considered**:
  - Single-run timing: rejected, too noisy.
  - Only test scripts with fades: rejected, would miss regressions in legacy
    path.
