"""Unit counterpart of ``cuemsutils.tools.CommunicatorServices``: one class per class and method.

No socket is opened here. ``Req0``/``Rep0`` are replaced by :class:`FakeSocket`, which records what
was sent and replays a scripted list of incoming frames. When the script runs out, it raises
:class:`ScriptEnded`, which is how the otherwise endless ``reply`` loop ends. Real NNG sockets over
IPC are in ``tests/integration/test_communicatorservices.py``.
"""
import asyncio
import json
import os
import threading
import warnings
from unittest.mock import AsyncMock, Mock, patch

import pynng
import pytest

from cuemsutils.tools import CommunicatorServices as module
from cuemsutils.tools.CommunicatorServices import (
    Communicator,
    CommunicatorService,
    IpcAddress,
    Nng_request_response,
    NngRequestResponse,
)
from tests.support import cuems_logs

ADDRESS = "ipc:///tmp/cuems-unit-test.ipc"

@pytest.fixture(autouse=True)
def cuems_debug_logs(caplog):
    """Assertions on log text must not depend on CUEMS_LOG_LEVEL."""
    cuems_logs.capture(caplog, module.__name__)


class ScriptEnded(Exception):
    """Raised by FakeSocket.arecv once its scripted frames are used up."""


class FakeSocket:
    def __init__(self, incoming=(), fail_send=None):
        self.incoming = list(incoming)
        self.sent: list[bytes] = []
        self.fail_send = fail_send
        self.closed = False
        self.contexts: list["FakeSocket"] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    async def asend(self, data):
        if self.fail_send:
            raise self.fail_send
        self.sent.append(data)

    async def arecv(self):
        if not self.incoming:
            raise ScriptEnded
        item = self.incoming.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def new_context(self):
        context = FakeSocket(self.incoming[:1], self.fail_send)
        del self.incoming[:1]
        self.contexts.append(context)
        return context

    def close(self):
        self.closed = True


class StuckSocket(FakeSocket):
    """What pynng's asyncio bridge does in the rare case C6 measured: a pending operation swallows
    CancelledError and waits for NNG's completion callback, which never comes. Only closing the
    socket ends it (NNG completes the operation with ECLOSED)."""

    def __init__(self, stuck=("arecv",), **kwargs):
        super().__init__(**kwargs)
        self.stuck = set(stuck)
        self._released = None

    async def _hang(self):
        self._released = self._released or asyncio.get_running_loop().create_future()
        while not self._released.done():
            try:
                await asyncio.shield(self._released)
            except asyncio.CancelledError:
                continue
        raise pynng.Closed("Object closed", 7)

    async def arecv(self):
        if "arecv" in self.stuck:
            await self._hang()
        return await super().arecv()

    async def asend(self, data):
        if "asend" in self.stuck:
            await self._hang()
        await super().asend(data)

    def close(self):
        self.closed = True
        if self._released is not None and not self._released.done():
            self._released.set_result(None)

    def __exit__(self, *exc):
        self.close()


async def cancelled_promptly(coro_factory, sock, *, settle=0.05, bound=1.0):
    """Start the coroutine, let it reach its pending pynng call, cancel it. Returns (done, closed),
    with ``closed`` read before this helper closes the socket itself to release a red run."""
    task = asyncio.create_task(coro_factory())
    await asyncio.sleep(settle)
    task.cancel()
    await asyncio.wait({task}, timeout=bound)
    done, closed = task.done(), sock.closed
    sock.close()
    await asyncio.wait({task}, timeout=bound)
    return done, closed


def frame(obj) -> bytes:
    return json.dumps(obj).encode()


def run(coro):
    return asyncio.run(asyncio.wait_for(coro, timeout=5))


def timed_out():
    return pynng.Timeout("Timed out", 5)


def request_ms() -> int:
    return int(module.REQUEST_TIMEOUT * 1000)


# --- module constants -------------------------------------------------------------------------

class TestTimeouts:
    def test_a_request_waits_at_most_100_seconds_by_default(self):
        assert module.REQUEST_TIMEOUT == 100.0



# --- IpcAddress -------------------------------------------------------------------------------

class TestIpcAddress:
    def test_names_one_socket_per_service(self):
        assert {a.name: a.value for a in IpcAddress} == {
            "HWDISCOVERY": "/tmp/hwdiscovery.ipc",
            "NODECONF": "/tmp/nodeconf.ipc",
            "EDITOR": "/tmp/editor.ipc",
        }


