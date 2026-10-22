"""Unit counterpart of ``cuemsutils.tools.AsyncCommsThread``: one class per method, in source order.

No socket is opened here. Each test starts a real thread with plain coroutines as its tasks
(``Comms``), because the class's whole job is the hand-off between threads and a fake loop would test
nothing. Real NNG sockets driven by the thread are in ``tests/integration/test_asynccommsthread.py``.
"""
import asyncio
import threading
import time

import pytest

from cuemsutils.tools import AsyncCommsThread as module
from cuemsutils.tools.AsyncCommsThread import TIMEOUT, AsyncCommsThread
from tests.support import cuems_logs

BOUND = 5.0  # seconds; every wait here is a few milliseconds when it works


@pytest.fixture(autouse=True)
def cuems_debug_logs(caplog):
    """Assertions on log text must not depend on CUEMS_LOG_LEVEL."""
    cuems_logs.capture(caplog, module.__name__)


@pytest.fixture(autouse=True)
def no_thread_left_behind():
    yield
    AsyncCommsThread.stop_all(timeout=BOUND)


async def forever():
    await asyncio.Event().wait()


async def returns():
    return "done"


async def raises():
    raise ValueError("boom")


class Comms(AsyncCommsThread):
    """Runs the coroutine functions it is given; names in ``essential`` are marked essential."""

    def __init__(self, *tasks, essential=(), **kwargs):
        super().__init__(**kwargs)
        self.task_functions = tasks
        self.essential_names = set(essential)
        self.ended_with = []

    def create_all_tasks(self):
        tasks = []
        for function in self.task_functions:
            task = asyncio.create_task(function())
            if function.__name__ in self.essential_names:
                self.essential(task)
            tasks.append(task)
        return tasks

    def on_comms_ended(self, task):
        self.ended_with.append(task)
        super().on_comms_ended(task)


def started(comms):
    comms.start()
    deadline = time.monotonic() + BOUND
    # A thread whose tasks end at once may have closed its loop before this looks.
    while not comms.ended.is_set() and (comms.event_loop is None or not comms.event_loop.is_running()):
        assert time.monotonic() < deadline, "the event loop never started"
        time.sleep(0.001)
    return comms


def _wait_until(predicate):
    deadline = time.monotonic() + BOUND
    while not predicate():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.001)
    return True


def ended(comms):
    assert comms.ended.wait(BOUND), "the communications did not end"
    comms.join(BOUND)
    assert not comms.is_alive()
    return comms


class TestInit:
    def test_the_thread_is_a_daemon_named_after_the_subclass(self):
        comms = Comms()
        assert comms.daemon
        assert comms.thread_name == "Comms"
        assert comms.name == "AsyncComms-Comms"

    def test_thread_name_and_timeout_can_be_given(self):
        comms = Comms(thread_name="Engine", timeout=3)
        assert comms.name == "AsyncComms-Engine"
        assert comms.timeout == 3

    def test_the_default_timeout_is_in_seconds(self):
        assert Comms().timeout == TIMEOUT == 15

    def test_nothing_runs_until_start(self):
        comms = Comms()
        assert comms.event_loop is None
        assert not comms.stop_requested
        assert not comms.ended.is_set()
        assert comms.end_reason is None


class TestRun:
    def test_the_loop_is_closed_when_the_thread_ends(self):
        comms = started(Comms(forever))
        comms.stop(timeout=BOUND)
        assert comms.event_loop.is_closed()
        assert comms.ended.is_set()

    def test_a_failing_loop_is_recorded_and_the_thread_still_ends(self, caplog, monkeypatch):
        class Failing(asyncio.SelectorEventLoop):
            def run_forever(self):
                raise OSError("selector broke")

        monkeypatch.setattr(asyncio, "new_event_loop", Failing)
        comms = Comms(forever)
        comms.start()
        ended(comms)
        assert isinstance(comms.end_reason, OSError)
        assert comms.event_loop.is_closed()
        assert "event loop failed: OSError: selector broke" in caplog.text

    def test_a_loop_that_will_not_close_is_logged_and_ended_is_still_set(self, caplog, monkeypatch):
        class Unclosable(asyncio.SelectorEventLoop):
            def close(self):
                super().close()
                raise OSError("busy")

        monkeypatch.setattr(asyncio, "new_event_loop", Unclosable)
        comms = started(Comms(forever))
        comms.stop(timeout=BOUND)
        assert comms.ended.is_set()
        assert "could not close its event loop: busy" in caplog.text

    def test_the_loop_is_not_the_thread_s_current_loop(self):
        # D5: run() does not call set_event_loop, as neither original did.
        seen = []

        async def probe():
            seen.append(asyncio.get_running_loop())
            await forever()

        comms = started(Comms(probe))
        deadline = time.monotonic() + BOUND
        while not seen:
            assert time.monotonic() < deadline
            time.sleep(0.001)
        assert seen == [comms.event_loop]
        comms.stop(timeout=BOUND)


