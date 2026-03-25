# Contract: MediaCue Fade XML

## Scope

Defines XML-level contract additions for fade support in `MediaCueType`, covering
both `fade_in` and `fade_out` directions for parametric and predefined
functions.

## MediaCue Extension

- `MediaCueType` gains an optional repeatable element `fade_profile`.
- Each `fade_profile` declares a required `type` value: `in` or `out`.
- Zero, one, or two `fade_profile` elements are allowed; at most one per type.
- If omitted, cue behavior remains legacy-compatible.

## Fade Profile Contract

### `fade_profile`

- `type` (required): `in` or `out`
- `mode` (required): `preset` or `parametric`
- `function_id` (required): system-recognized fade function identifier
- `parameters` (optional container): list of parameters

### `parameters` entry

- `parameter_name` (required, string)
- `parameter_value` (required, float)

## Mode Semantics

- **Preset mode**:
  - `parameters` MAY be absent.
  - System resolves behavior using `function_id` only.
- **Parametric mode**:
  - `parameters` MUST include required function inputs.
  - Missing required parameters are validation/runtime errors.

## Validation Rules

- Unknown `type` values are invalid.
- Unknown `mode` values are invalid.
- Empty `function_id` is invalid.
- Duplicate `parameter_name` in the same profile is invalid.
- Non-numeric `parameter_value` is invalid.
- Duplicate `fade_profile` with the same `type` is invalid.

## Backward Compatibility

- Scripts without fade profile elements remain valid.
- Existing media cues continue to load and execute without migration.

## Example (Preset)

```xml
<fade_profile>
  <type>in</type>
  <mode>preset</mode>
  <function_id>linear_in_out</function_id>
</fade_profile>
```

## Example (Parametric)

```xml
<fade_profile>
  <type>out</type>
  <mode>parametric</mode>
  <function_id>bezier</function_id>
  <parameters>
    <parameter>
      <parameter_name>p1</parameter_name>
      <parameter_value>0.25</parameter_value>
    </parameter>
    <parameter>
      <parameter_name>p2</parameter_name>
      <parameter_value>0.75</parameter_value>
    </parameter>
  </parameters>
</fade_profile>
```
