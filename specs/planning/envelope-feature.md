# The Envelope feature — design inputs and open decisions

**Status:** design inputs only. No feature number assigned. **Not imminent** — expected to land
together with the Crossover feature (repo owner, 2026-08-27), which is why feature 008 deletes the old
surface outright rather than renaming it: there is no near-term re-add to churn against.

**Landing with Crossover is the right shape, provided one thing holds.** Two features that both touch
`script.xsd` should land as **one** schema change at **one** version step — one migration-guide entry,
one conversion (identity, if both are additive), one thing for operators to understand. Two separate
bumps for work that ships together is pure cost. The condition: this holds only while both are
*additive*. If Crossover **modifies or narrows an existing type** — output routing, channel mapping,
anything already declared — it is a rule 4 migration with a real conversion, and it should be assessed
on its own terms rather than inheriting this document's "identity conversion" conclusion (§7.2).
**Created:** 2026-08-27
**Origin:** feature 008 deletes the unimplemented fade-profile surface
(`specs/008-rebuild-extension/spec.md`, FR-007a — FR-007c, Clarifications session (d)). This document
is what stops that deletion from losing the design thinking embedded in the deleted code.

**Read first:** `specs/agreements/schema-evolution-convention.md` — the rules that make reintroducing a
type cheap, and the ones that make it expensive.

---

## 1. What was deleted, and what it meant

`script.xsd` declared a fade-profile surface that was reachable from two cue types and consumed by
nothing:

| Artifact | Where it lived |
|---|---|
| `FadeProfileType` | `script.xsd:135` |
| `FadeProfilesWrapperType` | `script.xsd:145`, `fade_profile` child, `maxOccurs="2"` |
| `FadeParameterType` | bound to `FadeFunctionParameter` |
| `fade_profiles` element | `AudioCueType` (`script.xsd:282`), `VideoCueType` (`:319`), `minOccurs="0"` |
| `FadeProfile`, `FadeFunctionParameter` | `src/cuemsutils/cues/FadeProfile.py` |
| Five semantic rules | `fade_profile_type`, `fade_profile_mode`, `fade_profile_parameters`, `fade_profile_parameter_value`, `fade_profile_caps` |

The shape it expressed, which is worth keeping:

- **A profile is directional.** `type` is `in` or `out`. The wrapper's `maxOccurs="2"` plus the
  `fade_profile_caps` rule enforce at most one of each — an envelope has a head and a tail, and no more
  than one of either. This constraint was correct and should survive into whatever replaces it.
- **Two modes.** `preset` names a system-defined function by `function_id` and needs no parameters;
  `parametric` supplies named numeric parameters that shape the curve. The distinction between "pick a
  standard curve" and "describe a curve" is real and worth keeping.
- **Parameters are named and numeric.** `parameter_name` (string) and `parameter_value` (float), with a
  duplicate-name rule. A flat named-scalar bag, deliberately not a nested structure.
- **It attaches to Audio and Video cues, not to `MediaCueType`.** Feature 004 (T059) moved it down
  deliberately. Whatever replaces it should re-derive that placement rather than inherit it unexamined.

## 2. Why it was deleted rather than renamed

The trigger was a name collision: `FadeProfile.py` sits beside `FadeCue.py`, both concern fades, and
they are unrelated — a *profile* is a cue's own in/out envelope, a `FadeCue` is an `ActionCue` subtype
that fades **another** cue. The collision caused a real misreading during 008's clarification (the
profile module was proposed for deletion as a suspected orphan; it was, at that moment, fully live).

The first proposal was to rename `FadeProfile` → `Envelope`. That was rejected for one reason:

> **Renaming would enshrine a shape already known to be wrong.**

See §3. The replacement cannot use the deleted field set, so a rename would ship a broken shape under a
better name — and a better name invites use. Deletion lets the replacement arrive as a **new type**,
which the schema-evolution convention sanctions as the non-breaking path, instead of forcing a second
migration on documents that would by then hold real data.

