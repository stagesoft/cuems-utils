from abc import ABC, abstractmethod
from collections.abc import Callable
import asyncio
import json
import os
import sys
from pynng import Req0, Rep0, Bus0
from pynng import exceptions as pynng_exceptions
from functools import partial
from enum import Enum
from dataclasses import dataclass
import socket
import struct
from datetime import datetime
from typing import Optional, Dict, List, Tuple



@dataclass
class Message:
    data: dict
    sender: str

@dataclass
class ConnectionInfo:
    """Information about an active bus connection."""
    pipe_id: int
    sender: str
    connected_at: datetime

from ..log import Logger
from ..helpers import check_path

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

class HubService(ABC):
    @abstractmethod
    def __init__(self, address:str):
        self.address = address

    @abstractmethod
    def send_message(self, message: dict | Message) -> None:
        """ Add message (dict or Message) to the queue to be sent to hub """

    @abstractmethod
    def get_message(self) -> Message:
        """ Get message from the queue. Message.data is already JSON-decoded as dict """


class Nng_request_response(CommunicatorService):
    """ Communicates over NNG (nanomsg)  """

    def __init__(self, address, requester_dials=True):
        """
        Initialize Nng_request_response instance with address and dialing/listening mode.

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

class Nng_bus_hub(HubService):
    """ Communicates over NNG (nanomsg) using Bus topology for many-to-one, one-to-many messaging """

    class Mode(Enum):
        CONTROLLER = "controller"
        NODE = "node"

    def __init__(self, hub_address:str, mode:Mode=Mode.CONTROLLER):
        """
        Initialize Nng_bus_hub instance with address and operational mode.

        Parameters:
        - hub_address (str): The address to connect or listen for bus connections.
        - mode (Mode, optional): The operational mode - CONTROLLER (listens) or NODE (dials). Default is CONTROLLER.

        The instance will set up incoming and outgoing message queues for asynchronous message handling.
        """
        self.active_connections: Dict[int, ConnectionInfo] = {}  # pipe_id -> ConnectionInfo
        self.address = hub_address
        self.mode = mode
        self.incoming = asyncio.Queue()
        self.outgoing = asyncio.Queue()
        
        # Connection health tracking
        self._last_message_received: Optional[datetime] = None
        self._last_message_sent: Optional[datetime] = None
        self._messages_received_count: int = 0
        self._messages_sent_count: int = 0
        
        # Ping/pong configuration
        self._auto_ping_enabled: bool = False
        self._auto_ping_interval: float = 10.0
        self._auto_ping_task: Optional[asyncio.Task] = None
        self._auto_pong_enabled: bool = True  # Nodes auto-respond by default
        self._ping_count: int = 0
        self._pong_count: int = 0


    async def start(self):
        """
        Start the bus communication by initializing the connection and launching message handlers.

        This method starts the bus connection based on the mode (CONTROLLER or NODE),
        then launches infinite receiver and sender loops. It monitors both tasks and
        exits when the first exception occurs or connection is broken, properly cleaning
        up all running tasks.

        Raises:
        - ValueError: If an unknown mode is set.
        - Exception: Re-raises any exception that occurs during task execution after cleanup.
        """
        match self.mode:
            case self.Mode.CONTROLLER:
                await self.start_hub()
            case self.Mode.NODE:
                await self.start_node()
            case _:
                raise ValueError(f"Unknown mode: {self.mode}")

        try:
            sender_task = asyncio.create_task(self._send_handler())
            receiver_task = asyncio.create_task(self._receiver_handler())
            ping_task = asyncio.create_task(self._auto_ping_handler())
            
            tasks = [sender_task, receiver_task, ping_task]
            
            done_tasks, pending_tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            
            # Check if completed task had an exception
            for task in done_tasks:
                if task.exception() is not None:
                    Logger.error(f"Handler failed with exception: {task.exception()}")
            
            # Cancel and await pending tasks
            for task in pending_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            Logger.error(f"Error occurred while starting tasks: {e} type: {type(e)}")
            # Cancel any running tasks
            for task in [sender_task, receiver_task, ping_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            raise
        


    async def start_hub(self):
        """
        Initialize the bus connection in CONTROLLER mode (listening for connections).
        
        Creates a Bus0 socket that listens on the configured address with a 100ms receive timeout.
        """
        self.connection = Bus0(listen=self.address, recv_timeout=100)
        self._add_callbacks()

    async def start_node(self):
        """
        Initialize the bus connection in NODE mode (dialing to controller).
        
        Creates a Bus0 socket that dials to the configured address with a 100ms receive timeout.
        """
        self.connection = Bus0(dial=self.address, recv_timeout=100)
        self._add_callbacks()

    async def send_message(self, message: dict | Message):
        """
        Queue a message to be sent to the bus.

        Parameters:
        - message (dict | Message): The message to be sent. Must be a dict or Message object with dict data.

        Raises:
        - TypeError: If message is not a dict or Message object, or if Message.data is not a dict.

        The message is JSON-encoded and placed in the outgoing queue to be sent by the sender handler.
        """
        # Extract data from Message object or use raw data
        if isinstance(message, Message):
            data = message.data
            if not isinstance(data, dict):
                raise TypeError(f"Message.data must be a dict, got {type(data).__name__}")
        elif isinstance(message, dict):
            data = message
        else:
            raise TypeError(f"send_message requires dict or Message, got {type(message).__name__}")
        
        # JSON-encode the dict
        json_data = json.dumps(data)
        
        await self.outgoing.put(json_data)

    async def get_message(self) -> Message:
        """
        Retrieve a message from the incoming queue.

        Returns:
        - Message: The next message received from the bus. The `data` field is already JSON-decoded as a dict.
                   This method blocks until a message is available.
        """
        return await self.incoming.get()

    def get_active_connections(self) -> List[ConnectionInfo]:
        """
        Get a list of all active connections.

        Returns:
        - List[ConnectionInfo]: List of all active connection information.
        """
        return list(self.active_connections.values())

    def get_connection_count(self) -> int:
        """
        Get the number of active connections.

        Returns:
        - int: Number of currently active connections.
        """
        return len(self.active_connections)

    def get_connection_health_info(self, activity_timeout: float = 30.0) -> Dict:
        """
        Get connection health information based on message activity.
        
        This is particularly useful for NODEs to check if they're still 
        connected to the controller, since nodes don't track the controller
        connection in active_connections.

        Parameters:
        - activity_timeout: Seconds of inactivity before considering unhealthy (default: 30.0)

        Returns:
        - dict: Health information containing:
            - is_healthy: bool - True if recent activity detected
            - last_received: datetime or None - Last message received time
            - last_sent: datetime or None - Last message sent time
            - seconds_since_activity: float or None - Seconds since last activity
            - messages_received: int - Total messages received
            - messages_sent: int - Total messages sent
        """
        now = datetime.now()
        last_activity = None
        
        # Determine most recent activity
        if self._last_message_received and self._last_message_sent:
            last_activity = max(self._last_message_received, self._last_message_sent)
        elif self._last_message_received:
            last_activity = self._last_message_received
        elif self._last_message_sent:
            last_activity = self._last_message_sent
        
        # Calculate seconds since last activity
        seconds_since_activity = None
        if last_activity:
            seconds_since_activity = (now - last_activity).total_seconds()
        
        # Determine health status
        is_healthy = False
        if seconds_since_activity is not None:
            is_healthy = seconds_since_activity <= activity_timeout
        
        return {
            'is_healthy': is_healthy,
            'last_received': self._last_message_received,
            'last_sent': self._last_message_sent,
            'seconds_since_activity': seconds_since_activity,
            'messages_received': self._messages_received_count,
            'messages_sent': self._messages_sent_count
        }

    def is_connection_healthy(self, activity_timeout: float = 30.0) -> bool:
        """
        Check if the connection is healthy based on recent activity.
        
        Parameters:
        - activity_timeout: Seconds of inactivity before considering unhealthy (default: 30.0)
        
        Returns:
        - bool: True if connection appears healthy
        """
        return self.get_connection_health_info(activity_timeout)['is_healthy']

    def enable_auto_ping(self, interval: float = 10.0, inactivity_threshold: float = 5.0):
        """
        Enable automatic ping mechanism for the controller.
        
        The controller will automatically send ping messages to all nodes if there's
        been no activity for the specified threshold period. Nodes will automatically
        respond with pong messages.
        
        Parameters:
        - interval: How often to check for inactive connections (default: 10.0 seconds)
        - inactivity_threshold: Send ping if no activity for this many seconds (default: 5.0)
        
        Note: This is primarily useful for CONTROLLER mode to verify node connections.
        """
        self._auto_ping_enabled = True
        self._auto_ping_interval = interval
        self._inactivity_threshold = inactivity_threshold
        Logger.info(f"Auto-ping enabled: check every {interval}s, ping after {inactivity_threshold}s inactivity")

    def disable_auto_ping(self):
        """Disable automatic ping mechanism."""
        self._auto_ping_enabled = False
        Logger.info("Auto-ping disabled")

    def enable_auto_pong(self):
        """Enable automatic pong responses (enabled by default)."""
        self._auto_pong_enabled = True
        Logger.debug("Auto-pong enabled")

    def disable_auto_pong(self):
        """Disable automatic pong responses."""
        self._auto_pong_enabled = False
        Logger.debug("Auto-pong disabled")

    async def send_ping(self):
        """
        Manually send a ping message to all connected nodes.
        
        Returns:
        - int: Number of pings sent
        """
        ping_message = {"__type__": "ping", "timestamp": datetime.now().isoformat()}
        await self.send_message(ping_message)
        self._ping_count += 1
        Logger.debug(f"Ping sent (total: {self._ping_count})")
        return 1

    async def _auto_ping_handler(self):
        """
        Internal handler for automatic ping mechanism.
        
        Periodically checks for inactive connections and sends pings if needed.
        Only runs in CONTROLLER mode when auto_ping is enabled.
        """
        if not hasattr(self, '_inactivity_threshold'):
            self._inactivity_threshold = 5.0
            
        while await asyncio.sleep(0, result=True):
            try:
                await asyncio.sleep(self._auto_ping_interval)
                
                if not self._auto_ping_enabled:
                    continue
                
                # Check if we need to send a ping
                now = datetime.now()
                should_ping = False
                
                if self._last_message_sent:
                    seconds_since_last_sent = (now - self._last_message_sent).total_seconds()
                    if seconds_since_last_sent >= self._inactivity_threshold:
                        should_ping = True
                else:
                    should_ping = True  # Never sent anything yet
                
                if should_ping:
                    Logger.debug(f"Sending ping due to inactivity")
                    await self.send_ping()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                Logger.error(f"Error in auto-ping handler: {e}")

    async def _receiver_handler(self):
        """
        Internal handler that continuously receives messages from the bus.

        This infinite loop listens for incoming messages on the bus connection and
        places them in the incoming queue. Timeout exceptions are silently ignored
        to allow continuous polling. Other exceptions are logged.

        The loop runs until cancelled or an unhandled exception occurs.
        """
        while await asyncio.sleep(0, result=True):
            try:
                pynng_message = await self.connection.arecv_msg()
                
                # Extract sender information from the message pipe
                sender = self._extract_sender_info(pynng_message.pipe)
                
                # Decode bytes to string, then parse JSON to dict
                decoded_string = pynng_message.bytes.decode()
                try:
                    data_dict = json.loads(decoded_string)
                except json.JSONDecodeError:
                    Logger.warning(f"Received non-JSON message from {sender}: {decoded_string}")
                    data_dict = {"raw_data": decoded_string}
                
                message = Message(data=data_dict, sender=sender)
                
                # Track message receipt for connection health
                self._last_message_received = datetime.now()
                self._messages_received_count += 1
                
                # Handle ping/pong messages
                handled = await self._handle_ping_pong(message, sender)
                
                if not handled:
                    # Normal message - put in queue for user
                    Logger.debug(f"Received message from {sender}: {message.data}")
                    await self.incoming.put(message)
                    
            except pynng_exceptions.Timeout:
                pass  # Timeout is expected during polling
            except Exception as e:
                Logger.error(f"Error in receiver handler: {e}, type: {type(e)}")

    async def _handle_ping_pong(self, message: Message, sender) -> bool:
        """
        Handle ping/pong messages internally.
        
        Parameters:
        - message: The received message
        - sender: The sender information
        
        Returns:
        - bool: True if message was handled (ping/pong), False if it's a normal message
        """
        try:
            # Data is already parsed as dict
            data = message.data
            message_type = data.get("__type__")
            
            if message_type == "ping":
                # Received ping - send pong if auto-pong enabled
                if self._auto_pong_enabled:
                    pong_message = {
                        "__type__": "pong",
                        "timestamp": datetime.now().isoformat(),
                        "ping_timestamp": data.get("timestamp")
                    }
                    await self.send_message(pong_message)
                    self._pong_count += 1
                    Logger.debug(f"Received ping from {sender}, sent pong (total pongs: {self._pong_count})")
                else:
                    Logger.debug(f"Received ping from {sender} (auto-pong disabled)")
                return True
                
            elif message_type == "pong":
                # Received pong response
                Logger.debug(f"Received pong from {sender}")
                return True
                
        except (AttributeError, TypeError, KeyError):
            # Doesn't have __type__ or invalid structure - treat as normal message
            pass
        
        return False


    async def _send_handler(self):
        """
        Internal handler that continuously sends messages to the bus.

        This infinite loop retrieves messages from the outgoing queue and sends
        them to the bus connection. Any exceptions during sending are logged.

        The loop runs until cancelled or an unhandled exception occurs.
        """
        while await asyncio.sleep(0, result=True):
            try:
                message = await self.outgoing.get()
                Logger.debug(f"Sending message: {message}")
                await self.connection.asend(message.encode())
                
                # Track message send for connection health
                self._last_message_sent = datetime.now()
                self._messages_sent_count += 1
            except Exception as e:
                Logger.error(f"Error in send handler: {e}, type: {type(e)}")

    def _add_callbacks(self):
        self.connection.add_post_pipe_connect_cb(self._post_connect_callback)
        self.connection.add_post_pipe_remove_cb(self._post_remove_callback)

    def _post_connect_callback(self, pipe):
        """Internal callback when a new pipe connects."""
        try:
            sender = self._extract_sender_info(pipe)
            conn_info = ConnectionInfo(
                pipe_id=pipe.id,
                sender=sender,
                connected_at=datetime.now()
            )
            self.active_connections[pipe.id] = conn_info
            Logger.info(f"Connection established - Pipe ID: {pipe.id}, Sender: {sender}")
        except Exception as e:
            Logger.error(f"Error in connect callback: {e}")

    def _post_remove_callback(self, pipe):
        """Internal callback when a pipe disconnects."""
        try:
            conn_info = self.active_connections.pop(pipe.id, None)
            if conn_info:
                Logger.info(f"Connection closed - Pipe ID: {pipe.id}, Sender: {conn_info.sender}")
            else:
                Logger.warning(f"Pipe {pipe.id} disconnected but not found in active connections")
        except Exception as e:
            Logger.error(f"Error in disconnect callback: {e}")
            
    def _extract_sender_info(self, pipe):
        """
        Extract sender information from the message pipe.
        
        Handles both TCP and IPC addresses. For TCP, extracts the IP address.
        For IPC, returns the pipe URL.
        
        Parameters:
        - pipe: The pynng pipe object containing remote address information.
        
        Returns:
        - str: The sender identifier (IP address for TCP, URL for IPC).
        """
        try:
            remote_addr = pipe.remote_address
            # Check if it's a TCP address (has 'addr' attribute)
            if hasattr(remote_addr, 'addr'):
                as_bytes = struct.pack("I", remote_addr.addr)
                ip = socket.inet_ntop(socket.AF_INET, as_bytes)
                port = socket.ntohs(remote_addr.port)
                return (ip, port)
            else:
                # For IPC or other address types, use the pipe URL
                return str(pipe.url) if hasattr(pipe, 'url') else "unknown"
        except Exception as e:
            Logger.debug(f"Error extracting sender info: {e}")
            return "unknown"




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
        self.communicator_service = communicator_service(self.address, requester_dials=self.nng_mode)
        
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