# --- CommunicatorService ----------------------------------------------------------------------

class TestCommunicatorService:
    def test_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            CommunicatorService(ADDRESS)

    def test_a_subclass_must_implement_all_three_methods(self):
        class Partial(CommunicatorService):
            def __init__(self, address):
                self.address = address

            def send_request(self, request):
                return {}

        with pytest.raises(TypeError, match="reply"):
            Partial(ADDRESS)


# --- NngRequestResponse.__init__ ------------------------------------------------------------

class TestNngRequestResponseInit:
    def test_by_default_the_requester_dials_and_the_replier_listens(self):
        rr = NngRequestResponse(ADDRESS)
        assert rr.address == ADDRESS
        assert rr.params_request == {"dial": ADDRESS}
        assert rr.params_reply == {"listen": ADDRESS}

    def test_requester_dials_false_reverses_the_roles(self):
        rr = NngRequestResponse(ADDRESS, requester_dials=False)
        assert rr.params_request == {"listen": ADDRESS}
        assert rr.params_reply == {"dial": ADDRESS}


# --- NngRequestResponse.send_request / _get_response ------------------------------------------

class TestSendRequest:
    def test_opens_a_req_socket_with_the_request_parameters(self):
        sock = FakeSocket([frame({"ok": 1})])
        with patch.object(module, "Req0", return_value=sock) as req0:
            run(NngRequestResponse(ADDRESS, requester_dials=False).send_request({"q": 1}))
        req0.assert_called_once_with(listen=ADDRESS, send_timeout=request_ms(), recv_timeout=request_ms())

    def test_the_timeout_bounds_both_the_send_and_the_reply(self):
        sock = FakeSocket([frame({"ok": 1})])
        with patch.object(module, "Req0", return_value=sock) as req0:
            run(NngRequestResponse(ADDRESS).send_request({"q": 1}, timeout=2.5))
        assert req0.call_args.kwargs["send_timeout"] == 2500
        assert 0 < sock.recv_timeout <= 2500  # what remains of the deadline after the send

    def test_no_reply_within_the_timeout_returns_none_and_says_so(self, caplog):
        with patch.object(module, "Req0", return_value=FakeSocket([timed_out()])):
            assert run(NngRequestResponse(ADDRESS).send_request({}, timeout=0.5)) is None
        assert f"no reply from {ADDRESS} within 0.5 s" in caplog.text

    def test_a_send_that_times_out_returns_none(self, caplog):
        with patch.object(module, "Req0", return_value=FakeSocket(fail_send=timed_out())):
            assert run(NngRequestResponse(ADDRESS).send_request({}, timeout=0.5)) is None
        assert f"no reply from {ADDRESS} within 0.5 s" in caplog.text

    def test_sends_the_request_json_encoded(self):
        sock = FakeSocket([frame({"ok": 1})])
        with patch.object(module, "Req0", return_value=sock):
            run(NngRequestResponse(ADDRESS).send_request({"q": "ñ", "n": [1, 2]}))
        assert [json.loads(s) for s in sock.sent] == [{"q": "ñ", "n": [1, 2]}]

    def test_returns_the_reply_json_decoded(self):
        sock = FakeSocket([frame({"answer": 42})])
        with patch.object(module, "Req0", return_value=sock):
            assert run(NngRequestResponse(ADDRESS).send_request({"q": 1})) == {"answer": 42}

    def test_closes_the_socket_afterwards(self):
        sock = FakeSocket([frame({})])
        with patch.object(module, "Req0", return_value=sock):
            run(NngRequestResponse(ADDRESS).send_request({}))
        assert sock.closed is True

    def test_a_socket_error_returns_none_and_is_logged(self, caplog):
        with patch.object(module, "Req0", side_effect=OSError("no such socket")):
            assert run(NngRequestResponse(ADDRESS).send_request({})) is None
        assert "Error occurred while sending request: no such socket" in caplog.text

    def test_a_non_json_reply_returns_none(self):
        with patch.object(module, "Req0", return_value=FakeSocket([b"not json"])):
            assert run(NngRequestResponse(ADDRESS).send_request({})) is None

    def test_cancelling_it_while_the_reply_hangs_finishes_and_closes_the_socket(self):
        """C6 on the requester: a caller's own timeout (cuems-editor uses asyncio.timeout) cancels it."""
        sock = StuckSocket()
        with patch.object(module, "Req0", return_value=sock):
            done, closed = run(cancelled_promptly(lambda: NngRequestResponse(ADDRESS).send_request({}), sock))
        assert (done, closed) == (True, True)

    def test_an_abandoned_operation_that_later_fails_is_not_reported_as_unretrieved(self, caplog):
        sock = StuckSocket()

        async def scenario():
            with patch.object(module, "Req0", return_value=sock):
                await cancelled_promptly(lambda: NngRequestResponse(ADDRESS).send_request({}), sock)
            await asyncio.sleep(0.05)
            import gc
            gc.collect()

        run(scenario())
        assert "exception was never retrieved" not in caplog.text

    def test_get_response_returns_the_raw_frame(self):
        assert run(NngRequestResponse(ADDRESS)._get_response(FakeSocket([b"raw"]))) == b"raw"


