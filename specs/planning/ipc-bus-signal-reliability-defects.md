<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Reliability defects in `SignalEngine`, `CommunicatorServices` and `HubServices`

**Found 2026-10-22** while writing these modules' test counterparts:
- `tests/{unit,integration}/test_signalengine.py`;
- `tests/{unit,integration}/test_communicatorservices.py`;
- `tests/{unit,integration}/test_hubservices.py`.

Every defect was **measured** over real sockets, signals and processes, never inferred.

**Status (2026-10-22):** **every defect is fixed (C1–C8, H1–H4, S1), and H5 was measured and not reproduced**, test first: their xfail markers were
removed, the tests went red, and the fix turned them green. Failed requests are now answered with
`{"OK": False, "error": "<ExceptionType>: <message>"}`, the shape `cuems-nodeconf` already uses and
`cuems-editor` already reads. C7 was found while fixing C3, and fixed the same way. A callback that *raises* is deliberately not answered for: it owns its context, and may already have replied or handed the context on (`cuems-engine` replies later, from another thread). **Nothing is open outside this repository any more.** H1's engine half landed on `cuems-engine`'s `feat/xml-refactor` in `69c2d9a` (pushed 2026-10-22, the `AsyncCommsThread` migration), and H6's engine half is the ping resend below. The upstream report that carried both, `upstream-cuems-engine-hub-start-supervision.md`, is deleted (in git history). This record's own deletion condition is therefore met; it stays until `CLAUDE.md`'s Recent Changes entry stops pointing at it. This
document is deleted once those are resolved.

Before the fixes, the production code was unchanged. Each defect except C6 is pinned by `xfail(strict=True)` tests that
state the *correct* behaviour, and their reasons start with `defect:`. Fixing a defect turns its
tests into strict-XPASS failures, so their markers have to go in the same commit as the fix. That
is the tripwire.

These three modules carry every message between CUEMS services and every node of a cluster, and
they run each service's lifecycle. Every defect below can stall or kill a service, or make a lost
message look delivered.

## CommunicatorServices (REQ/REP over IPC: editor ↔ nodeconf ↔ hwdiscovery)

| Id | Defect | Effect, measured | Pinned by |
|---|---|---|---|
| **C1** ✅ fixed | `Communicator("ipc://…")` passes the prefixed address to `check_path`, which resolves it as the relative path `./ipc:/…` and calls `sys.exit(1)` | **the calling service exits**. A plain path works. The existing test hid this by patching `check_path` | `unit::TestCommunicatorInit::test_an_address_with_the_ipc_prefix_is_accepted` |
| **C2** ✅ fixed | an exception from the request processor escapes `reply()`'s `while` loop | **the service stops answering**; every later request hangs | `unit::TestReply::test_a_raising_processor_does_not_stop_the_replier`, `integration::TestFailureModes::test_the_service_keeps_answering_after_its_processor_raised` |
| **C3** ✅ fixed | a request that is not JSON does the same | same as C2 | `unit::TestReply::test_a_malformed_request_does_not_stop_the_replier` |
| **C4** ✅ fixed | a response that cannot be JSON-encoded is logged and **never sent** | REQ/REP needs one reply per request, so **that requester hangs forever** | `unit::TestRespond::test_an_unencodable_response_still_answers_the_requester`, `integration::TestFailureModes::test_a_requester_is_answered_even_when_its_response_cannot_be_encoded` |
| **C5** ✅ fixed | `send_request` has no timeout | asking a service that is not running **waits forever**, where every other failure returns `None` | `integration::TestFailureModes::test_asking_a_service_that_is_not_running_returns_none` |
| **C7** ✅ fixed | the context API's `responder_get_request` logs a request that is not JSON and drops it: no reply, and the context is never closed | **its requester waits forever**, and the context leaks. Same class as C3, on the other server API | `unit::TestResponderGetRequest::test_a_malformed_request_is_answered_and_its_context_closed` |
| **C8** ✅ fixed (found 2026-10-22, during the `AsyncCommsThread` absorption) | the context API's `responder_get_request` wrapped its whole body in `except Exception`, so a **socket** error was logged and swallowed: `new_context()` on a closed responder raises `Closed`, a receive pending when the socket closes raises `Closed`, and a responder never connected raises `AttributeError` | measured: the call returned **~28,700 times/s** on a closed socket and **~27,000 times/s** unconnected, logging an ERROR each time, **without ever yielding**, so a consumer's `while not stop_requested:` loop (`cuems-engine` `editor_listener`, `cuems-nodeconf` `engine_listener`) starved every other task on its event loop (bus hub, WebSocket OSC), and no supervision could see it. Now a socket error raises, after closing the context; an unconnected responder raises `RuntimeError`. A malformed request (C7) and a raising callback are handled as before | `unit::TestResponderGetRequest::test_a_closed_responder_socket_raises` (+2), `integration::TestContextResponderFailureModes::test_a_listener_loop_on_a_closed_socket_ends_instead_of_spinning` (+1), `integration/test_asynccommsthread.py::TestResponder::test_a_closed_responder_socket_ends_the_communications` |
| **C6** ✅ fixed | `reply()` waits in `arecv()` with no receive timeout | **about 1 cancellation in 1000** of that pending receive never completes. Measured over 1000 rounds, both with one event loop and with a fresh loop per round. So a service that stops `reply()` by cancelling it can hang at shutdown until systemd kills it | not pinnable (probabilistic). The integration tests stop servers by closing the socket instead, as their docstring explains |

