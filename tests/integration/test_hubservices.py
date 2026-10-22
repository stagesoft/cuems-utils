"""Integration counterpart of ``cuemsutils.tools.HubServices``: real NNG buses over TCP and IPC.

This is the controller/node topology the cluster runs: one LISTENER (the controller) and DIALERs
(the nodes). Every wait is bounded, so a lost message shows up as a failure, not a stuck suite. The
behaviour of each method in isolation is in ``tests/unit/test_hubservices.py``.
"""
import asyncio
import shutil
import socket
import tempfile
import time
from contextlib import asynccontextmanager

import pytest
from pynng import Bus0

from cuemsutils.tools.HubServices import NngBusHub

BOUND = 2.0  # seconds; a local round trip takes milliseconds
# NNG grows a dialer's retry delay after every failed dial, up to start_dialer's
# reconnect_time_max (30 s), and several dials can fail before the controller exists. Measured
# 2026-10-22 on an idle box: 0.4-8.5 s over 15 runs, so a 10 s bound flaked. Only the configured
# maximum is a bound that cannot flake. A normal run takes 1-2 s; only a real failure waits it out.
RECONNECT = 30.0 + 5.0


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def tcp():
    return f"tcp://127.0.0.1:{free_port()}"


@pytest.fixture
def ipc():
    directory = tempfile.mkdtemp(prefix="cuems-bus-")  # sun_path is limited to 108 bytes
    yield f"ipc://{directory}/bus.ipc"
    shutil.rmtree(directory, ignore_errors=True)


def run(coro):
    return asyncio.run(asyncio.wait_for(coro, timeout=60))


async def until(predicate, timeout=BOUND, interval=0.01):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return False


class Running:
    """Hubs whose start() runs in a task, stopped by cancelling it."""

    def __init__(self):
        self.tasks: dict[NngBusHub, asyncio.Task] = {}

    def start(self, hub):
        self.tasks[hub] = asyncio.create_task(hub.start())
        return hub

    async def stop(self, hub):
        task = self.tasks.pop(hub)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def stop_all(self):
        for hub in list(self.tasks):
            await self.stop(hub)


@asynccontextmanager
async def running():
    hubs = Running()
    try:
        yield hubs
    finally:
        await hubs.stop_all()


#: NNG's BUS is best-effort, and a message sent the instant a connection is up can be dropped (H6):
#: measured 2026-10-22, 3 lost in 12000 when sent as soon as both sides reported the connection,
#: 0 in 12000 after 20 ms. Tests that assert exact deliveries let a new connection settle first.
SETTLE = 0.02


async def connected(address, nodes=1, configure=None, settle=SETTLE):
    """A started listener and ``nodes`` started dialers, once the listener sees them all.
    ``configure(listener)`` runs before the listener starts. ``settle`` seconds then pass before
    returning (see SETTLE). A test that does not depend on delivery passes 0."""
    hubs = Running()
    listener = NngBusHub(address, NngBusHub.Mode.LISTENER)
    if configure:
        configure(listener)
    hubs.start(listener)
    # start_listener() creates the socket and listens with no await in between, so once the
    # connection exists the address is bound. No fixed sleep: it was 50 of the H5 test's 64 s.
    assert await until(lambda: listener.connection is not None, interval=0.001), "the controller never listened"
    dialers = [hubs.start(NngBusHub(address, NngBusHub.Mode.DIALER)) for _ in range(nodes)]
    assert await until(lambda: listener.get_connection_count() == nodes, interval=0.001), \
        "the nodes never connected"
    if settle:
        await asyncio.sleep(settle)
    return hubs, listener, dialers


async def next_message(hub, timeout=BOUND):
    return await asyncio.wait_for(hub.get_message(), timeout)


async def nothing_arrives(hub, within=0.3):
    try:
        await asyncio.wait_for(hub.get_message(), within)
    except asyncio.TimeoutError:
        return True
    return False


# --- send_message / get_message across the bus -------------------------------------------------

