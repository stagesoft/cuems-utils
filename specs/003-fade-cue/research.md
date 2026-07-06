# Research: FadeCue Implementation

**Feature**: 003-fade-cue  
**Date**: 2026-04-16

---

## 1. Enum handling in the XML pipeline

**Decision**: Use a plain Python `enum.Enum` subclass for `curve_type`.

**Rationale**: `VALUE_TYPES` in `XmlBuilder.py` already includes `Enum` (line 14), so any `Enum` value is serialized via `str(value)` by the generic builder without a custom builder class. The enum's `.value` (a lowercase string) will be written into XML text nodes directly. No custom `FadeCueXmlBuilder` is required.

**Alternatives considered**: Plain string with manual validation — rejected because the enum gives a closed set and IDE/type support at no cost.

---

## 2. `duration` storage and serialization

**Decision**: Store `duration` as a `CTimecode` object using the existing `format_timecode()` helper, matching the pattern of `prewait`, `postwait`, and `offset` in `Cue`.

**Rationale**: `format_timecode()` already accepts strings, `CTimecode` objects, `int`/`float`, `None`, and the `{'CTimecode': ...}` dict produced by the XML parser — covering all ingestion paths. The XML schema type `CTimecodeType` (which wraps `<CTimecode>`) is already wired for these fields. Using the same pattern requires zero new infrastructure.

**Alternatives considered**: Raw float seconds — rejected (inconsistent with the rest of the model and the user's stated requirement). Custom timecode class — rejected (unnecessary, `CTimecode` already exists).

---

## 3. `action_type` fixed value

**Decision**: Override `set_action_type` in `FadeCue` to accept only `'fade_action'` and raise `ValueError` for any other value. The default value in `REQ_ITEMS` is set to `'fade_action'`. `'fade_action'` is added to the `ActionType` XSD enumeration.

**Rationale**: The parent's setter writes directly to the underlying dict. Overriding the setter is the minimal, idiomatic way to enforce the constraint while keeping the property API consistent. No separate field is needed.

**Alternatives considered**: Removing `action_type` from FadeCue entirely — rejected because the XML schema inherits `action_type` from `ActionCueType` and it must appear in serialized output. Making `action_type` a read-only computed property — considered but an override of the setter is simpler and consistent with how other cues guard their properties.

---

## 4. `target_value` bounds

**Decision**: `target_value` is stored as a plain `int`. The setter validates `0 <= value <= 100` and raises `ValueError` otherwise. Both boundary values (0 and 100) are valid.

**Rationale**: Simple, consistent with `master_vol` (PercentType) already present on AudioCue. The XSD type `PercentType` is already defined and can be reused for the schema element.

**Alternatives considered**: Float in 0.0–1.0 range — rejected (user specified 0–100 integer). Enum/level constants — rejected (continuous range, not a discrete set).

---

## 5. XML schema approach

**Decision**: Add to `script.xsd`:
1. `'fade_action'` value to the existing `ActionType` simpleType restriction.
2. New `FadeCurveType` simpleType with enumeration: `linear`, `exponential`, `logarithmic`, `sigmoid`.
3. New `FadeCueType` complexType extending `ActionCueType` with a sequence of `curve_type` (`FadeCurveType`), `duration` (`CTimecodeType`), and `target_value` (`PercentType`).
4. `<xs:element name="FadeCue" type="cms:FadeCueType" />` inside `CueListContentsType`.

**Rationale**: Extending `ActionCueType` means all inherited fields (`action_target`, `action_type`) appear in XML for free. Adding `fade_action` to `ActionType` ensures the fixed value passes schema validation.

**Alternatives considered**: A standalone `FadeCueType` extending `CueType` directly — rejected because it would duplicate the `action_target` field definition unnecessarily.

---

## 6. `create_script` integration

**Decision**: Add one `FadeCue` instance (with `target_value=0`, `curve_type='linear'`, `duration='00:00:02.000'`) after the existing `ActionCue` in the cue list. Increment the index-based ID assignments accordingly (currently indices 0–3; FadeCue becomes index 4).

**Rationale**: Minimal addition, demonstrates the full property set, validates with the same `validate_template` call already present.

---

## 7. Custom XmlBuilder required?

**Decision**: No custom `FadeCueXmlBuilder` is needed.

**Rationale**: `GenericCueXmlBuilder` handles `Enum` (via `VALUE_TYPES`), `CTimecode` (via the existing builder chain), and `int`/`str` scalars. `FadeCue.items()` will return properties in the correct order matching the XSD sequence.

---

## Summary of new artifacts

| Artifact | Change |
|----------|--------|
| `src/cuemsutils/cues/FadeCue.py` | New file |
| `src/cuemsutils/cues/__init__.py` | Add `FadeCue` export |
| `src/cuemsutils/xml/schemas/script.xsd` | Add `FadeCurveType`, `FadeCueType`, `fade_action`, `FadeCue` element |
| `src/cuemsutils/create_script.py` | Add `FadeCue` instance |
| `tests/test_fade_cue.py` | New test file |
