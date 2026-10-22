"""Make ``caplog`` see a CUEMS module's DEBUG records, whatever ``CUEMS_LOG_LEVEL`` says.

``cuemsutils.log.Logger`` logs through one logger per calling module. ``main_logger`` builds that
logger once, sets its level from ``CUEMS_LOG_LEVEL``, and caches it. So lowering the level only
holds if the logger already exists: build it first, then let ``caplog`` set its level, and
``caplog`` restores the level when the test ends.
"""
import logging

from cuemsutils.log import main_logger

#: The ``@logged`` decorator logs from ``cuemsutils.log`` itself.
DECORATOR = "cuemsutils.log"


def capture(caplog, *module_names: str) -> None:
    for name in (*module_names, DECORATOR):
        main_logger(module_name=name)
        caplog.set_level(logging.DEBUG, logger=name)