**Cost of the deletion was measured, not assumed:** zero references to `fade_profile`, `FadeProfile` or
`function_id` across `cuems-engine`, `cuems-editor` and `cuems-frontend` (2026-08-27), and the repo
owner confirms no project document depends on it. The feature was never implemented end to end.

## 3. The two gaps that made the old shape unusable

These are the load-bearing findings. Any replacement design must answer both.

### Gap 1 — an envelope cannot produce a fade cue

The stated intent is that an envelope materialises `FadeCue` objects positioned at the start and end of
a media cue. But the two shapes do not meet:

| `FadeCueType` requires | `FadeProfileType` provided |
|---|---|
| `curve_type` (`FadeCurveType`) | `mode` + `function_id` + `parameters` |
| `duration` (`CTimecodeType`) | — **nothing** |
| `target_value` (`PercentType`) | — **nothing** |
| `action_target` (from `ActionCueType`) | — implied by attachment, never stated |

Two of the four required fields have no source. A replacement must either declare them, or define
where they are inherited from (the parent cue's own duration? a system default? the media's length?).
This is a design decision, not an implementation detail.

### Gap 2 — two vocabularies for one question

`FadeCurveType` enumerates `linear | exponential | logarithmic | sigmoid`. The profile instead carried
`mode` (`preset | parametric`) plus a free-string `function_id` plus a parameter list. Both answer
"what shape is this fade", and both were introduced by feature **003**, the same feature.

This is the duplication disease the whole XML rebuild has been curing elsewhere — two sources of truth
for one property — sitting inside the fade domain itself. D2 says the schema settles such questions.
A replacement must pick one:

- **Envelope derives from `FadeCurveType`** — envelopes gain `curve_type` and lose `mode`/`function_id`.
  Simple, immediately expandable into `FadeCue`, but loses the parametric-curve capability.
- **`FadeCurveType` becomes the preset vocabulary** — `curve_type` values become the legal
  `function_id`s in `preset` mode, and `parametric` remains for custom curves. Preserves both
  capabilities; requires `FadeCue` to accept a parametric form too, which widens `FadeCueType`.
- **They stay separate with a documented mapping** — worst option, and named here only so it is
  rejected explicitly rather than by default.

## 4. The central open decision — where expansion happens

An envelope is declarative; a fade is an action. Something must turn one into the other. **Where that
happens is the design.**

| Placement | What the document holds | Consequence |
|---|---|---|
| **Authoring time** (editor) | Real `FadeCue`s | Users can hand-edit individual fades. Raises whether the envelope belongs in the schema at all, or is purely an editor affordance. |
| **Load time** (`cuemsutils`) | Envelope; model materialises fade cues | **Rejected on current evidence.** It breaks the invariant features 005 and 006 established — that the object model is a faithful projection of the document. `load(save(x)) == load(x)` survives only if expansion is exactly reversible, and re-collapsing an edited fade cue back into one envelope is lossy. |
| **Engine time** (`cuems-engine`) | Envelope; engine builds fades when running | Serialization stays pure. The engine already owns fade execution (`ActionHandler._handle_fade_action`, with the gradient engine). |

**Recommendation: engine time, or authoring time.** Not load time.

The general principle this follows is the one features 004–008 applied throughout: the model layer
owns *what a document says*, and other repositories own *what happens as a result*. D11 brought the
node model in and left discovery and role election out; D22 brings the network-map config object in and
D23 explicitly declines to bring the daemon's orchestration with it. An expansion that runs inside
`cuemsutils` and puts derived objects into the persisted model runs that principle backwards.

## 5. A gap in the current fade behaviour, worth fixing regardless

Independent of envelopes, and already true today:

**Nothing reconciles a cue's declared fade shape with a `FadeCue` that targets it.**
`ActionHandler._handle_fade_action` does not consult the target cue's declared profile at all. A cue
could declare an exponential in-envelope while a `FadeCue` targeting it specifies `linear`, and no
layer notices the disagreement.

This is a `cuems-engine` question and can be answered before, after or independently of the envelope
work: should `_handle_fade_action` fall back to the target's declared envelope when the fade cue does
not override it? Answering it first would clarify what an envelope is *for*, which would in turn
constrain §4.

