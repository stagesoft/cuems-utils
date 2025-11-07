import asyncio
import json
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from functools import partial
from deprecated import deprecated
from pynng import Req0, Rep0

from ..log import Logger
from ..helpers import check_path

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
    def send_request(self, request:dict) -> dict:
        """ Send request dic and return response dict  """

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

    async def send_request(self, request):
        """
        Send a request to the specified address and return the response.

        Parameters:
        - request (dict): The request to be sent. It should be a dictionary.

        Returns:
        - dict: The response received from the address. It will be a dictionary.
        """
        try:
            with Req0(**self.params_request) as socket:
                while await asyncio.sleep(0, result=True):
                    Logger.debug(f"Sending: {request}")
                    encoded_request = json.dumps(request).encode()
                    await socket.asend(encoded_request)
                    response = await self._get_response(socket)
                    decoded_response = json.loads(response.decode())
                    Logger.debug(f"receiving: {decoded_response}")
                    return decoded_response
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
        response = await socket.arecv()
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
            with Rep0(**self.params_reply) as socket:
                while await asyncio.sleep(0, result=True):
                    request = await socket.arecv()
                    decoded_request = json.loads(request.decode())  # Parse the JSON request
                    Logger.debug(f"Received: {decoded_request}")
                    if asyncio.iscoroutinefunction(request_processor):
                        response = await request_processor(decoded_request)
                    else:
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(None, partial(request_processor, decoded_request))
                    await self._respond(socket, response)
        except Exception as e:
            Logger.error(f"Error occurred while handling request: {e}")

    async def _respond(self, socket, response):
        try:
            encoded_response = json.dumps(response).encode()
            Logger.debug(f"Sending: {encoded_response}")
            await socket.asend(encoded_response)
        except Exception as e:
            Logger.error(f"Error occurred while sending response: {e}")

    async def responder_connect(self):
        self.responder = Rep0(**self.params_reply)

    async def responder_get_request(self, callback):
        try:
            context = self.responder.new_context()
            request = await context.arecv()
            decoded_request = json.loads(request.decode())  # Parse the JSON request
            Logger.debug(f"Received: {decoded_request}")
            if asyncio.iscoroutinefunction(callback):
                Logger.debug(f"Calling callback function async")
                await callback(decoded_request, context)
            else:
                loop = asyncio.get_event_loop()
                Logger.debug(f"Calling sync callback function in executor")
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
        try:
            check_path(address)
        except PermissionError as e:
            Logger.error(e)
            sys.exit(1)
        except FileNotFoundError:
            try:
                check_path(address, dir_only = True)
            except (NotADirectoryError, PermissionError) as e:
                Logger.error(e)
                sys.exit(1)

        if address[0:6] != 'ipc://':
            address = "ipc://" + address
        self.address = address
        self.requester_dials = requester_dials
        self.communicator_service:CommunicatorService = communicator_service(self.address, requester_dials=self.requester_dials)
        
    async def send_request(self, request):
        response = await self.communicator_service.send_request(request)
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