class TestStop:
    def test_stop_cancels_the_tasks_and_joins_the_thread(self):
        cancelled = threading.Event()

        async def listener():
            try:
                await forever()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        comms = started(Comms(listener))
        comms.stop(timeout=BOUND)
        assert cancelled.is_set()
        assert not comms.is_alive()
        assert comms.stop_requested

    def test_a_requested_stop_has_no_end_reason_and_no_hook_call(self):
        comms = started(Comms(forever, essential={"forever"}))
        comms.stop(timeout=BOUND)
        assert comms.end_reason is None
        assert comms.ended_with == []

    def test_stop_waits_self_timeout_by_default(self):
        comms = started(Comms(forever, timeout=BOUND))
        comms.stop()
        assert not comms.is_alive()

    def test_stop_before_start_returns(self):
        comms = Comms()
        comms.stop(timeout=BOUND)
        assert comms.stop_requested

    def test_stop_twice_is_harmless(self):
        comms = started(Comms(forever))
        comms.stop(timeout=BOUND)
        comms.stop(timeout=BOUND)
        assert not comms.is_alive()

    def test_stop_after_the_communications_ended_only_joins(self):
        comms = ended(started(Comms(raises)))
        comms.stop(timeout=BOUND)
        assert isinstance(comms.end_reason, ValueError)

    def test_stop_while_the_communications_end_by_themselves_only_joins(self, caplog):
        # nodeconf's fatal path: on_comms_ended signals the process, and the signal handler
        # calls stop() from another thread while this loop is still shutting itself down.
        stopped = []

        class Signalling(Comms):
            def on_comms_ended(self, task):
                stopper = threading.Thread(target=lambda: stopped.append(self.stop(timeout=BOUND)))
                stopper.start()
                time.sleep(0.05)  # let stop() start while this loop is still running

        begin = time.monotonic()
        comms = ended(started(Signalling(raises)))
        deadline = time.monotonic() + BOUND
        while not stopped:
            assert time.monotonic() < deadline, "stop() did not return"
            time.sleep(0.001)
        assert time.monotonic() - begin < 1.0
        assert "Error cancelling tasks" not in caplog.text
        assert isinstance(comms.end_reason, ValueError)

    def test_stop_from_the_comms_thread_raises(self):
        errors = []

        async def stopper():
            try:
                threading.current_thread().stop()
            except RuntimeError as e:
                errors.append(e)
            await forever()

        comms = started(Comms(stopper))
        deadline = time.monotonic() + BOUND
        while not errors:
            assert time.monotonic() < deadline
            time.sleep(0.001)
        assert "cannot stop itself" in str(errors[0])
        comms.stop(timeout=BOUND)

    def test_a_task_that_will_not_cancel_is_logged_and_the_join_is_bounded(self, caplog):
        release = threading.Event()

        async def stubborn():
            while not release.is_set():
                try:
                    await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    continue

        comms = started(Comms(stubborn))
        begin = time.monotonic()
        comms.stop(timeout=0.2)
        assert time.monotonic() - begin < 2
        assert "Error cancelling tasks" in caplog.text
        release.set()
        comms.join(BOUND)


