"""Unit counterpart of ``cuemsutils.tools.HubServices``: one class per class and method, in source order.

No socket is opened here. The handlers run against :class:`FakeBus`, which replays scripted frames
(bytes or exceptions) and records what was sent. When the script runs out it raises pynng's
``Closed``, which is how the receiver loop ends in production too. Real NNG buses over TCP and IPC
are in ``tests/integration/test_hubservices.py``.
"""
import asyncio
import json
import socket
import struct
import warnings
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pynng import exceptions as pynng_exceptions

from cuemsutils.tools import HubServices as module
from cuemsutils.tools.HubServices import ConnectionInfo, Message, Nng_bus_hub, NngBusHub
from tests.support import cuems_logs

ADDRESS = "tcp://127.0.0.1:5555"
IPC_PIPE = SimpleNamespace(remote_address=SimpleNamespace(), url="ipc:///tmp/node.ipc")

@pytest.fixture(autouse=True)
def cuems_debug_logs(caplog):
    """Assertions on log text must not depend on CUEMS_LOG_LEVEL."""
    cuems_logs.capture(caplog, module.__name__)


def closed():
    """A real Closed instance; the class needs (msg, errno) to construct."""
    return pynng_exceptions.Closed("Object closed", 7)


def timed_out():
    return pynng_exceptions.Timeout("Timed out", 5)


def run(coro, timeout=5):
    return asyncio.run(asyncio.wait_for(coro, timeout=timeout))


class FakeBus:
    def __init__(self, frames=(), pipe=IPC_PIPE, send_errors=()):
        self.frames = list(frames)
        self.pipe = pipe
        self.send_errors = list(send_errors)
        self.sent: list[bytes] = []

    async def arecv_msg(self):
        if not self.frames:
            raise closed()
        item = self.frames.pop(0)
        if isinstance(item, BaseException):
            raise item
        return SimpleNamespace(bytes=item, pipe=self.pipe)

    async def asend(self, data):
        if self.send_errors:
            raise self.send_errors.pop(0)
        self.sent.append(data)


@pytest.fixture
def listener():
    return NngBusHub(ADDRESS, NngBusHub.Mode.LISTENER)


@pytest.fixture
def dialer():
    return NngBusHub(ADDRESS, NngBusHub.Mode.DIALER)


def received(hub, frames, pipe=IPC_PIPE):
    """Run the receiver over ``frames``; return what reached the user queue."""
    hub.connection = FakeBus(frames, pipe)
    run(hub._receiver_handler())
    out = []
    while not hub.incoming.empty():
        out.append(hub.incoming.get_nowait())
    return out


async def _run_sender_until_drained(hub, settle=0.05):
    task = asyncio.create_task(hub._send_handler())
    for _ in range(200):
        await asyncio.sleep(0.005)
        if hub.outgoing.empty():
            break
    await asyncio.sleep(settle)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


# --- Message / ConnectionInfo ---------------------------------------------------------------

class TestMessage:
    def test_holds_the_decoded_data_and_its_sender(self):
        message = Message(data={"test": "value"}, sender="node-1")
        assert (message.data, message.sender) == ({"test": "value"}, "node-1")

    def test_compares_by_value(self):
        assert Message({"a": 1}, "s") == Message({"a": 1}, "s")
        assert Message({"a": 1}, "s") != Message({"a": 2}, "s")


class TestConnectionInfo:
    def test_holds_key_sender_and_connection_time(self):
        when = datetime.now()
        info = ConnectionInfo(pipe_id=3, sender="unknown", connected_at=when)
        assert (info.pipe_id, info.sender, info.connected_at) == (3, "unknown", when)


# --- NngBusHub.__init__ ---------------------------------------------------------------------

