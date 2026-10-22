"""Unit counterpart of ``cuemsutils.tools.SignalEngine``: one class per section of the source.

Handlers are called directly, and every handler a test installs is restored afterwards. Before this
file restored them, the engine's ``handle_interrupt`` replaced pytest's own SIGINT handler for the
rest of the session. Real signals delivered to a real process are in
``tests/integration/test_signalengine.py``.
"""
import builtins
import logging
import signal
from unittest.mock import Mock, patch

import pytest

from cuemsutils.tools import SignalEngine as signal_engine_module
from cuemsutils.tools.SignalEngine import SignalEngine
from tests.support import cuems_logs

HANDLED = {
    signal.SIGINT: "handle_interrupt",
    signal.SIGTERM: "handle_terminate",
    signal.SIGUSR1: "handle_print_running",
    signal.SIGUSR2: "handle_print_all",
    signal.SIGCHLD: "handle_child_signal",
}

@pytest.fixture(autouse=True)
def cuems_debug_logs(caplog):
    """Assertions on log text must not depend on CUEMS_LOG_LEVEL."""
    cuems_logs.capture(caplog, signal_engine_module.__name__)


@pytest.fixture(autouse=True)
def restore_signal_handlers():
    saved = {signum: signal.getsignal(signum) for signum in HANDLED}
    yield
    for signum, handler in saved.items():
        signal.signal(signum, handler)


@pytest.fixture
def engine():
    return SignalEngine(with_signals=False)


@pytest.fixture
def no_sleep():
    with patch.object(signal_engine_module, "sleep") as fake:
        yield fake


# --- __init__ ----------------------------------------------------------------------------

class TestInit:
    def test_records_its_own_pid(self, engine):
        import os
        assert engine.pid == os.getpid()

    def test_starts_not_running(self, engine):
        assert engine.running is False

    def test_registers_the_signal_handlers_by_default(self):
        engine = SignalEngine()
        for signum, name in HANDLED.items():
            assert signal.getsignal(signum) == getattr(engine, name), signal.Signals(signum).name

    def test_with_signals_false_leaves_the_handlers_alone(self):
        before = {signum: signal.getsignal(signum) for signum in HANDLED}
        SignalEngine(with_signals=False)
        assert {signum: signal.getsignal(signum) for signum in HANDLED} == before

    def test_logs_its_class_and_pid(self, caplog):
        caplog.set_level(logging.INFO)
        engine = SignalEngine(with_signals=False)
        assert f"Starting SignalEngine with PID {engine.pid}" in caplog.text


# --- start / run / stop / restart / reload ---------------------------------------------------

class TestStart:
    def test_sets_running_and_enters_run(self, engine):
        with patch.object(engine, "run") as run:
            engine.start()
        assert engine.running is True
        run.assert_called_once_with()


class TestRun:
    def test_returns_at_once_when_not_running(self, engine, no_sleep):
        engine.run()
        no_sleep.assert_not_called()

    def test_sleeps_one_tick_per_loop_until_stopped(self, engine, no_sleep):
        calls = []

        def tick(seconds):
            calls.append(seconds)
            if len(calls) == 3:
                engine.running = False

        no_sleep.side_effect = tick
        engine.running = True
        engine.run(tick=0.5)
        assert calls == [0.5, 0.5, 0.5]

    def test_max_tick_grows_the_tick_by_a_hundredth_and_then_stops(self, engine, no_sleep):
        engine.running = True
        engine.run(tick=0.1, max_tick=0.13)
        slept = [round(call.args[0], 2) for call in no_sleep.call_args_list]
        assert slept == [0.1, 0.11, 0.12, 0.13]
        assert engine.running is False

    def test_max_tick_below_tick_stops_after_one_tick(self, engine, no_sleep):
        engine.running = True
        engine.run(tick=1, max_tick=0.5)
        assert no_sleep.call_count == 1
        assert engine.running is False

    def test_is_logged_with_its_arguments_and_result(self, engine, no_sleep, caplog):
        caplog.set_level(logging.DEBUG)
        engine.running = True
        engine.run(tick=0.1, max_tick=0.1)
        assert "kwargs: {'tick': 0.1, 'max_tick': 0.1}" in caplog.text
        assert "Finished with result: None" in caplog.text


class TestStop:
    def test_clears_running_and_records_the_request(self, engine):
        engine.running = True
        engine.stop()
        assert engine.running is False
        assert engine.stop_requested is True

    def test_calls_a_subclass_stop_all_hook(self, engine):
        engine.stop_all = Mock()
        engine.stop()
        engine.stop_all.assert_called_once_with()

    def test_a_failing_stop_all_is_logged_and_still_stops(self, engine, caplog):
        engine.stop_all = Mock(side_effect=RuntimeError("player stuck"))
        engine.running = True
        engine.stop()
        assert engine.running is False
        assert "Exception when calling stop_all" in caplog.text

    def test_without_a_hook_just_stops(self, engine):
        assert not hasattr(engine, "stop_all")
        engine.stop()
        assert engine.running is False


