# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Adrià Masip <adria@stagelab.coop>

"""A daemon thread that runs an asyncio event loop for NNG communications.

Absorbed from ``cuems-engine`` (``cuemsengine.comms.AsyncCommsThread``), which ``cuems-nodeconf``
had copied. The plan is ``specs/planning/async-comms-thread-absorption.md``.
"""
import asyncio
import threading
from threading import Thread
from typing import Any, Callable, List, Optional

from ..log import Logger

TIMEOUT = 15  # seconds


class AsyncCommsThread(Thread):
    """Base class for asynchronous communication threads.

    This class extends Thread to run an asyncio event loop in a separate daemon
    thread. Subclasses must implement `create_all_tasks()` to define the async
    tasks that will be executed concurrently.

    The event loop runs in the background thread and can be safely accessed
    from other threads using `run_coroutine()`.

    Supervision: a task that raises ends the communications. A task that
    returns ends them only if it was marked with `essential()`; any other task
    may finish early (for instance a listener with nothing to listen for) and
    the rest keep running. When the communications end without `stop()` being
    called, `end_reason` says why, `on_comms_ended()` runs on this thread, and
    the loop stops. The library never exits the process: a subclass decides
    what an ended communications thread means for its service.

    Attributes:
        thread_name (str): Base name for the thread.
        name (str): Full thread name with 'AsyncComms-' prefix.
        timeout (float): Default timeout in seconds for coroutine execution.
        stop_requested (bool): Flag indicating whether thread should stop.
        event_loop (asyncio.AbstractEventLoop): The asyncio event loop running
            in this thread. None until `run()` is called.
        ended (threading.Event): Set once the event loop has stopped, for any
            reason.
        end_reason: None after a requested stop; otherwise the exception a
            task raised, or a message naming the essential task that returned.

    Example:
        Subclass implementation:

        ```python
        class MyAsyncComms(AsyncCommsThread):
            async def my_task(self):
                # Do async work
                pass

            def create_all_tasks(self):
                return [self.essential(asyncio.create_task(self.my_task()))]
        ```
    """

    def __init__(self, **kwargs):
        """Initialize the AsyncCommsThread.

        Creates a daemon thread that will run an asyncio event loop. The thread
        is configured with a name and optional timeout for coroutine execution.

        Args:
            **kwargs: Keyword arguments.
                - thread_name (str, optional): Base name for the thread.
                    Defaults to the name of the subclass.
                - timeout (float, optional): Timeout in seconds for coroutine
                    execution. Defaults to TIMEOUT (15 seconds).

        Note:
            The thread is created as a daemon thread, so it will automatically
            terminate when the main program exits.
        """
        self.thread_name = kwargs.get("thread_name") or type(self).__name__
        Logger.info(f"Initializing AsyncCommsThread: {self.thread_name}")
        super().__init__(name=self.thread_name, daemon=True)
        self.name = f"AsyncComms-{self.thread_name}"
        self.timeout = kwargs.get("timeout", TIMEOUT)
        self.stop_requested = False
        self.event_loop: asyncio.AbstractEventLoop | None = None
        self.ended = threading.Event()
        self.end_reason: BaseException | str | None = None
        self._essential: set = set()

    def run(self) -> None:
        """Thread entry point.

        Creates a new asyncio event loop, schedules the async communications
        task, and runs the event loop until `stop()` is called or the
        communications end. The loop is then closed here, in this thread, so
        any remaining pynng aio is finalized now rather than at interpreter
        exit. This method never raises.
        """
        Logger.info(f"Running {self.name}")
        loop = asyncio.new_event_loop()
        self.event_loop = loop
        try:
            loop.create_task(self.run_asyncio_comms())
            loop.run_forever()
            loop.run_until_complete(self._cancel_tasks())
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception as e:
            Logger.error(f"{self.name} event loop failed: {type(e).__name__}: {e}")
            if self.end_reason is None and not self.stop_requested:
                self.end_reason = e
        finally:
            try:
                loop.close()
            except Exception as e:
                Logger.warning(f"{self.name} could not close its event loop: {e}")
            self.ended.set()
            Logger.info(f"{self.name} event loop closed")

    def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the thread and event loop, and wait for it to terminate.

        Thread-safe method that cancels all pending tasks, stops the event
        loop and joins the thread. Calling it again, before `start()`, or
        after the communications ended by themselves is harmless.

        This MUST block until the thread is gone. The event loop drives NNG
        (pynng) sockets, and pynng registers an atexit hook that calls
        nng_fini(), which destroys NNG's global state. CPython does not join
        daemon threads before running atexit hooks, so if this thread is still
        alive at interpreter shutdown, its next NNG call lands in freed
        internals and aborts the process with
        "panic: pthread_mutex_lock: Invalid argument" (ClickUp 869ed00ya).

        Args:
            timeout: Seconds to wait for task cancellation and for the thread
                to join. Defaults to `self.timeout`.

        Raises:
            RuntimeError: If called from this thread, which cannot join itself.
        """
        if threading.current_thread() is self:
            raise RuntimeError(f"{self.name} cannot stop itself from its own thread")

        self.stop_requested = True
        if timeout is None:
            timeout = self.timeout

        loop = self.event_loop
        # Once end_reason is set the loop is already cancelling its tasks and
        # stopping by itself (typically: on_comms_ended signalled the process,
        # and this is the signal handler). A cancellation posted now could land
        # in a loop that closes before running it, so only join.
        ending = self.ended.is_set() or self.end_reason is not None
        if loop is not None and self.is_alive() and not ending:
            try:
                # Cancel the tasks first and WAIT for them: cancelling the NNG
                # receiver while NNG is still alive lets pynng cancel and free
                # its aio cleanly.
                future = asyncio.run_coroutine_threadsafe(self._cancel_tasks(), loop)
                future.result(timeout=timeout)
            except Exception as e:
                Logger.warning(f"Error cancelling tasks in {self.name}: {e!r}")
            finally:
                # Stop the loop only after cancellation has settled, otherwise
                # the future above can never resolve.
                try:
                    loop.call_soon_threadsafe(loop.stop)
                except RuntimeError:
                    pass  # the loop closed meanwhile

        if self.ident is None:
            # Never started — nothing to join, and join() would raise.
            return

        self.join(timeout=timeout)
        if self.is_alive():
            Logger.error(
                f"{self.name} still alive after {timeout}s — NNG teardown may abort"
            )
        else:
            Logger.info(f"{self.name} stopped and joined")

    @classmethod
    def stop_all(cls, timeout: float = 5) -> None:
        """Stop every live instance of this class (or a subclass) in the process.

        For test teardown and last-resort shutdown paths: every comms thread
        must be gone before pynng's atexit hook finalizes NNG (see `stop()`).
        An instance that fails to stop is logged and the others still stop.
        """
        for thread in threading.enumerate():
            if isinstance(thread, cls) and thread is not threading.current_thread():
                try:
                    thread.stop(timeout=timeout)
                except Exception as e:
                    Logger.error(f"Error stopping {thread.name}: {e!r}")

    async def _cancel_tasks(self) -> None:
        """Cancel every task in this loop except the caller.

        Runs inside the event loop. Deliberately does NOT stop the loop — see
        `stop()`, which stops it once this has settled.
        """
        current_task = asyncio.current_task()
        pending_tasks = [
            task
            for task in asyncio.all_tasks(self.event_loop)
            if task is not current_task and not task.done()
        ]

        for task in pending_tasks:
            task.cancel()

        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
            Logger.debug(f"{self.name} cancelled {len(pending_tasks)} pending tasks")

    async def stop_async(self) -> None:
        """Async stop handler.

        Cancels all running tasks, waits for cleanup, then stops the event
        loop.

        Note:
            This coroutine must run in the same event loop that it stops.
            Prefer `stop()`, which also joins the thread — a caller that
            awaits this alone cannot observe the loop actually stopping,
            because stopping the loop prevents this coroutine's result from
            ever being delivered.
        """
        self.stop_requested = True
        await self._cancel_tasks()

        # Now stop the event loop
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(loop.stop)
        Logger.info(f"{self.name} event loop stopped")

    def essential(self, task: asyncio.Task) -> asyncio.Task:
        """Mark `task` as essential: the communications end when it returns.

        A task that raises always ends them; this only matters for a task that
        returns. Use it on tasks that are meant to run for the life of the
        thread, such as `NngBusHub.start()`, which returns when its bus socket
        closes.

        Returns:
            The same task, so it can wrap `asyncio.create_task(...)` inline.
        """
        self._essential.add(task)
        return task

    async def run_asyncio_comms(self) -> None:
        """Run all async communication tasks, and supervise them.

        Waits for the tasks from `create_all_tasks()` one completion at a
        time. A task that raises, or an essential task that returns, ends the
        communications: `end_reason` is recorded, the other tasks are
        cancelled, `on_comms_ended()` is called and the loop stops. A
        non-essential task that returns is logged and the others keep
        running. Nothing is reported once `stop()` has been requested.
        """
        Logger.info(f"Starting asyncio communications in {self.name}")
        try:
            remaining = set(self.create_all_tasks())
        except Exception as e:
            Logger.error(
                f"{self.name} create_all_tasks failed with {type(e).__name__}: {e}"
            )
            self.end_reason = e
            await self._end_comms(None)
            return
        ended_by = None
        while remaining and not self.stop_requested:
            done, remaining = await asyncio.wait(
                remaining, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                if task.cancelled() or self.stop_requested:
                    continue
                label = self._task_label(task)
                error = task.exception()
                if error is not None:
                    Logger.error(
                        f"{self.name} task {label} failed with "
                        f"{type(error).__name__}: {error}"
                    )
                    self.end_reason = self.end_reason or error
                    ended_by = ended_by or task
                elif task in self._essential:
                    Logger.error(f"{self.name} essential task {label} ended")
                    self.end_reason = self.end_reason or (
                        f"essential task {label} ended"
                    )
                    ended_by = ended_by or task
                else:
                    Logger.info(f"{self.name} task {label} finished")
            if ended_by is not None:
                break

        if ended_by is None or self.stop_requested:
            # Every task finished on its own: the loop keeps running, so
            # run_coroutine() still works.
            Logger.info(f"{self.name} asyncio communications finished")
            return

        await self._end_comms(ended_by)

    async def _end_comms(self, ended_by: Optional[asyncio.Task]) -> None:
        """Cancel the other tasks, call `on_comms_ended()` and stop the loop."""
        await self._cancel_tasks()
        try:
            self.on_comms_ended(ended_by)
        except Exception as e:
            Logger.error(f"{self.name} on_comms_ended raised {type(e).__name__}: {e}")
        asyncio.get_running_loop().stop()

    def on_comms_ended(self, task: Optional[asyncio.Task]) -> None:
        """Called on this thread when the communications end without `stop()`.

        `task` is the task that ended them, and `end_reason` is already set.
        The default only logs. A service overrides it to take its fatal path,
        for instance by sending itself SIGTERM and exiting non-zero so that
        systemd's ``Restart=on-failure`` applies. Anything this raises is
        logged and ignored.
        """
        Logger.error(f"{self.name} communications ended: {self.end_reason}")

    @staticmethod
    def _task_label(task: asyncio.Task) -> str:
        coro = task.get_coro()
        return getattr(coro, "__qualname__", None) or task.get_name()

    def create_all_tasks(self) -> List[asyncio.Task]:
        """Create all async tasks to run concurrently.

        Subclasses must implement this method to return a list of asyncio
        tasks that should run concurrently in the event loop. These tasks
        typically handle various communication channels or services. Wrap the
        ones that must run for the life of the thread in `essential()`.

        Returns:
            List[asyncio.Task]: List of asyncio tasks to run concurrently.

        Raises:
            NotImplementedError: If not implemented by subclass.

        Example:
            ```python
            def create_all_tasks(self):
                return [
                    self.essential(asyncio.create_task(self.listener_task())),
                    asyncio.create_task(self.sender_task()),
                ]
            ```
        """
        raise NotImplementedError("create_all_tasks is not implemented")

    def run_coroutine(
        self,
        coroutine: Callable,
        message: dict,
        timeout: Optional[float] = None,
    ) -> Any:
        """Run a coroutine in the event loop from another thread.

        Thread-safe method to execute a coroutine function in this thread's
        event loop. The coroutine is called with the provided message and
        the result is returned synchronously, with a timeout.

        This is the primary way to interact with the async event loop from
        other threads (e.g., the main thread).

        Args:
            coroutine: A coroutine function to execute. Must be a coroutine
                function (not a regular function).
            message: Dictionary to pass as argument to the coroutine.
            timeout: Optional timeout in seconds (defaults to self.timeout). -1
            means no timeout.

        Returns:
            Any: The return value from the coroutine.

        Raises:
            AttributeError: If the event loop has not been initialized (thread
                not started).
            RuntimeError: If the communications have already ended.
            TypeError: If `coroutine` is not a coroutine function.
            TimeoutError: If the coroutine does not complete within `timeout`
                seconds.
            Exception: If the coroutine raises an exception, it is re-raised
                here.

        Example:
            ```python
            async def send_message(msg: dict) -> dict:
                # Async operation
                return {'status': 'ok'}

            # From another thread:
            result = comms_thread.run_coroutine(send_message, {'data': 'test'})
            ```
        """
        if not self.event_loop:
            raise AttributeError(f"{self.name} event loop is not initialized")

        if self.ended.is_set():
            raise RuntimeError(
                f"{self.name} communications have ended: {self.end_reason or 'stopped'}"
            )

        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError(
                f"{self.name} parameter coroutine is not a coroutine function"
            )

        function_name = coroutine.__name__
        Logger.debug(f"{self.name} running coroutine: {function_name}")

        if timeout is None:
            timeout = self.timeout

        if timeout == -1:
            timeout = None

        send_task = asyncio.run_coroutine_threadsafe(
            coroutine(message), self.event_loop
        )
        try:
            result = send_task.result(timeout=timeout)
            Logger.debug(f"{self.name} {function_name} returned: {result!r}")
            return result
        except TimeoutError:
            Logger.error(f"{self.name} {function_name} timed out after {timeout}s")
            send_task.cancel()
            raise
        except Exception as exc:
            Logger.error(f"{self.name} {function_name} raised an exception: {exc!r}")
            send_task.cancel()
            raise