class TestInit:
    @pytest.mark.parametrize("mode", list(NngBusHub.Mode))
    def test_records_address_and_mode(self, mode):
        hub = NngBusHub(ADDRESS, mode)
        assert (hub.address, hub.mode) == (ADDRESS, mode)

    def test_starts_unconnected_and_empty(self, listener):
        assert listener.connection is None
        assert listener.active_connections == {}
        assert listener.incoming.empty() and listener.outgoing.empty()
        assert listener._closing is False
        assert listener._next_conn_key == 0

    def test_starts_with_no_traffic_recorded(self, listener):
        assert listener._messages_received_count == 0
        assert listener._messages_sent_count == 0
        assert listener._last_message_received is None
        assert listener._last_message_sent is None

    def test_auto_ping_is_off_and_auto_pong_is_on(self, listener):
        assert listener._auto_ping_enabled is False
        assert listener._auto_ping_interval == 10.0
        assert listener._auto_pong_enabled is True
        assert (listener._ping_count, listener._pong_count) == (0, 0)

    def test_the_modes_are_listen_and_dial(self):
        assert {m.name: m.value for m in NngBusHub.Mode} == {"LISTENER": "listen", "DIALER": "dial"}


# --- NngBusHub.start ----------------------------------------------------------------------------

class TestStart:
    @pytest.fixture
    def hub(self, listener):
        listener.start_listener = AsyncMock(side_effect=lambda: setattr(listener, "connection", Mock()))
        listener.start_dialer = AsyncMock()
        return listener

    def test_an_unknown_mode_raises_value_error(self, listener):
        listener.mode = "sideways"
        with pytest.raises(ValueError, match="Unknown mode: sideways"):
            run(listener.start())

    def test_a_listener_starts_listening_and_a_dialer_starts_dialing(self, hub, dialer):
        hub._send_handler = AsyncMock(side_effect=RuntimeError("stop"))
        run(hub.start())
        hub.start_listener.assert_awaited_once_with()
        hub.start_dialer.assert_not_awaited()

        dialer.start_dialer = AsyncMock(side_effect=lambda: setattr(dialer, "connection", Mock()))
        dialer._send_handler = AsyncMock(side_effect=RuntimeError("stop"))
        run(dialer.start())
        dialer.start_dialer.assert_awaited_once_with()

    def test_returns_when_a_handler_raises_and_logs_it(self, hub, caplog):
        hub._receiver_handler = AsyncMock(side_effect=RuntimeError("receiver broke"))
        run(hub.start())
        assert "receiver handler failed: receiver broke" in caplog.text

    def test_on_exit_it_closes_the_socket_and_marks_itself_closing(self, hub):
        hub._send_handler = AsyncMock(side_effect=RuntimeError("stop"))
        run(hub.start())
        assert hub._closing is True
        assert hub.connection is None
        assert hub.start_listener.await_count == 1

    def test_the_other_handlers_are_cancelled_when_one_fails(self, hub):
        cancelled = []

        async def forever(name):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(name)
                raise

        hub._receiver_handler = lambda: forever("receiver")
        hub._auto_ping_handler = lambda: forever("ping")
        hub._send_handler = AsyncMock(side_effect=RuntimeError("stop"))
        run(hub.start())
        assert sorted(cancelled) == ["ping", "receiver"]

    def test_cancelling_start_still_closes_the_socket(self, hub):
        async def scenario():
            task = asyncio.create_task(hub.start())
            await asyncio.sleep(0.05)
            connection = hub.connection
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            return connection

        connection = run(scenario())
        connection.close.assert_called_once_with()
        assert hub.connection is None and hub._closing is True

    def test_a_failing_close_is_swallowed(self, hub):
        hub.start_listener = AsyncMock(side_effect=lambda: setattr(
            hub, "connection", Mock(close=Mock(side_effect=OSError("already gone")))))
        hub._send_handler = AsyncMock(side_effect=RuntimeError("stop"))
        run(hub.start())
        assert hub.connection is None

    @pytest.mark.xfail(strict=True, raises=asyncio.TimeoutError, reason=(
        "defect: start() waits with FIRST_EXCEPTION, and the receiver *returns* on a closed socket. "
        "So once the socket is closed start() never returns, and the service never learns its bus "
        "is gone. Measured over real TCP: still running 2 s after the close."
    ))
    def test_returns_when_the_receiver_stops_on_a_closed_socket(self, hub):
        async def stops():
            return None

        hub._receiver_handler = stops
        run(hub.start(), timeout=1)


