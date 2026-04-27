"""Quarter-frame timer that hooks to a CTimecode object.

Fires a registered callback at every quarter-frame boundary. Optionally
accepts an immutable list of parameter tuples at construction time; each
tuple's contents are unpacked as callback arguments at the corresponding
quarter-frame. When a tuple list is provided the timer stops automatically
after the last tuple is consumed; without one it runs until explicitly stopped.
"""

from __future__ import annotations

import enum
import threading
from typing import Callable

from cuemsutils.log import Logger
from cuemsutils.tools.CTimecode import CTimecode


class _State(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    EXHAUSTED = "exhausted"


class CTimecodeTimer:
    """Timer that fires a callback at every quarter-frame boundary."""

    def __init__(
        self,
        timecode: CTimecode,
        params: list[tuple] | None = None,
    ) -> None:
        if timecode is None:
            raise ValueError("CTimecodeTimer: timecode must not be None")

        self._timecode = timecode

        # QF interval: handle 'ms' pseudo-framerate (= 1000 fps)
        fr = timecode.framerate
        qf_fr = 1000.0 if fr == "ms" else float(fr)
        self._qf_interval: float = 1.0 / (4.0 * qf_fr)

        # Freeze params; empty list → bare-signal mode
        if params is not None and len(params) > 0:
            self._params: tuple[tuple, ...] | None = tuple(
                tuple(p) for p in params
            )
        else:
            self._params = None

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._callback: Callable | None = None
        self._state: _State = _State.IDLE
        self._index: int = 0

    # ── Public interface ────────────────────────────────────────────────

    @property
    def callback(self) -> Callable | None:
        with self._lock:
            return self._callback

    @callback.setter
    def callback(self, fn: Callable | None) -> None:
        with self._lock:
            self._callback = fn

    def start(self) -> None:
        """Start the timer loop.

        IDLE or STOPPED → RUNNING.  No-op if already RUNNING.
        EXHAUSTED → no-op with a warning.
        """
        with self._lock:
            if self._state == _State.EXHAUSTED:
                Logger.warning(
                    "CTimecodeTimer: cannot restart exhausted timer"
                    " — create a new instance"
                )
                return
            if self._state == _State.RUNNING:
                return
            self._stop_event.clear()
            self._state = _State.RUNNING
            prev = self._thread

        # Join any previous thread outside the lock
        if prev is not None:
            prev.join(timeout=self._qf_interval * 4)

        t = threading.Thread(
            target=self._run_loop, daemon=True, name="CTimecodeTimer"
        )
        self._thread = t
        t.start()

    def stop(self) -> None:
        """Stop the timer loop.  RUNNING → STOPPED.  No-op otherwise."""
        with self._lock:
            if self._state != _State.RUNNING:
                return
            self._state = _State.STOPPED

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._qf_interval * 4)

    # ── Private loop ────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        prev_tc_ms: float = self._timecode.milliseconds_exact
        qf_ms: float = self._qf_interval * 1000.0

        while True:
            # Wait for one QF interval or early exit on stop
            if self._stop_event.wait(timeout=self._qf_interval):
                break

            # Read current timecode position (for seek detection)
            current_tc_ms = self._timecode.milliseconds_exact
            delta_ms = current_tc_ms - prev_tc_ms
            prev_tc_ms = current_tc_ms

            # Seek detection — parameterised mode only
            if self._params is not None:
                if delta_ms > 1.5 * qf_ms:
                    extra = round(delta_ms / qf_ms) - 1
                    self._index = min(
                        self._index + extra, len(self._params)
                    )
                elif delta_ms < 0:
                    self._index = 0

                if self._index >= len(self._params):
                    with self._lock:
                        self._state = _State.EXHAUSTED
                    break

            # Dispatch callback
            with self._lock:
                cb = self._callback

            if cb is not None:
                try:
                    if self._params is not None:
                        cb(*self._params[self._index])
                    else:
                        cb()
                except Exception:
                    Logger.error(
                        "CTimecodeTimer: callback raised an exception"
                    )

            # Post-dispatch index advance
            if self._params is not None:
                self._index += 1
                if self._index >= len(self._params):
                    with self._lock:
                        self._state = _State.EXHAUSTED
                    break
