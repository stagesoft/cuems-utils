from time import time, sleep

class Timeoutloop():
    """ universal for time-out loop """
    def __init__(self, timeout, interval=None):
        self.timeout = timeout
        self.delay = interval
    def __iter__(self):
        self.start_time = time()
        return self
    def __next__(self):
        if self.delay is not None:
            sleep(self.delay)
        now = time()
        time_passed = now - self.start_time
        if time_passed > self.timeout: 
            raise TimeoutError(f"Timeout after {self.timeout} seconds")
        else:
            return time_passed
