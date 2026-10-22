"""Integration counterpart of ``cuemsutils.tools.AsyncCommsThread``: real NNG sockets on the thread.

The two shapes the CUEMS services run are both here. ``Responder`` is cuems-nodeconf's: one
``Communicator`` answering requests over IPC, stopped while it waits in a receive. ``Bus`` is
cuems-engine's: an ``NngBusHub`` as an essential task, whose socket closing must end the
communications instead of leaving the thread running with no bus (H1). The last class runs the thread
in a child process and checks it exits cleanly, which is ClickUp 869ed00ya: a comms thread still
inside NNG when pynng's atexit hook finalizes NNG aborts the process with exit status 134. The
behaviour of each method in isolation is in ``tests/unit/test_asynccommsthread.py``.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time

import pynng
import pytest

from cuemsutils.tools.AsyncCommsThread import AsyncCommsThread
from cuemsutils.tools.CommunicatorServices import Communicator
from cuemsutils.tools.HubServices import NngBusHub

BOUND = 5.0  # seconds
ROUNDS = 200  # start/stop rounds against a live receive; C6's lost callback was about 1 in 1000


@pytest.fixture(autouse=True)
def no_thread_left_behind():
    yield
    AsyncCommsThread.stop_all(timeout=BOUND)


@pytest.fixture
def ipc_dir():
    # sun_path is limited to 108 bytes, which a deep tmp_path can exceed.
    directory = tempfile.mkdtemp(prefix="cuems-act-")
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def _wait_for(predicate, timeout=BOUND):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.002)
    return False


class Responder(AsyncCommsThread):
    """cuems-nodeconf's shape: one essential listener answering with ``reply``."""

    def __init__(self, path):
        super().__init__(thread_name="Responder")
        self.path = path
        self.communicator = Communicator(path)
        self.ended_with = []

    def create_all_tasks(self):
        return [self.essential(asyncio.create_task(self.listener()))]

    async def listener(self):
        await self.communicator.responder_connect()
        try:
            while not self.stop_requested:
                await self.communicator.responder_get_request(self.callback)
        finally:
            self.communicator.communicator_service.responder.close()

    async def callback(self, request, context):
        await self.communicator.responder_post_reply({"echo": request}, context)

    def on_comms_ended(self, task):
        self.ended_with.append(task)


def ask(path, request):
    with pynng.Req0(dial=f"ipc://{path}", send_timeout=1000, recv_timeout=1000) as sock:
        sock.send(json.dumps(request).encode())
        return json.loads(sock.recv().decode())


class TestResponder:
    def test_requests_are_answered_and_stop_joins_the_thread(self, ipc_dir):
        path = f"{ipc_dir}/svc.ipc"
        comms = Responder(path)
        comms.start()
        assert _wait_for(lambda: os.path.exists(path))
        assert ask(path, {"n": 1}) == {"echo": {"n": 1}}
        comms.stop(timeout=BOUND)
        assert not comms.is_alive()
        assert comms.end_reason is None
        assert comms.ended_with == []

    def test_a_reply_can_be_sent_from_another_thread_through_run_coroutine(self, ipc_dir):
        # cuems-nodeconf answers from its own threads with respond_to_engine on the comms loop.
        path = f"{ipc_dir}/svc.ipc"

        class Deferred(Responder):
            contexts: list = []

            async def callback(self, request, context):
                self.contexts.append((request, context))

        comms = Deferred(path)
        comms.start()
        assert _wait_for(lambda: os.path.exists(path))
        results = []
        asker = threading.Thread(target=lambda: results.append(ask(path, {"n": 2})))
        asker.start()
        assert _wait_for(lambda: Deferred.contexts)
        request, context = Deferred.contexts.pop()

        async def post(message):
            await comms.communicator.responder_post_reply({"later": message}, context)

        comms.run_coroutine(post, request)
        asker.join(BOUND)
        assert results == [{"later": {"n": 2}}]
        comms.stop(timeout=BOUND)

    def test_stop_during_a_pending_receive_is_prompt_every_time(self, ipc_dir):
        slowest = 0.0
        for i in range(ROUNDS):
            path = f"{ipc_dir}/r{i}.ipc"
            comms = Responder(path)
            comms.start()
            assert _wait_for(lambda: os.path.exists(path)), f"round {i}: no socket"
            begin = time.monotonic()
            comms.stop(timeout=BOUND)
            slowest = max(slowest, time.monotonic() - begin)
            assert not comms.is_alive(), f"round {i}: the thread did not stop"
        assert slowest < 1.0, f"the slowest of {ROUNDS} stops took {slowest:.3f} s"


