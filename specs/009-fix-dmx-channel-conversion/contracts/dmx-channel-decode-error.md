# Contract: `cuemsutils.errors.DmxChannelDecodeError`

This is a library (Python API), not a service — its "contract" is the public exception surface
consumers (cuems-engine, cuems-editor) are expected to catch by name, per `errors.py`'s own
stated convention ("An exception the caller cannot name is one it cannot catch").

## Surface

```python
from cuemsutils.errors import DmxChannelDecodeError, CuemsError

class DmxChannelDecodeError(CuemsError):
    """Raised by DmxUniverse.set_dmx_channels when one entry in the input
    cannot be converted to a DmxChannel."""

    def __init__(self, universe, index: int, entry: object) -> None: ...

    universe: "DmxUniverse"
    index: int
    entry: object
```

Added to `cuemsutils/errors.py`'s `__all__`.

## Behavioral guarantees (callers may rely on these)

1. **Catchable as `DmxChannelDecodeError` and as `CuemsError`.** A caller that only wants to catch
   *this* library's deliberate failures (`except CuemsError:`) catches this without needing to name
   it specifically.
2. **`str(exc)` never contains a `repr()` of the failing entry or the universe's channel data** —
   only the universe's `universe_num` (or a placeholder if unavailable) and the failing entry's
   *type name*. Show/config content never leaks into a log line via this exception (mirrors
   `DmxSceneWriteError`'s FR-033 precedent).
3. **`exc.__cause__` is the original `KeyError` or `TypeError`** that triggered the failure — never
   swallowed, always chained via `raise ... from exc`.
4. **Raised on the *first* failing entry** — not deferred until the whole batch is scanned. A caller
   catching this and inspecting `exc.index` gets the earliest offender, not necessarily the only
   one.
5. **Never raised for input that converts cleanly** — including every entry already a `DmxChannel`
   instance, every `None` entry (skipped, as today), an empty list (stored as empty, as today), and
   a batch **mixing** already-`DmxChannel` instances with still-raw-but-valid dict entries (FR-004a
   — this last case is a **defined**, tested behavior as of this feature, not merely "unraised";
   see data-model.md's Invariants for why today's two-branch code could silently drop entries in
   exactly this case). This is the "zero behavior change on the success path, and a well-defined
   fix for the one path that was previously ill-defined" guarantee (FR-004, FR-004a, FR-008).
6. **Not raised, and not reachable, from loading a schema-valid `script.xml`** — confirmed by the
   XSD investigation (spec.md). A caller building error-handling around `CuemsScript.load` does not
   need to add a `DmxChannelDecodeError` clause there; it only needs one around
   `CuemsScript.from_json` or any code path that constructs a `DmxUniverse` from an
   un-schema-validated payload.

## Non-goals

- This contract does **not** promise a stable, parseable message format beyond "names the universe
  and the entry's type" — consumers must not string-match the message; they must use `exc.index`,
  `exc.universe`, `exc.entry`, and `exc.__cause__` for programmatic handling.
- This contract does **not** cover recovery (skipping the bad entry and continuing) — that is
  proposal 2, explicitly out of this feature's scope. A caller wanting per-entry recovery must
  catch this error and implement its own retry/filter logic; the library does not do it for them.