class TestStopAll:
    def test_every_live_instance_is_stopped(self):
        threads = [started(Comms(forever, thread_name=f"t{i}")) for i in range(3)]
        AsyncCommsThread.stop_all(timeout=BOUND)
        assert not any(thread.is_alive() for thread in threads)

    def test_a_failing_stop_is_logged_and_the_others_still_stop(self, caplog, monkeypatch):
        broken = started(Comms(forever, thread_name="broken"))
        healthy = started(Comms(forever, thread_name="healthy"))
        real_stop = AsyncCommsThread.stop

        def stop(self, timeout=None):
            if self is broken:
                raise OSError("no")
            real_stop(self, timeout)

        monkeypatch.setattr(AsyncCommsThread, "stop", stop)
        AsyncCommsThread.stop_all(timeout=BOUND)
        assert not healthy.is_alive()
        assert "Error stopping AsyncComms-broken" in caplog.text
        monkeypatch.undo()
        broken.stop(timeout=BOUND)


class TestCancelTasks:
    def test_it_does_not_stop_the_loop(self):
        comms = started(Comms(forever))
        asyncio.run_coroutine_threadsafe(comms._cancel_tasks(), comms.event_loop).result(BOUND)
        assert comms.event_loop.is_running()
        comms.stop(timeout=BOUND)


class TestStopAsync:
    def test_it_cancels_and_stops_the_loop(self):
        comms = started(Comms(forever))
        asyncio.run_coroutine_threadsafe(comms.stop_async(), comms.event_loop)
        ended(comms)
        assert comms.stop_requested
        assert comms.end_reason is None


class TestEssential:
    def test_it_returns_the_task_it_marks(self):
        marked = []

        class Marking(AsyncCommsThread):
            def create_all_tasks(self):
                task = asyncio.create_task(forever())
                marked.append(self.essential(task) is task)
                return [task]

        comms = started(Marking())
        comms.stop(timeout=BOUND)
        assert marked == [True]


class TestRunAsyncioComms:
    def test_a_task_that_raises_ends_the_communications(self, caplog):
        cancelled = threading.Event()

        async def other():
            try:
                await forever()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        comms = ended(started(Comms(raises, other)))
        assert isinstance(comms.end_reason, ValueError)
        assert cancelled.is_set()
        assert len(comms.ended_with) == 1
        assert comms.ended_with[0].get_coro().__qualname__ == "raises"
        assert "task raises failed with ValueError: boom" in caplog.text

    def test_an_essential_task_that_returns_ends_the_communications(self, caplog):
        comms = ended(started(Comms(returns, forever, essential={"returns"})))
        assert comms.end_reason == "essential task returns ended"
        assert "essential task returns ended" in caplog.text

    def test_a_non_essential_task_that_returns_is_only_logged(self, caplog):
        comms = started(Comms(returns, forever))
        deadline = time.monotonic() + BOUND
        while "task returns finished" not in caplog.text:
            assert time.monotonic() < deadline
            time.sleep(0.001)
        assert comms.is_alive()
        assert comms.end_reason is None
        comms.stop(timeout=BOUND)

    def test_a_task_cancelled_by_another_is_not_reported(self, caplog):
        victim = []

        async def cancels_its_sibling():
            await asyncio.sleep(0)
            victim[0].cancel()
            await forever()

        class Pair(Comms):
            def create_all_tasks(self):
                tasks = super().create_all_tasks()
                victim.append(tasks[1])
                return tasks

        comms = started(Pair(cancels_its_sibling, forever, essential={"forever"}))
        assert _wait_until(lambda: victim and victim[0].done())
        time.sleep(0.02)
        assert comms.is_alive()
        assert comms.end_reason is None
        assert "forever" not in caplog.text
        comms.stop(timeout=BOUND)

    def test_when_every_task_returns_the_loop_keeps_serving_run_coroutine(self):
        comms = started(Comms(returns))

        async def echo(message):
            return message

        assert comms.run_coroutine(echo, {"a": 1}) == {"a": 1}
        assert comms.end_reason is None
        comms.stop(timeout=BOUND)

    def test_a_create_all_tasks_that_raises_ends_the_communications(self, caplog):
        class Broken(Comms):
            def create_all_tasks(self):
                raise KeyError("missing")

        comms = ended(started(Broken()))
        assert isinstance(comms.end_reason, KeyError)
        assert comms.ended_with == [None]
        assert "create_all_tasks failed with KeyError" in caplog.text

    def test_the_base_class_has_no_tasks(self):
        comms = ended(started(AsyncCommsThread()))
        assert isinstance(comms.end_reason, NotImplementedError)

    def test_the_first_failure_is_the_end_reason(self):
        async def also_raises():
            raise OSError("second")

        comms = ended(started(Comms(raises, also_raises)))
        assert isinstance(comms.end_reason, (ValueError, OSError))
        assert len(comms.ended_with) == 1