class Bus(AsyncCommsThread):
    """cuems-engine's shape: the hub essential, a receiver that may return early not."""

    def __init__(self, address, mode):
        super().__init__(thread_name=f"Bus-{mode.name}")
        self.hub = NngBusHub(address, mode)
        self.ended_with = []

    def create_all_tasks(self):
        return [self.essential(asyncio.create_task(self.hub.start()))]

    def on_comms_ended(self, task):
        self.ended_with.append(task)


class TestBus:
    def test_a_closed_bus_socket_ends_the_communications(self, ipc_dir):
        comms = Bus(f"ipc://{ipc_dir}/bus.ipc", NngBusHub.Mode.LISTENER)
        comms.start()
        assert _wait_for(lambda: comms.hub.connection is not None)
        comms.hub.connection.close()
        assert comms.ended.wait(BOUND), "a closed bus left the thread running (H1)"
        comms.join(BOUND)
        assert not comms.is_alive()
        assert comms.end_reason == "essential task NngBusHub.start ended"
        assert [task.get_coro().__qualname__ for task in comms.ended_with] == ["NngBusHub.start"]

    def test_listener_and_dialer_exchange_a_message_through_run_coroutine(self, ipc_dir):
        address = f"ipc://{ipc_dir}/bus.ipc"
        listener = Bus(address, NngBusHub.Mode.LISTENER)
        listener.start()
        assert _wait_for(lambda: listener.hub.connection is not None)
        dialer = Bus(address, NngBusHub.Mode.DIALER)
        dialer.start()
        assert _wait_for(lambda: listener.hub.get_connection_count() == 1)
        time.sleep(0.02)  # SETTLE: the first BUS message on a new link can be dropped (H6)

        dialer.run_coroutine(dialer.hub.send_message, {"hello": "controller"})

        async def receive(_):
            return await asyncio.wait_for(listener.hub.get_message(), BOUND)

        message = listener.run_coroutine(receive, {})
        assert message.data == {"hello": "controller"}
        dialer.stop(timeout=BOUND)
        listener.stop(timeout=BOUND)
        assert listener.end_reason is None and dialer.end_reason is None


CHILD = textwrap.dedent("""
    import asyncio, os, sys
    from cuemsutils.tools.AsyncCommsThread import AsyncCommsThread
    from cuemsutils.tools.CommunicatorServices import Communicator

    path = sys.argv[1]

    class Responder(AsyncCommsThread):
        def create_all_tasks(self):
            return [self.essential(asyncio.create_task(self.listener()))]

        async def listener(self):
            communicator = Communicator(path)
            await communicator.responder_connect()
            while not self.stop_requested:
                await communicator.responder_get_request(lambda request, context: None)

    comms = Responder()
    comms.start()
    while not os.path.exists(path):
        pass
    comms.stop(timeout=5)
    print("stopped", comms.is_alive())
""")


class TestProcessExit:
    def test_a_stopped_comms_thread_lets_the_process_exit_cleanly(self, ipc_dir, tmp_path):
        script = tmp_path / "child.py"
        script.write_text(CHILD)
        for i in range(10):
            proc = subprocess.run(
                [sys.executable, str(script), f"{ipc_dir}/c{i}.ipc"],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "CUEMS_LOG_LEVEL": "WARNING"},
            )
            assert proc.returncode == 0, f"run {i}: exit {proc.returncode}\n{proc.stderr}"
            assert "stopped False" in proc.stdout
