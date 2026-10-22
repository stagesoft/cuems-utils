<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Upstream report → `cuems-engine`: notice when the bus hub stops

**From:** `cuems-utils`, 2026-10-22 (defect H1 in `specs/planning/ipc-bus-signal-reliability-defects.md`).
`cuems-utils` edits no file in your repository. Delete this note once the engine change lands.

## What changed in `cuems-utils` 0.1.1

`NngBusHub.start()` used to run forever once its bus socket had closed: its receiver stopped, but
`start()` kept waiting. It now **returns** as soon as its receiver or sender stops, whether a handler
failed or the socket closed. Before it returns it logs one error: `NNG <mode> <handler> handler stopped:
bus socket closed`, or `... handler failed: <error>`. It still raises only for startup errors (an
unknown mode, or a socket it cannot open). Nothing else about the hub changed.

## Why your engine does not notice yet

`AsyncCommsThread.run_asyncio_comms` runs every comms task through
`asyncio.gather(*tasks, return_exceptions=True)`. That waits for **all** of them. The hub's message
receiver (`start_message_receiver`) and `editor_listener` never end, so when `nng_hub.start()`
returns, the gather keeps waiting and the engine carries on with no bus. A controller then reaches no
node, and a node hears no controller, with no error beyond the hub's own log line. This is the
behaviour you have today, so nothing gets worse, but nothing gets better either until the engine
reacts.

## What we suggest

Treat the end of the `nng_hub.start()` task as fatal for the comms thread:

```python
tasks = self.create_all_tasks()
done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
for task in done:
    if task.exception() is not None:
        Logger.error(f"{self.name} task failed: {task.exception()!r}")
    else:
        Logger.error(f"{self.name} task ended: {task.get_coro().__qualname__}")
for task in pending:
    task.cancel()
await asyncio.gather(*pending, return_exceptions=True)
raise SystemExit(1)   # or your own fatal path; systemd's Restart= then brings the service back
```

Any of the long-lived tasks ending is a fault, so `FIRST_COMPLETED` over the whole list is the simplest
rule. If some task is allowed to finish, watch only `nng_hub.start()`, with a done-callback or a
separate `asyncio.wait`.

Before relying on a restart, check that the engine's systemd units carry `Restart=on-failure` (or
`always`).

## How to verify

Against `cuems-utils` 0.1.1:
1. start a node and a controller;
2. close the hub's socket under a running engine: call `connection.close()` on the
   `NodeCommunications`/`ControllerCommunications` instance's `nng_hub` from a debug hook;
3. the comms thread should end and the service exit non-zero. Today it keeps running.

`cuems-utils` covers its own half in `tests/integration/test_hubservices.py::TestLifecycle::
test_start_returns_when_its_socket_is_closed`.