## 6. Adjacent cleanup this feature should absorb

- **`_handle_fade_in` / `_handle_fade_out` in `cuems-engine`.** Feature 008 removes `fade_in` and
  `fade_out` from `ActionType` (FR-029a), making both handlers and their dispatch entries unreachable.
  Their deletion is feature 009's (FR-053b). Note that `_handle_fade_out` carries a recorded
  zombie-process defect — it bumps the generation counter without disarming — which disappears with the
  handler rather than needing a separate fix.
- **`MediaCue.get_fade_profile`'s `'fade_in'`/`'fade_out'` aliases** go with the deletion in 008. If a
  replacement reintroduces a direction accessor, it should **not** reintroduce those aliases: they are
  the source of the original collision.
- **`JSON_SELF_WRAPS` on the deleted classes was likely vestigial.** The nested wire projection uses
  schema element names (`fade_profile`, `parameter`), not class names — so the self-wrap only applied to
  an object dumped standalone, a path nothing appears to use for profiles. If a replacement class sets
  that flag, it should be because something dumps one standalone, not by imitation.

## 7. Constraints any replacement inherits

1. **New type, optional attachment.** Per the schema-evolution convention: a required element may
   appear in a **new** type, but the element attaching that type to `AudioCueType`/`VideoCueType` must
   be `minOccurs="0"` with a model-layer default. This is what makes reintroduction non-breaking, and
   it is the whole reason deletion was preferable to renaming.
2. **Feature 008's version marker applies — and the reason is the reverse of the obvious one.**
   Reintroducing the envelope as new types attached by `minOccurs="0"` elements is **purely additive**,
   so there is **no conversion to write**: every document already on disk stays valid in the new
   library. That is precisely what deleting rather than renaming bought, and requiring a migration for
   it would discard the benefit.
   A version step is still warranted, for the **opposite direction**. No schema declares a wildcard, so
   a *new* document carrying `<envelope>` fails structural validation in an *older* library with a bare
   "unexpected element" error. Incrementing the version turns that into feature 008's FR-052
   diagnostic — "written by a newer version than this library" — which is both the true statement and
   the actionable one for an operator on a node that was not upgraded.
   So: **bump the `script` version, with an identity conversion.** Feature 008's FR-051d requires the
   machinery to support exactly that — a step that increments the version and transforms nothing,
   writing no backup and reporting no repair.
3. **The descriptor will publish it.** Feature 008's schema descriptor emits field names, types,
   cardinality, enumeration values, defaults and a repairability classification for every type in every
   schema (FR-027 — FR-031b). A reintroduced envelope type is published to the cue-creation UI
   automatically — which means its enumerations must be true and its defaults must be real values, not
   placeholders.
4. **Semantic rules must declare repairability.** Feature 008 requires every registered semantic rule to
   state whether its violation is repairable (FR-031b). The five deleted rules did not; any replacement
   rules must.
5. **Byte-identical `project_load` still binds** (Part 2d). Whatever the envelope's wire shape is, it
   reaches the Angular UI verbatim.

## 8. Open questions, none answered here

1. Where does expansion happen — authoring, load or engine time? (§4)
2. Which curve vocabulary survives, and does `FadeCueType` widen to carry parametric curves? (§3, Gap 2)
3. Where do `duration` and `target_value` come from — declared on the envelope, or inherited from the
   parent cue or its media? (§3, Gap 1)
4. Does an envelope remain an attribute of a cue, or become a reusable named object referenced by
   several cues? The deleted design assumed the former; the `preset`/`function_id` split hints that
   someone was reaching for the latter.
5. Should `_handle_fade_action` consult a target's envelope today, independent of all of the above? (§5)
6. Is the name `Envelope` or `EnvelopeProfile`? "Envelope" already denotes the shape, so "profile" may
   be redundant — but if the answer to (4) is "reusable named object", *profile* earns its place.
   (Note: the noun is **envelope**; "envelop" is the verb.)