# --- NngBusHub.start_listener / start_dialer ------------------------------------------------------

class TestStartListener:
    def test_sets_options_and_callbacks_before_listening(self, listener):
        bus = Mock()
        with patch.object(module, "Bus0", return_value=bus) as bus0:
            run(listener.start_listener())
        bus0.assert_called_once_with(recv_timeout=module.RECV_TIMEOUT)
        assert bus.tcp_keepalive is True
        names = [c[0] for c in bus.mock_calls]
        assert names.index("add_post_pipe_connect_cb") < names.index("listen")
        assert names.index("add_post_pipe_remove_cb") < names.index("listen")
        bus.listen.assert_called_once_with(ADDRESS)
        assert listener.connection is bus


class TestStartDialer:
    def test_sets_options_and_callbacks_then_dials_without_blocking(self, dialer):
        bus = Mock()
        with patch.object(module, "Bus0", return_value=bus):
            run(dialer.start_dialer())
        assert bus.tcp_keepalive is True
        assert (bus.reconnect_time_min, bus.reconnect_time_max) == (1000, 30000)
        names = [c[0] for c in bus.mock_calls]
        assert names.index("add_post_pipe_connect_cb") < names.index("dial")
        bus.dial.assert_called_once_with(ADDRESS, block=False)
        assert dialer.connection is bus


# --- NngBusHub.send_message / get_message --------------------------------------------------------

class TestSendMessage:
    def test_queues_a_dict_as_a_json_string(self, listener):
        run(listener.send_message({"test": "value", "n": 42}))
        assert listener.outgoing.get_nowait() == json.dumps({"test": "value", "n": 42})

    def test_queues_a_message_object_by_its_data_only(self, listener):
        run(listener.send_message(Message(data={"test": "value"}, sender="ignored")))
        assert listener.outgoing.get_nowait() == json.dumps({"test": "value"})

    @pytest.mark.parametrize("bad", ["invalid_string", 123, [1, 2], None])
    def test_anything_else_raises_type_error(self, listener, bad):
        with pytest.raises(TypeError, match="send_message requires dict or Message"):
            run(listener.send_message(bad))
        assert listener.outgoing.empty()

    def test_a_message_whose_data_is_not_a_dict_raises_type_error(self, listener):
        with pytest.raises(TypeError, match="Message.data must be a dict"):
            run(listener.send_message(Message(data="not_a_dict", sender="s")))

    def test_an_unserializable_dict_raises_and_queues_nothing(self, listener):
        with pytest.raises(TypeError):
            run(listener.send_message({"when": datetime.now()}))
        assert listener.outgoing.empty()

    def test_messages_are_queued_in_order(self, listener):
        for i in range(3):
            run(listener.send_message({"i": i}))
        assert [json.loads(listener.outgoing.get_nowait())["i"] for _ in range(3)] == [0, 1, 2]


class TestGetMessage:
    def test_returns_the_next_queued_message(self, listener):
        expected = Message(data={"test": "value"}, sender="node")
        listener.incoming.put_nowait(expected)
        assert run(listener.get_message()) == expected

    def test_waits_until_a_message_arrives(self, listener):
        async def scenario():
            waiter = asyncio.create_task(listener.get_message())
            await asyncio.sleep(0.02)
            assert not waiter.done()
            await listener.incoming.put(Message({"late": 1}, "node"))
            return await waiter

        assert run(scenario()).data == {"late": 1}


