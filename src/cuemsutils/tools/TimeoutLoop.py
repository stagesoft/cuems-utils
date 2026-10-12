from __future__ import annotations

from collections.abc import Iterator
from time import sleep, time


class TimeoutLoop:
    """Iterate until ``timeout`` seconds have elapsed, then raise ``TimeoutError``.

    A small state machine for bounded polling loops: each iteration
    optionally sleeps ``interval`` seconds, then yields the elapsed time
    since the loop started. Once elapsed time exceeds ``timeout``, the next
    iteration raises instead of yielding — there is no silent "loop forever"
    path, and no sentinel return value to check.

    Re-entrant: iterating the same instance twice (two separate ``for``
    statements) restarts the clock, since ``__iter__`` re-stamps
    ``start_time`` on every call. A fresh instance per wait is still the
    common case (every example below does this) — reuse is supported, not
    required.

    Used by ``cuems-nodeconf`` to bound avahi node-discovery and first-run
    detection waits (``CuemsNodeConf.get_ips`` /
    ``wait_for_local_service_registration`` / ``retreive_local_node``).

    Args:
        timeout: seconds after which iteration raises ``TimeoutError``. A
            value ``<= 0`` raises as soon as any time at all has elapsed
            since iteration started — in practice immediately, since
            executing Python bytecode between the two clock reads already
            takes nonzero wall-clock time. There is no separate "already
            expired" check to call ahead of time.
        interval: seconds to ``sleep`` before each yield. ``None`` (the
            default) never sleeps — appropriate when the loop body itself
            blocks (e.g. a socket read) and no extra pacing is needed.

    Example:
        Poll until a condition holds, sleeping ``interval`` seconds between
        checks, and let ``TimeoutError`` propagate if it never does — the
        shape every current caller uses (``cuems-nodeconf``'s
        ``CuemsNodeConf.wait_for_local_service_registration``)::

            def wait_for_local_service_registration(self):
                for _elapsed in TimeoutLoop(timeout=5, interval=0.2):
                    for node in self.listener.nodes.values():
                        if node.get("ip") == self.ip:
                            return
                # unreachable in practice: the loop above ends only by the
                # `return` above, or by `TimeoutError` propagating out of
                # `__next__` once 5 seconds have elapsed.

        Polling something that already blocks, with no extra sleep::

            for _elapsed in TimeoutLoop(timeout=10):
                if socket_has_data(sock):
                    break
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