class TestBusRoundTrip:
    def test_a_node_message_reaches_the_controller_with_the_node_tcp_address(self, tcp):
        async def scenario():
            hubs, listener, (node,) = await connected(tcp)
            try:
                await node.send_message({"cue": "go"})
                return await next_message(listener)
            finally:
                await hubs.stop_all()

        message = run(scenario())
        assert message.data == {"cue": "go"}
        ip, port = message.sender
        assert ip == "127.0.0.1" and isinstance(port, int) and port > 0

    def test_a_controller_message_reaches_the_node(self, tcp):
        async def scenario():
            hubs, listener, (node,) = await connected(tcp)
            try:
                await listener.send_message({"load": "show"})
                return await next_message(node)
            finally:
                await hubs.stop_all()

        assert run(scenario()).data == {"load": "show"}

    def test_a_controller_message_reaches_every_node(self, tcp):
        async def scenario():
            hubs, listener, nodes = await connected(tcp, nodes=3)
            try:
                await listener.send_message({"all": 1})
                return [await next_message(node) for node in nodes]
            finally:
                await hubs.stop_all()

        assert [m.data for m in run(scenario())] == [{"all": 1}] * 3

    def test_the_bus_does_not_relay_one_node_to_another(self, tcp):
        """NNG BUS delivers to direct peers only: nodes talk to the controller, not each other."""
        async def scenario():
            hubs, listener, (a, b) = await connected(tcp, nodes=2)
            try:
                await a.send_message({"from": "a"})
                await next_message(listener)
                return await nothing_arrives(b)
            finally:
                await hubs.stop_all()

        assert run(scenario()) is True

    def test_messages_keep_their_order(self, tcp):
        async def scenario():
            hubs, listener, (node,) = await connected(tcp)
            try:
                for i in range(20):
                    await node.send_message({"i": i})
                return [(await next_message(listener)).data["i"] for _ in range(20)]
            finally:
                await hubs.stop_all()

        assert run(scenario()) == list(range(20))

    def test_ipc_works_the_same_and_the_sender_is_the_socket_url(self, ipc):
        async def scenario():
            hubs, listener, (node,) = await connected(ipc)
            try:
                await node.send_message({"over": "ipc"})
                return await next_message(listener)
            finally:
                await hubs.stop_all()

        message = run(scenario())
        assert message.data == {"over": "ipc"}
        assert message.sender == ipc


# --- the pipe callbacks, through real connections --------------------------------------------------

class TestConnectionTracking:
    def test_the_controller_counts_nodes_coming_and_going(self, tcp):
        async def scenario():
            hubs, listener, (a, b) = await connected(tcp, nodes=2)
            try:
                counts = [listener.get_connection_count()]
                await hubs.stop(a)
                await until(lambda: listener.get_connection_count() == 1)
                counts.append(listener.get_connection_count())
                return counts
            finally:
                await hubs.stop_all()

        assert run(scenario()) == [2, 1]


# --- ping / pong across the bus ------------------------------------------------------------------

class TestPingPongOverTheWire:
    def test_a_node_answers_the_controller_ping_and_neither_user_queue_sees_it(self, tcp):
        async def scenario():
            hubs, listener, (node,) = await connected(tcp)
            try:
                await listener.send_ping()
                await until(lambda: listener._messages_received_count >= 1)
                return (node._pong_count, listener._messages_received_count,
                        listener.incoming.qsize(), node.incoming.qsize())
            finally:
                await hubs.stop_all()

        assert run(scenario()) == (1, 1, 0, 0)

    def test_auto_ping_enabled_on_a_running_controller_starts_at_once(self, tcp):
        """H4 over the wire: enabling after start() no longer waits out the default 10 s interval."""
        async def scenario():
            hubs, listener, (node,) = await connected(tcp)
            try:
                listener.enable_auto_ping(interval=0.05, inactivity_threshold=0.0)
                return await until(lambda: node._pong_count >= 2, timeout=BOUND)
            finally:
                await hubs.stop_all()

        assert run(scenario()) is True

    def test_a_node_with_auto_pong_disabled_stays_silent(self, tcp):
        async def scenario():
            hubs, listener, (node,) = await connected(tcp)
            node.disable_auto_pong()
            try:
                await listener.send_ping()
                await until(lambda: node._messages_received_count >= 1)
                await asyncio.sleep(0.2)
                return node._pong_count, listener._messages_received_count
            finally:
                await hubs.stop_all()

        assert run(scenario()) == (0, 0)

    def test_auto_ping_keeps_an_idle_link_alive_and_healthy(self, tcp):
        async def scenario():
            # Before start(): the handler's first sleep uses the interval set at that moment.
            hubs, listener, (node,) = await connected(
                tcp, configure=lambda hub: hub.enable_auto_ping(interval=0.05, inactivity_threshold=0.0))
            try:
                await until(lambda: node._pong_count >= 2)
                return node._pong_count, listener.is_connection_healthy(), node.is_connection_healthy()
            finally:
                await hubs.stop_all()

        pongs, controller_healthy, node_healthy = run(scenario())
        assert pongs >= 2 and controller_healthy and node_healthy


# --- _send_handler's wait, start_dialer's reconnection ------------------------------------------