class TestRestartAndReload:
    """Placeholders today: a subclass overrides them. Pinned so a change is deliberate."""

    def test_restart_does_nothing(self, engine):
        engine.running = True
        assert engine.restart() is None
        assert engine.running is True

    def test_reload_does_nothing(self, engine):
        engine.running = True
        assert engine.reload() is None
        assert engine.running is True


# --- notify_systemd ------------------------------------------------------------------------

class TestNotifySystemd:
    def test_sends_ready_by_default(self, engine):
        with patch.object(signal_engine_module, "notify_systemd_daemon") as notify:
            engine.notify_systemd()
        notify.assert_called_once_with("READY=1")

    def test_upper_cases_the_status(self, engine):
        with patch.object(signal_engine_module, "notify_systemd_daemon") as notify:
            engine.notify_systemd("stopping")
        notify.assert_called_once_with("STOPPING=1")


# --- register_signals --------------------------------------------------------------------

class TestRegisterSignals:
    def test_installs_one_handler_per_signal(self, engine):
        with patch("signal.signal") as install:
            engine.register_signals()
        assert {call.args[0]: call.args[1] for call in install.call_args_list} == {
            signum: getattr(engine, name) for signum, name in HANDLED.items()
        }
        assert install.call_count == len(HANDLED)


# --- handle_interrupt / handle_terminate ------------------------------------------------------

@pytest.mark.parametrize("handler, label", [("handle_interrupt", "SIGINT"), ("handle_terminate", "SIGTERM")])
class TestExitHandlers:
    def test_stops_then_exits_with_status_0(self, engine, no_sleep, handler, label):
        engine.running = True
        with pytest.raises(SystemExit) as exited:
            getattr(engine, handler)(signal.Signals[label].value, None)
        assert engine.running is False
        assert exited.value.code in (None, 0)

    def test_runs_the_stop_all_hook_before_exiting(self, engine, no_sleep, handler, label):
        engine.stop_all = Mock()
        with pytest.raises(SystemExit):
            getattr(engine, handler)(signal.Signals[label].value, None)
        engine.stop_all.assert_called_once_with()

    def test_announces_the_signal(self, engine, no_sleep, capsys, caplog, handler, label):
        caplog.set_level(logging.INFO)
        with pytest.raises(SystemExit):
            getattr(engine, handler)(signal.Signals[label].value, None)
        assert f"{label} received!" in capsys.readouterr().out
        assert f"{label} received!" in caplog.text

    @pytest.mark.xfail(strict=True, reason=(
        "defect: the handlers call the site builtin exit(), which an interpreter without the site "
        "module (python -S, frozen or embedded builds) does not define. sys.exit() is the API."
    ))
    def test_exits_through_sys_exit_not_the_site_builtin(self, engine, no_sleep, monkeypatch, handler, label):
        monkeypatch.delattr(builtins, "exit")
        with pytest.raises(SystemExit):
            getattr(engine, handler)(signal.Signals[label].value, None)


# --- handle_print_all / handle_print_running / handle_child_signal ----------------------------

class TestHandlePrintAll:
    def test_calls_a_subclass_print_all_status_hook(self, engine):
        engine.print_all_status = Mock()
        engine.handle_print_all(signal.SIGUSR2, None)
        engine.print_all_status.assert_called_once_with()

    def test_without_a_hook_only_logs(self, engine, caplog):
        caplog.set_level(logging.INFO)
        engine.handle_print_all(signal.SIGUSR2, None)
        assert "STATUS REQUEST BY SIGUSR2" in caplog.text


class TestHandlePrintRunning:
    def test_reports_running(self, engine, capsys):
        engine.running = True
        engine.handle_print_running(signal.SIGUSR1, None)
        assert "SignalEngine is running" in capsys.readouterr().out

    def test_reports_not_running(self, engine, capsys):
        engine.handle_print_running(signal.SIGUSR1, None)
        assert "SignalEngine is NOT running" in capsys.readouterr().out

    def test_does_not_change_state(self, engine):
        engine.running = True
        engine.handle_print_running(signal.SIGUSR1, None)
        assert engine.running is True


class TestHandleChildSignal:
    def test_is_a_no_op(self, engine):
        engine.running = True
        assert engine.handle_child_signal(signal.SIGCHLD, None) is None
        assert engine.running is True
