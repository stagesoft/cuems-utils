import logging
import pytest
import signal
from unittest.mock import patch

from cuemsutils.tools.SignalEngine import SignalEngine

@pytest.fixture
def daemon(with_signals: bool = True):
    return SignalEngine(with_signals=with_signals)

@pytest.fixture
def mock_signal():
    with patch('signal.signal') as mock_signal_obj:
        yield mock_signal_obj

def test_daemon_run_stops_after_signal(daemon, caplog):
    caplog.set_level(logging.DEBUG)

    # Run with a max cycle count to avoid infinite loop
    engine = daemon
    engine.running = True
    engine.run(tick=0.1, max_tick=0.5)

    assert "Call recieved" in caplog.text
    assert "kwargs: {'tick': 0.1, 'max_tick': 0.5}" in caplog.text
    assert "Finished with result: None" in caplog.text

def test_signal_handlers_are_registered(daemon, mock_signal):
    # Register the signal handlers
    daemon.register_signals()

    # Ensure signal.signal was called with correct arguments
    mock_signal.assert_any_call(signal.SIGTERM, daemon.handle_terminate)
    mock_signal.assert_any_call(signal.SIGINT, daemon.handle_interrupt)
    assert mock_signal.call_count == 5

def test_engine_can_start_and_stop():
    from time import sleep
    engine = SignalEngine(with_signals=False)
    sleep(0.05)
    engine.stop()
    assert engine.running == False

def test_signal_handling_graceful_exit(daemon):
    from multiprocessing import Process
    from time import sleep
    from os import kill

    proc = Process(target=daemon.start)
    proc.start()

    # Give it a moment to start
    sleep(0.05)

    # Send SIGTERM to the child process
    kill(proc.pid, signal.SIGTERM)  # type: ignore[attr-union]

    # Wait for the process to cleanly exit
    proc.join(timeout=1)

    assert proc.exitcode == 0 or proc.exitcode is None  # None means graceful stop
