# `DmxUniverse.set_dmx_channels` silently swallows conversion failures

Found while closing a code-coverage gap (no feature attached yet) — `src/cuemsutils/cues/DmxCue.py:372-396`.
Characterized, not fixed, by `tests/unit/test_dmx_universe_channels.py`. Written as the record a
future feature should read before deciding what to do about it.

## What the code does today

```python
def set_dmx_channels(self, channels):
    Logger.info("DmxUniverse set_channels called with channels: {}".format(channels))
    if not isinstance(channels, list):
        channels = [channels]
    channel_list = []
    try:
        for r in channels:
            if r is not None:
                if not isinstance(r, DmxChannel):
                    new_dmxchannel = DmxChannel(r['DmxChannel'])
                    channel_list.append(new_dmxchannel)
                    super().__setitem__('dmx_channels', channel_list)
                else:
                    super().__setitem__('dmx_channels', channels)
    except Exception as e:
        Logger.error(f"Error converting channels to DmxChannel: {e}")
        super().__setitem__('dmx_channels', channels)
```

The whole per-channel conversion loop sits inside one `try`/`except Exception`. If **any** entry
fails to convert — wrong shape, missing `'DmxChannel'` key, a plain `int`, anything that raises on
`r['DmxChannel']` — the `except` branch fires and stores the **raw, unconverted `channels`
argument** as `dmx_channels`, silently, with no exception raised to the caller and only a
`Logger.error` line as any trace. Three specific behaviours, each pinned by a test:

- **One bad entry discards every good entry in the same batch.** `[good, bad, good]` produces
  `dmx_channels == [good, bad, good]` — none converted to `DmxChannel`, not just the offending one —
  because the exception aborts the loop entirely
  (`test_one_bad_entry_discards_conversion_of_every_good_entry_in_the_batch`).
- **Both `KeyError` (dict without `'DmxChannel'`) and `TypeError` (non-subscriptable entry, e.g. a
  bare `int`) hit the same fallback**, because the `except` clause is unqualified
  (`test_a_malformed_dict_entry_falls_back_to_storing_the_raw_input`,
  `test_a_non_subscriptable_entry_falls_back_to_storing_the_raw_input`).
- The single-instance and list-of-instances paths (`isinstance(r, DmxChannel)` true) are unaffected
  — those already store correctly-typed data.

## Why this is reachable from untrusted input, not just internal misuse

`DmxUniverse` is bound in the schema registry (`xml/registry.py:236`,
`registry.bind("DmxUniverseType", DmxUniverse)`) and constructed generically by
`Mapper.decode_config`/`decode_document` whenever a `<DmxUniverse>` element is decoded off a real
script XML document — i.e. **on the read path for files loaded from disk**, not only when
application code builds a `DmxUniverse` by hand. `CuemsDict.setter` (`helpers.py:527-538`) calls
`set_dmx_channels` for the `'dmx_channels'` key like any other declared-field setter, with no
special casing.

Concretely: a `script.xml` whose `<DmxUniverse>` content is malformed in one channel — hand-edited,
corrupted, or produced by a future writer bug — does not fail T1 schema validation in a way that
prevents this method from running (the malformed shape is realized as a Python dict *after* XSD
decode, at the object-construction step), and does not raise here either. The document loads
"successfully" with garbage sitting in `dmx_channels` — raw dicts/ints instead of `DmxChannel`
objects — for `cuems-engine` to eventually hand to real lighting output. Whether that failure mode
is "wrong light state" or a downstream `TypeError`/`AttributeError` far from this call site depends
entirely on what the engine does with a non-`DmxChannel` list member; this repository does not own
that code and cannot characterize it here.

## Precedent: this is the same shape of defect feature 005 already removed elsewhere

`tests/contract/test_dmx_failure_path.py`'s docstring records `DmxSceneXmlBuilder.build` (the
*write* path, `xml/mapper.py`, pre-005) doing the identical thing: a blanket `except Exception` that
logged and produced an empty-but-valid-looking document instead of raising. Feature 005 inverted
that — a failing DMX scene now aborts the write with a `DmxSceneWriteError` naming the scene (by id
or index) and the originating cue, with the original exception preserved as `__cause__`
(`FR-019` row 7, `FR-023`).

