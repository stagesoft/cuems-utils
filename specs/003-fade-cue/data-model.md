# Data Model: FadeCue

**Feature**: 003-fade-cue  
**Date**: 2026-04-16

---

## Entity: FadeCue

Inherits all fields from `ActionCue` → `Cue` → `CuemsDict`.

### Own Fields

| Field | Python type | Default | Validation | XML element / type |
|-------|-------------|---------|------------|-------------------|
| `action_type` | `str` (fixed) | `'fade_action'` | Must equal `'fade_action'`; any other value raises `ValueError` | `<action_type>` / `ActionType` (inherited from `ActionCueType`) |
| `curve_type` | `FadeCurveType` (Enum) | `FadeCurveType.linear` | Must be a `FadeCurveType` member; string → member coercion on set | `<curve_type>` / `FadeCurveType` |
| `duration` | `CTimecode` | `CTimecode()` (zero) | Processed by `format_timecode()`; zero or negative MUST raise `ValueError` | `<duration>` / `CTimecodeType` |
| `target_value` | `int` | `0` | `0 <= value <= 100`; otherwise raises `ValueError` | `<target_value>` / `PercentType` |

### Inherited Fields (from ActionCue / Cue)

| Field | Notes |
|-------|-------|
| `action_target` | UUID of the cue to fade — required, validated by parent |
| `id`, `name`, `description`, `enabled` | Standard Cue identity fields |
| `timecode`, `offset`, `prewait`, `postwait`, `post_go` | Standard Cue timing/execution fields |
| `loop`, `target`, `autoload`, `ui_properties` | Standard Cue behaviour fields |

---

## Enum: FadeCurveType

Defined in `FadeCue.py` (same file or as a separate importable, TBD at implementation).

| Member | `.value` | XML text |
|--------|----------|----------|
| `FadeCurveType.linear` | `'linear'` | `linear` |
| `FadeCurveType.exponential` | `'exponential'` | `exponential` |
| `FadeCurveType.logarithmic` | `'logarithmic'` | `logarithmic` |
| `FadeCurveType.sigmoid` | `'sigmoid'` | `sigmoid` |

`str(FadeCurveType.linear)` → `'FadeCurveType.linear'` — the setter must store `.value` or the Enum member directly. Because `VALUE_TYPES` in `XmlBuilder` includes `Enum`, `str(value)` is called when building XML; therefore the Enum's `__str__` should return the plain `.value` string. Override `__str__` accordingly.

---

## REQ_ITEMS (dict defaults)

```python
REQ_ITEMS = {
    'action_target': None,   # inherited key, kept for ensure_items
    'action_type': 'fade_action',
    'curve_type': FadeCurveType.linear,
    'duration': None,        # converted to CTimecode() by setter
    'target_value': 0,
}
```

---

## Validation Rules

| Rule | Trigger | Error |
|------|---------|-------|
| `action_type` must be `'fade_action'` | `set_action_type()` called with other value | `ValueError` |
| `curve_type` must be a `FadeCurveType` member | `set_curve_type()` receives unknown string or value | `ValueError` |
| `duration` must be positive, non-zero | `set_duration()` after `format_timecode()` conversion | `ValueError` |
| `target_value` must be in [0, 100] | `set_target_value()` receives out-of-range int | `ValueError` |

---

## XML Schema Changes (script.xsd)

### 1. Add `fade_action` to `ActionType`

```xml
<xs:enumeration value="fade_action" />
```

Location: inside the existing `ActionType` simpleType restriction.

### 2. New `FadeCurveType` simpleType

```xml
<xs:simpleType name="FadeCurveType">
  <xs:restriction base="xs:string">
    <xs:enumeration value="linear" />
    <xs:enumeration value="exponential" />
    <xs:enumeration value="logarithmic" />
    <xs:enumeration value="sigmoid" />
  </xs:restriction>
</xs:simpleType>
```

### 3. New `FadeCueType` complexType

```xml
<xs:complexType name="FadeCueType">
  <xs:complexContent>
    <xs:extension base="cms:ActionCueType">
      <xs:sequence>
        <xs:element name="curve_type" type="cms:FadeCurveType" />
        <xs:element name="duration" type="cms:CTimecodeType" />
        <xs:element name="target_value" type="cms:PercentType" />
      </xs:sequence>
    </xs:extension>
  </xs:complexContent>
</xs:complexType>
```

### 4. Register `FadeCue` in `CueListContentsType`

```xml
<xs:element name="FadeCue" type="cms:FadeCueType" />
```

Location: inside the existing `<xs:choice>` in `CueListContentsType`.

---

## `items()` order

`FadeCue.items()` must return keys in the order matching the XSD sequence for `FadeCueType`, which is: all `CommonPropertiesType` fields → `action_target` → `action_type` → `curve_type` → `duration` → `target_value`.

The `items()` override follows the pattern of `ActionCue.items()`: start from `super().items()`, then insert own `REQ_ITEMS` keys sorted.

---

## State Transitions

FadeCue is a data container with no runtime state transitions. All transitions (fading in progress, completed, aborted) are managed by the show engine at runtime, outside the scope of this class.
