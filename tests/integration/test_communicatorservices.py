"""Integration counterpart of ``cuemsutils.tools.CommunicatorServices``: real NNG REQ/REP over IPC.

These are the paths the CUEMS services use between themselves: one process replies, another asks.
Every await is bounded, so a hang shows up as a failure, never as a stuck suite. The behaviour of
each method in isolation is in ``tests/unit/test_communicatorservices.py``.

**Servers are stopped by closing their socket, never by cancelling alone.** ``reply()`` blocks in
pynng's ``arecv()`` with no receive timeout. Measured 2026-10-22 over 1000 rounds, both with one
event loop and with a fresh loop per round: about 1 cancellation in 1000 of that pending receive
never completes. A test that only cancelled would hang about once in 250 runs of this file. Closing the
socket makes ``arecv()`` raise ``Closed``, which ``reply()`` handles by returning, so every socket
this module opens is recorded (``OPENED``) and closed by the helpers and by teardown.
"""
import asyncio
import os
import shutil
import tempfile

import pynng
import pytest

from cuemsutils.tools import CommunicatorServices as module
from cuemsutils.tools.CommunicatorServices import Communicator, NngRequestResponse

BOUND = 1.0  # seconds; an answer on a local socket takes a few milliseconds
OPENED: list = []  # every Req0/Rep0 the module opened during the current test


@pytest.fixture(autouse=True)
def recorded_sockets(monkeypatch):
    class Rep0(pynng.Rep0):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            OPENED.append(self)

    class Req0(pynng.Req0):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            OPENED.append(self)

    monkeypatch.setattr(module, "Rep0", Rep0)
    monkeypatch.setattr(module, "Req0", Req0)
    OPENED.clear()
    yield
    for sock in OPENED:
        sock.close()
    OPENED.clear()


@pytest.fixture
def ipc_dir():
    # sun_path is limited to 108 bytes, which a deep tmp_path can exceed.
    directory = tempfile.mkdtemp(prefix="cuems-rr-")
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def address(ipc_dir):
    return f"ipc://{ipc_dir}/svc.ipc"


def run(coro):
    return asyncio.run(asyncio.wait_for(coro, timeout=15))


async def _serving(address, processor, *, requester_dials=True):
    """Start ``reply`` and wait until its socket exists. Returns the task; cancel it when done."""
    task = asyncio.create_task(NngRequestResponse(address, requester_dials=requester_dials).reply(processor))
    if requester_dials:
        path = address.removeprefix("ipc://")
        for _ in range(200):
            if os.path.exists(path):
                break
            await asyncio.sleep(0.005)
    return task


async def _stop(task):
    """Close the replier's socket so reply() returns; cancel only as a fallback (see the docstring)."""
    for sock in OPENED:
        if isinstance(sock, pynng.Rep0):
            sock.close()
    await asyncio.wait({task}, timeout=BOUND)
    if not task.done():
        task.cancel()
        await asyncio.wait({task}, timeout=BOUND)


async def _ask(address, request, *, requester_dials=True):
    """send_request, bounded. A timeout raises asyncio.TimeoutError after releasing the request by
    closing its socket, because cancelling a pending pynng receive is not reliable."""
    before = len(OPENED)
    task = asyncio.create_task(
        NngRequestResponse(address, requester_dials=requester_dials).send_request(request))
    await asyncio.wait({task}, timeout=BOUND)
    if task.done():
        return task.result()
    for sock in OPENED[before:]:
        if isinstance(sock, pynng.Req0):
            sock.close()
    await asyncio.wait({task}, timeout=BOUND)
    raise asyncio.TimeoutError(f"no reply within {BOUND} s")


# --- send_request + reply ---------------------------------------------------------------------

