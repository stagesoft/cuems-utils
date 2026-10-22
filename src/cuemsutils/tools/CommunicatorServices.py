import asyncio
import json
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from functools import partial

from deprecated import deprecated
from pynng import Rep0, Req0
from pynng import Timeout as NngTimeout

from ..helpers import check_path
from ..log import Logger

#: The longest a request waits, in seconds: for the send (no replier yet) and the reply together.
REQUEST_TIMEOUT = 100.0


async def _shielded(operation):
    """Await a pynng socket or context operation without exposing it to cancellation (C6).

    When the awaiting task is cancelled, pynng's asyncio bridge calls ``nng_aio_cancel`` and then
    waits for NNG's completion callback. Measured 2026-10-22: about 1 time in 1000 that callback never
    comes, so the cancelled task never finishes, and a receive timeout does not end it either.
    Shielded, the operation keeps running on its own while the cancellation reaches the caller at
    once. Every caller closes its socket or context on the way out (a ``with`` block, or an explicit
    ``close()``), which completes the abandoned operation with ``Closed``. That error is retrieved
    here, so it is never logged as "exception was never retrieved".
    """
    inner = asyncio.ensure_future(operation)
    inner.add_done_callback(lambda done: done.cancelled() or done.exception())
    return await asyncio.shield(inner)


def _error_reply(error: Exception) -> dict:
    """The reply sent when a request cannot be answered normally.

    REQ/REP needs exactly one reply per request: a requester left unanswered waits for good. The
    shape is the one ``cuems-nodeconf``'s replies already use, which the editor reads as
    ``reply.get('OK') is not True`` -> ``reply.get('error')``.
    """
    return {"OK": False, "error": f"{type(error).__name__}: {error}"}


class IpcAddress(Enum):
    """ IPC addresses for the different services """
    HWDISCOVERY = '/tmp/hwdiscovery.ipc'
    NODECONF = '/tmp/nodeconf.ipc'
    EDITOR = '/tmp/editor.ipc'

class CommunicatorService(ABC):
    @abstractmethod
    def __init__(self, address:str):
        self.address = address

    @abstractmethod
    def send_request(self, request:dict, timeout: float = REQUEST_TIMEOUT) -> dict:
        """ Send request dict and return response dict, or None after ``timeout`` seconds.
        Communicator passes ``timeout`` through, so an implementation must accept it. """

    @abstractmethod
    def reply(self, request_processor:Callable[[dict], dict]) -> dict:
        """ Get request, give it to request processor, and return the response from it  """