# --- connections -------------------------------------------------------------------------------

class TestActiveConnections:
    def test_lists_every_tracked_connection(self, listener):
        one = ConnectionInfo(pipe_id=1, sender="a", connected_at=datetime.now())
        two = ConnectionInfo(pipe_id=2, sender="b", connected_at=datetime.now())
        listener.active_connections = {1: one, 2: two}
        assert listener.get_active_connections() == [one, two]

    def test_counts_them(self, listener):
        assert listener.get_connection_count() == 0
        listener.active_connections = {k: Mock() for k in range(3)}
        assert listener.get_connection_count() == 3


# --- connection health -------------------------------------------------------------------------

class TestConnectionHealth:
    def test_no_traffic_at_all_is_unhealthy(self, listener):
        assert listener.get_connection_health_info() == {
            "is_healthy": False, "last_received": None, "last_sent": None,
            "seconds_since_activity": None, "messages_received": 0, "messages_sent": 0,
        }

    def test_recent_traffic_both_ways_is_healthy_and_reports_the_counts(self, listener):
        now = datetime.now()
        listener._last_message_received = listener._last_message_sent = now
        listener._messages_received_count, listener._messages_sent_count = 5, 3
        health = listener.get_connection_health_info()
        assert health["is_healthy"] is True
        assert (health["last_received"], health["last_sent"]) == (now, now)
        assert health["seconds_since_activity"] < 1.0
        assert (health["messages_received"], health["messages_sent"]) == (5, 3)

    def test_received_only_counts_as_activity(self, listener):
        listener._last_message_received = datetime.now()
        assert listener.get_connection_health_info()["is_healthy"] is True

    def test_sent_only_counts_as_activity(self, listener):
        listener._last_message_sent = datetime.now()
        assert listener.get_connection_health_info()["is_healthy"] is True

    def test_the_most_recent_direction_decides(self, listener):
        listener._last_message_received = datetime(2020, 1, 1)
        listener._last_message_sent = datetime.now()
        assert listener.get_connection_health_info()["seconds_since_activity"] < 1.0

    def test_activity_older_than_the_timeout_is_unhealthy(self, listener):
        listener._last_message_received = datetime(2020, 1, 1)
        health = listener.get_connection_health_info(activity_timeout=30.0)
        assert health["is_healthy"] is False
        assert health["seconds_since_activity"] > 30.0

    def test_the_timeout_is_a_parameter(self, listener):
        listener._last_message_received = datetime.now() - timedelta(seconds=10)
        assert listener.is_connection_healthy(activity_timeout=30) is True
        assert listener.is_connection_healthy(activity_timeout=5) is False

    def test_is_connection_healthy_answers_the_health_flag(self, listener):
        listener._last_message_received = datetime.now()
        assert listener.is_connection_healthy() is True
        listener._last_message_received = datetime(2020, 1, 1)
        assert listener.is_connection_healthy() is False


# --- auto ping / auto pong configuration, send_ping ------------------------------------------------

class TestAutoPingConfiguration:
    def test_enable_sets_interval_and_threshold(self, listener):
        listener.enable_auto_ping(interval=5.0, inactivity_threshold=2.0)
        assert listener._auto_ping_enabled is True
        assert (listener._auto_ping_interval, listener._inactivity_threshold) == (5.0, 2.0)

    def test_enable_defaults(self, listener):
        listener.enable_auto_ping()
        assert (listener._auto_ping_interval, listener._inactivity_threshold) == (10.0, 5.0)

    def test_disable(self, listener):
        listener.enable_auto_ping()
        listener.disable_auto_ping()
        assert listener._auto_ping_enabled is False


class TestAutoPongConfiguration:
    def test_disable_and_enable(self, listener):
        listener.disable_auto_pong()
        assert listener._auto_pong_enabled is False
        listener.enable_auto_pong()
        assert listener._auto_pong_enabled is True


