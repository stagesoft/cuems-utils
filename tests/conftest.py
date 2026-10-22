import functools
import importlib
import os as _os

import pytest as _pytest


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


# Paths are relative to this directory. Feature 017 moved these modules out of the tests/ root
# (FR-063), and the globs moved with them: a stale glob silently stops gating.
collect_ignore_glob = []

if not _module_available("pynng"):
    collect_ignore_glob += [
        "integration/test_communicatorservices.py", "integration/test_hubservices.py",
        "unit/test_communicatorservices.py", "unit/test_hubservices.py",
    ]

# systemd is NOT skipped: systemd-python is in the hatch test environment, so a missing module is a
# failure to see (tests/contract/test_systemd_dependency.py).


# ---------------------------------------------------------------------------
# Feature 011, T006 — the suite must not depend on a host /etc/cuems.
#
# Measured 2026-09-25 on a fresh box: 25 tests errored because four modules
# constructed ``ConfigManager(load_all=False)`` with no ``config_dir`` while
# ``tests/support/config_inventory.py`` pops ``CUEMS_CONF_PATH`` from the
# environment at import time, so the constructor's ``/etc/cuems/`` default had
# to exist on the developer's machine — the very condition the feature exists
# to remove. This guard makes that dependence a named failure instead of a
# ``FileNotFoundError`` three frames down.
# ---------------------------------------------------------------------------

@_pytest.fixture(autouse=True, scope="session")
def _no_host_etc_cuems_dependence():
    from cuemsutils.tools import ConfigManager as _cm

    original = _cm.ConfigManager.__init__
    default_dir = _cm.CUEMS_CONF_PATH

    @functools.wraps(original)  # keeps the signature the public API golden pins
    def guarded(self, config_dir=default_dir, load_all=True, *args, **kwargs):
        # CUEMS_CONF_PATH redirects load_base_settings, so a default config_dir
        # under a set variable is hermetic; only the bare default is the defect.
        if (config_dir == default_dir and not _os.path.isdir(default_dir)
                and not _os.environ.get("CUEMS_CONF_PATH")):
            _pytest.fail(
                f"{_os.environ.get('PYTEST_CURRENT_TEST', '<unknown test>')} constructs "
                "ConfigManager() without config_dir and would read the host's "
                f"{default_dir}. Pass config_dir=<corpus> explicitly (feature 011, T006)."
            )
        return original(self, config_dir, load_all, *args, **kwargs)

    _cm.ConfigManager.__init__ = guarded
    try:
        yield
    finally:
        _cm.ConfigManager.__init__ = original


# --- the directory is the marker (feature 017, FR-063) --------------------------------
#
# Every test lives in exactly one of tests/{unit,integration,contract,packaging}/, and gets that
# kind as a marker from its path, so `pytest -m unit` (or integration, contract, packaging) selects
# by kind without each module having to remember a `pytestmark`. The release line used to add tests
# at the tests/ root; tests/contract/test_test_layout.py now refuses that.
_KINDS = ("unit", "integration", "contract", "packaging")
_TESTS_ROOT = _os.path.dirname(_os.path.abspath(__file__))


def pytest_collection_modifyitems(config, items):
    for item in items:
        relative = _os.path.relpath(str(item.path), _TESTS_ROOT)
        kind = relative.split(_os.sep, 1)[0]
        if kind in _KINDS:
            item.add_marker(getattr(_pytest.mark, kind))
        # Feature 017, FR-071: the gate summary counts these from the JUnit XML, which
        # records user_properties but not markers.
        if item.get_closest_marker("reads_siblings") is not None:
            item.user_properties.append(("reads_siblings", "true"))
