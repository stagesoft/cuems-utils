<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Absorb `AsyncCommsThread` into `cuems-utils` (ships in the coordinated `0.1.1`)

**Written 2026-10-22.** **Status: library half (U1–U5) committed (`1c1334c`, plus `b592a57`: once
`end_reason` is set, `stop()` only joins, which N2's SIGTERM-driven shutdown needs). nodeconf half
(N1–N5) implemented on its `feat/xml-refactor` at `6e9be84`: suite 203 → 211 passed, stable over 3
runs, no failure in either arm. Engine half (E1–E6) implemented 2026-10-22 on its `feat/xml-refactor`
after its 009 landed (`796f61e`), so the rule-4 reconciliation was not touched: suite 1495 → 1518
passed, 1 xfailed, no failure in either arm. Once the engine and nodeconf halves are committed,
only §8.4 remains: re-cut and re-validate the three candidate tags (maintainer).**

Engine corrections to §6.2, measured while doing it:
- **E1 deviates on purpose.** `comms/AsyncCommsThread.py` is not deleted. It becomes the engine's thin
  subclass carrying the fatal path both engine threads share (`on_comms_ended` → module-level
  `terminate_process()`, a SIGTERM to self). That keeps the import path, the conftest's
  `isinstance` check and one place to patch.
- **E2 as recommended**: the bus hub is essential on both engines and `editor_listener` is essential
  on the controller. The receiver and the WebSocket listener are not. Over the whole suite, only the
  five tests written to end the comms log `communications ended`, so no existing test trips the
  supervision.
- **E3 needed a library change.** `engine.start()` never returns: `SignalEngine.start()` blocks in
  `run()`. So on SIGTERM it is `SignalEngine.handle_terminate` that runs, never the entry scripts'
  handlers. It calls `engine.stop()` (so `stop_comms()` *is* reached) and then `sys.exit()`, which
  exits **0** whatever happened. The first engine draft changed the scripts, and its tests mocked the
  engine, so they passed while the production path still exited 0. Fixed by
  **`SignalEngine.exit_status()`**: both handlers now `sys.exit(self.exit_status())`, 0 unless
  overridden, and `cuems-engine` is the only subclass. `BaseEngine.exit_status()` overrides it: 1
  when `end_reason` is set (`NodeEngine` reads the cue handler's thread). The scripts are unchanged.
  The engine's test drives `handle_terminate` on both engines and fails against a library without
  the hook. `stop_comms()` passes `timeout=COMMS_STOP_TIMEOUT` (5 s).
- **Tests**: an autouse `terminated` fixture replaces `terminate_process` with a recorder, so a test
  that starts real comms threads can never SIGTERM pytest.
- **E5 was already done**: 009 removed `src/cuems/`.
- **E6's arms**: A0 (library before today, `ff84193`) and A (library HEAD), engine unchanged, both
  1495 passed, 1 xfailed. B (migrated) 1518 passed, 1 xfailed. Measured with a scratchpad build of
  `libmtcmaster` against this box's `librtmidi.so.7`, since the released deb needs `.so.6`. That is
  a real library rather than the 009 stub. ⚠ The suite needs `LD_LIBRARY_PATH` pointing at it.
- Noticed, not changed: the entry scripts install their own SIGTERM handler *after*
  `engine.start()`, which only returns once the engine has stopped running. Those handlers are
  therefore effectively dead code.

nodeconf corrections to §6.3:
- It now lives in `src/cuemsnodeconf/` with tests by kind.
- The thread's name changes to `AsyncComms-Communications`.
- Its fatal path's non-zero exit is `run_nodeconf._exit_status`.
- Found while doing this and **fixed as C8** (`specs/planning/ipc-bus-signal-reliability-defects.md`):
  `responder_get_request` swallowed socket errors, so a closed responder made the listener spin
  without yielding instead of ending, and supervision could not see it. It now raises.
- The engine half waits until the engine's own 009 (release-line reconciliation) lands, so that
  reconciliation is not affected.

Measured at the library half:
- Full suite 4209 passed, 114 skipped, 2 xfailed, 0 failures.
- 47 new tests, stable over 3 runs. Module coverage 99% (only the `call_soon_threadsafe`
  closed-loop race guard is untested).
- ruff 0. mypy 294 → 297: all three new errors are the `pytest`/`pynng` import-stub errors every
  test file carries in the `types` env, and the module itself has 0.
- U3's ×200 stop-during-receive loop: slowest stop under 1 s.
- U3's child-process test has a control arm, measured with a short IPC path. Without `stop()`, 11 of
  20 runs aborted with exit 134. With it, 20 of 20 exited 0. ⚠ A scratchpad-length IPC path silently
  exceeds `sun_path`'s 108 bytes, and the control child then spins forever instead of failing.

This document is the whole work order. It
does not assume you have read anything else. Where it cites another document, that document is
background only.

**Delete this file** once all three of these are true: the library module has landed on
`feat/xml-refactor`, both consumers have migrated on their `feat/xml-refactor`, and the candidate tags
have been re-cut (§8). Record the landing in `CLAUDE.md` "Recent Changes" when you delete it.

---

## 1. What this is, in one paragraph

Two sibling repositories each have their own class called `AsyncCommsThread`. Both do the same job:
they run an asyncio event loop in a daemon thread, so that synchronous code can drive pynng
(NNG) sockets. `cuems-engine` has a 304-line base class that is mature and documented.
`cuems-nodeconf` has its own 111-line copy that has drifted from it. The pynng lifecycle rules this
class depends on already live in this library (`tools/HubServices.py`, `tools/CommunicatorServices.py`,
`_shielded`), so the class belongs here too. The plan has three parts:

- Move the engine's class into `cuemsutils.tools.AsyncCommsThread`, and fix it on the way in: it should
  stop when an essential task ends, and its shutdown should be safe.
- Make both consumers subclass the library's class.
- Ship all of it inside the unpublished `0.1.1`.

## 2. Process decision: no SDD feature directory

This work does **not** get a `specs/NNN-feature/` directory. It follows the same pattern as the
2026-10-22 "Test counterparts for `SignalEngine`, `CommunicatorServices` and `HubServices`" work in
`CLAUDE.md`: commits go straight onto `feat/xml-refactor`, this document is the plan, and the landing
is recorded in "Recent Changes". The reasons:

- It adds one module and one public class, and needs no schema, XSD, version-marker or
  wire-format change.
- It has exactly two consumers. Both have been measured (§3), and their migrations are mechanical.
- The only change consumers can observe is the stop-when-an-essential-task-ends behaviour (D3). That
  behaviour is already specified and requested in
  `specs/planning/upstream-cuems-engine-hub-start-supervision.md` (deleted 2026-10-22 once the engine
  half landed; in git history).

**Escalate to a full SDD feature** if any of the following happens during the work:

- A third consumer appears. Re-run the §3 search before you start.
- The engine team rejects D3, which means the class has to keep two supervision behaviours.
- A consumer needs its `cuems-utils` dependency bound changed (§8.2 explains why it should not).
- The migration changes a measured behaviour in a consumer's suite beyond the items listed in §6.

## 3. Inventory (measured 2026-10-22)

The search covered every sibling under `/disk/Projects/StageLab/`. It looked for classes whose name
matches `Async*Comm*Thread*` / `CommsThread`, for `Thread` subclasses that call `new_event_loop()` /
`run_forever()`, and for imports of `CommunicatorServices` / `HubServices`.

### 3.1 The two instances

| | `cuems-engine` | `cuems-nodeconf` |
|---|---|---|
| File (working branch) | `src/cuemsengine/comms/AsyncCommsThread.py`, 304 lines | `cuemsnodeconf/communicate.py:26`, inside a 111-line module |
| Shape | Abstract base class: subclasses implement `create_all_tasks()` | One concrete class with a single hard-wired task, `engine_listener()` |
| Subclasses or users | `ControllerCommunications`, `NodeCommunications` | `CuemsNodeConf.py:365` (`self.communications_thread`) |
| `stop()` | Blocking. Cancels the tasks inside the loop, waits for them, stops the loop, then joins the thread (`a4e5e61`, ClickUp 869ed00ya) | Not blocking. Posts `stop_async()` and returns without joining |
| Cancel wait | `gather` of every pending task, bounded by `timeout` | Only `_engine_task`, with a 2 s cap |
| Loop close | Never closed | Closed after `run_forever()` |
| Supervision | `gather(*tasks, return_exceptions=True)`: waits for **all** tasks | `await self._engine_task` |
| `timeout` | Seconds (15). Used by `run_coroutine` and subclasses | `TIMEOUT * 1000` (milliseconds), **never read** |
| `send_contexts` | Defined, **never read** | Defined, **never read** |
| Thread → loop entry point | `run_coroutine(coro_fn, message, timeout)` | None. Callers use `asyncio.run_coroutine_threadsafe(..., thread.event_loop)` directly (five sites, `CuemsNodeConf.py:392–443`) |
| Tests | `tests/conftest.py:184` `_stop_comms_threads`, plus a fixture fallback at about line 300 | `tests/test_communicate.py`, `tests/test_node_set.py:199` |
| Test patches | Several tests patch `asyncio.run_coroutine_threadsafe` | `test_engine_callback.py`, `test_adoption_flow.py`, `test_startup_readiness.py`, `test_node_set.py` patch `asyncio.run_coroutine_threadsafe` |

Both files carry `SPDX-License-Identifier: GPL-3.0-or-later`, and the engine's file is by the same
contributor as this library, so moving the code raises no licensing question.

### 3.2 State on the other branches (relevant to rule 4, §8.3)

- **`cuems-engine`:** `origin/debian/bookworm` has the file **identical** to `feat/xml-refactor`, so the
  release line has not diverged. `origin/main` has an **older** copy, without the stop-and-join fix
  (22+/63−). On `origin/dev` the file is absent.
- **`cuems-nodeconf`:** `origin/main`, `origin/debian/bookworm` and `origin/dev` keep the class at the
  **old root path** `communicate.py:25`, from before the package layout. It is the pre-fix copy.
- The local `cuems-engine` checkout is currently on `009-release-line-reconciliation`, three commits
  (docs) ahead of `feat/xml-refactor`. The engine's rule-4 merge is in progress there (§8.3).

### 3.3 Similar code that is *not* absorbed, and why

| Item | Decision |
|---|---|
| `cuems-engine` `comms/NodesHub.py` (`NngBusHub` subclass, `NodeOperation`/`OperationType`/`ActionType`) | **Stays in the engine.** The operation vocabulary is the engine's protocol, not a transport concern. Revisit only if a second repository needs to speak it. `cuems-power-bridge`'s `cluster_bus.py` reads the bus directly; see the last row. |
| `cuems-engine` `src/cuems/ComunicatorServices.py` (177 lines: old `Nng_request_response` over `Req0`/`Rep0`) | **Dead code.** Nothing under `src/` or `tests/` imports it. Deleting it is engine task E5. Absorbing it would revive the bugs C1–C7 fixed. |
| `cuems-engine` `ControllerCommunications`/`NodeCommunications` | **Stay in the engine.** They become subclasses of the library class (§6.2). |
| nodeconf's `engine_listener` and its `os.chmod(NODECONF_IPC, 0o666)` loop | **Stays in nodeconf**, as its subclass's task. The socket-mode fix is a deployment fact about nodeconf running as root. |
| `cuems-editor` `CuemsWsServer` | **Not the pattern.** Its loop runs on the main thread (`run_until_complete`) with a `ThreadPoolExecutor`. `stop()` posts into the loop from a signal handler, and there is no comms thread. Nothing to migrate. |
| `cuems-power-bridge` (`scripts/power_bridge.py`, `cluster_bus.py`) | **Not the pattern.** It uses plain `asyncio.run()` and raw pynng Bus0 on the main loop. Nothing to migrate. Consolidating its bus client onto `NngBusHub` would be a separate question. |
| `cuems-hardware-manager`, `cuems-dmxplayer` | No match. |

## 4. Why absorb it

1. **The two copies have already drifted, and the drift is a real defect.** nodeconf's `stop()` does
   not join the thread. That leaves the race the engine fixed in `a4e5e61` open: CPython runs pynng's
   `atexit` `nng_fini()` before daemon threads finish, and the next NNG call aborts the process with
   `panic: pthread_mutex_lock: Invalid argument`. nodeconf patched one symptom (it closes the loop) but
   not the race itself.
2. **The rules this class depends on are this library's rules.** `_shielded` (C6), the
   close-the-socket-to-end-a-receive rule, the 100 s `send_request` deadline (C5), and
   `NngBusHub.start()` returning on socket close (H1) all live in `cuems-utils` 0.1.1. The thread that
   drives those sockets should live next to them and be tested against them.
3. **H1 is invisible without supervision.** `NngBusHub.start()` now returns when its socket closes.
   The engine's `gather(..., return_exceptions=True)` swallows that, and the comms thread carries on
   with no bus. Fixing this once in the shared base fixes both consumers. The engine has already been
   asked for exactly that change (`upstream-cuems-engine-hub-start-supervision.md`).
4. **Test teardown is repeated discipline.** Every consumer suite needs "stop every live comms
   thread before NNG is finalized". The library can ship that once, as `stop_all()` (D6).

## 5. Library design

### 5.1 Location and name

- Module: **`src/cuemsutils/tools/AsyncCommsThread.py`**. The `tools/` modules use CamelCase file
  names (`HubServices.py`, `SignalEngine.py`, `CommunicatorServices.py`), and keeping the class name
  lets consumers migrate by changing only the import line.
- Class: **`AsyncCommsThread`**, imported as `from cuemsutils.tools.AsyncCommsThread import AsyncCommsThread`.
- Header: SPDX block as in the engine's file. Logging uses `cuemsutils.log.Logger`, as in every
  `tools/` module.

### 5.2 Public surface

The surface is the engine's, kept compatible so its subclasses need no change, plus three additions
(★):

```python
TIMEOUT = 15  # seconds

class AsyncCommsThread(Thread):
    thread_name: str
    name: str                      # "AsyncComms-<thread_name>"
    timeout: float                 # seconds
    stop_requested: bool
    event_loop: asyncio.AbstractEventLoop | None
    ended: threading.Event         # ★ set when the loop has stopped, for any reason
    end_reason: BaseException | str | None   # ★ None after a requested stop

    def __init__(self, *, thread_name: str | None = None, timeout: float = TIMEOUT) -> None
    def run(self) -> None
    def stop(self, timeout: float | None = None) -> None       # blocking; from any other thread
    async def stop_async(self) -> None                         # kept for compatibility (D7)
    def create_all_tasks(self) -> list[asyncio.Task]           # abstract
    def essential(self, task: asyncio.Task) -> asyncio.Task    # ★ mark a task essential (D3)
    def on_comms_ended(self, task: asyncio.Task | None) -> None  # ★ hook, runs on the comms thread
    def run_coroutine(self, coroutine, message, timeout=None)  # unchanged signature and semantics

    @classmethod
    def stop_all(cls, timeout: float = 5) -> None              # ★ D6: stop every live instance
```

Removed relative to the engine's class: `send_contexts`, which neither consumer reads (§3.1). Grep the
consumers again before deleting it.

### 5.3 Behaviour

**`run()`** creates a new loop, schedules `run_asyncio_comms()`, and calls `run_forever()`. Two things
are new, both taken from the better half of each copy:
- In a `finally`: cancel and wait for any tasks still pending, run
  `loop.shutdown_asyncgens()`, **close the loop**, set `ended`. Closing is nodeconf's fix, so that pynng
  aios are finalized on this thread and not at interpreter exit.
- `run()` must never raise. Log any exception, record it in `end_reason`, and still set `ended`.

**`stop(timeout)`** keeps the engine's semantics exactly:
1. Set `stop_requested`.
2. If the loop is running, `run_coroutine_threadsafe(self._cancel_tasks(), loop).result(timeout)`.
3. Then `loop.call_soon_threadsafe(loop.stop)`.
4. Return at once if the thread never started (`ident is None`).
5. `join(timeout)`. If the thread is still alive, log an ERROR naming the NNG-teardown risk.

On top of that, it is:
- **Idempotent**: a second call returns without error.
- **Safe after the loop has ended by itself** (`ended` already set): it only joins.
- **Refused from the comms thread itself**: raise `RuntimeError`, because joining yourself deadlocks.
  The engine documents this restriction but does not enforce it.

**`run_asyncio_comms()`**, the supervision (D3):
```text
tasks = create_all_tasks()
until stop_requested or no task is left:
    done = await asyncio.wait(remaining, return_when=FIRST_COMPLETED)
    for each finished task:
        if it was cancelled during stop()  -> ignore it
        if it raised                       -> ERROR "<name> task <qualname> failed: <Type>: <msg>"; fatal
        if it returned and is essential    -> ERROR "<name> essential task <qualname> ended"; fatal
        if it returned and is not essential -> INFO "<name> task <qualname> finished"; keep going
on fatal: end_reason = exception or message; cancel the rest and wait (the _cancel_tasks path);
          call on_comms_ended(task) (log and swallow anything it raises); stop the loop
```
The default `on_comms_ended` only logs. **The library never exits the process.** Raising `SystemExit`
in a non-main thread ends only that thread, and the library cannot know what a consumer's fatal path
is. Each consumer overrides the hook (§6), or watches `ended`.

**`_cancel_tasks()`** is the engine's version, unchanged: it cancels everything except the current
task and runs `gather(..., return_exceptions=True)`. Since 0.1.1, every pynng await in
`CommunicatorServices`/`HubServices` goes through `_shielded`, and each caller closes its socket or
context when it exits. So cancelling a task that is waiting in a receive is now bounded. **Verify that
claim with a test (U3), do not assume it.** H5 was measured as not reproducing, and C6's lost callback
is 1-in-1000.

**`run_coroutine()`** keeps its exact behaviour: `AttributeError` if the loop does not exist yet,
`TypeError` if the argument is not a coroutine function, a default timeout, `-1` for no timeout, and
it cancels and re-raises on timeout or error. One addition: if `ended` is set, raise `RuntimeError`
with the `end_reason`, instead of submitting to a closed loop (which raises a confusing
`RuntimeError: Event loop is closed`).

### 5.4 Decisions

| # | Decision | Recommendation | Status |
|---|---|---|---|
| D1 | Module path and class name | `cuemsutils.tools.AsyncCommsThread.AsyncCommsThread` (§5.1) | recommended |
| D2 | Compatibility | The engine's surface is kept as-is (§5.2). nodeconf's `respond_to_engine`/`event_loop` users keep working because `event_loop` keeps its name | recommended |
| D3 | Supervision | A task that raises is fatal. A task that returns is fatal only if it is marked `essential()`. A non-essential task that returns is INFO. **This is why it cannot simply be "first completed is fatal"**: measured, the engine has legitimate early returns. `NodesHub.start_message_receiver` returns when no callbacks are set (`NodesHub.py:153–155`), and `websocket_osc_listener` returns when a server already holds the port (`WebSocketOscHandler.py:270`). `NngBusHub.start()` **returns** on socket close (H1), so it must be marked essential to be noticed | recommended; needs engine sign-off |
| D4 | Fatal path | The library logs, stops the loop, sets `ended`/`end_reason` and calls `on_comms_ended`. Consumers override the hook to do `os.kill(os.getpid(), signal.SIGTERM)`, so their existing signal handling runs a clean shutdown: the engine's `SignalEngine`, and nodeconf's `run_nodeconf.py:32` handler. ⚠ **The shutdown must then exit non-zero.** Measured: `cuems-{controller,node}-engine.service` and `cuems-nodeconf.service` (shipped by cuems-common) are `Restart=on-failure`, so a clean SIGTERM shutdown that exits 0 is **not** restarted, and the service would just stay down. Each consumer's main path exits with status 1 when `communications_thread.end_reason is not None` | recommended |
| D5 | Thread-local loop | Do **not** call `asyncio.set_event_loop()` in `run()`. Neither copy does, and code on the loop uses `get_running_loop()`. Changing it would change what `asyncio.get_event_loop()` returns on that thread | keep as is |
| D6 | Test teardown helper | `AsyncCommsThread.stop_all()` iterates `threading.enumerate()` for live instances and stops each one. The engine's `_stop_comms_threads` becomes one call. `_free_orphan_nng_aios` (engine conftest) is **not** absorbed: it reaches into pynng internals and is a test-suite workaround | recommended |
| D7 | `stop_async()` | Keep it, with the engine's docstring warning that awaiting it alone cannot observe the stop. Neither consumer should call it after migrating | keep, discouraged |
| D8 | Public API golden | `tests/golden/api/public_api.json` lists only `ConfigBase`, `ConfigManager`, `CuemsScript` (+ errors/functions/scripts) and no `tools` transport module, so this addition does **not** re-hash it. If the team wants transport classes in the golden, that is a separate decision covering `HubServices` too | no golden change |
| D9 | nodeconf's millisecond `timeout` | Drop it. The subclass inherits seconds. The value is never read (§3.1) | recommended |

## 6. Work plan

The order is fixed: the library lands first (U), then the engine (E) and nodeconf (N). E and N are
independent of each other. Every commit is GPG-signed. If signing fails, retry; never use
`--no-gpg-sign`. Nothing is pushed and no tag is moved by an agent (§8).

### 6.1 `cuems-utils` (this repository, `feat/xml-refactor`)

- **U1: module.** Write `src/cuemsutils/tools/AsyncCommsThread.py` per §5. Start from the engine's
  file at `feat/xml-refactor` (`a4e5e61` is its last functional change) so the docstrings and the
  ClickUp 869ed00ya rationale come with it.
- **U2: unit tests**, `tests/unit/test_asynccommsthread.py`. Follow the `test_hubservices.py` layout:
  fakes, one class per production method in source order. Cover:
  - start and stop;
  - `stop()` before `start()`;
  - `stop()` twice;
  - `stop()` from the comms thread raises;
  - `stop()` after the loop ended by itself;
  - `run_coroutine` (result; timeout cancels; exception re-raised; not a coroutine function → `TypeError`;
    loop missing → `AttributeError`; after `ended` → `RuntimeError`; `-1` means no timeout);
  - supervision (raise is fatal; essential return is fatal; non-essential return is INFO and the rest
    keep running; cancelled tasks during stop are not reported);
  - `on_comms_ended` is called once, and an exception inside it is swallowed;
  - the loop is closed after `run()`;
  - `stop_all()`.

  Assert log text through `tests/support/cuems_logs.capture`, never `caplog`: each module's logger
  reads `CUEMS_LOG_LEVEL` once and caches it.
- **U3: integration tests**, `tests/integration/test_asynccommsthread.py`. Use real pynng:
  - A subclass running a `Communicator` responder (nodeconf's shape) over `ipc://` in `tmp_path`.
    Answer requests through `run_coroutine` from the main thread. `stop()` while the responder waits
    in a receive must return within `timeout`, and the thread must be joined. Run it ×200 in a loop
    and record the result; this is the C6 cancellation question applied to this class.
  - A subclass running `NngBusHub` LISTENER + DIALER as an essential task. Close the bus socket and
    check that `ended` is set, `end_reason` names the hub, and `on_comms_ended` ran.
  - A child-process test: start a comms thread with a live NNG receive, call `stop()`, exit normally.
    The child's exit code must be 0, not 134. This is the ClickUp 869ed00ya regression. Reuse the
    child-process pattern from `tests/integration/test_signalengine.py`.
  - Use `SETTLE` before the first BUS message (H6) and allow up to `reconnect_time_max` for a dialer
    that starts before its listener.
- **U4: changelog and docs.**
  - `CHANGELOG.md` `0.1.1`: "Added `cuemsutils.tools.AsyncCommsThread`, absorbed from cuems-engine;
    stops when an essential task ends; blocking, idempotent `stop()`".
  - **No** `debian/changelog` version change. It stays inside the existing `0.1.1` entry (§8.2). Add a
    bullet to that entry.
  - `CLAUDE.md` "Submodules → tools/": add `AsyncCommsThread`.
- **U5: gates.** Run `uvx hatch run test.py3.11:run -- -q`. The full suite must stay at 0 failures,
  and its ms/test must stay inside the 115% band (CLAUDE.md, feature 015). `ruff` must report 0 and
  `mypy` must not rise above the current count. Coverage for the new module should be ≥ 95%, the same
  bar as its neighbours.

### 6.2 `cuems-engine` (`feat/xml-refactor`, coordinated with its rule-4 branch, §8.3)

- **E1: base class.** Change `comms/ControllerCommunications.py` and `comms/NodeCommunications.py` to
  `from cuemsutils.tools.AsyncCommsThread import AsyncCommsThread`. Delete
  `src/cuemsengine/comms/AsyncCommsThread.py`. Update the two docstring references
  (`osc/WebSocketOscHandler.py:13`, `tools/CuemsDeploy.py:17`) and the comment at
  `ControllerEngine.py:533`.
- **E2: mark essential tasks** in `create_all_tasks()`:
  - Controller: `nng_hub.start()` and `editor_listener()` are essential. `start_message_receiver()`
    and `_websocket_osc_task()` are not, because of their legitimate early returns (D3).
  - Node: `nng_hub.start()` is essential, `start_message_receiver()` is not.
  - Confirm each choice with the engine team. This discharges
    `upstream-cuems-engine-hub-start-supervision.md`; delete that note in the same commit that lands
    this.
- **E3: fatal path.** Override `on_comms_ended` in both subclasses to send `SIGTERM` to the process
  (D4). Check that `BaseEngine` (a `SignalEngine`) shuts down cleanly from it, including
  `stop_comms()` → `stop()`, which now finds `ended` set and only joins. Make the exit status 1 when
  `end_reason` is set, so `Restart=on-failure` applies. Check `SignalEngine`'s exit handlers, which use
  `sys.exit` since S1.
- **E4: tests.**
  - `tests/conftest.py` `_stop_comms_threads` becomes `AsyncCommsThread.stop_all(timeout=5)`, imported
    from `cuemsutils`.
  - The fixture fallback at about line 300 stays. Its `stop_requested`/`event_loop` attributes keep
    their names.
  - Add one engine test: a hub socket closed under a running `ControllerCommunications` leads to
    `on_comms_ended`, with `os.kill` patched.
- **E5: dead code.** Delete `src/cuems/ComunicatorServices.py` after one more grep confirms no
  importer. Drop `src/cuems/` too if nothing else is left in it.
- **E6: suite, two-armed.** Run the engine's suite against the library before U1 (arm A) and after it
  (arm B), interleaved ×3, as feature 016 did. The only expected differences are E4's new test, plus
  any test that observed the old swallow-and-continue behaviour. List those by name in the commit
  message. ⚠ Feature 015 recorded 28 failures in both arms against a **mock `pyossia`**. Compare the
  sets of failures, not their counts.

### 6.3 `cuems-nodeconf` (`feat/xml-refactor`)

- **N1: subclass.** In `cuemsnodeconf/communicate.py`, replace the class with
  `class AsyncCommsThread(cuemsutils.tools.AsyncCommsThread.AsyncCommsThread)`. Keep the local name,
  so `CuemsNodeConf.py:28` and the tests keep importing it from `communicate`. Then:
  - `__init__(self, command_callback)` calls `super().__init__(thread_name="Communications")`, keeps
    `command_callback` and `self.nodeconf = get_nodeconf_comm()`, and drops `timeout`, `send_contexts`
    and `_engine_task`.
  - `create_all_tasks()` returns `[self.essential(asyncio.create_task(self.engine_listener()))]`.
  - `engine_listener()` stays as it is, `chmod` loop included. `respond_to_engine()` stays.
  - `run()`, `stop()`, `stop_async()` and `run_asyncio_comms()` are **deleted**, because the library
    versions replace them.
  - The exported `TIMEOUT = 15` stays. `CuemsNodeConf.py:28` imports it.
- **N2: fatal path.** Override `on_comms_ended` to send `SIGTERM` (D4). Then make `run_nodeconf.main()`
  return or exit 1 when `communications_thread.end_reason` is set. Today a SIGTERM-driven stop exits
  0, so `Restart=on-failure` would leave nodeconf down. The engine treats a missing
  `/tmp/nodeconf.ipc` as "nodeconf unavailable", so a nodeconf that keeps running with a dead
  responder is worse than one that restarts.
- **N3: shutdown path.** `CuemsNodeConf.py:155` `self.communications_thread.stop()` now **blocks** and
  joins the thread. Pass `stop(timeout=5)`, because the default of 15 s exceeds the unit's
  `TimeoutStopSec=10` (§9). Check that it is not called from the comms thread itself; `stop()`
  would raise there (§5.3). Of the call sites at 392–443, the ones that run inside `engine_callback`
  run on the comms loop, and none of them call `stop()`. Verify that rather than trust it.
- **N4: tests.** `tests/test_communicate.py` asserted the old attributes (`timeout` in ms,
  `send_contexts`). Rewrite it to assert the subclass contract (thread name, a single essential task,
  `TIMEOUT` exported) and to delegate lifecycle behaviour to the library's tests. `test_node_set.py:199`
  ("a Req0 client, the real AsyncCommsThread, a temp socket") must pass unedited. That test is the
  integration proof.
- **N5: suite, two-armed** as in E6. nodeconf's own suite needs `zeroconf`, which is not on the dev
  box (CLAUDE.md, 015). Install it into nodeconf's per-repository `.venv`, or record which modules
  were skipped.

## 7. Acceptance criteria

1. `grep -rn "class AsyncCommsThread" ../cuems-*/` finds exactly one base definition, in
   `cuems-utils`. nodeconf's subclass is the only other `class AsyncCommsThread` line.
2. In a child process: a comms thread with a live NNG receive that is `stop()`ped exits 0. This holds
   for the library test (U3) and for each consumer's entry point. Check each consumer by starting and
   stopping its service in the bookworm chroot or on a node.
3. A closed bus socket under a running engine comms thread produces the `on_comms_ended` ERROR line
   and a SIGTERM (E4). Before this change it produced nothing.
4. The library suite has 0 failures and its ms/test is inside the 115% band. The engine and nodeconf
   two-armed runs show no unexplained new failure.
5. `specs/016-coordinated-minor-bump/tools/verdicts.sh` still passes in full (§8.2: no relation moves).
6. `upstream-cuems-engine-hub-start-supervision.md` is deleted, because E2/E3 discharge it.

## 8. Release integration

### 8.1 It ships in `0.1.1`

`0.1.1` is **unpublished**. As of 2026-10-22, PyPI's 0.1.0 line ends at rc16, and rc17 is Debian-only.
Its candidate tags were re-cut on 2026-10-16. The coordinated bump document
(`specs/planning/coordinated-release-version-bump.md`) still owes rule 4, §11.1 validation, the engine
relock and publication. So this work joins the set that has not shipped yet; it is not a new release.

### 8.2 No dependency bound moves

Both consumers already declare `cuems-utils (>= 0.1.1), cuems-utils (<< 0.1.2~)`
(`cuems-engine/debian/control:30–31`, `cuems-nodeconf/debian/control:18–19`). No `0.1.1` without the
module will ever exist, so `>= 0.1.1` is already the correct floor, and none of the 126 relation sites
changes. **If `0.1.1` were published before this work lands, that premise breaks.** The consumers
would then need `>= 0.1.2~` or a new patch release, and this plan must be re-scoped (an escalation
trigger, §2). Check that it is still unpublished before you start: query PyPI's JSON API, not
`pip index` (which hides yanked releases).

The release line (`origin/debian/bookworm`) may keep cutting `0.1.0rcN` until `0.1.1` is published
(feature 017, Q10). Such a release **must not** carry this module unless it is also merged into the
refactor, and the consumers' `>= 0.1.1` floor already keeps them off any rc.

### 8.3 Rule 4 interaction ("merge before bump")

- **`cuems-utils`** is reconciled (feature 017), and this work adds commits on top. Re-measure
  `git rev-list --count HEAD..origin/debian/bookworm`; it must be 0. Then
  `tests/packaging/test_changelog_completeness.py` must pass.
- **`cuems-engine`** is mid-reconciliation (`009-release-line-reconciliation`).
  `origin/debian/bookworm`'s `AsyncCommsThread.py` is identical to the refactor's (§3.2), so the
  merge does not conflict on that file. If E1 lands first, the merge produces a delete/unchanged
  pair, which git resolves as a delete. Land E1–E5 on `feat/xml-refactor` and merge them into the
  009 branch, or land them on the 009 branch after its merge. **Decide with the engine maintainer**,
  and do not do both.
- **`cuems-nodeconf`**'s release lines carry the class at root `communicate.py` (§3.2). Their rule-4
  merge sees an unrelated path and will not conflict, but the merged tree must not bring back a
  root-level copy. Check `git ls-files communicate.py` after that merge; it must print nothing.

### 8.4 Tags and the maintainer's acts

No agent creates, moves or pushes a tag (CLAUDE.md). Once U, E and N have landed, three candidate
tags are stale: `cuems-utils`, `cuems-engine` and `cuems-nodeconf` `xml-refactor-merge-candidate`.
Feature 011's lesson applies: **a candidate tag set is only as current as its least current member**.
So:

1. Add these commits to `../.xml-refactor-tag-messages/` for the three repositories (the messages
   name commits, not tag objects: use `<tag>^{commit}`).
2. The maintainer re-cuts the three tags (`recut-and-push.sh`) and re-runs §11.1 validation on the
   re-cut set.
3. Add a line to the coordinated bump document's "still owed" list in the same commit as U4, so this
   item appears where the release owners look.

## 9. Risks and traps

- **A blocking `stop()` in nodeconf is new.** If anything calls it from the comms loop, it now raises
  instead of silently doing nothing, which is correct and loud. If anything calls it during a slow
  responder callback, shutdown can take up to `timeout`. ⚠ Measured: all three units have
  **`TimeoutStopSec=10`**, and the default `TIMEOUT` is 15 s. A stop that waits the full 15 s gets
  SIGKILLed at 10 s, mid-teardown. So both consumers' shutdown paths pass `stop(timeout=5)`. The engine
  already does this in its test fixtures; check that `stop_comms()` does it too. That leaves headroom
  for the rest of the shutdown.
- **Supervision could restart a service that used to limp along.** That is the intent, and it is
  safe only if each essential choice in E2 is right. A wrongly-essential task that legitimately
  returns would make the service crash-loop. That is why D3 is opt-in per task and needs engine
  sign-off.
- **pynng cancellation is probabilistic** (C6, about 1 in 1000). U3's ×200 loop is not proof. If
  `stop()` ever exceeds `timeout` there, the fix is closing the socket from `_cancel_tasks` before
  waiting, not a longer timeout ("no socket timeout ends that", `CLAUDE.md`).
- **REQ sockets cannot poll** (a timed-out receive abandons the request). Do not add a
  "health-check `run_coroutine`" that sends on a Communicator's REQ side.
- **Patching `asyncio.run_coroutine_threadsafe` in consumer tests** keeps working, because the
  library calls it by module attribute (`asyncio.run_coroutine_threadsafe`). Keep it that way: no
  `from asyncio import run_coroutine_threadsafe` in the new module, or the nodeconf and engine
  patches stop applying.
- **Sibling-reading tests.** If U adds a contract test that reads the siblings (for example
  "exactly one base definition", §7.1), mark it `@pytest.mark.reads_siblings`. It will skip in
  scratchpad worktrees.