class TestOnCommsEnded:
    def test_the_default_logs_the_reason(self, caplog):
        class Plain(AsyncCommsThread):
            def create_all_tasks(self):
                return [asyncio.create_task(raises())]

        ended(started(Plain()))
        assert "AsyncComms-Plain communications ended: boom" in caplog.text

    def test_it_runs_on_the_comms_thread(self):
        seen = []

        class Hooked(Comms):
            def on_comms_ended(self, task):
                seen.append(threading.current_thread())

        comms = ended(started(Hooked(raises)))
        assert seen == [comms]

    def test_an_exception_inside_it_is_logged_and_the_loop_still_stops(self, caplog):
        class Hooked(Comms):
            def on_comms_ended(self, task):
                raise RuntimeError("hook failed")

        comms = ended(started(Hooked(raises)))
        assert comms.event_loop.is_closed()
        assert "on_comms_ended raised RuntimeError: hook failed" in caplog.text


class TestRunCoroutine:
    @pytest.fixture
    def comms(self):
        comms = started(Comms(forever))
        yield comms
        comms.stop(timeout=BOUND)

    def test_it_returns_the_coroutine_s_result(self, comms):
        async def answer(message):
            return {"echo": message, "loop": asyncio.get_running_loop()}

        result = comms.run_coroutine(answer, {"x": 1})
        assert result["echo"] == {"x": 1}
        assert result["loop"] is comms.event_loop

    def test_an_exception_is_re_raised(self, comms):
        async def fails(message):
            raise LookupError(message["why"])

        with pytest.raises(LookupError, match="because"):
            comms.run_coroutine(fails, {"why": "because"})

    def test_a_timeout_raises_and_cancels_the_coroutine(self, comms):
        cancelled = threading.Event()

        async def slow(message):
            try:
                await forever()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        with pytest.raises(TimeoutError):
            comms.run_coroutine(slow, {}, timeout=0.05)
        assert cancelled.wait(BOUND)

    def test_minus_one_means_no_timeout(self, comms):
        async def takes_a_moment(message):
            await asyncio.sleep(0.05)
            return "ok"

        comms.timeout = 0.001
        assert comms.run_coroutine(takes_a_moment, {}, timeout=-1) == "ok"

    def test_a_plain_function_is_refused(self, comms):
        with pytest.raises(TypeError, match="not a coroutine function"):
            comms.run_coroutine(lambda message: None, {})

    def test_before_start_it_raises_attribute_error(self):
        async def anything(message):
            return None

        with pytest.raises(AttributeError, match="not initialized"):
            Comms().run_coroutine(anything, {})

    def test_after_the_communications_ended_it_names_the_reason(self):
        comms = ended(started(Comms(raises)))

        async def anything(message):
            return None

        with pytest.raises(RuntimeError, match="communications have ended: boom"):
            comms.run_coroutine(anything, {})

    def test_after_a_stop_it_says_stopped(self):
        comms = started(Comms(forever))
        comms.stop(timeout=BOUND)

        async def anything(message):
            return None

        with pytest.raises(RuntimeError, match="communications have ended: stopped"):
            comms.run_coroutine(anything, {})

    def test_it_goes_through_asyncio_run_coroutine_threadsafe_by_module_attribute(self, comms, monkeypatch):
        # Consumer suites patch asyncio.run_coroutine_threadsafe (plan §9); that must keep applying.
        calls = []
        real = asyncio.run_coroutine_threadsafe

        def spy(coro, loop):
            calls.append(loop)
            return real(coro, loop)

        monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", spy)

        async def anything(message):
            return 1

        assert comms.run_coroutine(anything, {}) == 1
        assert calls == [comms.event_loop]
