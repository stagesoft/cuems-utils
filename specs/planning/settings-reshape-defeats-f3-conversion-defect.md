<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Defect — 013's player reshape defeats F3's `settings` 1 → 2 conversion

**Found by** `cuems-nodeconf`'s feature-014 gate (T030), reported in that repository at `2045897`,
`specs/sibling-gates/014-xs-boolean-and-media-elements.md` §3.2.
**Verified independently in this repository** 2026-10-05, at `b8b44e7`, by reproducing both tool
orders on a real pre-013 document. The sibling named the dead end; the mechanism below is narrower
than its report states and makes the fix a small one.

**Severity: this blocks the `xml-refactor-merge-candidate` tag.** Not because it is subtle, but
because the affected document is every `settings.xml` last written before 2026-09-23 and not
regenerated since — which on a deployed node is the ordinary case. §3 bounds that in both
directions, including the counterexample on this box that keeps it from being *every* document.

---

## 1. The mechanism, in one paragraph

`reshape_file` (`xml/reshape_devices.py`) mutates the tree **before** it validates it:

```python
elif schema_name == "settings":
    reshape_players(root)            # node/audioplayer -> node/players/player[@class='audio']
...
get_schema(schema_name).validate(_as_the_load_path_sees_it(schema_name, tree))
```

`_as_the_load_path_sees_it` exists precisely so the two migration tools compose — it applies the
registered version conversion to a throwaway copy, which is 013's answer to the deadlock its own
docstring describes at length. But it is handed the **already-reshaped** tree, and F3's converter
addresses the elements by their **pre-013 flat paths**:

```python
def _settings_1_to_2(root):                       # xml/versioning.py:321
    node = root.find("Settings/node")
    for section, field in (("audioplayer", "audio_cards"), ("dmxplayer", "universes")):
        parent = node.find(section)               # <- None after reshape_players ran
        if parent is None:
            continue                              # <- nothing dropped, silently
```

`reshape_players` has just renamed `audioplayer` to `players/player[@class='audio']`, so both
`find`s miss, both `continue`, nothing is dropped, and the validation then sees `audio_cards` inside
a `<player class="audio">` whose `AudioPlayerType` does not declare it. The tool refuses — correctly
— and writes nothing.

**So the very mechanism 013 built to make reshape and convert compose is defeated by the reshape it
runs after.** `settings` is the only schema where this can happen, because it is the only one whose
registered conversion names elements that the reshape *moves*.

## 2. Reproduced, both orders

Input: `cuems-nodeconf`'s `tests/fixtures/etc_cuems/settings.xml` at `4d7c91d` (before that
repository hand-fixed it) — flat players, `audio_cards` and `universes` present, no `doc_version`.

| Order | Result |
|---|---|
| `cuems-reshape-devices <file>` | `skipped (would not validate: … Unexpected child with tag 'audio_cards' at position 3 … Schema component: AudioPlayerType …)`, exit 1 |
| `cuems-convert-documents <file>` | `skipped (… Unexpected child with tag 'videoplayer' at position 14 … Schema component: NodeConfType …)`, exit 1 |

Note what the second line says, because it is the part the sibling's report did not separate out:
**convert-first drops the two fields correctly** — its flat paths match a flat document — and then
fails on the *device shape* alone. The F3 half of the migration works in that order. What stops it
is that `cuems-convert-documents` validates before writing, so its correct partial result is thrown
away.

The load path dead-ends for the same pair of reasons, in the other order:
`read_versioned_config_document` converts first (the drop fires), then calls
`raise_if_old_device_shape`, which refuses a flat document and tells the operator to run
`cuems-reshape-devices` — which cannot.

**No combination of the shipped tools or the load path produces a valid document.**

## 3. Who is affected — bounded, and measured rather than argued

The sibling's report judges it *"likely rare in the field"*, on the grounds that 013's own
measurement found the old shape only in test fixtures. The schema history says it is wider than
that, but **not** as wide as a first reading suggests. Both bounds below are measured.

**The upper bound, and the half of the argument that holds:**

- Pre-F3, both elements were declared **without `minOccurs`** — so both were **required**
  (`git show 782f669^:src/cuemsutils/xml/schemas/settings.xsd`, lines 99 and 117). F3's own
  converter docstring says so in as many words: *"Both were **required**, so every settings document
  in the field carries them."*
- F3 landed 2026-09-23 (`782f669`); 013's player reshape landed 2026-10-01 (`c0a41c0`), **after**
  it. So **any document carrying the two fields is necessarily also flat-shaped** — the dead-end
  state is not a freak combination, it is the only state a pre-F3 document can be in.
