import time

from pynng import Bus0, Timeout
import pynng
import socket
import struct

address = "tcp://127.0.0.1:13131"

master = Bus0(listen=address, recv_timeout=100)
slave0 = Bus0(dial=address, recv_timeout=100)
slave1 = Bus0(dial=address, recv_timeout=100)

master.send("test".encode())
while True:
    try:
        message = master.recv_msg(block=False)
        print(f"decode: {message.bytes.decode()}")
        print(f"url: {message.pipe.url}")
        print(f"remote_address: {message.pipe.remote_address}")
        port = socket.ntohs(message.pipe.remote_address.port)
        print(f"remote_address port: {port}")
        as_bytes = struct.pack("I", message.pipe.remote_address.addr)
        ip = socket.inet_ntop(socket.AF_INET, as_bytes)
        print(f"remote_address host: {ip}")
        print(f"dialer: {message.pipe.dialer}")
    except (pynng.exceptions.TryAgain, TypeError):
        pass