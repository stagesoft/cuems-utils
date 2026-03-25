# Data Model: MediaCue Parametric Fades

## Entity: MediaCueFadeProfile

- **Description**: Fade definition attached to one `MediaCue` direction.
- **Fields**:
  - `direction` (enum: `fade_in` | `fade_out`) - required
  - `mode` (enum: `preset` | `parametric`) - required
  - `function_id` (string) - required; identifies the fade function
  - `parameters` (list[`FadeFunctionParameter`]) - optional for `preset`,
    required for `parametric` when function needs inputs
- **Validation rules**:
  - `direction` MUST be one of `fade_in` or `fade_out`.
  - `mode` MUST be one of the allowed values.
  - `function_id` MUST be non-empty.
  - `preset` mode MUST allow empty `parameters`.
  - `parametric` mode MUST include all required parameters for the selected
    function.

## Entity: FadeFunctionParameter

- **Description**: One named numeric input for a parametric fade function.
- **Fields**:
  - `parameter_name` (string) - required
  - `parameter_value` (float) - required
- **Validation rules**:
  - Parameter names MUST be unique within one profile.
  - Parameter values MUST be finite numeric values.
  - Value ranges MAY be function-specific and enforced at validation/runtime.

## Entity: MediaCueXmlFadeBlock

- **Description**: XML representation under `MediaCueType` for schema validation
  and serialization.
- **Fields**:
  - `fade_profile` (optional, repeatable container)
  - each profile includes required `type` (`in` or `out`)
  - each profile includes `mode`, `function_id`, optional `parameters`
- **Validation rules**:
  - `fade_profile` entries are optional for backward compatibility.
  - At most one `fade_profile` per `type` is allowed.
  - If present, required child fields MUST exist and validate by mode.

## Relationships

- One `MediaCue` has zero, one, or two `MediaCueFadeProfile` entries.
- At most one profile of type `in` and at most one profile of type `out`.
- One `MediaCueFadeProfile` has zero or many `FadeFunctionParameter`.
- `AudioCue` and `VideoCue` inherit `MediaCue` behavior and therefore inherit
  fade-profile support without separate model duplication.

## State Transitions

- **No fade configured** -> default legacy behavior.
- **Type `in` preset selected** -> fade-in uses system-defined
  function, no user parameters required.
- **Type `out` parametric selected** -> fade-out uses supplied
  parameters after validation.
- **Invalid fade block** -> schema validation failure, script rejected before
  runtime execution.
