# Decision stop 2 — the per-rule corpus sweep

**Date**: 2026-08-18
**Question answered**: §9.2 (2) — *"if T2 runs on read, which of the 14 rules would reject a
document currently accepted? Answer with a corpus sweep, per rule, before deciding — not
with a judgement call."*
**Script**: [`sweep_t2.py`](sweep_t2.py) · run with
`PYENV_VERSION=3.11.9 pyenv exec hatch run python specs/006-public-object-api/sweep_t2.py`

## Method

For every corpus document that loads to objects today, walk the decoded object tree and, for
each value-rejecting setter applicable to an object's class, **open the `_initialized` gate
and re-invoke the real setter with the value the load path actually produced**. That runs
genuine rule code against genuine decoded values — which is precisely what "T2 runs on read"
would do. The uuid rule is measured twice: strict (`Uuid(raw)`, what a T2 rule would do) and
through the real coercion path (`node.coerce(...)`, what the load path does today).

Sources swept: the 3 corpus script documents that load today, plus
`tests/data/sample_script.json` — the live editor payload — ingested through
`CuemsParser(data).parse()`, which is the editor's actual path.

### Three probe artifacts corrected before the numbers below were trusted

Each produced a false finding on an earlier run, and each is a trap for anyone re-running
this:

1. **`isinstance` without `hasattr`.** `set_output_name` and `set_canvas_region` are declared
   on `VideoCueOutput`, not on the `CueOutput` base, so matching the base class reported
   `AttributeError: 'AudioCueOutput' object has no attribute 'set_output_name'` as two rule
   rejections. It is a missing attribute, not a rejected value.
2. **Sweeping every key named `id` as a uuid.** `RegionType.id` is `xs:nonNegativeInteger`
   (and `Region.set_id` assigns raw, with no coercion at all), and `ui_properties` is
   `xs:anyType` wildcard content no adapter touches. Both were reported as uuid rejections.
   Only fields the schema types `UuidType`/`TargetType` count.
3. **`CuemsScript(payload)` does not build wrapped children.** The sample file is a WebSocket
   envelope (`{action, value}`), and even correctly unwrapped, `CuemsScript(body)` leaves
   `contents` as plain `{"AudioCue": {…}}` dicts — **zero** cue objects, so the sweep ran
   clean over an empty tree and proved nothing. The editor's real path is `CuemsParser`.

Artifact 3 is a finding in its own right: **it is the work `from_json` (FR-002) has to do.**

## Result

| Rule | Objects probed | Would reject a currently-accepted document? |
|---|---:|---|
| R01 `ActionCue.set_action_target` | 2 | **No** |
| R02 `CueOutput.set_output_name` | 9 | **No** |
| R03 `CueOutput.set_canvas_region` | 9 | **No** |
| R04 `CuemsScript.set_CueList` | 4 | **No** |
| R05 `FadeCue.set_action_type` | **0** | *unproven — no coverage* |
| R06 `FadeCue.set_curve_type` | **0** | *unproven — no coverage* |
| R07 `FadeCue.set_duration` | **0** | *unproven — no coverage* |
| R08 `FadeCue.set_target_value` | **0** | *unproven — no coverage* |
| R09 `FadeProfile.set_parameter_value` | **0** | *unproven — no coverage* |
| R10 `FadeProfile.set_type` | **0** | *unproven — no coverage* |
| R11 `FadeProfile.set_mode` | **0** | *unproven — no coverage* |
| R12 `FadeProfile.set_parameters` | **0** | *unproven — no coverage* |
| R13 `Media.set_duration` | 12 | **No** |
| R14 `MediaCue.set_fade_profiles` | 12 | **No** |
| R15 `Uuid` uuid4 shape (via `set_id`) | 36 | **YES — 3 occurrences** |

**Headline: of the fourteen setter rules, none rejects anything the library accepts today.**
The single rule that would is the fifteenth — the one that does not live in a setter.

### R15, the only rejection

Three occurrences, all in the live editor payload, all the same value:

```
$.CueList.contents[0].Media  id='00000000-0000-0000-0000-000000000000'
$.CueList.contents[1].Media  id='00000000-0000-0000-0000-000000000000'
$.CueList.contents[2].Media  id='00000000-0000-0000-0000-000000000000'

strict  Uuid(...)      -> ValueError: uuid 00000000-… is not valid
today   node.coerce(…) -> str('00000000-0000-0000-0000-000000000000')   ← absorbed
```

`Media.id` is `cms:TargetType`, which resolves to `_UuidAdapter`. The adapter **keeps an
unparseable value as its raw string** — deliberately, per feature 004 — and that is exactly
what preserves read parity today. The nil UUID is not a corner case in a fixture: it is what
the editor sends for media that has no id yet, three times in one ordinary payload.

So a strict "ids must be real uuid4s" rule on the read path would reject **live editor
traffic on its first use**. This is measured, not projected.

### The coverage gap — 8 of 15 rules are untested by the corpus

Every `FadeCue` and `FadeProfile` rule has **zero** corpus coverage. There is no fade cue in
any vendored document, and `grep` finds no fade fixture outside `sample_script.json` either.

This is a gap in the evidence, not a clean result, and it must not be read as one:

- **Proven safe**: R01, R02, R03, R04, R13, R14 — six rules, exercised against real values.
- **Unproven**: R05–R12 — eight rules, never reached. The sweep cannot say whether they
  would reject anything, because the corpus contains nothing for them to judge.

Feature 003 (`003-fade-cue`) built the fade cue model and its tests, so the rules are covered
by *unit* tests; what is missing is a **document** exercising them end to end. Any decision
that turns these eight rules on for the read path is making an unevidenced change, and the
honest mitigation is to add a fade-cue document to the corpus **before** flipping them,
not after.

## What this evidence supports

1. Turning the fourteen setter rules on for the read path is **safe against everything
   measurable today** — six proven, eight unproven-for-lack-of-input, zero rejections.
2. Turning the uuid4 shape rule on for the read path is **not safe** and would break the
   editor immediately.
3. The two rules therefore cannot share a single answer, and any decision that treats "the
   T2 tier" as one uniform switch will get one of the two wrong.