**How C5 and C6 were fixed (2026-10-22), and a correction to the direction suggested below.**

- **C5.** `send_request(request, timeout=REQUEST_TIMEOUT)` waits at most 100 s by default, for the
  send and the reply together, then returns `None` and logs `no reply from <address> within <t> s`.
  `Communicator.send_request` forwards `timeout`, and the abstract `CommunicatorService.send_request`
  declares it, so a custom service must accept it. Measured: with no replier the hang was in
  **`asend()`**, not in the receive, so a receive timeout alone would never have fixed C5. The fix
  sets `send_timeout` to the deadline, then `recv_timeout` to what the send left. A REQ socket cannot
  poll: a timed-out receive abandons the request (`BadState` on retry).
- **C6.** The suggested 100 ms receive timeout was implemented and **measured not to work**: still 2
  stalls in 1000 rounds. The stuck receive was still pending 7 s later. The mechanism, read in
  `pynng/_aio.py`: on cancellation, `asyncio_helper.wait_for_aio` calls `nng_aio_cancel` and keeps
  waiting, swallowing `CancelledError`, for NNG's completion callback. Rarely that callback never
  comes, and then no timeout can end the operation. The fix never exposes a pynng operation to
  cancellation. `_shielded()` lets the cancellation reach the caller at once. The caller closes its
  socket (the `with` block) or context, which ends the abandoned operation with `Closed`, and that
  error is retrieved so it is never logged. The receive timeout was removed again. Measured after the
  fix: **0 stalls in 7000 cancellations** (about 7 expected before). It is pinned deterministically
  by `StuckSocket`, a fake that reproduces the bridge's behaviour, and by the slow 1000-round
  `integration::TestPromptCancellation::test_a_thousand_cancellations_all_complete`.

Found on the way, not a defect: a node started **before** its controller takes 0.4–8.5 s to connect
(15 runs, idle box). It can take up to `start_dialer`'s `reconnect_time_max` of 30 s, because NNG
grows the dialer's retry delay after every failed dial. The integration bound is therefore 35 s.

Direction suggested before the fixes (kept for the record; corrected above for C5 and C6):
- **C2, C3, C4:** catch per request inside the loop, and always send one reply (an error object, for example).
- **C5, C6:** give the sockets a receive timeout, as `NngBusHub` does with `recv_timeout=100`, and loop on `Timeout`. That makes cancellation prompt and lets `send_request` take a deadline.
- **C1:** strip `ipc://` before `check_path`.

## HubServices (NNG BUS over TCP: controller ↔ nodes)

| Id | Defect | Effect, measured | Pinned by |
|---|---|---|---|
| **H1** ✅ fixed (library half) | `start()` waits with `FIRST_EXCEPTION`, but the receiver **returns** on `Closed` | once the socket closes, **`start()` never returns** (still running 2 s later), so the service cannot react to losing its bus | `unit::TestStart::test_returns_when_the_receiver_stops_on_a_closed_socket`, `integration::TestLifecycle::test_start_returns_when_its_socket_is_closed` |
| **H2** ✅ fixed | the receiver calls `.get()` on the decoded payload before delivering it | valid JSON that is not an object (`[1, 2]`, `"text"`, `42`) and non-UTF-8 bytes are **counted as received and silently dropped**, while plain non-JSON text *is* delivered as `raw_data` | `unit::TestReceiverHandler::test_every_received_frame_is_delivered[…]` (4 cases) |
| **H3** ✅ fixed | the sent counter and last-sent time are updated **before** `asend()` | a failed send counts as traffic, so **`is_connection_healthy()` stays `True` while nothing goes out**, and the message is lost | `unit::TestSendHandler::test_a_failed_send_is_not_counted_as_sent` |
| H4 (quirk) ✅ fixed | `_auto_ping_handler` sleeps its interval *before* reading the new one | `enable_auto_ping()` after `start()` takes effect only after the previous interval (default 10 s). Configure it before `start()` | not pinned. `integration::TestPingPongOverTheWire` enables it before `start()` |

