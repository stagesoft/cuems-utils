import time

from pynng import Bus0, Timeout
import pynng

wait_time = 0.01
address = "tcp://127.0.0.1:13131"

slave0 = Bus0(dial=address, recv_timeout=100)
slave1 = Bus0(dial=address, recv_timeout=100)


while True:
    try:
        slave0.send("soy slave0".encode())
        time.sleep(wait_time)
        slave1.send("soy slave1".encode())
        time.sleep(wait_time)

    except pynng.exceptions.TryAgain:
        pass