class TestSendPing:
    def test_queues_a_typed_timestamped_ping_and_counts_it(self, listener):
        assert run(listener.send_ping()) == 1
        ping = json.loads(listener.outgoing.get_nowait())
        assert ping["__type__"] == "ping"
        datetime.fromisoformat(ping["timestamp"])
        assert listener._ping_count == 1


# --- _auto_ping_handler ---------------------------------------------------------------------------

class TestAutoPingHandler:
    @staticmethod
    def pings_after(hub, seconds=0.1):
        async def scenario():
            task = asyncio.create_task(hub._auto_ping_handler())
            await asyncio.sleep(seconds)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        run(scenario())
        return hub._ping_count

    def test_sends_nothing_while_disabled(self, listener):
        listener._auto_ping_interval = 0.01
        assert self.pings_after(listener) == 0

    def test_pings_when_nothing_was_ever_sent(self, listener):
        listener.enable_auto_ping(interval=0.01, inactivity_threshold=5.0)
        assert self.pings_after(listener) >= 1

    def test_pings_after_the_inactivity_threshold(self, listener):
        listener.enable_auto_ping(interval=0.01, inactivity_threshold=1.0)
        listener._last_message_sent = datetime.now() - timedelta(seconds=2)
        assert self.pings_after(listener) >= 1

    def test_does_not_ping_while_traffic_is_recent(self, listener):
        listener.enable_auto_ping(interval=0.01, inactivity_threshold=60.0)
        listener._last_message_sent = datetime.now()
        assert self.pings_after(listener) == 0

    def test_defaults_the_threshold_when_never_enabled(self, listener):
        listener._auto_ping_interval = 0.01
        self.pings_after(listener, 0.02)
        assert listener._inactivity_threshold == 5.0

    def test_an_error_is_logged_and_the_handler_keeps_running(self, listener, caplog):
        listener.enable_auto_ping(interval=0.01)
        listener.send_ping = AsyncMock(side_effect=RuntimeError("queue broke"))
        self.pings_after(listener)
        assert listener.send_ping.await_count >= 2
        assert "Error in auto-ping handler: queue broke" in caplog.text


# --- _receiver_handler ---------------------------------------------------------------------------

class TestReceiverHandler:
    def test_delivers_a_json_object_with_its_sender(self, listener):
        assert received(listener, [b'{"cue": 1}']) == [Message({"cue": 1}, "ipc:///tmp/node.ipc")]

    def test_delivers_frames_in_arrival_order(self, listener):
        frames = [json.dumps({"i": i}).encode() for i in range(5)]
        assert [m.data["i"] for m in received(listener, frames)] == list(range(5))

    def test_records_the_traffic(self, listener):
        received(listener, [b"{}", b"{}"])
        assert listener._messages_received_count == 2
        assert listener._last_message_received is not None

    def test_a_ping_is_answered_and_not_delivered(self, listener):
        assert received(listener, [b'{"__type__": "ping", "timestamp": "t0"}']) == []
        pong = json.loads(listener.outgoing.get_nowait())
        assert (pong["__type__"], pong["ping_timestamp"]) == ("pong", "t0")

    def test_a_pong_is_not_delivered(self, listener):
        assert received(listener, [b'{"__type__": "pong"}']) == []

    def test_non_json_text_is_delivered_as_raw_data(self, listener, caplog):
        assert received(listener, [b"hello"]) == [Message({"raw_data": "hello"}, "ipc:///tmp/node.ipc")]
        assert "Received non-JSON message" in caplog.text

    @pytest.mark.xfail(strict=True, reason=(
        "defect: valid JSON that is not an object (a list, string or number), and bytes that are not "
        "UTF-8, are counted as received but never delivered. Plain non-JSON text is delivered as "
        "raw_data, so these are lost silently by comparison. Measured over real TCP."
    ))
    @pytest.mark.parametrize("payload", [b"[1, 2]", b'"text"', b"42", b"\xff\xfe"])
    def test_every_received_frame_is_delivered(self, listener, payload):
        assert len(received(listener, [payload])) == 1

    def test_a_timeout_keeps_polling(self, listener):
        assert received(listener, [timed_out(), timed_out(), b'{"after": 1}']) == [
            Message({"after": 1}, "ipc:///tmp/node.ipc")
        ]

    def test_an_unexpected_error_is_logged_and_polling_continues(self, listener, caplog):
        assert received(listener, [RuntimeError("glitch"), b'{"after": 1}'])[0].data == {"after": 1}
        assert "Error in receiver handler: glitch" in caplog.text


