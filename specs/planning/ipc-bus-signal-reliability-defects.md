<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Reliability defects in `SignalEngine`, `CommunicatorServices` and `HubServices`

**Found 2026-10-22** while writing these modules' test counterparts:
- `tests/{unit,integration}/test_signalengine.py`;
- `tests/{unit,integration}/test_communicatorservices.py`;
- `tests/{unit,integration}/test_hubservices.py`.

Every defect was **measured** over real sockets, signals and processes, never inferred. The
production code is **unchanged**. Each defect except C6 is pinned by `xfail(strict=True)` tests that
state the *correct* behaviour, and their reasons start with `defect:`. Fixing a defect turns its
tests into strict-XPASS failures, so their markers have to go in the same commit as the fix. That
is the tripwire.

These three modules carry every message between CUEMS services and every node of a cluster, and
they run each service's lifecycle. Every defect below can stall or kill a service, or make a lost
message look delivered.

## CommunicatorServices (REQ/REP over IPC: editor ↔ nodeconf ↔ hwdiscovery)

| Id | Defect | Effect, measured | Pinned by |
|---|---|---|---|
| **C1** | `Communicator("ipc://…")` passes the prefixed address to `check_path`, which resolves it as the relative path `./ipc:/…` and calls `sys.exit(1)` | **the calling service exits**. A plain path works. The existing test hid this by patching `check_path` | `unit::TestCommunicatorInit::test_an_address_with_the_ipc_prefix_is_accepted` |
| **C2** | an exception from the request processor escapes `reply()`'s `while` loop | **the service stops answering**; every later request hangs | `unit::TestReply::test_a_raising_processor_does_not_stop_the_replier`, `integration::TestFailureModes::test_the_service_keeps_answering_after_its_processor_raised` |
| **C3** | a request that is not JSON does the same | same as C2 | `unit::TestReply::test_a_malformed_request_does_not_stop_the_replier` |
| **C4** | a response that cannot be JSON-encoded is logged and **never sent** | REQ/REP needs one reply per request, so **that requester hangs forever** | `unit::TestRespond::test_an_unencodable_response_still_answers_the_requester`, `integration::TestFailureModes::test_a_requester_is_answered_even_when_its_response_cannot_be_encoded` |
| **C5** | `send_request` has no timeout | asking a service that is not running **waits forever**, where every other failure returns `None` | `integration::TestFailureModes::test_asking_a_service_that_is_not_running_returns_none` |
| **C6** | `reply()` waits in `arecv()` with no receive timeout | **about 1 cancellation in 1000** of that pending receive never completes. Measured over 1000 rounds, both with one event loop and with a fresh loop per round. So a service that stops `reply()` by cancelling it can hang at shutdown until systemd kills it | not pinnable (probabilistic). The integration tests stop servers by closing the socket instead, as their docstring explains |

Suggested direction (a design decision, not made here):
- **C2, C3, C4:** catch per request inside the loop, and always send one reply (an error object, for example).
- **C5, C6:** give the sockets a receive timeout, as `NngBusHub` does with `recv_timeout=100`, and loop on `Timeout`. That makes cancellation prompt and lets `send_request` take a deadline.
- **C1:** strip `ipc://` before `check_path`.

## HubServices (NNG BUS over TCP: controller ↔ nodes)

| Id | Defect | Effect, measured | Pinned by |
|---|---|---|---|
| **H1** | `start()` waits with `FIRST_EXCEPTION`, but the receiver **returns** on `Closed` | once the socket closes, **`start()` never returns** (still running 2 s later), so the service cannot react to losing its bus | `unit::TestStart::test_returns_when_the_receiver_stops_on_a_closed_socket`, `integration::TestLifecycle::test_start_returns_when_its_socket_is_closed` |
| **H2** | the receiver calls `.get()` on the decoded payload before delivering it | valid JSON that is not an object (`[1, 2]`, `"text"`, `42`) and non-UTF-8 bytes are **counted as received and silently dropped**, while plain non-JSON text *is* delivered as `raw_data` | `unit::TestReceiverHandler::test_every_received_frame_is_delivered[…]` (4 cases) |
| **H3** | the sent counter and last-sent time are updated **before** `asend()` | a failed send counts as traffic, so **`is_connection_healthy()` stays `True` while nothing goes out**, and the message is lost | `unit::TestSendHandler::test_a_failed_send_is_not_counted_as_sent` |
| H4 (quirk) | `_auto_ping_handler` sleeps its interval *before* reading the new one | `enable_auto_ping()` after `start()` takes effect only after the previous interval (default 10 s). Configure it before `start()` | not pinned. `integration::TestPingPongOverTheWire` enables it before `start()` |

Measured and **correct**, for the record: a TCP peer's identity is its real `(ip, port)`. The old
unit test asserted a reversed IP only because its mock stored the address in host order; pynng
delivers it in network order.

## SignalEngine (every CUEMS service's lifecycle)

| Id | Defect | Effect | Pinned by |
|---|---|---|---|
| **S1** | `handle_interrupt`/`handle_terminate` call the `site` builtin `exit()`, not `sys.exit()` | in an interpreter without `site` (`python -S`, frozen or embedded builds) **the SIGTERM/SIGINT handler raises `NameError`**, so the service does not exit | `unit::TestExitHandlers::test_exits_through_sys_exit_not_the_site_builtin[…]` (2) |

## Fixed in the tests (no production change)

- **Signal-handler leak.** The old `daemon` fixture installed the engine's handlers in the pytest
  process and never restored them. After `test_signalengine.py`, pytest's SIGINT handler was
  `SignalEngine.handle_interrupt`. An autouse fixture now restores all five.
- **Log assertions depended on `CUEMS_LOG_LEVEL`.** `tests/support/cuems_logs.py` builds a module's
  logger first, then lowers its level.
- **The old `test_signal_handling_graceful_exit`** accepted `exitcode is None`, which is a process
  still running after the timeout. It is replaced by exact exit-status checks on a real child process.