# --- NngRequestResponse.reply / _respond -----------------------------------------------------

class TestReply:
    def test_opens_a_rep_socket_with_the_reply_parameters(self):
        with patch.object(module, "Rep0", return_value=FakeSocket()) as rep0:
            run(NngRequestResponse(ADDRESS).reply(lambda q: q))
        rep0.assert_called_once_with(listen=ADDRESS)

    def test_cancelling_it_while_its_receive_hangs_still_finishes_and_closes_the_socket(self):
        """C6: never wait out pynng's cancellation of a pending receive."""
        sock = StuckSocket()
        with patch.object(module, "Rep0", return_value=sock):
            done, closed = run(cancelled_promptly(lambda: NngRequestResponse(ADDRESS).reply(Mock()), sock))
        assert (done, closed) == (True, True)

    def test_cancelling_it_while_its_reply_send_hangs_still_finishes(self):
        sock = StuckSocket(stuck=("asend",), incoming=[frame({"n": 1})])
        with patch.object(module, "Rep0", return_value=sock):
            done, closed = run(cancelled_promptly(lambda: NngRequestResponse(ADDRESS).reply(lambda q: q), sock))
        assert (done, closed) == (True, True)

    def test_answers_every_request_with_the_processor_result(self):
        sock = FakeSocket([frame({"n": 1}), frame({"n": 2})])
        with patch.object(module, "Rep0", return_value=sock):
            run(NngRequestResponse(ADDRESS).reply(lambda q: {"double": q["n"] * 2}))
        assert [json.loads(s) for s in sock.sent] == [{"double": 2}, {"double": 4}]

    def test_awaits_an_async_processor(self):
        async def processor(q):
            await asyncio.sleep(0)
            return {"async": q["n"]}

        sock = FakeSocket([frame({"n": 7})])
        with patch.object(module, "Rep0", return_value=sock):
            run(NngRequestResponse(ADDRESS).reply(processor))
        assert json.loads(sock.sent[0]) == {"async": 7}

    def test_runs_a_sync_processor_off_the_event_loop_thread(self):
        threads = []

        def processor(q):
            threads.append(threading.current_thread())
            return {}

        with patch.object(module, "Rep0", return_value=FakeSocket([frame({})])):
            run(NngRequestResponse(ADDRESS).reply(processor))
        assert threads and threads[0] is not threading.main_thread()

    def test_the_loop_ends_on_a_socket_error_and_logs_it(self, caplog):
        with patch.object(module, "Rep0", return_value=FakeSocket()):
            run(NngRequestResponse(ADDRESS).reply(lambda q: q))  # returns, does not raise
        assert "Error occurred while handling request" in caplog.text

    def test_a_raising_processor_does_not_stop_the_replier(self):
        def processor(q):
            if q.get("boom"):
                raise ValueError("boom")
            return {"ok": q["n"]}

        sock = FakeSocket([frame({"boom": 1}), frame({"n": 2})])
        with patch.object(module, "Rep0", return_value=sock):
            run(NngRequestResponse(ADDRESS).reply(processor))
        assert {"ok": 2} in [json.loads(s) for s in sock.sent]

    def test_a_malformed_request_does_not_stop_the_replier(self):
        sock = FakeSocket([b"not json", frame({"n": 2})])
        with patch.object(module, "Rep0", return_value=sock):
            run(NngRequestResponse(ADDRESS).reply(lambda q: {"ok": q["n"]}))
        assert {"ok": 2} in [json.loads(s) for s in sock.sent]

    def test_a_raising_processor_is_answered_with_an_error_reply(self):
        sock = FakeSocket([frame({"n": 1})])
        with patch.object(module, "Rep0", return_value=sock):
            run(NngRequestResponse(ADDRESS).reply(Mock(side_effect=ValueError("boom"))))
        assert [json.loads(s) for s in sock.sent] == [{"OK": False, "error": "ValueError: boom"}]

    def test_a_malformed_request_is_answered_with_an_error_reply(self):
        sock = FakeSocket([b"not json"])
        with patch.object(module, "Rep0", return_value=sock):
            run(NngRequestResponse(ADDRESS).reply(Mock()))
        (reply,) = [json.loads(s) for s in sock.sent]
        assert reply["OK"] is False and reply["error"].startswith("JSONDecodeError: ")

    def test_every_request_gets_exactly_one_reply(self):
        """REQ/REP: a request left unanswered blocks its requester for good."""
        def processor(q):
            if q["n"] == 1:
                raise ValueError("boom")
            return {"ok": q["n"]}

        sock = FakeSocket([frame({"n": 0}), frame({"n": 1}), b"junk", frame({"n": 3})])
        with patch.object(module, "Rep0", return_value=sock):
            run(NngRequestResponse(ADDRESS).reply(processor))
        assert len(sock.sent) == 4
        assert json.loads(sock.sent[0]) == {"ok": 0} and json.loads(sock.sent[3]) == {"ok": 3}