class TestDeliveryAcrossStartupOrder:
    def test_a_controller_message_queued_before_any_node_is_delivered_once_one_connects(self, tcp):
        async def scenario():
            async with running() as hubs:
                listener = hubs.start(NngBusHub(tcp, NngBusHub.Mode.LISTENER))
                await listener.send_message({"early": 1})
                await asyncio.sleep(0.3)
                node = hubs.start(NngBusHub(tcp, NngBusHub.Mode.DIALER))
                return await next_message(node)

        assert run(scenario()).data == {"early": 1}

    def test_a_node_started_before_the_controller_connects_when_it_appears(self, tcp):
        async def scenario():
            async with running() as hubs:
                node = hubs.start(NngBusHub(tcp, NngBusHub.Mode.DIALER))
                await asyncio.sleep(0.2)
                listener = hubs.start(NngBusHub(tcp, NngBusHub.Mode.LISTENER))
                assert await until(lambda: listener.get_connection_count() == 1, RECONNECT)
                await node.send_message({"hello": "late controller"})
                return await next_message(listener)

        assert run(scenario()).data == {"hello": "late controller"}

    def test_a_node_reconnects_after_the_controller_restarts(self, tcp):
        async def scenario():
            async with running() as hubs:
                first = hubs.start(NngBusHub(tcp, NngBusHub.Mode.LISTENER))
                node = hubs.start(NngBusHub(tcp, NngBusHub.Mode.DIALER))
                assert await until(lambda: first.get_connection_count() == 1)
                await hubs.stop(first)
                second = hubs.start(NngBusHub(tcp, NngBusHub.Mode.LISTENER))
                assert await until(lambda: second.get_connection_count() == 1, RECONNECT)
                await second.send_message({"after": "restart"})
                return await next_message(node)

        assert run(scenario()).data == {"after": "restart"}


# --- start()'s teardown -----------------------------------------------------------------------

class TestLifecycle:
    def test_stopping_the_controller_releases_its_address(self, tcp):
        async def scenario():
            async with running() as hubs:
                first = hubs.start(NngBusHub(tcp, NngBusHub.Mode.LISTENER))
                await asyncio.sleep(0.1)
                await hubs.stop(first)
                assert first.connection is None and first._closing is True
                with Bus0(listen=tcp):  # raises AddressInUse if the socket was not closed
                    return True

        assert run(scenario()) is True

    def test_start_returns_when_its_socket_is_closed(self, tcp):
        async def scenario():
            hubs, listener, _ = await connected(tcp)
            try:
                listener.connection.close()
                await asyncio.wait_for(asyncio.shield(hubs.tasks[listener]), BOUND)
                return listener._closing, listener.connection
            finally:
                await hubs.stop_all()

        assert run(scenario()) == (True, None)


    @pytest.mark.slow
    def test_a_thousand_shutdowns_all_complete(self, ipc):
        """H5, measured 2026-10-22 and not reproduced: 8000 hub receiver cancellations (IPC and TCP)
        all completed, worst 3 ms. C6's lost-callback hang on a REP receive would have predicted about
        8. Kept as a regression test, like C6's, so a pynng upgrade that changes this is caught.
        ``slow``, so CI never selects it: run it with ``-m slow``."""
        async def scenario():
            for i in range(1000):
                address = f"{ipc}.{i}"
                hubs, listener, (node,) = await connected(address, settle=0)
                # A message on the fresh link, so the receivers are mid-loop when cancelled. The
                # bus may drop it (H6), so resend, as anything on a best-effort bus must.
                for _attempt in range(3):
                    await node.send_message({"i": i})
                    try:
                        await next_message(listener, timeout=0.5)
                        break
                    except asyncio.TimeoutError:
                        continue
                else:
                    raise AssertionError(f"round {i}: three messages lost on one link")
                tasks = list(hubs.tasks.values())
                for task in tasks:
                    task.cancel()
                await asyncio.wait(tasks, timeout=BOUND)
                assert all(t.done() for t in tasks), f"round {i}: a hub's start() did not finish"
                hubs.tasks.clear()
            return True

        assert asyncio.run(asyncio.wait_for(scenario(), timeout=600)) is True


# --- _receiver_handler, against a peer that is not a hub ----------------------------------------

class TestForeignPeers:
    def test_non_json_text_from_a_raw_bus_peer_is_delivered_as_raw_data(self, tcp):
        async def scenario():
            async with running() as hubs:
                listener = hubs.start(NngBusHub(tcp, NngBusHub.Mode.LISTENER))
                await asyncio.sleep(0.1)
                with Bus0() as peer:
                    peer.dial(tcp, block=True)
                    assert await until(lambda: listener.get_connection_count() == 1)
                    await peer.asend(b"not json")
                    return await next_message(listener)

        assert run(scenario()).data == {"raw_data": "not json"}

    def test_every_frame_from_a_raw_bus_peer_reaches_the_user_queue(self, tcp):
        frames = [b'{"ok": 1}', b"[1, 2]", b"42", b"\xff\xfe", b"plain"]

        async def scenario():
            async with running() as hubs:
                listener = hubs.start(NngBusHub(tcp, NngBusHub.Mode.LISTENER))
                await asyncio.sleep(0.1)
                with Bus0() as peer:
                    peer.dial(tcp, block=True)
                    assert await until(lambda: listener.get_connection_count() == 1)
                    for f in frames:
                        await peer.asend(f)
                    return [(await next_message(listener)).data for _ in frames]

        assert run(scenario()) == [
            {"ok": 1}, {"raw_data": "[1, 2]"}, {"raw_data": "42"},
            {"raw_data": "\ufffd\ufffd"}, {"raw_data": "plain"},
        ]