class NngRequestResponse(CommunicatorService):
    """ Communicates over NNG (nanomsg) using a Request-Response protocol"""
    def __init__(self, address, requester_dials=True):
        """
        Initialize NngRequestResponse instance with address and dialing/listening mode.

        Parameters:
        - address (str): The address to connect or listen for connections.
        - requester_dials (bool, optional): If True, the instance requester will dial the address and replier will listen. If False, it will be the opposite way, requester listens and replier dials. Default is True.

        The instance will set up the parameters for request and reply sockets based on the requester_dials value.
        """
        self.address = address
        if requester_dials:
            self.params_request = {'dial': self.address}
            self.params_reply = {'listen': self.address}
        else:
            self.params_request = {'listen': self.address}
            self.params_reply = {'dial': self.address}

    async def send_request(self, request, timeout: float = REQUEST_TIMEOUT):
        """
        Send a request to the specified address and return the response.

        Parameters:
        - request (dict): The request to be sent. It should be a dictionary.
        - timeout (float, optional): Seconds to wait in all, for the send and the reply together.
          Default REQUEST_TIMEOUT (100 s). With no replier listening, the send itself would
          otherwise block for good.

        Returns:
        - dict: The response received from the address. It will be a dictionary.
        - None: When there is no reply within ``timeout``, or on any other error. Both are logged.
        """
        deadline_ms = max(1, int(timeout * 1000))
        try:
            with Req0(**self.params_request, send_timeout=deadline_ms, recv_timeout=deadline_ms) as socket:
                while await asyncio.sleep(0, result=True):
                    Logger.debug(f"Sending: {request}")
                    encoded_request = json.dumps(request).encode()
                    started = time.monotonic()
                    await _shielded(socket.asend(encoded_request))
                    # One deadline for both halves: the reply gets what the send left.
                    socket.recv_timeout = max(1, deadline_ms - int((time.monotonic() - started) * 1000))
                    response = await self._get_response(socket)
                    decoded_response = json.loads(response.decode())
                    Logger.debug(f"receiving: {decoded_response}")
                    return decoded_response
        except NngTimeout:
            Logger.error(f"Error occurred while sending request: no reply from {self.address} within {timeout} s")
            return None
        except Exception as e:
            Logger.error(f"Error occurred while sending request: {e}")
            return None

    async def _get_response(self, socket: Req0):
        """
        Get the response from the socket.

        Parameters:
        - socket (Req0): The socket to get the response from.

        Returns:
        - bytes: The response from the socket.
        """
        response = await _shielded(socket.arecv())
        return response

    async def reply(self, request_processor):
        """
        Asynchronously handle incoming requests and respond using the provided request processor.

        This function sets up a Rep0 socket with parameters based on the instance's configuration.
        It then enters a loop where it listens for incoming requests, processes them using the provided
        request processor, and sends the response back to the requester.
        Parameters:
        - request_processor (Callable[[dict], dict]): A function that takes a request dictionary as input and returns a response dictionary.

        Returns:
        - None: This function is designed to run indefinitely, handling incoming requests and responses.
        """
        try:
            # On cancellation the with block closes the socket, which ends a shielded pending
            # receive (see _shielded).
            with Rep0(**self.params_reply) as socket:
                while await asyncio.sleep(0, result=True):
                    request = await _shielded(socket.arecv())
                    # One bad request must not stop the service: a request that is not JSON, or
                    # whose processor raises, is answered with _error_reply() and the loop goes on.
                    # Only a socket error (above, in arecv) ends it.
                    try:
                        decoded_request = json.loads(request.decode())  # Parse the JSON request
                        Logger.debug(f"Received: {decoded_request}")
                        if asyncio.iscoroutinefunction(request_processor):
                            response = await request_processor(decoded_request)
                        else:
                            loop = asyncio.get_event_loop()
                            response = await loop.run_in_executor(None, partial(request_processor, decoded_request))
                    except Exception as e:
                        Logger.error(f"Error occurred while processing request: {e}")
                        response = _error_reply(e)
                    await self._respond(socket, response)
        except Exception as e:
            Logger.error(f"Error occurred while handling request: {e}")

    async def _respond(self, socket, response):
        try:
            try:
                encoded_response = json.dumps(response).encode()
            except (TypeError, ValueError) as e:
                # Still answer: without a reply the requester waits for good.
                Logger.error(f"Error occurred while sending response: cannot encode it: {e}")
                encoded_response = json.dumps(_error_reply(e)).encode()
            Logger.debug(f"Sending: {encoded_response}")
            await _shielded(socket.asend(encoded_response))
        except Exception as e:
            Logger.error(f"Error occurred while sending response: {e}")

    async def responder_connect(self):
        self.responder = Rep0(**self.params_reply)

    async def responder_get_request(self, callback):
        try:
            context = self.responder.new_context()
            try:
                request = await _shielded(context.arecv())
            except asyncio.CancelledError:
                context.close()  # ends the shielded pending receive (see _shielded)
                raise
            try:
                decoded_request = json.loads(request.decode())  # Parse the JSON request
            except ValueError as e:
                # The callback never sees this request, so it is answered here and its context
                # closed: unanswered, its requester would wait for good. (A callback that raises is
                # different: it owns the context, and may already have replied or handed it on.)
                Logger.error(f"Error occurred while handling request: {e}")
                await self.responder_post_reply(_error_reply(e), context)
                return
            Logger.debug(f"Received: {decoded_request}")
            if asyncio.iscoroutinefunction(callback):
                Logger.debug("Calling callback function async")
                await callback(decoded_request, context)
            else:
                loop = asyncio.get_event_loop()
                Logger.debug("Calling sync callback function in executor")
                await loop.run_in_executor(None, partial(callback, decoded_request, context))
        except Exception as e:
            Logger.error(f"Error occurred while handling request: {e}")

    async def responder_post_reply(self, response, context):
        try:
            await self._respond(context, response)
        except Exception as e:
            Logger.error(f"Error occurred while sending response: {e}")
        finally:
            context.close()


@deprecated(
    reason="This is an alias, use NngRequestResponse instead",
    version="0.1.0rc1"
)
class Nng_request_response(NngRequestResponse):
    pass

class Communicator(CommunicatorService):
    def __init__(
        self,
        address:str,
        communicator_service:CommunicatorService = NngRequestResponse,
        requester_dials:bool = True
    ):
        """
        Initialize Communicator instance with address and communicator service.

        Parameters:
        - address (str): The address to connect or listen for connections.
        - communicator_service (Callable[[str, bool], CommunicatorService]): The communicator service to use.
        - requester_dials (bool): If True, the instance will dial the address. If False, it will listen for connections.
        """
        # The filesystem check needs the socket path: an ipc:// address checked as given resolves
        # to the relative path ./ipc:/... and exits.
        socket_path = address[6:] if address[0:6] == 'ipc://' else address
        try:
            check_path(socket_path)
        except PermissionError as e:
            Logger.error(e)
            sys.exit(1)
        except FileNotFoundError:
            try:
                check_path(socket_path, dir_only = True)
            except (NotADirectoryError, PermissionError) as e:
                Logger.error(e)
                sys.exit(1)

        if address[0:6] != 'ipc://':
            address = "ipc://" + address
        self.address = address
        self.requester_dials = requester_dials
        self.communicator_service:CommunicatorService = communicator_service(self.address, requester_dials=self.requester_dials)

    async def send_request(self, request, timeout: float = REQUEST_TIMEOUT):
        response = await self.communicator_service.send_request(request, timeout=timeout)
        return response

    async def reply(self, request_processor):
       await self.communicator_service.reply(request_processor)

    async def responder_connect(self):
        self._has_callable('responder_connect')
        await self.communicator_service.responder_connect()

    async def responder_get_request(self, callback):
        self._has_callable('responder_get_request')
        await self.communicator_service.responder_get_request(callback)

    async def responder_post_reply(self, response, context):
        self._has_callable('responder_post_reply')
        await self.communicator_service.responder_post_reply(response, context)

    def _has_callable(self, name):
        """Check if communicator_service has callable attribute of the given name"""
        if not hasattr(self.communicator_service, name):
            raise AttributeError(f"{name} is not an attribute of {type(self.communicator_service)}")
        if not callable(getattr(self.communicator_service, name)):
            raise AttributeError(f"{name} is not a callable attribute of {type(self.communicator_service)}")