class TestRespond:
    def test_sends_the_response_json_encoded(self):
        sock = FakeSocket()
        run(NngRequestResponse(ADDRESS)._respond(sock, {"a": [1, "ñ"]}))
        assert [json.loads(s) for s in sock.sent] == [{"a": [1, "ñ"]}]

    def test_an_unencodable_response_is_logged_not_raised(self, caplog):
        sock = FakeSocket()
        run(NngRequestResponse(ADDRESS)._respond(sock, {"when": object()}))
        assert "Error occurred while sending response" in caplog.text

    def test_an_unencodable_response_still_answers_the_requester(self):
        sock = FakeSocket()
        run(NngRequestResponse(ADDRESS)._respond(sock, {"when": object()}))
        assert len(sock.sent) == 1

    def test_the_answer_to_an_unencodable_response_is_an_error_reply(self):
        sock = FakeSocket()
        run(NngRequestResponse(ADDRESS)._respond(sock, {"when": object()}))
        (reply,) = [json.loads(s) for s in sock.sent]
        assert reply["OK"] is False and reply["error"].startswith("TypeError: ")

    def test_a_failing_send_is_logged_not_raised(self, caplog):
        run(NngRequestResponse(ADDRESS)._respond(FakeSocket(fail_send=OSError("peer gone")), {"r": 1}))
        assert "peer gone" in caplog.text


# --- NngRequestResponse.responder_* ----------------------------------------------------------

class TestResponderConnect:
    def test_opens_a_rep_socket_with_the_reply_parameters(self):
        rr = NngRequestResponse(ADDRESS, requester_dials=False)
        with patch.object(module, "Rep0", return_value=FakeSocket()) as rep0:
            run(rr.responder_connect())
        rep0.assert_called_once_with(dial=ADDRESS)
        assert rr.responder is rep0.return_value