- Feature 011 installs its generated documents **only where absent**, so an existing node keeps the
  `settings.xml` it has and is never quietly regenerated out of the problem.

So: **every `settings.xml` last written before 2026-09-23 and not regenerated since.** On a deployed
node that is the ordinary case, which is why this blocks the tag.

**The lower bound, because the converse does not hold** — and this box is the counterexample, so it
is stated rather than left for someone to find:

```
/etc/cuems/settings.xml        flat players (<videoplayer>/<audioplayer>/<dmxplayer>), no doc_version
                              audio_cards / universes: ZERO occurrences
cuems-reshape-devices <copy>   -> "reshaped"      # succeeds
```

A flat-shaped document **without** the retired fields migrates cleanly. Being pre-013 does not imply
being pre-F3 — the two windows are eight days apart, and anything generated by feature 011's
`make_defaults` / `cuems-init-node` in between is in exactly that state. ⚠ So *"every settings
document that exists today"* would be the wrong claim, and the triage question for an operator is
**not** "is it flat-shaped?" but:

```bash
grep -cE '<(audio_cards|universes)>' /etc/cuems/settings.xml    # non-zero  ->  affected
```

**Why no suite caught it**: this repository's own fixtures were migrated shape-first, document by
document, so none was ever in both states at once when a tool was pointed at it — and the one live
document on this box happens to sit in the eight-day window. Two migrations, each tested in
isolation, never exercised together — which is exactly what 013's `_as_the_load_path_sees_it` was
written to prevent for `script`, and got right there.

## 4. The fix, and the one to avoid

**Make `_settings_1_to_2` find the fields in either shape.** Four lines: look under
`node/audioplayer` *and* under `node/players/player[@class='audio']`, same for `dmxplayer` /
`universes`. It is a conversion step, so being tolerant of both shapes is in character — a
conversion exists to read what is on disk, and after 013 "what is on disk" has two spellings.

Three properties worth keeping in whatever lands:

1. **It must drop the field wherever it finds it**, not assume one shape, because the document
   reaching the converter may or may not have been through `reshape_players` first — on the load
   path it has not, inside `reshape_file`'s probe it has, and both are legitimate.
2. **It must stay idempotent**, like every other step: a document with neither field present
   converts to itself.
3. **The red test is the composition, not the unit.** A unit test on `_settings_1_to_2` with a
   reshaped tree would pass the moment the paths are added and would not catch the next instance of
   this class. The test that matters runs `cuems-reshape-devices` over a document that is *both*
   pre-013 and pre-F3 and asserts it is **reshaped**, then loads it.

**The fix to avoid**: reordering `reshape_file` to convert before reshaping. That inverts the
deadlock 013 resolved deliberately and documented at length — a version-1 `script` carries a bare
`<duration>` that the 1 → 2 step wraps, so convert-before-reshape fails for `script` exactly as
reshape-before-convert fails for `settings` here. The order is right; the converter's paths are
stale.

## 5. Scope — whose feature is this?

**Not 014's.** 014 is `xs:boolean`, the media block, the curve names and the configuration
ingestion; none of them touches `settings`' player shape or F3's converter, and 014's own arms are
unaffected (`cuems-nodeconf` measured the identical 32-failure set at the 014 branch point and on
the 014 branch, so the feature neither caused nor fixed it).

It is a **013 defect**, found after 013 landed on its branch. On this repository's own precedent it
wants a numbered feature of its own — `dmx-universe-channel-conversion-defect.md` →
`specs/009-fix-dmx-channel-conversion/` is the shape, and CLAUDE.md names it as the precedent — and
this record is the prompt for it. **Delete this file once that feature lands.**

**It must land before the coordinated `xml-refactor-merge-candidate` tag**, because that tag is what
puts the new schema in front of nodes holding these documents. Everything else in 011–015 can ship
with it; this cannot ship without it.

## 6. What `cuems-nodeconf` did locally, and why it does not close this

It hand-rewrote its two fixtures (`61c5705`): players wrapped, `audio_cards`/`universes` dropped,
`doc_version="2"` set, validated against the live schema; its suite went 142/174 → **174/174**. That
is the right call for a fixture and it closed that repository's 013 debt — which `cuems-utils`' own
`specs/013-device-class-reshape/sibling-repository-updates.md` had explicitly left open as *"a
prediction for them"* and nobody closed.

But a hand-rewrite is not available to an operator with a node in the field, and that is the case
§3 is about.