**H1, fixed (library half), decided 2026-10-22: return, not raise.** `start()` waits with
`FIRST_COMPLETED`, so it ends as soon as its receiver or sender stops, and it logs `... handler
stopped: bus socket closed`. It **returns**, as it already did when a handler failed. Raising stays
reserved for startup errors. Return is the lower-impact choice:
- it keeps one rule for runtime failures;
- a caller's `try` around startup errors does not start catching runtime ones;
- a task that is never awaited raises no "exception never retrieved";
- for `cuems-engine` the two were indistinguishable, because its `asyncio.gather(..., return_exceptions=True)`
  waits on tasks that never end.
That engine half is the upstream report.

**H2, fixed:** every frame is delivered. A JSON object is `data`. Anything else is
`{"raw_data": <its text>}`, with a warning log: bytes that are not UTF-8 (decoded with
`errors="replace"`), text that is not JSON (as before), and JSON that is not an object. Nothing that
was delivered before changes shape.

**H4, fixed:** `enable_auto_ping()`/`disable_auto_ping()` wake a running handler, which starts a new
interval with the new settings at once. The handler creates its event on its own loop. A change made
from another thread goes through `call_soon_threadsafe`, and with no handler running it is a no-op.

**H5, measured and not reproduced (no change made).** The suspicion was C6's lost-callback hang in the
hub's shutdown, since `NngBusHub` awaits pynng unshielded and `start()`'s teardown awaits each
cancelled task with no bound. Measured: a controller and a node connect, exchange a message, and both
`start()` tasks are cancelled. Over 2 × 1000 rounds on IPC and 2000 on TCP, that is **8000 receiver
cancellations, with no stall; the worst took 3 ms**. C6's rate predicts about 8 (P(0) ≈ 0.03%). Why
this path differs is not shown: C6's stalls were on a REP `arecv()`, and the hub uses BUS
`arecv_msg()`. The measurement is kept as the slow
`integration::TestLifecycle::test_a_thousand_shutdowns_all_complete` (about 64 s), so a pynng upgrade
that changes it is caught.

**H6, measured 2026-10-22: a protocol property, not a library defect; no code change.** NNG's BUS
protocol is best-effort. A message a node sends **the instant** a new connection is up is
occasionally dropped. Both sides report the connection, the node's `asend()` completes, and the
controller never sees the message. Found when the H5 test lost its 50 ms sleep.
- Sent as soon as both sides reported the connection: **3 lost in 12000** rounds. In each case the
  next message on the same link arrived, so it is not C6's stuck receive.
- With a 20 ms pause first: **0 in 12000**.

So the loss is confined to connection establishment. For the engine, a command or status sent right
after a node (re)connects can vanish without a trace, so anything that must arrive needs an
application-level acknowledgement and resend. That request was in the engine upstream report. The
tests let a connection settle first (`SETTLE`, 20 ms), and the H5 test resends instead.

**Engine remediation, decided 2026-10-22: resend only what is idempotent.** The engine sends nothing
automatically when a link comes up. Every bus message follows an operator action or an arm, seconds
after connection, so the exposure is a node that (re)connects just before one. Measured per message:
- **`ping` is resent.** The liveness probe resends it at 1/3 and 2/3 of its 1.5 s window to nodes
  that have not ponged, and the window is not extended. A lost ping used to silently drop a live node
  from the GO gate's required set. It is idempotent: the node only answers it.
- **`load` is not resent.** `armed_ready` already acknowledges it, and a loss is visible
  (`Load stalled`, the gate stays closed). A duplicate would re-arm the node, and could race a GO.
- **`go` / `stop` / … are not resent.** `run_seq` is per run, not per GO, so a resent GO that did
  arrive would fire the next cue. Resending them needs per-message ids and node-side dedupe, a
  wire-format change for a full SDD feature in `cuems-engine` if it is ever wanted.

Measured and **correct**, for the record: a TCP peer's identity is its real `(ip, port)`. The old
unit test asserted a reversed IP only because its mock stored the address in host order; pynng
delivers it in network order.

## SignalEngine (every CUEMS service's lifecycle)

| Id | Defect | Effect | Pinned by |
|---|---|---|---|
| **S1** ✅ fixed | `handle_interrupt`/`handle_terminate` call the `site` builtin `exit()`, not `sys.exit()` | in an interpreter without `site` (`python -S`, frozen or embedded builds) **the SIGTERM/SIGINT handler raises `NameError`**, so the service does not exit | `unit::TestExitHandlers::test_exits_through_sys_exit_not_the_site_builtin[…]` (2) |

## Fixed in the tests (no production change)

- **Signal-handler leak.** The old `daemon` fixture installed the engine's handlers in the pytest
  process and never restored them. After `test_signalengine.py`, pytest's SIGINT handler was
  `SignalEngine.handle_interrupt`. An autouse fixture now restores all five.
- **Log assertions depended on `CUEMS_LOG_LEVEL`.** `tests/support/cuems_logs.py` builds a module's
  logger first, then lowers its level.
- **The old `test_signal_handling_graceful_exit`** accepted `exitcode is None`, which is a process
  still running after the timeout. It is replaced by exact exit-status checks on a real child process.