`set_dmx_channels` is the **read-path** sibling of the exact defect 005 fixed on the write path, in
the same subsystem (DMX), never addressed because it was never the one under test at the time. It
was not caught by 005's own coherence work because that feature scoped itself to the write path
(`DmxSceneXmlBuilder`), and no test exercised `set_dmx_channels` at all until this pass (see the
project's `CLAUDE.md` "Recent Changes" — 005/004/006 do not mention `DmxUniverse`).

## What is *not* proposed here

No code change ships with this document. `tests/unit/test_dmx_universe_channels.py` intentionally
**characterizes current behaviour** (including the fallback) rather than fixing it — changing
runtime behaviour was out of scope for the coverage-closing pass that found this, and the fix
deserves its own design decision (below), not a silent behaviour change bundled into an unrelated
commit.

## Remediation proposals, for whoever picks this up

Three shapes, not mutually exclusive, roughly ordered by how much they change observable behaviour:

1. **Raise instead of swallowing — mirror feature 005's `DmxSceneWriteError` pattern on the read
   side.** Let the per-entry `KeyError`/`TypeError` propagate (or wrap it in a named error, e.g.
   `DmxChannelDecodeError`, carrying the universe's `universe_num` and the failing entry's index —
   same "identify what failed" instinct as `FR-023`). This is the most consistent choice: it makes
   `set_dmx_channels` behave like the rest of the read path (`ConfigManager`/`CuemsScript.load`
   already raise `SchemaError`/`ValidationError` on structural problems per feature 008's ITEM E),
   and it surfaces a corrupt document immediately instead of at some unrelated point during
   playback. Requires deciding whether this is a T1-class failure (schema-shape) or a new
   application-level validation tier — `dmx_channels`' shape is not currently expressible in XSD
   terms beyond what T1 already checks, so this is likely a new, narrowly-scoped check rather than
   a `.xsd` change.
2. **Convert entries independently — one bad entry drops only itself, not the batch.** Move the
   `try`/`except` inside the `for` loop, per-entry, and either skip the bad entry (with a log line,
   current logging behaviour kept) or collect bad entries into a side channel the caller can inspect
   (echoes `LoadReport`'s repair-record shape from feature 008's ITEM E,
   `cuemsutils.errors.LoadReport`/`RepairRecord` — though `dmx_channels` is show content, not
   config, so reusing that exact type is not assumed, only the pattern of "report what was dropped
   rather than saying nothing"). This preserves "loading mostly-good data still loads" while closing
   the "good entries silently get corrupted too" defect specifically.
3. **Do nothing structural; just log louder.** Keep the swallow, but make the log line identify the
   universe and the failing index/value (today's message has neither), so at least the operational
   trace exists. The weakest option — it doesn't stop garbage from reaching the engine, only makes it
   diagnosable after the fact — listed for completeness, not as a recommendation.

None of these are free: option 1 is a behaviour change that could turn a document that "loads with
bad data" today into one that fails to load at all, which is exactly the kind of change feature
008's `migration-guide.md` and D3 relaxations show this codebase treats carefully and records
explicitly rather than doing incidentally. Whichever option is chosen belongs in a scoped feature
with its own spec, its own decision record, and — given the precedent this document exists to
name — the same "characterize before changing" discipline `tests/contract/test_nodeindex_characterization.py`
and `tests/unit/test_dmx_universe_channels.py` both already apply.

## Evidence trail

- Defect site: `src/cuemsutils/cues/DmxCue.py:372-396`.
- Characterization tests: `tests/unit/test_dmx_universe_channels.py` (8 tests, all passing against
  current behaviour).
- Registry binding proving reachability from document decode: `src/cuemsutils/xml/registry.py:236`.
- Generic setter dispatch: `src/cuemsutils/helpers.py:527-538` (`CuemsDict.setter`).
- Prior art for the fix shape: `tests/contract/test_dmx_failure_path.py` and its docstring
  (feature 005, `DmxSceneWriteError`, `FR-019` row 7, `FR-023`).
