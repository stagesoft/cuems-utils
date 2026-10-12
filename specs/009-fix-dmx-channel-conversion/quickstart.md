# Quickstart: verifying the DMX channel conversion fix

## Reproduce the defect (before the fix)

```python
from cuemsutils.cues.DmxCue import DmxUniverse

u = DmxUniverse()
u.dmx_channels = [
    {"DmxChannel": {"channel": 1, "value": 1}},   # well-formed
    {"not_dmxchannel_key": 1},                     # malformed — missing 'DmxChannel' key
    {"DmxChannel": {"channel": 2, "value": 2}},   # well-formed
]
print(u.dmx_channels)
# Today: the raw list, unconverted — every entry, including the two good ones.
# No exception. Only a Logger.error line, easy to miss.
```

## After the fix

```python
from cuemsutils.cues.DmxCue import DmxUniverse
from cuemsutils.errors import DmxChannelDecodeError

u = DmxUniverse()
try:
    u.dmx_channels = [
        {"DmxChannel": {"channel": 1, "value": 1}},
        {"not_dmxchannel_key": 1},
        {"DmxChannel": {"channel": 2, "value": 2}},
    ]
except DmxChannelDecodeError as exc:
    print(exc.index)        # 1 — the failing entry's position
    print(exc.universe)     # the DmxUniverse being populated
    print(exc.__cause__)    # KeyError('DmxChannel')
    print(str(exc))         # names the universe and the entry's type, not its content
```

## Verify no regression on valid input

```python
from cuemsutils.cues.DmxCue import DmxChannel, DmxUniverse

u = DmxUniverse()
u.dmx_channels = [{"DmxChannel": {"channel": 3, "value": 200}}]
assert isinstance(u.dmx_channels[0], DmxChannel)
assert u.dmx_channels[0].channel == 3
```

## Verify the mixed-batch fix (FR-004a)

```python
from cuemsutils.cues.DmxCue import DmxChannel, DmxUniverse

already = DmxChannel({"channel": 1, "value": 10})
u = DmxUniverse()
u.dmx_channels = [already, {"DmxChannel": {"channel": 2, "value": 20}}]

# Both entries are proper DmxChannel objects — neither is dropped, unlike pre-fix behavior.
assert len(u.dmx_channels) == 2
assert u.dmx_channels[0] is already
assert isinstance(u.dmx_channels[1], DmxChannel)
assert u.dmx_channels[1].channel == 2
```

## Verify the performance budget (SC-PERF-001)

```python
import time
from cuemsutils.cues.DmxCue import DmxUniverse

realistic = [{"DmxChannel": {"channel": i, "value": 100}} for i in range(8)]
start = time.perf_counter()
for _ in range(1000):
    DmxUniverse().dmx_channels = realistic
per_call_ms = (time.perf_counter() - start) * 1000 / 1000
assert per_call_ms <= 3.0, f"{per_call_ms:.4f} ms/call exceeds the 3 ms budget"
```

## Run the test suite for this feature

```bash
cd <this repo>
hatch test --show -- tests/unit/test_dmx_universe_channels.py tests/contract/test_dmx_channel_decode_failure_path.py
```

Expect: all "well-formed path" tests unchanged and green; the three former "exception-swallow
fallback" tests rewritten to assert `pytest.raises(DmxChannelDecodeError)`; the new contract test
file green, mirroring `tests/contract/test_dmx_failure_path.py`'s coverage of
`DmxSceneWriteError`.

## Full suite regression check

```bash
hatch test --show
```

Expect: no change outside the two files above. Per FR-008, every other test in the suite continues
to pass exactly as before this feature.
