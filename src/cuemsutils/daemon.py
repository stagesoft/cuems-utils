#!/usr/bin/env python3
"""
Daemon mode support for CUEMS engines.

WARNING: DO NOT USE with systemd services!
=========================================

The python-daemon library's DaemonContext causes NNG connections to fail.
When entering the context, python-daemon performs:

1. Double-fork: Creates a new process detached from the terminal. Only the
   calling thread survives the fork - any threads created before fork are lost.

2. File descriptor cleanup: Closes ALL open file descriptors except those
   explicitly listed in files_preserve. This can close sockets, pipes, and
   other resources that libraries (like NNG) may have opened internally.

3. Signal handler reset: Resets signal handlers which may interfere with
   how NNG handles internal signals for its worker threads.

4. Session leader: Becomes a new session leader, which changes process
   group behavior.

The result: NNG connections disconnect approximately 0.43 seconds after
establishment, likely due to internal NNG resources being invalidated by
the fork/cleanup process.

SOLUTION: For systemd-managed services, use foreground mode (no --daemon flag).
Systemd is already a process supervisor, so the daemon layer is redundant.

This module is preserved only for edge cases where traditional Unix daemon
behavior is absolutely required outside of systemd.
"""

import sys
from pathlib import Path
from typing import Any
from daemon import DaemonContext

from .log import Logger

def run_daemon(engine_instance: Any, pid_name: str) -> None:
    """
    Run an engine instance as a traditional Unix daemon.
    
    WARNING: INCOMPATIBLE with NNG (pynng) communications!
    ======================================================
    python-daemon's DaemonContext.open() performs:
    - Double fork (detaches from terminal, only main thread survives)
    - Closes all file descriptors (may close NNG internal sockets)
    - Resets signal handlers (may break NNG thread signaling)
    - Changes working directory and umask
    
    These operations corrupt NNG's internal state, causing connections
    to disconnect ~0.43 seconds after establishment.
    
    For systemd services: Run WITHOUT --daemon flag (foreground mode).
    
    Args:
        engine_instance: Instance of an engine (NodeEngine or ControllerEngine)
        pid_name: Name to use for the PID file (without extension)
    """
    # Ensure log directory exists
    Path('/var/log/cuems').mkdir(parents=True, exist_ok=True)
    
    # Create daemon context
    context = DaemonContext(
        working_directory='/',
        umask=0o002,
        pidfile=Path(f'/var/run/cuems/{pid_name}.pid'),
        files_preserve=[sys.stdout, sys.stderr]
    )
    
    # Start daemon
    with context:
        try:
            engine_instance.start()
        except Exception as e:
            Logger.error(f"Engine failed: {e}")
            sys.exit(1)
