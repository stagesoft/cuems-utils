<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Project-scope pause / resume: deferred, with the retired vocabulary

**Status: deferred to a future release.** Written 2026-10-21 by feature 017
(`specs/017-release-line-reconciliation/`, FR-053, Q1, Q2, Q13), in the commit that retires the
vocabulary, so the values are never gone without this record. It is a living, forward-looking
document, not part of 017's frozen record.

**What it is for.** Whoever picks up project-level pause/resume starts here. It covers:
1. what was removed, verbatim;
2. what exists to build on;
3. what reinstating takes in this library, the engine (`libmtcmaster`) and the siblings;
4. a naming option raised along the way.

Every cross-repository claim names its path and commit, read from the checkouts on 2026-10-21.

---

## 1. What was retired, verbatim

### 1.1 The schema values

From `src/cuemsutils/xml/schemas/script.xsd` at `2318dee` (lines 321–322), inside
`<xs:simpleType name="ActionType">`:

```xml
      <xs:enumeration value="pause_project" />
      <xs:enumeration value="resume_project" />
```

They were removed by feature 017 (A-1's commit, 2026-10-21) **inside the still-unreleased
`script` 1 → 2 step**. So there is no version 3 and no conversion entry. `ActionType` went from 12
values, through 13 (the release-line merge added `stop_project`), to **11**:
`play pause stop load unload enable disable fade_action wait go_to stop_project`.

### 1.2 The enum audit's retained set

`tests/contract/test_enum_audit.py`, `RETAINED[("script", "ActionType")]`, before 017:

```python
        "play", "pause", "stop", "load", "unload", "enable", "disable",
        "fade_action", "wait", "go_to", "pause_project", "resume_project",
```

### 1.3 Why feature 008 kept them

`specs/008-rebuild-extension/enum-audit.md` (frozen), lines 35–36:

| Value | Verdict | Evidence |
|---|---|---|
| `pause_project` | RETAIN | No dispatch entry found in `ActionHandler.py`; project-level pause is a different code path (`ControllerEngine`/`NodeEngine` status machinery, not `ActionCue` dispatch). Not in scope for removal |
| `resume_project` | RETAIN | Same as `pause_project` |

### 1.4 What rc17 said

`CHANGELOG.md`, section `0.1.0rc17 — 2026-10-15` (kept verbatim in this repository's changelog,
because it is true of rc17):

> `pause_project`, `resume_project`, `load`, `unload` and `wait` stay in the enum and stay
> unimplemented.

### 1.5 Why they could be removed without a conversion (Q13, measured 2026-10-21)

`git grep pause_project|resume_project` was run on every checkout's working head and on its
release lines:

| Repository | Result |
|---|---|
| cuems-frontend (`9e91464`; `origin/dev` `6dc775c`; `origin/main`) | **0**: never authored |
| cuems-editor (`a2431f0`; `origin/debian/bookworm` `69d749e`; `origin/main`) | **0** |
| cuems-nodeconf, cuems-power-bridge (all lines) | **0** |
| cuems-utils corpus and goldens | **0** |
| cuems-engine | named as unimplemented, and in one test (§2.2). The only "implementation" is 2020 placeholder code (§2.1) |

No producer ever wrote either value, so no document in the field carries one. A document that
somehow did would now be refused by **T1**: an enumeration violation on `action_type`, whose message lists the allowed values. It is never rewritten into another
action.

---

## 2. What exists to build on

### 2.1 The 2020 "implementation" is a placeholder, not prior art for behaviour

`cuems-engine` `origin/dev` `9852d79` (2020-12-17), `src/cuems/ActionCue.py:95-98`, in the old
layout:

```python
        elif self.action_type == 'pause_project':
            self._action_target_object.enabled = False
        elif self.action_type == 'resume_project':
            self._action_target_object.enabled = False
```

Every branch of that dispatch does the same thing (`fade_in`, `wait` and `go_to` too). So it
records only that the names were planned. **There is no working behaviour to recover.**

### 2.2 The engine today

All of these are in `cuems-engine` `aa0ffe6` (its `009-release-line-reconciliation` branch):
- `src/cuemsengine/cues/ActionHandler.py:27-29`: *"The XSD schema … also defines these
  not-yet-implemented actions: load, unload, wait, pause_project, resume_project."* After 017 the
  last two are no longer in the schema, so the comment should drop them (upstream report).
- `SUPPORTED_CUE_ACTIONS` and `_ACTION_HANDLERS` (`ActionHandler.py:30-40`, `:752-760`) dispatch
  `play pause stop enable disable fade_action go_to`, all **cue**-level.
- `NodeEngine.commands_dict` (`src/cuemsengine/NodeEngine.py:358-372`) has `"pause": None`: the
  operator-level pause command is **not implemented** on nodes. `"stop": self.stop_playback`
  is.
- `EngineStatus.pause` (`src/cuemsengine/core/EngineStatus.py:66-72`) exists as a status field,
  and nothing sets it. This is the "status machinery" 008 pointed at. It is a slot, not a feature.
- On the release line, `origin/debian/bookworm` `b8431a3`, the engine's **`stop_project`** path,
  which is the worked precedent for §3:
  - **node:** `NodeEngine.py:1209-1212` sees an applied `stop_project` action and calls
    `_notify_stop_project`, guarded by a watchdog (`:109-113`);
  - **controller:** `ControllerEngine.py:589-592` routes it to `_handle_stop_project`
    (`:718-…`), which validates the sender, the cue, `running` and `run_seq`, then runs the
    operator STOP (`stop_script`);
  - **introduced by** `4121749` "feat(actions): stop_project ActionCue, the authored end of an
    unattended show (869fhjdq5)".

### 2.3 `libmtcmaster`: what pause and play actually do

`../libmtcmaster` `6afe645`. `interface.h:26-32` exports `MTCSender_play`, `MTCSender_stop`,
`MTCSender_pause` and `MTCSender_setTime`. The engine wraps them with `ctypes` in
`cuems-engine` `src/cuemsengine/core/libmtc.py:29-39`, and calls them from `ControllerEngine`:
`start_timecode()` calls `MTCSender_play` (`ControllerEngine.py:414-419`), and `stop_timecode()`
calls `MTCSender_stop` (`:421-426`).

**⚠ The semantics are a toggle, not a state.** From `MtcMaster_class.cpp`:

```cpp
void MtcMaster::pause() { play(); }            // :119-122 — pause IS play

void MtcMaster::play() {                       // :125-…
    if (playing) { setPlaying(false); /* … wait for the thread */ }   // already playing → PAUSE
    else         { /* start the sender thread from mtcTime */ }       // not playing → PLAY
}

void MtcMaster::stop() {                       // :163-…
    setPlaying(false); /* … */ setTime(0);     // stop → and reset the time to 0
}
```

So:
- `pause` and `play` are **the same call**. Each flips the sender between running and held, and
  **keeps** the time.
- `stop` holds **and resets the time to 0**. That is why `stop_project` (the operator STOP) is
  not a pause.
- **A naïve `resume_project → MTCSender_play` pauses a show that is already running.** Every
  handler must read the state first (`getPlaying()` exists in `MtcMaster_class.h:101`, but
  `interface.h` does **not** export it). Either the engine keeps its own
  `paused`/`running` state and calls the toggle only on a real transition, or `libmtcmaster`
  gains an `MTCSender_isPlaying` export. That second option is a change in that repository.

---

## 3. Reinstating them after `0.1.1`

By then `script` version 2 has shipped, so the order matters.

### 3.1 Library (`cuems-utils`)

1. **Schema, with a version step.** Adding enumeration values is additive, so under
   `specs/agreements/schema-evolution-convention.md` no existing document is invalidated. But
   version 2 is released by then, so the addition is a `script` **2 → 3** step: an identity step,
   with no registry entry, because nothing needs transforming. It is **not** the free edit 017 made
   inside the unreleased step.

   ```xml
         <xs:enumeration value="stop_project" />
         <xs:enumeration value="pause_project" />   <!-- project-scope; no target -->
         <xs:enumeration value="resume_project" />  <!-- project-scope; no target -->
   ```

2. **The targetless set**, a one-line change in `src/cuemsutils/cues/ActionCue.py`:

   ```python
   TARGETLESS_ACTION_TYPES: frozenset[str] = frozenset(
       {'stop_project', 'pause_project', 'resume_project'}
   )
   ```

   That one line extends all of A-1 to them: the three T2 rules (`action_target_required` passes
   `None`, `action_target_resolves` skips, `project_action_takes_no_target` repairs a leftover
   target on load and refuses it on save), the construction guard, and `from_json`. **Nothing
   else in the library changes.**
3. **Contract counts.** `tests/contract/test_action_type.py` goes from eleven to thirteen by name.
   `RETAINED` in `tests/contract/test_enum_audit.py` gains both values, with the engine evidence
   that they are now implemented. `tests/contract/test_retired_action_types.py` is retired, and the
   retirement recorded. The `script.xsd` hash moves once, with the version step.
4. **Tests per value, modelled on 017's `tests/unit/test_targetless_actions.py`:**
   - construct with no target, `None` and `""`;
   - `from_json` with `null`;
   - `save` → `<action_target />` → `load_with_report` CLEAN;
   - a leftover target REPAIRED on load and refused on save;
   - the descriptor publishes the value, and `action_target` stays UNREPAIRABLE.

### 3.2 Engine (`cuems-engine`) and `libmtcmaster`

Follow `stop_project`'s shape (§2.2): the **node** applies the action and notifies, and the
**controller** validates (adopted sender, cue in the project, `running`, `run_seq`) and acts
**once**, first valid message wins. A sketch, in the controller:

```python
def _handle_pause_project(self, operation):
    if not self._valid_project_action(operation, "pause_project"):  # as _handle_stop_project
        return
    if self.get_status("running") != "yes" or self._paused:
        return                                    # idempotent: never toggle twice
    libmtcmaster.MTCSender_pause(self.mtcmaster)  # holds MTC, KEEPS the time (§2.3)
    self._paused = True
    self.set_status("pause", "yes")               # the existing EngineStatus slot (§2.2)
    # players: hold, not stop — the node side needs its own pause of running players

def _handle_resume_project(self, operation):
    if not self._valid_project_action(operation, "resume_project"):
        return
    if not self._paused:
        return                                    # MTCSender_play would PAUSE a running show
    libmtcmaster.MTCSender_play(self.mtcmaster)   # toggle back: resumes from the held time
    self._paused = False
    self.set_status("pause", None)
```

**Open design points**, which are the engine's to decide:
- **Players.** MTC is only the clock. Audio, video and DMX players must hold and resume in step,
  and `NodeEngine.commands_dict["pause"]` is `None` today.
- **Who may resume.** A `resume_project` *cue* can only fire while the show runs, and a paused
  show is held. So in practice resume is an operator command, and a `resume_project` **cue** may
  be pointless. Decide whether only `pause_project` is a cue, with resume an operator action.
- **Interaction with STOP.** STOP during a pause must reset the time (`stop()` does) and clear
  `_paused`.

### 3.3 Siblings

- **cuems-frontend**: authors the two values like `stop_project`, with no target chooser and
  `action_target = null`. Its `origin/dev` `6dc775c` already has `stop_project` authoring
  (`src/app/components/projects/project-edit/sequence/sequence.component.html:124-125`,
  `:590-605`), and the new values follow the same chips and option list. The list of action types
  comes from this library's descriptor (015 G3), so it appears there once §3.1 lands.
- **cuems-editor**: saves through `CuemsScript`, so it needs nothing beyond sending `null`. Its
  release line already nulls targets in places (`origin/debian/bookworm` `69d749e`,
  `src/cuemseditor/CuemsDBProject.py:927`), so it must not send a leftover uuid, which this
  library refuses on save.
- **cuems-power-bridge**: today a `stop_project` cue looks to it exactly like an operator STOP
  (`origin/main` `CLAUDE.md:60`): `running no` → re-arm → `armed yes`. A pause must not look like
  a STOP, or the bridge's auto-load would re-drive a paused show. Its rule *"never auto-stop a
  running project"* (`CLAUDE.md:20`, `HEAD` `666cb25`) needs a statement about a **paused**
  project: running, but held.

---

## 4. A future option: naming the scope explicitly (`stop` → `stop_cue`)

Raised in 017's Q2: should cue-scope and project-scope actions be told apart by name? Today
`stop` (cue) and `stop_project` (project) are already **distinct values**, and nothing can repair
one into the other: no T2 rule rewrites `action_type`. So this is about readability, not safety.

**What a rename costs:**
- **Documents.** Every v2 script with a `stop` cue. That is a `script` **2 → 3** step with a
  registered conversion (`stop` → `stop_cue`), unlike §3.1's identity step. If `play`, `pause`
  and the rest followed, every action cue in every document converts.
- **Engine.** The dispatch tables key on the value: `ActionHandler.py:34` and `:759`
  (`"stop": _handle_stop`), `NodeEngine.py:366` (`"stop": self.stop_playback`, the operator
  command, which may stay as it is), and the handlers' result strings (`ActionHandler.py:487-498`).
- **Frontend.** Its action option lists and the translation keys (`action.stop…`).
- **The coordinated release.** All three must move in one coordinated tag. Taking it together
  with §3 means one version step instead of two.

**Recommendation.** Do it only together with §3, or not at all. On its own it buys readability at
the price of a converted library and a lock-step release.