class TestResponderGetRequest:
    @pytest.fixture
    def rr(self):
        rr = NngRequestResponse(ADDRESS)
        rr.responder = FakeSocket([frame({"n": 1})])
        return rr

    def test_awaits_an_async_callback_with_the_request_and_its_context(self, rr):
        callback = AsyncMock()
        run(rr.responder_get_request(callback))
        context = rr.responder.contexts[0]
        callback.assert_awaited_once_with({"n": 1}, context)

    def test_calls_a_sync_callback_with_the_request_and_its_context(self, rr):
        callback = Mock()
        run(rr.responder_get_request(callback))
        callback.assert_called_once_with({"n": 1}, rr.responder.contexts[0])

    def test_cancelling_it_while_its_receive_hangs_finishes_and_closes_the_context(self, rr):
        context = StuckSocket()
        rr.responder.new_context = lambda: context
        done, closed = run(cancelled_promptly(lambda: rr.responder_get_request(Mock()), context))
        assert (done, closed) == (True, True)

    def test_each_request_gets_its_own_context(self, rr):
        rr.responder.incoming.append(frame({"n": 2}))
        run(rr.responder_get_request(Mock()))
        run(rr.responder_get_request(Mock()))
        assert len(rr.responder.contexts) == 2
        assert rr.responder.contexts[0] is not rr.responder.contexts[1]

    def test_a_malformed_request_is_answered_and_its_context_closed(self, rr):
        rr.responder.incoming[:] = [b"not json"]
        run(rr.responder_get_request(Mock()))
        context = rr.responder.contexts[0]
        assert len(context.sent) == 1 and context.closed is True

    def test_the_answer_to_a_malformed_request_is_an_error_reply(self, rr):
        rr.responder.incoming[:] = [b"not json"]
        run(rr.responder_get_request(Mock()))
        (reply,) = [json.loads(s) for s in rr.responder.contexts[0].sent]
        assert reply["OK"] is False and reply["error"].startswith("JSONDecodeError: ")

    def test_a_raising_callback_is_not_answered_for_it(self, rr):
        """The callback owns its context: it may already have replied, or have handed the context on
        to reply later (cuems-engine does, from another thread). A second reply is not ours to send."""
        run(rr.responder_get_request(Mock(side_effect=RuntimeError("handler bug"))))
        context = rr.responder.contexts[0]
        assert context.sent == [] and context.closed is False

    def test_a_malformed_request_is_logged_and_the_callback_not_called(self, rr, caplog):
        rr.responder.incoming[:] = [b"not json"]
        callback = Mock()
        run(rr.responder_get_request(callback))
        callback.assert_not_called()
        assert "Error occurred while handling request" in caplog.text

    def test_a_raising_callback_is_logged_not_raised(self, rr, caplog):
        run(rr.responder_get_request(Mock(side_effect=RuntimeError("handler bug"))))
        assert "handler bug" in caplog.text

    def test_a_closed_responder_socket_raises(self, rr):
        def closed():
            raise pynng.Closed("Object closed", 7)

        rr.responder.new_context = closed
        with pytest.raises(pynng.Closed):
            run(rr.responder_get_request(Mock()))

    def test_a_failing_receive_closes_its_context_then_raises(self, rr):
        rr.responder.incoming[:] = [pynng.Closed("Object closed", 7)]
        callback = Mock()
        with pytest.raises(pynng.Closed):
            run(rr.responder_get_request(callback))
        assert rr.responder.contexts[0].closed is True
        callback.assert_not_called()

    def test_a_responder_that_was_never_connected_raises(self):
        with pytest.raises(RuntimeError, match=r"responder_connect\(\) was not called"):
            run(NngRequestResponse(ADDRESS).responder_get_request(Mock()))


class TestResponderPostReply:
    def test_sends_the_reply_on_the_context_and_closes_it(self):
        context = FakeSocket()
        run(NngRequestResponse(ADDRESS).responder_post_reply({"r": 1}, context))
        assert [json.loads(s) for s in context.sent] == [{"r": 1}]
        assert context.closed is True

    def test_closes_the_context_even_when_sending_fails(self, caplog):
        context = FakeSocket(fail_send=OSError("peer gone"))
        run(NngRequestResponse(ADDRESS).responder_post_reply({"r": 1}, context))
        assert context.closed is True
        assert "peer gone" in caplog.text


# --- Nng_request_response (deprecated alias) --------------------------------------------------

class TestDeprecatedAlias:
    def test_warns_and_behaves_as_nng_request_response(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            alias = Nng_request_response(ADDRESS)
        assert isinstance(alias, NngRequestResponse)
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)


# --- Communicator.__init__ -------------------------------------------------------------------

