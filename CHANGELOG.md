# Changelog

## 0.1.0rc5 — 2026-04-22

### Added
- `settings.xsd` defines optional `<output_latency_ms>` on
  `AudioPlayerType`, `VideoPlayerType`, and `DmxPlayerType`.
  - Audio and video accept `AutoOrIntLatencyMsType` — a union of
    `xs:nonNegativeInteger` (maxInclusive=500) or the literal
    `"auto"`. Integer is an explicit override in ms; `"auto"` defers
    to the binary's built-in default (JACK query for audioplayer;
    hard-coded 33 ms for videocomposer).
  - Dmx accepts `IntLatencyMsType` (integer only) — no auto-measurement
    path exists for the DMX pipeline; `"auto"` is rejected at
    validation time to avoid implying magic that doesn't exist. Absent
    element defers to dmxplayer's hard-coded 35 ms default.
- Tests for the tri-state (int / `"auto"` / absent) round-trip and a
  negative test for `"auto"` on dmxplayer.

### Notes
- Schema change is strictly additive (`minOccurs="0"`); existing
  `settings.xml` files remain valid with no migration.
- Typing contract: `xmlschema.to_dict()` returns Python `int` for
  integer values and `str` for `"auto"`. `cuems-engine`'s NodeEngine
  arg-building relies on `isinstance(value, int)` to decide whether
  to emit the `--output-latency-ms` CLI flag to each player process.