class TestRequestReply:
    def test_a_sync_processor_answers_the_requester(self, address):
        async def scenario():
            server = await _serving(address, lambda q: {"double": q["n"] * 2})
            try:
                return await _ask(address, {"n": 21})
            finally:
                await _stop(server)

        assert run(scenario()) == {"double": 42}

    def test_an_async_processor_answers_the_requester(self, address):
        async def processor(q):
            await asyncio.sleep(0.01)
            return {"async": q["n"]}

        async def scenario():
            server = await _serving(address, processor)
            try:
                return await _ask(address, {"n": 7})
            finally:
                await _stop(server)

        assert run(scenario()) == {"async": 7}

    def test_one_replier_answers_successive_requesters_in_order(self, address):
        async def scenario():
            server = await _serving(address, lambda q: {"echo": q["i"]})
            try:
                return [await _ask(address, {"i": i}) for i in range(5)]
            finally:
                await _stop(server)

        assert run(scenario()) == [{"echo": i} for i in range(5)]

    def test_non_ascii_and_nested_payloads_arrive_intact(self, address):
        payload = {"name": "Fàbrica ñ — 日本", "cues": [{"id": 1, "args": [None, True, 1.5]}]}

        async def scenario():
            server = await _serving(address, lambda q: q)
            try:
                return await _ask(address, payload)
            finally:
                await _stop(server)

        assert run(scenario()) == payload

    def test_with_requester_dials_false_the_requester_listens_and_the_replier_dials(self, address):
        async def scenario():
            server = await _serving(address, lambda q: {"ok": q["n"]}, requester_dials=False)
            try:
                return await _ask(address, {"n": 3}, requester_dials=False)
            finally:
                await _stop(server)

        assert run(scenario()) == {"ok": 3}


# --- responder_connect / responder_get_request / responder_post_reply ------------------------

class TestContextResponder:
    def test_concurrent_requests_are_answered_to_the_right_requester_in_any_order(self, address):
        """The context API exists so a service can answer requests out of order."""
        async def scenario():
            responder = NngRequestResponse(address)
            await responder.responder_connect()
            pending = []

            async def collect(request, context):
                pending.append((request, context))

            try:
                asks = [asyncio.create_task(_ask(address, {"i": i})) for i in range(2)]
                await asyncio.wait_for(responder.responder_get_request(collect), BOUND)
                await asyncio.wait_for(responder.responder_get_request(collect), BOUND)
                for request, context in reversed(pending):  # answer the later one first
                    await responder.responder_post_reply({"for": request["i"]}, context)
                return await asyncio.gather(*asks)
            finally:
                responder.responder.close()

        assert run(scenario()) == [{"for": 0}, {"for": 1}]

    def test_a_sync_callback_can_hold_the_context_and_reply_later(self, address):
        async def scenario():
            responder = NngRequestResponse(address)
            await responder.responder_connect()
            held = []
            try:
                ask = asyncio.create_task(_ask(address, {"n": 5}))
                await asyncio.wait_for(responder.responder_get_request(lambda q, c: held.append((q, c))), BOUND)
                (request, context), = held
                await responder.responder_post_reply({"late": request["n"]}, context)
                return await ask
            finally:
                responder.responder.close()

        assert run(scenario()) == {"late": 5}


# --- Communicator, end to end ---------------------------------------------------------------

class TestCommunicatorEndToEnd:
    def test_two_communicators_on_one_path_exchange_a_request(self, ipc_dir):
        path = f"{ipc_dir}/svc.ipc"

        async def scenario():
            server = asyncio.create_task(Communicator(path).reply(lambda q: {"pong": q["ping"]}))
            for _ in range(200):
                if os.path.exists(path):
                    break
                await asyncio.sleep(0.005)
            try:
                return await asyncio.wait_for(Communicator(path).send_request({"ping": "x"}), BOUND)
            finally:
                await _stop(server)

        assert run(scenario()) == {"pong": "x"}


# --- failure modes ---------------------------------------------------------------------------

class TestFailureModes:
    @pytest.mark.xfail(strict=True, raises=asyncio.TimeoutError, reason=(
        "defect: send_request has no timeout, so asking a service that is not running waits "
        "forever instead of returning None as its other failures do."
    ))
    def test_asking_a_service_that_is_not_running_returns_none(self, address):
        assert run(_ask(address, {"n": 1})) is None

    def test_the_service_keeps_answering_after_its_processor_raised(self, address):
        def processor(q):
            if q.get("boom"):
                raise ValueError("boom")
            return {"ok": q["n"]}

        async def scenario():
            server = await _serving(address, processor)
            try:
                failed = await _ask(address, {"boom": 1})
                return failed, await _ask(address, {"n": 2})
            finally:
                await _stop(server)

        assert run(scenario()) == ({"OK": False, "error": "ValueError: boom"}, {"ok": 2})

    def test_a_requester_is_answered_even_when_its_response_cannot_be_encoded(self, address):
        async def scenario():
            server = await _serving(address, lambda q: {"when": object()})
            try:
                return await _ask(address, {"n": 1})
            finally:
                await _stop(server)

        reply = run(scenario())
        assert reply["OK"] is False and reply["error"].startswith("TypeError: ")