class TestTeardownDoesNotRetryClosedSocket:
    """Regression tests for ClickUp 869ed00ya.

    pynng registers an atexit hook that calls nng_fini(), which frees NNG's global state. Any NNG
    call issued after that aborts the whole process with "panic: pthread_mutex_lock: Invalid
    argument". The receive/send loops must therefore stop for good the first time the socket
    reports Closed, instead of looping straight back into another arecv_msg()/asend().
    """

    def test_receiver_stops_on_closed(self, dialer):
        dialer.connection = Mock()
        dialer.connection.arecv_msg = AsyncMock(side_effect=closed())
        run(dialer._receiver_handler())
        assert dialer.connection.arecv_msg.await_count == 1, (
            "receiver retried on a closed socket — this is what aborts the process once "
            "nng_fini() has run"
        )
        assert dialer._closing is True

    def test_sender_stops_on_closed(self, dialer):
        dialer.connection = Mock()
        dialer.connection.asend = AsyncMock(side_effect=closed())
        dialer.outgoing.put_nowait(json.dumps({"a": 1}))
        dialer.outgoing.put_nowait(json.dumps({"b": 2}))
        run(dialer._send_handler())
        assert dialer.connection.asend.await_count == 1
        assert dialer._closing is True

    def test_receiver_keeps_polling_on_timeout(self, dialer):
        dialer.connection = Mock()
        dialer.connection.arecv_msg = AsyncMock(side_effect=[timed_out() for _ in range(3)] + [closed()])
        run(dialer._receiver_handler())
        assert dialer.connection.arecv_msg.await_count == 4

    def test_receiver_does_not_start_when_already_closing(self, dialer):
        dialer.connection = Mock()
        dialer.connection.arecv_msg = AsyncMock()
        dialer._closing = True
        run(dialer._receiver_handler())
        dialer.connection.arecv_msg.assert_not_awaited()

    def test_sender_does_not_start_when_already_closing(self, dialer):
        dialer.connection = FakeBus()
        dialer._closing = True
        dialer.outgoing.put_nowait("{}")
        run(dialer._send_handler())
        assert dialer.connection.sent == []


# --- _handle_ping_pong -----------------------------------------------------------------------------

class TestHandlePingPong:
    def test_a_ping_is_handled_and_answered_with_a_pong(self, listener):
        ping = Message({"__type__": "ping", "timestamp": "2023-01-01T00:00:00"}, "node")
        assert run(listener._handle_ping_pong(ping, "node")) is True
        pong = json.loads(listener.outgoing.get_nowait())
        assert pong["__type__"] == "pong"
        assert pong["ping_timestamp"] == "2023-01-01T00:00:00"
        datetime.fromisoformat(pong["timestamp"])
        assert listener._pong_count == 1

    def test_with_auto_pong_disabled_a_ping_is_handled_but_not_answered(self, listener):
        listener.disable_auto_pong()
        assert run(listener._handle_ping_pong(Message({"__type__": "ping"}, "n"), "n")) is True
        assert listener.outgoing.empty()
        assert listener._pong_count == 0

    def test_a_pong_is_handled_without_a_reply(self, listener):
        assert run(listener._handle_ping_pong(Message({"__type__": "pong"}, "n"), "n")) is True
        assert listener.outgoing.empty()

    @pytest.mark.parametrize("data", [{"__type__": "normal"}, {"content": "x"}, {"type": "ping"}])
    def test_anything_else_is_left_for_the_user(self, listener, data):
        assert run(listener._handle_ping_pong(Message(data, "n"), "n")) is False

    def test_a_non_dict_payload_is_left_for_the_user(self, listener):
        assert run(listener._handle_ping_pong(Message(["not", "a", "dict"], "n"), "n")) is False


