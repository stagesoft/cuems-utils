# `tools/`'s external consumers — corrected findings, and the `TimeoutLoop` relocation

Corrects three "dead code" claims made in an informal coverage-gap analysis earlier in this
project's history (chat only, never committed) and lays out a work plan for what those corrections
actually call for. Written as the record for a future feature, per this repo's `specs/planning/`
convention (`nodeconf-atomization.md`, `dmx-universe-channel-conversion-defect.md`) — no code ships
with this document except where noted.

## The mistake, stated plainly

`cuems-utils` is, by this repo's own `CLAUDE.md`: *"Shared Python library (`cuemsutils` on PyPI)
used by the engine, editor, and other components."* A prior pass flagged
`tools/CopyMoveVersioned.py`, `tools/StringSanitizer.py`, and `timeoutloop.py`'s `Timeoutloop` class
as dead code, on the strength of `grep -rl <ClassName> src/` finding zero hits **inside this
repository**. That evidence only tells you a symbol is unused *by cuems-utils itself* — for a
package whose entire purpose is to be imported by sibling repos, it says nothing about whether the
symbol is dead. All three are live, in production, in `cuems-editor` and `cuems-nodeconf`, checked
by grepping those repos directly on disk (`/disk/Projects/StageLab/cuems-editor`,
`/disk/Projects/StageLab/cuems-nodeconf`).

**Standing rule this correction establishes**: a "delete as dead" claim about anything under
`src/cuemsutils/` is not evidence-complete until the sibling repos that vendor this package
(`cuems-editor`, `cuems-nodeconf`, `cuems-engine`, `cuems-common`, and whatever else imports
`cuemsutils` — see `cuems-RELATIONS` for the current list) have been checked too. `git grep` inside
`cuems-utils` alone is necessary, not sufficient, for this specific claim.

## Corrected findings

### `tools/CopyMoveVersioned.py` — **not dead. Live, in `cuems-editor`, unguarded by any test.**

```
cuems-editor/src/cuemseditor/CuemsDBMedia.py:13:   from cuemsutils.tools.CopyMoveVersioned import CopyMoveVersioned
cuems-editor/src/cuemseditor/CuemsDBProject.py:7:   from cuemsutils.tools.CopyMoveVersioned import CopyMoveVersioned
```

Used at 9 call sites across both files for the project/media lifecycle: moving an uploaded file
into place, moving files/directories to their trash sub-directory on delete, moving a project
directory on export. `CopyMoveVersioned.move`'s collision-avoidance behaviour (append `-NNN` before
the extension when the destination exists) is load-bearing — `CuemsDBMedia.py`'s own docstrings
describe callers relying on the returned, possibly-renamed filename. **No test in either repo
exercises `CopyMoveVersioned` directly** (`tests/` in `cuems-utils` has no `test_copymoveversioned*`
file); its correctness rests entirely on `cuems-editor`'s own integration coverage, if any.

### `tools/StringSanitizer.py` — **not dead. Live, in `cuems-editor`, on a security-adjacent path, unguarded by any test — and it has a real (if low-severity) bug.**

```
cuems-editor/src/cuemseditor/CuemsUpload.py:10,15,126     StringSanitizer.sanitize_file_name
cuems-editor/src/cuemseditor/CuemsDBProject.py:6,171,350,354,462,486   sanitize_name / sanitize_text_size / sanitize_dir_permit_increment
cuems-editor/src/cuemseditor/CuemsDBMedia.py:12,87,316     sanitize_name / sanitize_text_size
```

`CuemsDBProject` subclasses `StringSanitizer` directly and uses `sanitize_dir_permit_increment` to
turn a project name into a filesystem directory name (`unix_name`); `CuemsUpload` uses
`sanitize_file_name` on uploaded filenames before they touch disk. This is exactly the kind of
"user-controlled string becomes a path component" code that a security audit would want covered by
tests, and none exist in either repo.

**Bug found while re-reading it for this correction** (`src/cuemsutils/tools/StringSanitizer.py`):

