"""``cuemsutils.timeoutloop.Timeoutloop`` — the compatibility shim for
``cuems-nodeconf``'s pre-existing ``from cuemsutils.timeoutloop import
Timeoutloop`` (see
``specs/planning/tools-external-consumers-and-timeoutloop-migration.md``,
Track 2). Kept separate from ``tests/contract/test_deprecation_shims.py``,
which pins feature 006's specific twelve-call-site retirement contract; this
shim is unrelated to that feature.
"""

from __future__ import annotations

import warnings

import pytest

from cuemsutils._deprecation import REMOVAL_RELEASE
from cuemsutils.timeoutloop import Timeoutloop
from cuemsutils.tools.TimeoutLoop import TimeoutLoop


def test_the_old_import_path_still_resolves():
    assert Timeoutloop is not None


def test_instances_are_still_isinstance_of_the_real_class():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        loop = Timeoutloop(timeout=1)
    assert isinstance(loop, TimeoutLoop)


def test_constructing_it_warns_with_the_new_path_and_removal_release():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Timeoutloop(timeout=1)

    records = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert records
    text = str(records[0].message)
    assert "cuemsutils.tools.TimeoutLoop.TimeoutLoop" in text
    assert REMOVAL_RELEASE in text


def test_warning_is_reported_at_the_callers_line():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Timeoutloop(timeout=1)  # <- this line

    records = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert records
    assert records[0].filename == __file__


def test_it_still_works_as_a_timeout_iterator():
    """The exact real-world call shape (``cuems-nodeconf``'s
    ``CuemsNodeConf.get_ips``), just via the old import path."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(TimeoutError):
            for _passed in Timeoutloop(timeout=0.05, interval=0.02):
                pass
