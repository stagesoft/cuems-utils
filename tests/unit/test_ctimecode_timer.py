"""Tests for CTimecodeTimer — quarter-frame callback timer."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.tools.CTimecodeTimer import CTimecodeTimer, _State

# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def make_tc():
    """Factory for CTimecode objects."""

    def _make(framerate=25, start_timecode="00:00:00:00"):
        return CTimecode(start_timecode=start_timecode, framerate=framerate)

    return _make


def _fast(timer: CTimecodeTimer) -> CTimecodeTimer:
    """Override QF interval to 1 ms for fast unit tests."""
    timer._qf_interval = 0.001
    return timer


def _run_to_exhaustion(timer: CTimecodeTimer, timeout: float = 2.0) -> None:
    """Start timer and block until EXHAUSTED or timeout."""
    timer.start()
    deadline = time.monotonic() + timeout
    while timer._state != _State.EXHAUSTED and time.monotonic() < deadline:
        time.sleep(0.0005)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: __init__ validation  (T005)
# ═══════════════════════════════════════════════════════════════════════════


class TestInit:
    def test_none_timecode_raises(self):
        with pytest.raises(ValueError, match="timecode must not be None"):
            CTimecodeTimer(timecode=None)

    def test_empty_params_is_bare_signal(self, make_tc):
        timer = CTimecodeTimer(make_tc(), params=[])
        assert timer._params is None

    def test_qf_interval_25fps(self, make_tc):
        timer = CTimecodeTimer(make_tc(25))
        assert timer._qf_interval == pytest.approx(1.0 / 100.0)

    def test_qf_interval_24fps(self, make_tc):
        timer = CTimecodeTimer(make_tc(24))
        assert timer._qf_interval == pytest.approx(1.0 / 96.0)

    def test_qf_interval_30fps(self, make_tc):
        timer = CTimecodeTimer(make_tc(30))
        assert timer._qf_interval == pytest.approx(1.0 / 120.0)

    def test_params_frozen_as_tuples(self, make_tc):
        timer = CTimecodeTimer(make_tc(), params=[[1, 2], [3, 4]])
        assert timer._params == ((1, 2), (3, 4))

    def test_initial_state_is_idle(self, make_tc):
        timer = CTimecodeTimer(make_tc())
        assert timer._state == _State.IDLE


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: start/stop state transitions  (T006)
# ═══════════════════════════════════════════════════════════════════════════


class TestStartStopTransitions:
    def test_start_idle_to_running(self, make_tc):
        timer = _fast(CTimecodeTimer(make_tc()))
        timer.start()
        assert timer._state == _State.RUNNING
        timer.stop()

    def test_stop_running_to_stopped(self, make_tc):
        timer = _fast(CTimecodeTimer(make_tc()))
        timer.start()
        timer.stop()
        assert timer._state == _State.STOPPED

    def test_start_after_stop_resumes(self, make_tc):
        timer = _fast(CTimecodeTimer(make_tc()))
        timer.start()
        timer.stop()
        assert timer._state == _State.STOPPED
        timer.start()
        assert timer._state == _State.RUNNING
        timer.stop()

    def test_start_noop_if_running(self, make_tc):
        timer = _fast(CTimecodeTimer(make_tc()))
        timer.start()
        thread1 = timer._thread
        timer.start()  # should be no-op
        assert timer._thread is thread1
        timer.stop()


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: _run_loop exits cleanly within 1× QF  (T007)
# ═══════════════════════════════════════════════════════════════════════════


class TestRunLoopExit:
    def test_exits_within_one_qf_interval(self, make_tc):
        timer = _fast(CTimecodeTimer(make_tc()))
        timer.start()
        time.sleep(0.005)  # let loop start
        t0 = time.monotonic()
        timer.stop()
        elapsed = time.monotonic() - t0
        assert not timer._thread.is_alive()
        # Must exit within 1× QF (1 ms) + generous OS jitter margin
        assert elapsed < 0.050


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 / US1: callback dispatch  (T011-T014, T017)
# ═══════════════════════════════════════════════════════════════════════════


class TestUS1CallbackDispatch:
    def test_parameterised_mode_correct_args(self, make_tc):
        """T011: 4 tuples → 4 callbacks with correct unpacked args."""
        calls: list[tuple] = []
        params = [(0,), (1,), (2,), (3,)]
        timer = _fast(CTimecodeTimer(make_tc(), params=params))
        timer.callback = lambda *a: calls.append(a)
        _run_to_exhaustion(timer)
        assert calls == [(0,), (1,), (2,), (3,)]

    def test_bare_signal_no_args(self, make_tc):
        """T012: bare-signal mode → callback() with no args."""
        done = threading.Event()
        calls: list[bool] = []

        def cb():
            calls.append(True)
            if len(calls) >= 3:
                done.set()

        timer = _fast(CTimecodeTimer(make_tc()))
        timer.callback = cb
        timer.start()
        done.wait(timeout=2.0)
        timer.stop()
        assert len(calls) >= 3

    def test_no_callback_no_error(self, make_tc):
        """T013: no callback → runs silently without raising."""
        timer = _fast(CTimecodeTimer(make_tc(), params=[(i,) for i in range(4)]))
        _run_to_exhaustion(timer)
        assert timer._state == _State.EXHAUSTED

    def test_exhausted_after_last_tuple(self, make_tc):
        """T014: transitions to EXHAUSTED after last tuple consumed."""
        cb = MagicMock()
        timer = _fast(CTimecodeTimer(make_tc(), params=[(i,) for i in range(4)]))
        timer.callback = cb
        _run_to_exhaustion(timer)
        assert timer._state == _State.EXHAUSTED
        assert cb.call_count == 4

    def test_timing_smoke_25fps(self, make_tc):
        """T017: at 25fps, callback fires correctly (mocked fast interval)."""
        calls: list[tuple] = []
        params = [(i,) for i in range(4)]
        timer = _fast(CTimecodeTimer(make_tc(25), params=params))
        timer.callback = lambda *a: calls.append(a)
        _run_to_exhaustion(timer)
        assert len(calls) == 4
        assert calls == [(0,), (1,), (2,), (3,)]


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4 / US2: start/stop lifecycle  (T019-T022)
# ═══════════════════════════════════════════════════════════════════════════


class TestUS2Lifecycle:
    def test_stop_halts_callbacks(self, make_tc):
        """T019: after stop(), no further callbacks fire."""
        calls: list[bool] = []
        gate = threading.Event()

        def cb():
            calls.append(True)
            if len(calls) >= 3:
                gate.set()

        timer = _fast(CTimecodeTimer(make_tc()))
        timer.callback = cb
        timer.start()
        gate.wait(timeout=2.0)
        timer.stop()
        count_at_stop = len(calls)
        time.sleep(0.010)  # 10× QF interval — no more calls expected
        assert len(calls) == count_at_stop

    def test_restart_after_stop_resumes_callbacks(self, make_tc):
        """T020: start() after stop() resumes callback emission."""
        calls: list[bool] = []
        gate = threading.Event()

        def cb():
            calls.append(True)
            if len(calls) >= 2:
                gate.set()

        timer = _fast(CTimecodeTimer(make_tc()))
        timer.callback = cb
        timer.start()
        gate.wait(timeout=2.0)
        timer.stop()

        # Reset gate and restart
        gate.clear()
        calls.clear()
        timer.start()
        gate.wait(timeout=2.0)
        timer.stop()
        assert len(calls) >= 2

    def test_stop_on_never_started_is_noop(self, make_tc):
        """T021: stop() on a never-started timer completes without error."""
        timer = CTimecodeTimer(make_tc())
        timer.stop()  # must not raise
        assert timer._state == _State.IDLE

    def test_start_on_exhausted_is_noop(self, make_tc):
        """T022: start() on EXHAUSTED timer is no-op with warning."""
        cb = MagicMock()
        timer = _fast(CTimecodeTimer(make_tc(), params=[(1,)]))
        timer.callback = cb
        _run_to_exhaustion(timer)
        assert timer._state == _State.EXHAUSTED
        timer.start()  # should be no-op
        assert timer._state == _State.EXHAUSTED


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5 / US3: replace or remove callback  (T027-T028)
# ═══════════════════════════════════════════════════════════════════════════


class TestUS3CallbackSwap:
    def test_replace_callback_while_running(self, make_tc):
        """T027: replacing callback mid-run — new one fires, old one stops."""
        old_calls: list[bool] = []
        new_calls: list[bool] = []
        gate_old = threading.Event()
        gate_new = threading.Event()

        def cb_old():
            old_calls.append(True)
            if len(old_calls) >= 2:
                gate_old.set()

        def cb_new():
            new_calls.append(True)
            if len(new_calls) >= 2:
                gate_new.set()

        timer = _fast(CTimecodeTimer(make_tc()))
        timer.callback = cb_old
        timer.start()
        gate_old.wait(timeout=2.0)
        # Swap callback
        old_count = len(old_calls)
        timer.callback = cb_new
        gate_new.wait(timeout=2.0)
        timer.stop()
        assert len(new_calls) >= 2
        # Old callback should not have received more calls after swap
        assert len(old_calls) == old_count

    def test_set_callback_none_while_running(self, make_tc):
        """T028: setting callback=None stops emission silently."""
        calls: list[bool] = []
        gate = threading.Event()

        def cb():
            calls.append(True)
            if len(calls) >= 2:
                gate.set()

        timer = _fast(CTimecodeTimer(make_tc()))
        timer.callback = cb
        timer.start()
        gate.wait(timeout=2.0)
        timer.callback = None
        count_at_clear = len(calls)
        time.sleep(0.010)
        timer.stop()
        assert len(calls) == count_at_clear


# ═══════════════════════════════════════════════════════════════════════════
# Phase 6: Polish & Cross-Cutting  (T032, T034, T039)
# ═══════════════════════════════════════════════════════════════════════════


class TestPolish:
    def test_callback_exception_does_not_halt_timer(self, make_tc):
        """T032: exception in callback does not stop subsequent firings."""
        results: list[int] = []

        params = [(0,), (1,), (2,), (3,)]

        def cb(val):
            if val == 1:
                raise RuntimeError("boom")
            results.append(val)

        timer = _fast(CTimecodeTimer(make_tc(), params=params))
        timer.callback = cb
        _run_to_exhaustion(timer)
        assert timer._state == _State.EXHAUSTED
        # val=1 raised, so we should get 0, 2, 3
        assert results == [0, 2, 3]

    def test_forward_seek_skips_tuples(self, make_tc):
        """T034a: forward seek advances index proportionally."""
        tc = make_tc()
        calls: list[tuple] = []
        params = [(i,) for i in range(10)]
        timer = _fast(CTimecodeTimer(tc, params=params))
        timer.callback = lambda *a: calls.append(a)

        timer.start()
        # Let one callback fire
        time.sleep(0.005)
        # Jump timecode forward by many QF intervals (add ~5 frames = 200ms)
        tc.add_frames(5)
        # Let it run to exhaustion
        deadline = time.monotonic() + 2.0
        while timer._state != _State.EXHAUSTED and time.monotonic() < deadline:
            time.sleep(0.0005)
        assert timer._state == _State.EXHAUSTED
        # Some tuples should have been skipped
        assert len(calls) < 10

    def test_backward_seek_resets_index(self, make_tc):
        """T034b: backward seek clamps index to 0."""
        tc = make_tc(start_timecode="00:00:01:00")
        calls: list[tuple] = []
        params = [(i,) for i in range(8)]
        timer = _fast(CTimecodeTimer(tc, params=params))
        timer.callback = lambda *a: calls.append(a)
        timer.start()
        time.sleep(0.005)
        # Jump backward by setting to an earlier timecode
        tc.set_timecode("00:00:00:00")
        # Let it finish
        deadline = time.monotonic() + 2.0
        while timer._state != _State.EXHAUSTED and time.monotonic() < deadline:
            time.sleep(0.0005)
        timer.stop()
        assert timer._state == _State.EXHAUSTED
        # After backward seek, index resets to 0, so we get more callbacks
        # (some indices will be repeated)
        assert len(calls) >= 8

    def test_bare_signal_ignores_seek(self, make_tc):
        """T034c: backward seek in bare-signal mode — timer continues."""
        tc = make_tc(start_timecode="00:00:01:00")
        calls: list[bool] = []
        gate = threading.Event()

        def cb():
            calls.append(True)
            if len(calls) >= 5:
                gate.set()

        timer = _fast(CTimecodeTimer(tc))
        timer.callback = cb
        timer.start()
        time.sleep(0.003)
        tc.set_timecode("00:00:00:00")  # backward jump
        gate.wait(timeout=2.0)
        timer.stop()
        assert len(calls) >= 5


@pytest.mark.slow
class TestIntegration:
    def test_realtime_25fps_jitter(self, make_tc):
        """T039: real-time 25fps — callback jitter within ±1ms."""
        timestamps: list[float] = []
        params = [(i,) for i in range(8)]
        timer = CTimecodeTimer(make_tc(25), params=params)
        timer.callback = lambda *a: timestamps.append(time.monotonic())
        _run_to_exhaustion(timer, timeout=5.0)
        assert len(timestamps) == 8
        qf_expected = 1.0 / 100.0  # 10ms
        for i in range(1, len(timestamps)):
            delta = timestamps[i] - timestamps[i - 1]
            # ±1ms tolerance
            assert abs(delta - qf_expected) < 0.001, (
                f"QF {i}: delta={delta*1000:.3f}ms, expected={qf_expected*1000:.3f}ms"
            )