# --- _send_handler ---------------------------------------------------------------------------------

class TestSendHandler:
    def test_sends_each_queued_message_utf8_encoded_in_order(self, dialer):
        dialer.connection = FakeBus()
        for payload in ({"i": 0}, {"i": "ñ"}):
            dialer.outgoing.put_nowait(json.dumps(payload))
        run(_run_sender_until_drained(dialer))
        assert [json.loads(b.decode()) for b in dialer.connection.sent] == [{"i": 0}, {"i": "ñ"}]

    def test_records_the_traffic(self, dialer):
        dialer.connection = FakeBus()
        dialer.outgoing.put_nowait("{}")
        run(_run_sender_until_drained(dialer))
        assert dialer._messages_sent_count == 1
        assert dialer._last_message_sent is not None

    def test_a_listener_holds_messages_until_a_node_connects(self, listener):
        listener.connection = FakeBus()
        listener.outgoing.put_nowait('{"early": 1}')

        async def scenario():
            task = asyncio.create_task(listener._send_handler())
            await asyncio.sleep(0.25)
            held = list(listener.connection.sent)
            listener._post_connect_callback(pipe=None)
            for _ in range(100):
                await asyncio.sleep(0.01)
                if listener.connection.sent:
                    break
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            return held

        assert run(scenario()) == []
        assert listener.connection.sent == [b'{"early": 1}']

    def test_a_dialer_sends_without_waiting_for_a_tracked_connection(self, dialer):
        dialer.connection = FakeBus()
        dialer.outgoing.put_nowait("{}")
        run(_run_sender_until_drained(dialer))
        assert dialer.connection.sent == [b"{}"]

    def test_an_unexpected_send_error_is_logged_and_the_next_message_still_goes(self, dialer, caplog):
        dialer.connection = FakeBus(send_errors=[RuntimeError("wire down")])
        dialer.outgoing.put_nowait('{"first": 1}')
        dialer.outgoing.put_nowait('{"second": 2}')
        run(_run_sender_until_drained(dialer))
        assert dialer.connection.sent == [b'{"second": 2}']
        assert "Error in send handler: wire down" in caplog.text

    def test_a_failed_send_is_not_counted_as_sent(self, dialer):
        dialer.connection = FakeBus(send_errors=[RuntimeError("wire down")])
        dialer.outgoing.put_nowait("{}")
        run(_run_sender_until_drained(dialer))
        assert dialer._messages_sent_count == 0
        assert dialer._last_message_sent is None

    def test_after_a_failed_send_the_next_success_counts_once(self, dialer):
        dialer.connection = FakeBus(send_errors=[RuntimeError("wire down")])
        dialer.outgoing.put_nowait('{"lost": 1}')
        dialer.outgoing.put_nowait('{"sent": 2}')
        run(_run_sender_until_drained(dialer))
        assert dialer._messages_sent_count == 1
        assert dialer._last_message_sent is not None

    def test_a_failed_send_alone_leaves_an_idle_link_unhealthy(self, dialer):
        dialer.connection = FakeBus(send_errors=[RuntimeError("wire down")])
        dialer.outgoing.put_nowait("{}")
        run(_run_sender_until_drained(dialer))
        assert dialer.is_connection_healthy() is False


# --- _add_callbacks / _post_connect_callback / _post_remove_callback -----------------------------

