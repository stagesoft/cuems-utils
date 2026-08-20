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

---

# Post-implementation: what the corpus proves now (T077)

**Date**: 2026-08-20 · **Added by**: US5, after the registry landed

The sweep above was taken *before* the rules had names. This section records
what changed, and — more importantly — **what did not**. The gap is recorded,
never read as a clean result.

## The eight unproven rules are now exercised

`cuems-utils/fade_showcase.xml` was added in **Phase 1** (T003c), before any
projection code existed, with its goldens captured by the pre-feature harness.
That sequencing is the point: a golden captured after the projection changed is
generated by the code it is meant to arbitrate, so the document would have
joined the corpus already exempt from the byte-identity guarantee every other
document carries — invisibly.

`tests/contract/test_fade_rules_corpus.py` (T076) exercises each of R05–R12
**twice** against it: passing on the document as authored, firing on a variant
that violates it. One without the other proves nothing.

| Rule | Registry name | Corpus coverage now |
|---|---|---|
| R05 `FadeCue.set_action_type` | `fade_action_type` | **covered** |
| R06 `FadeCue.set_curve_type` | `fade_curve_type` | **covered** |
| R07 `FadeCue.set_duration` | `fade_duration_positive` | **covered** |
| R08 `FadeCue.set_target_value` | `fade_target_value_range` | **covered** |
| R09 `FadeProfile.set_parameter_value` | `fade_profile_parameter_value` | **covered** |
| R10 `FadeProfile.set_type` | `fade_profile_type` | **covered** |
| R11 `FadeProfile.set_mode` | `fade_profile_mode` | **covered** |
| R12 `FadeProfile.set_parameters` | `fade_profile_parameters` | **covered** |

The document carries **both** profile modes, preset and parametric, because
three of the eight only apply to one of them: two presets would leave
`parameters` untouched and R09/R12 unreached again.

## What is still not proven, and will not be by this feature

**The original question stays answered the same way.** The sweep asked whether
turning T2 on *for the read path* would reject a currently-accepted document.
Adding a fade document tells us the eight rules **pass on it**; it does not tell
us they would pass on every fade document anyone has ever written, because the
corpus still contains exactly **one**, and this project authored it.

That is a real limit:

- the fade document is a *fixture*, not a vendored artifact from a running
  system. Every other script in the corpus came from `cuems-engine` or
  `cuems-editor`; this one came from feature 006.
- so the eight rules are now **proven consistent with the model**, and still
  **unproven against field data**. The other six (R01–R04, R13, R14) were
  proven against real values and remain so.

The decision does not rest on it either way: T2 runs on `save()`/`validate()`
only, so no rule — proven or not — has been given reach on the read path.
Closing that distinction properly needs a fade cue authored by the editor and
saved by the engine, which this repository cannot manufacture.

## R15 is unchanged, and stayed out of the registry

The uuid4 shape check is **not** in `RULES`, and
`tests/unit/test_id_clearing.py` asserts its absence rather than describing it.
It remains a coercion concern: `_UuidAdapter` keeps an unparseable identifier as
its raw string, which is what lets the editor's nil `Media.id` — three
occurrences in one ordinary payload — keep loading.

Two tests now pin the consequence end to end: the nil uuid survives
`from_json()`, and `validate()` reports nothing about it. If the rule ever
joined the registry, both would fail immediately rather than the editor failing
in production.

## The tier's inventory is now derived

`SEMANTIC_RULES` was a hand-written tuple of three prose names read by two
tests. It is generated from `RULES` (T072a) — the prose became identifiers, and
both readers were updated. **Rule messages, which are what users see, are
unchanged**; that is asserted per rule in
`tests/unit/test_setter_error_propagation.py`.