class TestCommunicatorInit:
    def test_a_plain_path_in_an_existing_directory_gets_the_ipc_prefix(self, tmp_path):
        comm = Communicator(str(tmp_path / "svc.ipc"))
        assert comm.address == f"ipc://{tmp_path}/svc.ipc"

    def test_an_existing_writable_socket_path_is_accepted(self, tmp_path):
        (tmp_path / "svc.ipc").touch()
        assert Communicator(str(tmp_path / "svc.ipc")).address == f"ipc://{tmp_path}/svc.ipc"

    def test_an_address_with_the_ipc_prefix_is_accepted(self, tmp_path):
        assert Communicator(f"ipc://{tmp_path}/svc.ipc").address == f"ipc://{tmp_path}/svc.ipc"

    def test_a_missing_directory_exits_with_status_1(self, tmp_path):
        with pytest.raises(SystemExit) as exited:
            Communicator(str(tmp_path / "absent" / "svc.ipc"))
        assert exited.value.code == 1

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file modes")
    def test_an_unwritable_existing_socket_exits_with_status_1(self, tmp_path):
        target = tmp_path / "svc.ipc"
        target.touch()
        target.chmod(0o444)
        with pytest.raises(SystemExit) as exited:
            Communicator(str(target))
        assert exited.value.code == 1

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file modes")
    def test_an_unwritable_directory_exits_with_status_1(self, tmp_path):
        directory = tmp_path / "ro"
        directory.mkdir()
        directory.chmod(0o555)
        try:
            with pytest.raises(SystemExit) as exited:
                Communicator(str(directory / "svc.ipc"))
            assert exited.value.code == 1
        finally:
            directory.chmod(0o755)

    def test_builds_the_service_with_the_address_and_orientation(self, tmp_path):
        service = Mock()
        comm = Communicator(str(tmp_path / "svc.ipc"), communicator_service=service, requester_dials=False)
        service.assert_called_once_with(f"ipc://{tmp_path}/svc.ipc", requester_dials=False)
        assert comm.communicator_service is service.return_value
        assert comm.requester_dials is False

    def test_defaults_to_nng_request_response_with_the_requester_dialing(self, tmp_path):
        comm = Communicator(str(tmp_path / "svc.ipc"))
        assert isinstance(comm.communicator_service, NngRequestResponse)
        assert comm.communicator_service.params_request == {"dial": comm.address}


# --- Communicator delegation and _has_callable ------------------------------------------------

class TestCommunicatorDelegation:
    @pytest.fixture
    def comm(self, tmp_path):
        return Communicator(str(tmp_path / "svc.ipc"), communicator_service=Mock(return_value=AsyncMock()))

    def test_send_request_returns_the_service_reply(self, comm):
        comm.communicator_service.send_request.return_value = {"r": 1}
        assert run(comm.send_request({"q": 1})) == {"r": 1}
        comm.communicator_service.send_request.assert_awaited_once_with({"q": 1}, timeout=module.REQUEST_TIMEOUT)

    def test_send_request_forwards_its_timeout(self, comm):
        run(comm.send_request({"q": 1}, timeout=3))
        comm.communicator_service.send_request.assert_awaited_once_with({"q": 1}, timeout=3)

    def test_reply_delegates_the_processor(self, comm):
        processor = Mock()
        run(comm.reply(processor))
        comm.communicator_service.reply.assert_awaited_once_with(processor)

    def test_responder_connect_delegates(self, comm):
        run(comm.responder_connect())
        comm.communicator_service.responder_connect.assert_awaited_once_with()

    def test_responder_get_request_delegates_the_callback(self, comm):
        callback = Mock()
        run(comm.responder_get_request(callback))
        comm.communicator_service.responder_get_request.assert_awaited_once_with(callback)

    def test_responder_post_reply_delegates_the_reply_and_context(self, comm):
        context = Mock()
        run(comm.responder_post_reply({"r": 1}, context))
        comm.communicator_service.responder_post_reply.assert_awaited_once_with({"r": 1}, context)


class TestHasCallable:
    @pytest.fixture
    def comm(self, tmp_path):
        return Communicator(str(tmp_path / "svc.ipc"), communicator_service=Mock(return_value=object()))

    @pytest.mark.parametrize("method", ["responder_connect", "responder_get_request", "responder_post_reply"])
    def test_a_service_without_the_method_raises_attribute_error(self, comm, method):
        args = {"responder_connect": (), "responder_get_request": (Mock(),),
                "responder_post_reply": ({}, Mock())}[method]
        with pytest.raises(AttributeError, match=f"{method} is not an attribute"):
            run(getattr(comm, method)(*args))

    def test_a_non_callable_attribute_raises_attribute_error(self, comm):
        comm.communicator_service = Mock(responder_connect="not callable")
        with pytest.raises(AttributeError, match="responder_connect is not a callable attribute"):
            comm._has_callable("responder_connect")

    def test_a_callable_attribute_passes(self, comm):
        comm.communicator_service = Mock()
        comm._has_callable("responder_connect")
