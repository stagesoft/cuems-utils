"""``tools.TimeoutLoop`` — new home for the class formerly at
``cuemsutils.timeoutloop.Timeoutloop`` (see
``specs/planning/tools-external-consumers-and-timeoutloop-migration.md``,
Track 2). Uses a fake clock (monkeypatching the module's ``time``/``sleep``
names) throughout, so nothing here waits in real time.

The two usage-pattern tests near the end are the exact shape
``cuems-nodeconf``'s ``CuemsNodeConf.wait_for_local_service_registration``/
``retreive_local_node`` use today: a ``for`` loop with an unconditional
``return``/``break`` inside, relying on ``TimeoutError`` to propagate rather
than checking a sentinel.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools.TimeoutLoop import TimeoutLoop


class _FakeClock:
    """``time()`` returns the current fake time; ``sleep(s)`` advances it by
    ``s`` — mirrors real ``time.sleep``'s effect on a subsequent ``time.time()``
    read, without waiting."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start
        self.sleep_calls: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = _FakeClock()
    monkeypatch.setattr("cuemsutils.tools.TimeoutLoop.time", fake.time)
    monkeypatch.setattr("cuemsutils.tools.TimeoutLoop.sleep", fake.sleep)
    return fake


# --- core state machine -------------------------------------------------------


def test_yields_elapsed_time_while_within_the_timeout(clock):
    loop = TimeoutLoop(timeout=5, interval=1)
    it = iter(loop)

    assert next(it) == 1.0
    assert next(it) == 2.0
    assert next(it) == 3.0


def test_raises_timeout_error_once_elapsed_exceeds_timeout(clock):
    loop = TimeoutLoop(timeout=2, interval=1)
    it = iter(loop)

    next(it)  # elapsed 1.0, within timeout
    next(it)  # elapsed 2.0, within timeout (not yet > 2)
    with pytest.raises(TimeoutError, match="Timeout after 2 seconds"):
        next(it)  # elapsed 3.0, exceeds timeout


def test_interval_none_never_sleeps(clock):
    loop = TimeoutLoop(timeout=5, interval=None)
    it = iter(loop)

    next(it)
    next(it)

    assert clock.sleep_calls == []
    # No sleep means no time passes either, under the fake clock — the loop
    # relies entirely on the caller's own pacing.
    assert clock.now == 0.0


def test_interval_sleeps_by_the_given_amount_each_iteration(clock):
    loop = TimeoutLoop(timeout=5, interval=0.5)
    it = iter(loop)

    next(it)
    next(it)
    next(it)

    assert clock.sleep_calls == [0.5, 0.5, 0.5]


def test_reiterating_the_same_instance_restarts_the_clock(clock):
    loop = TimeoutLoop(timeout=5, interval=1)

    first_pass = iter(loop)
    assert next(first_pass) == 1.0
    assert next(first_pass) == 2.0

    second_pass = iter(loop)  # a fresh `for` statement over the same object
    assert next(second_pass) == 1.0  # clock restarted, not 3.0


def test_timeout_at_or_below_zero_raises_once_any_time_has_passed(clock):
    """Under a genuinely frozen clock, ``timeout=0`` does *not* raise before
    any time has elapsed (``0 > 0`` is false) — it raises as soon as it has,
    which real wall-clock reads guarantee happens between ``__iter__``'s and
    ``__next__``'s calls to ``time()`` even with no explicit sleep. Modelled
    here by advancing the fake clock directly, standing in for that
    real-world drift."""
    loop = TimeoutLoop(timeout=0, interval=None)
    it = iter(loop)
    clock.now += 1e-6

    with pytest.raises(TimeoutError):
        next(it)


# --- the real usage pattern ----------------------------------------------------


def test_break_on_condition_met_exits_cleanly_without_a_timeout_error(clock):
    seen = []
    for elapsed in TimeoutLoop(timeout=5, interval=1):
        seen.append(elapsed)
        if elapsed >= 2.0:
            break

    assert seen == [1.0, 2.0]


def test_condition_never_met_propagates_timeout_error_out_of_the_for_statement(clock):
    """The exact shape of ``CuemsNodeConf.wait_for_local_service_registration``:
    no sentinel check after the loop, just letting the exception propagate."""
    def condition_met():
        return False

    with pytest.raises(TimeoutError):
        for _elapsed in TimeoutLoop(timeout=2, interval=1):
            if condition_met():
                break