```python
def sanitize_text_size(_string):
    if _string and (len(_string) > 65535):
        _string = _string[0:65534] # return frist 255 characters
    return _string

def sanitize_name(_string):
    if len(_string) > 255 :
        _string = _string[0:254] # return frist 255 characters
    return _string
```

Both comments claim "return first 255/65535 characters"; both slices are off by one
(`[0:254]` is 254 characters, `[0:65534]` is 65534). Cosmetically wrong rather than a security hole
— the string still ends up *shorter* than the stated limit, never longer, so no truncation-bypass
or overflow follows from it — but it is a real, live discrepancy between documented and actual
behaviour in code that decides what a project's directory name is, worth fixing deliberately rather
than leaving to be rediscovered the next time someone reads this file closely.

### `timeoutloop.py`'s `Timeoutloop` — **not dead. Live, in `cuems-nodeconf`, at three call sites — and this repo's own docs already call it `TimeoutLoop`.**

```
cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:26:   from cuemsutils.timeoutloop import Timeoutloop
cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:309,617,629:   for passed in Timeoutloop(timeout=..., interval=...):
```

Used as the polling/timeout mechanism for node-discovery waits during avahi listener startup and
first-run detection — directly in the daemon's node-adoption path this feature area (008/007) has
already been working in.

Separately, and found only by re-checking this repo's own docs while writing this correction:
`README.md:144` already documents the module as exposing a class called **`TimeoutLoop`** ("`
**`timeoutloop`** — `TimeoutLoop` utility that runs a callable with a configurable deadline; raises
on timeout."), and `docs/index.md:99` groups it by name alongside `StringSanitizer`/
`CopyMoveVersioned` under `tools/`. The documentation and the code have already disagreed about this
class's name and location; the user's requested move corrects the code to match what the docs
already promised, not the other way around.

## Work plan

Three independent tracks. None block each other; suggested order is by risk (lowest first).

### Track 1 — characterization tests for `CopyMoveVersioned` and `StringSanitizer` (in `cuems-utils`)

**Status: done.** Both are pure, dependency-light, and were previously proven correct only by the
absence of a bug report from `cuems-editor`. Since this repo is the one that owns the published
contract, the tests were added here, not only in the consumer:

1. `tests/unit/test_copy_move_versioned.py` (10 tests) — `move()`'s collision-avoidance sequence
   (`file.ext` → `file-001.ext` → `file-002.ext`, `tmp_path`-based, no real filesystem risk),
   `dest_filename=None` defaulting to `os.path.basename(orig_path)`, extension preservation across a
   collision (the `CuemsDBProject.export` call site), moving/versioning a **directory** rather than a
   file (the `CuemsDBProject.delete`/`restore` call sites — `shutil.move` and the collision loop make
   no file/dir distinction, and this was worth pinning explicitly rather than assumed), and
   `copy_dir()`'s equivalent sequence (`shutil.copytree`, no known consumer but public API).
2. `tests/unit/test_string_sanitizer.py` (17 tests) — one or more cases per method
   (`sanitize_text_size`/`sanitize_name`/`sanitize_file_name`/`sanitize_dir_name`/
   `sanitize_dir_permit_increment`), each modelled on the real call site that uses it (`CuemsUpload`,
   `CuemsDBProject.new`, `Project`/`Media`'s peewee `CharField`), covering under-limit strings passing
   through unchanged, boundary behaviour at the exact limit, character-stripping
   (space/hyphen → underscore, non-alnum dropped, lowercasing), and the different `keepcharacters`
   sets between `sanitize_file_name` (`.`, `_`) / `sanitize_dir_name` (`_` only) /
   `sanitize_dir_permit_increment` (`_`, `-`, and — its whole reason to exist as a separate method —
   the one that does *not* replace `-`, so `CopyMoveVersioned`'s `-NNN` suffix stays parseable).
3. **The off-by-one fix landed in the same change**, on explicit instruction: write tests asserting
   the *documented* 255/65535 caps first (both failed red against the pre-fix code — confirming the
   inaccuracy was real, not assumed), then fix `sanitize_name`/`sanitize_text_size`'s slices
   (`[0:254]` → `[0:255]`, `[0:65534]` → `[0:65535]`, plus `sanitize_text_size`'s comment which
   additionally said "255" where the code has always meant 65535 — a second, independent copy-paste
   error caught alongside the slice bug). Confirmed via peewee 3.17's source
   (`CharField.__init__(self, max_length=255, ...)`) that 255 is the *actual* enforced constraint on
   `Project.name`/`Media.name`, not an arbitrary number — and confirmed via grep that no consumer in
   `cuems-utils` or `cuems-editor` inspects the truncated length, so nothing could be relying on the
   old off-by-one value. Full suite re-run clean after the fix (2549 passed, up from 2522, zero
   regressions). `sanitize_file_name`/`sanitize_dir_name`/`sanitize_dir_permit_increment`'s 240-char
   cap (`236 + 4`) had no such bug and was left untouched.

### Track 2 — relocate `Timeoutloop` → `tools/TimeoutLoop.py`, with a compatibility shim

**Status: done.** Per the explicit instruction: moved the module into `tools/`, renamed the class
`Timeoutloop` → `TimeoutLoop`, added a full docstring, type hints, and usage examples. As
originally sketched below, with two differences worth recording:

- **Option (b) was chosen** for where `deprecated_alias` lives: `_deprecation.py` was promoted to
  `src/cuemsutils/_deprecation.py` (package root) in its own commit before this track started,
  updating all seven `xml/`-internal import sites plus the one test import. `timeoutloop.py`'s shim
  imports it from there.
- **One real edge-case correction, found by the new tests, not assumed going in**: the sketch's
  docstring claimed a `timeout <= 0` "times out on the very first iteration." Under a genuinely
  frozen clock (the test suite's fake-clock fixture) that's false — `0 > 0` is false, so it does
  *not* raise until *some* time has actually elapsed. This is not a class bug (a real
  `time.time()` always advances by a nonzero amount between two calls, so the practical behaviour
  is unchanged), but the docstring's wording was corrected to state the true invariant ("raises as
  soon as any time at all has elapsed... in practice immediately") rather than the imprecise one,
  and the test models it by advancing the fake clock explicitly rather than asserting a falsehood.

Landed as: `src/cuemsutils/tools/TimeoutLoop.py` (the class), `src/cuemsutils/timeoutloop.py`
(rewritten as the shim, `Timeoutloop = deprecated_alias(TimeoutLoop, "cuemsutils.tools.TimeoutLoop")`),
`tests/unit/test_timeout_loop.py` (8 tests, fake-clock-based, zero real waiting), and
`tests/unit/test_timeout_loop_deprecation_shim.py` (5 tests — deliberately kept separate from
`tests/contract/test_deprecation_shims.py`, which pins feature 006's own twelve-call-site retirement
contract and is not this shim's concern). `README.md`, `docs/index.md`, `docs/api.md`, and
`docs/tools.md` all updated. Full suite green after (2562 passed, up from 2549).

Original plan, for reference:

1. **New module** `src/cuemsutils/tools/TimeoutLoop.py`:
   ```python
   from __future__ import annotations
   from time import sleep, time
   from typing import Iterator

   class TimeoutLoop:
       """Iterate until ``timeout`` seconds have elapsed, then raise.

       On each ``next()``, optionally sleeps ``interval`` seconds, then yields
       the elapsed time since iteration started. Raises ``TimeoutError`` once
       elapsed time exceeds ``timeout``. Used for bounded polling loops —
       ``cuems-nodeconf`` uses it to wait for avahi node discovery and
       first-run detection.

       Args:
           timeout: seconds after which iteration raises ``TimeoutError``.
           interval: seconds to sleep before each yield. ``None`` (the
               default) never sleeps — the caller controls pacing.

       Example:
           >>> for elapsed in TimeoutLoop(timeout=10, interval=1):
           ...     if condition_met():
           ...         break
           ...     # else: loop again, up to ~10s total, sleeping 1s each pass
       """
       def __init__(self, timeout: float, interval: float | None = None) -> None:
           self.timeout = timeout
           self.delay = interval

       def __iter__(self) -> Iterator[float]:
           self.start_time = time()
           return self

       def __next__(self) -> float:
           if self.delay is not None:
               sleep(self.delay)
           time_passed = time() - self.start_time
           if time_passed > self.timeout:
               raise TimeoutError(f"Timeout after {self.timeout} seconds")
           return time_passed
   ```
   (Sketch — final version should also cover the zero/negative-`timeout` edge case, which the
   current implementation does not guard, in the docstring or in behaviour, whichever the test
   pass decides.)

2. **Compatibility shim at the old path**, `src/cuemsutils/timeoutloop.py`, because
   `cuems-nodeconf` imports `from cuemsutils.timeoutloop import Timeoutloop` today and this repo
   does not get to edit that repository as part of this work. This repo already has a mechanism for
   exactly this — `xml/_deprecation.py`'s `deprecated_alias(target, replacement)` — used for the
   feature-006 API retirement (`REMOVAL_RELEASE = "v0.1.1"`, warns on every call via `deprecated`,
   keeps `isinstance` compatibility via subclassing rather than a bare re-export, which matters here
   because `Timeoutloop` is used as `for x in Timeoutloop(...)`, not just constructed once). Two
   options, worth deciding rather than defaulting silently:
   - **(a)** import `deprecated_alias` from `cuemsutils.xml._deprecation` into the new shim. Simplest,
     but reaches into a nominally XML-scoped private module from package-root code — a naming
     mismatch, not a real coupling problem (the function is generic).
   - **(b)** promote `_deprecation.py` out of `xml/` to `cuemsutils/_deprecation.py` (package-private,
     no `xml` in the name), update `xml/settings.py`'s existing import alongside the new one. Slightly
     more churn, but the module's current location is arguably already a misnomer given it is a
     generic deprecation-shim builder, not an XML-specific one.

   Either way: `src/cuemsutils/timeoutloop.py` becomes a few lines —
   `Timeoutloop = deprecated_alias(TimeoutLoop, "cuemsutils.tools.TimeoutLoop")` — rather than a
   duplicated implementation.

3. **Tests**: `tests/unit/test_timeout_loop.py` for the new class (timeout-raises,
   interval-sleeps — use `monkeypatch` on `time`/`sleep` rather than a real 10-second test,
   zero-elapsed first iteration), and a small deprecation-shim test (`import cuemsutils.timeoutloop`
   still resolves, constructing/iterating `Timeoutloop` emits exactly one `DeprecationWarning` per
   call per FR-027b's "warn on every call" convention, and `isinstance(Timeoutloop(...), TimeoutLoop)`
   holds).

4. **Docs**: move the `timeoutloop` bullet in `README.md` from "Root modules" (line 144) into
   "Tools: `tools/`" (the section already containing `StringSanitizer`/`CopyMoveVersioned`,
   `README.md:87-116`), renamed to `TimeoutLoop`; update `docs/api.md`'s `:::: cuemsutils.timeoutloop`
   mkdocstrings directive to point at the new module; update `docs/index.md:99,183` accordingly.

5. **Cross-repo migration note** (not executed here — `cuems-nodeconf` is a different repository this
   work does not edit): once the shim ships, `cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:26` should
   change its import to `from cuemsutils.tools.TimeoutLoop import TimeoutLoop` (and its three call
   sites' bare name), removing the deprecation warning from that daemon's logs. Recorded here so
   whoever picks up the `cuems-nodeconf` side has the exact line numbers rather than needing to
   rediscover them.

### Track 3 — nothing to delete

Stated for completeness, since the original claim was "delete as dead code": no removal is proposed
for any of the three modules. The corrected action for all three is "add missing tests, in the repo
that owns the contract" (Track 1) and, for `Timeoutloop` specifically, "relocate and rename, with a
compatible shim" (Track 2) rather than delete.

## Suggested sequencing

Track 1 (tests only, zero API surface change, zero cross-repo risk) can land first and
independently. Track 2 touches a name a sibling repo imports today, so it needs the shim
(step 2) in the same change as the rename (step 1) — shipping the rename without the shim would
break `cuems-nodeconf` on its next `cuemsutils` upgrade with no warning period, which is exactly
what `_deprecation.py`'s whole design exists to avoid.
