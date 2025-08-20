from abc import ABC, abstractmethod
from collections.abc import Callable
import asyncio
import json
import os
import sys
from pynng import Req0, Rep0
from functools import partial

from ..log import Logger
from ..helpers import check_path

class CommunicatorService(ABC):
    @abstractmethod
    def __init__(self, address:str):
        self.address = address

    @abstractmethod
    def send_request(self, resquest:dict) -> dict:
        """ Send request dic and return response dict  """

    @abstractmethod
    def reply(self, request_processor:Callable[[dict], dict]) -> dict:
        """ Get request, give it to request processor, and return the response from it  """

class Nng_request_response(CommunicatorService):
    """ Communicates over NNG (nanomsg)  """,

    def __init__(self, address, resquester_dials=True):
        """
        Initialize Nng_request_resopone instance with address and dialing/listening mode.

        Parameters:
        - address (str): The address to connect or listen for connections.
        - resquester_dials (bool, optional): If True, the instance requester will dial the address and replier will listen. If False, it will be the oposite way, requester listens and replier dials. Default is True.

        The instance will set up the parameters for request and reply sockets based on the resquester_dials value.
        """
        self.address = address
        if resquester_dials:
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
                    print(f"Sending: {request}")
                    encoded_request = json.dumps(request).encode()
                    await socket.asend(encoded_request)
                    response = await self._get_response(socket)
                    decoded_response = json.loads(response.decode())
                    print(f"receiving: {decoded_response}")
                    return decoded_response
        except Exception as e:
            Logger.error(f"Error occurred while sending request: {e}")
            return None

    async def _get_response(self, socket):
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



class Communicator(CommunicatorService):
    def __init__(self, address, communicator_service = Nng_request_response, nng_mode=True):
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
        self.nng_mode = nng_mode
        self.communicator_service = communicator_service(self.address, resquester_dials=self.nng_mode)
        
    async def send_request(self, request):
        response = await self.communicator_service.send_request(request)
        return response

    async def reply(self, request_processor):
       await self.communicator_service.reply(request_processor)

    async def responder_connect(self):
        await self.communicator_service.responder_connect()

    async def responder_get_request(self, callback):
        await self.communicator_service.responder_get_request(callback)

    async def responder_post_reply(self, response, context):
        await self.communicator_service.responder_post_reply(response, context)