class TestAddCallbacks:
    def test_registers_both_pipe_callbacks_on_the_connection(self, listener):
        listener.connection = Mock()
        listener._add_callbacks()
        listener.connection.add_post_pipe_connect_cb.assert_called_once_with(listener._post_connect_callback)
        listener.connection.add_post_pipe_remove_cb.assert_called_once_with(listener._post_remove_callback)


class TestPostConnectCallback:
    def test_tracks_each_connection_under_a_monotonic_key(self, listener):
        for _ in range(3):
            listener._post_connect_callback(Mock())
        assert list(listener.active_connections) == [0, 1, 2]
        info = listener.active_connections[0]
        assert (info.pipe_id, info.sender) == (0, "unknown")
        assert isinstance(info.connected_at, datetime)

    def test_never_touches_the_pipe(self, listener):
        """pipe.id is a C call that can abort the process during NNG teardown."""
        pipe = Mock()
        listener._post_connect_callback(pipe)
        assert pipe.mock_calls == []

    def test_is_a_no_op_while_closing(self, listener):
        listener._closing = True
        listener._post_connect_callback(Mock())
        assert listener.active_connections == {}


class TestPostRemoveCallback:
    def test_forgets_the_oldest_connection_first(self, listener):
        for _ in range(3):
            listener._post_connect_callback(None)
        listener._post_remove_callback(None)
        assert list(listener.active_connections) == [1, 2]

    def test_with_nothing_tracked_it_is_harmless(self, listener):
        listener._post_remove_callback(None)
        assert listener.active_connections == {}

    def test_is_a_no_op_while_closing(self, listener):
        listener._post_connect_callback(None)
        listener._closing = True
        listener._post_remove_callback(None)
        assert len(listener.active_connections) == 1

    def test_a_dialer_left_without_connections_warns(self, dialer, caplog):
        dialer._post_connect_callback(None)
        dialer._post_remove_callback(None)
        assert "DIALER has no active connections" in caplog.text

    def test_a_listener_left_without_connections_does_not_warn(self, listener, caplog):
        listener._post_connect_callback(None)
        listener._post_remove_callback(None)
        assert "has no active connections" not in caplog.text


# --- _extract_sender_info ------------------------------------------------------------------------------

def tcp_pipe(ip, port):
    """A pipe whose address is encoded as pynng delivers it: sockaddr_in fields in network order,
    read back as native integers (what the integration test sees on a real TCP connection)."""
    addr = struct.unpack("I", socket.inet_aton(ip))[0]
    return SimpleNamespace(remote_address=SimpleNamespace(addr=addr, port=socket.htons(port)))


class TestExtractSenderInfo:
    @pytest.mark.parametrize("ip, port", [("127.0.0.1", 12345), ("10.0.0.5", 5555), ("192.168.1.200", 80)])
    def test_a_tcp_peer_is_its_ip_and_port(self, listener, ip, port):
        assert listener._extract_sender_info(tcp_pipe(ip, port)) == (ip, port)

    def test_an_ipc_peer_is_the_pipe_url(self, listener):
        assert listener._extract_sender_info(IPC_PIPE) == "ipc:///tmp/node.ipc"

    def test_a_peer_without_a_url_is_unknown(self, listener):
        assert listener._extract_sender_info(SimpleNamespace(remote_address=SimpleNamespace())) == "unknown"

    def test_a_pipe_that_cannot_be_read_is_unknown(self, listener):
        class Broken:
            @property
            def remote_address(self):
                raise RuntimeError("pipe gone")

        assert listener._extract_sender_info(Broken()) == "unknown"


# --- Nng_bus_hub (deprecated alias) --------------------------------------------------------------------

class TestDeprecatedAlias:
    def test_warns_and_behaves_as_nng_bus_hub(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            alias = Nng_bus_hub(ADDRESS, NngBusHub.Mode.DIALER)
        assert isinstance(alias, NngBusHub)
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
