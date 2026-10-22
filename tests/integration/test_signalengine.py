"""Integration counterpart of ``cuemsutils.tools.SignalEngine``: real signals, real systemd notify.

A child process runs an engine subclass with the ``stop_all`` and ``print_all_status`` hooks a
CUEMS service provides. Each hook writes a marker file, so the test sees what ran. The systemd half
binds a real ``NOTIFY_SOCKET`` datagram socket and reads what ``sd_notify`` sent, which is what
systemd itself receives.
"""
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time

import pytest

from cuemsutils.tools.SignalEngine import SignalEngine

CHILD = """
import os, sys
from pathlib import Path
from cuemsutils.tools.SignalEngine import SignalEngine

out = Path(sys.argv[1])

class Service(SignalEngine):
    def stop_all(self):
        (out / "stop_all").write_text("called")

    def print_all_status(self):
        (out / "status").write_text("called")

engine = Service()
engine.running = True
(out / "ready").write_text(str(os.getpid()))
engine.run(tick=0.02)
(out / "run_returned").write_text("yes")
"""


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def service(tmp_path):
    script = tmp_path / "service.py"
    script.write_text(CHILD)
    proc = subprocess.Popen(
        [sys.executable, "-u", str(script), str(tmp_path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env={**os.environ, "CUEMS_LOG_LEVEL": "WARNING"},
    )
    assert _wait_for(lambda: (tmp_path / "ready").exists()), "the service never became ready"
    yield proc, tmp_path
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=5)


# --- the exit handlers, through the kernel ---------------------------------------------------

@pytest.mark.parametrize("signum, label", [(signal.SIGTERM, "SIGTERM"), (signal.SIGINT, "SIGINT")])
class TestExitSignals:
    def test_the_process_exits_with_status_0(self, service, signum, label):
        proc, _ = service
        proc.send_signal(signum)
        assert proc.wait(timeout=5) == 0

    def test_stop_all_runs_before_the_process_exits(self, service, signum, label):
        proc, out = service
        proc.send_signal(signum)
        proc.wait(timeout=5)
        assert (out / "stop_all").read_text() == "called"

    def test_the_run_loop_does_not_resume(self, service, signum, label):
        proc, out = service
        proc.send_signal(signum)
        proc.wait(timeout=5)
        assert not (out / "run_returned").exists()

    def test_the_signal_is_announced_on_stdout(self, service, signum, label):
        proc, _ = service
        proc.send_signal(signum)
        proc.wait(timeout=5)
        assert f"{label} received!" in proc.stdout.read()


# --- the status handlers, through the kernel -------------------------------------------------

class TestStatusSignals:
    def test_sigusr1_reports_running_and_the_service_keeps_running(self, service):
        proc, _ = service
        proc.send_signal(signal.SIGUSR1)
        time.sleep(0.2)
        assert proc.poll() is None
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
        assert "Service is running" in proc.stdout.read()

    def test_sigusr2_calls_print_all_status_and_the_service_keeps_running(self, service):
        proc, out = service
        proc.send_signal(signal.SIGUSR2)
        assert _wait_for(lambda: (out / "status").exists())
        assert proc.poll() is None

    def test_sigchld_is_ignored(self, service):
        proc, out = service
        proc.send_signal(signal.SIGCHLD)
        time.sleep(0.2)
        assert proc.poll() is None
        assert not (out / "stop_all").exists()


# --- notify_systemd, through a real NOTIFY_SOCKET ----------------------------------------------

@pytest.fixture
def notify_socket(monkeypatch):
    # sun_path is limited to 108 bytes, which a deep tmp_path can exceed.
    directory = tempfile.mkdtemp(prefix="sd-")
    path = os.path.join(directory, "notify")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(path)
    sock.settimeout(2)
    monkeypatch.setenv("NOTIFY_SOCKET", path)
    yield sock
    sock.close()
    os.unlink(path)
    os.rmdir(directory)


class TestNotifySystemd:
    def test_systemd_receives_ready(self, notify_socket):
        SignalEngine(with_signals=False).notify_systemd()
        assert notify_socket.recv(256) == b"READY=1"

    def test_systemd_receives_the_given_status_upper_cased(self, notify_socket):
        SignalEngine(with_signals=False).notify_systemd("stopping")
        assert notify_socket.recv(256) == b"STOPPING=1"

    def test_without_notify_socket_it_is_a_silent_no_op(self, monkeypatch):
        monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
        SignalEngine(with_signals=False).notify_systemd()  # must not raise outside systemd
