# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a cached descriptor must keep true — ``specs/planning/descriptor-instance-cache.md``.

Written **before** the cache (phase 1) and green on the uncached tree: each test
pins behaviour a caller relies on today, so the cache is measured against it
rather than defining it.

* **The leaves are immutable scalars.** Every leaf of every instance is exactly
  ``str``/``int``/``float``/``bool``/``None`` and every container is exactly
  ``dict``/``list``. That is what makes copying the containers a *complete*
  copy — the copy-safety question feature 015 left open (its ``baseline.md``,
  "Exceeded, recorded as exceeded" item 1), answered by measurement. Exact
  types, not ``isinstance``: a ``CuemsDict`` is a ``dict`` subclass, and a
  ``Uuid``/``CTimecode`` leaf is an object a container copy would share.
* **A returned instance is the caller's.** Callers mutate it (``cuems-editor``
  fills one in to build a document), and the next caller must not see that.
* **Repeated calls agree.** A cache must not change the answer.
"""

from __future__ import annotations

import json

import pytest

from cuemsutils.xml import descriptor
from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import TypeKey

_SCALARS = (str, int, float, bool, type(None))


def _canonical(type_descriptors) -> str:
    return json.dumps(
        [[str(td.key), td.instance] for td in type_descriptors], sort_keys=True
    )


def _non_scalar_leaves(value, path="$"):
    kind = type(value)
    if kind is dict:
        for key, item in value.items():
            yield from _non_scalar_leaves(item, f"{path}.{key}")
    elif kind is list:
        for index, item in enumerate(value):
            yield from _non_scalar_leaves(item, f"{path}[{index}]")
    elif kind not in _SCALARS:
        yield f"{path}: {kind.__module__}.{kind.__qualname__}"


#: No schema declares a field or value of this name, so finding it in a fresh
#: result means a mutation leaked — from this test or from **any earlier one**.
#: Comparing before/after alone is blind to the second case: once an earlier
#: test has vandalised a shared object, "before" is already vandalised too.
_MARK = "__vandalised_by_test_descriptor_cache__"


def _vandalise(value) -> None:
    """Mutate every container in ``value``, innermost first, so a shared
    nested container is caught as well as a shared top-level one."""
    if type(value) is dict:
        for item in list(value.values()):
            _vandalise(item)
        value.clear()
        value[_MARK] = True
    elif type(value) is list:
        for item in list(value):
            _vandalise(item)
        value.clear()
        value.append(_MARK)


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_instance_leaves_are_immutable_scalars(schema_name):
    found = [
        f"{td.key}: {leaf}"
        for td in SchemaDescriptor().types(schema_name)
        for leaf in _non_scalar_leaves(td.instance)
    ]
    assert not found, "an instance carries a mutable or identity-carrying leaf:\n" + "\n".join(
        found
    )


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_a_returned_instance_is_independent(schema_name):
    before = _canonical(SchemaDescriptor().types(schema_name))
    assert _MARK not in before, "an earlier test's mutation leaked into this one"

    for td in SchemaDescriptor().types(schema_name):
        _vandalise(td.instance)

    after = _canonical(SchemaDescriptor().types(schema_name))
    assert _MARK not in after
    assert after == before


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_a_described_instance_is_independent(schema_name):
    """The same through ``describe()``, the single-type entry point."""
    descriptor = SchemaDescriptor()
    for td in descriptor.types(schema_name):
        before = json.dumps(td.instance, sort_keys=True)
        assert _MARK not in before, f"{td.key}: an earlier mutation leaked into this one"
        _vandalise(descriptor.describe(td.key).instance)
        after = json.dumps(descriptor.describe(td.key).instance, sort_keys=True)
        assert _MARK not in after, td.key
        assert after == before, td.key


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_repeated_calls_are_equal(schema_name):
    assert SchemaDescriptor().types(schema_name) == SchemaDescriptor().types(schema_name)


# --- the cache itself (phase 2) ----------------------------------------------


@pytest.fixture
def fresh_cache():
    """An empty descriptor cache, emptied again afterwards, so a monkeypatched
    build never outlives its test."""
    descriptor.clear_cache()
    yield
    descriptor.clear_cache()


def test_the_cache_rejects_a_mutable_leaf(fresh_cache, monkeypatch):
    """If a seed ever yields a value object, the cache must refuse it rather
    than hand one shared object to every caller."""
    from cuemsutils.tools.CTimecode import CTimecode

    monkeypatch.setattr(
        descriptor, "_instance_for", lambda key: {"duration": CTimecode("00:00:01.000")}
    )
    key = TypeKey("script", "MediaType")

    with pytest.raises(TypeError, match=r"script:MediaType.*CTimecode at \$\.duration"):
        SchemaDescriptor().describe(key)


def test_the_cache_is_hit(fresh_cache, monkeypatch):
    """A warm call builds no instance at all. Counted, not timed, so box
    contention cannot make it flaky (CLAUDE.md, feature 015's sampling lesson)."""
    SchemaDescriptor().types("script")

    calls = []
    original = descriptor._instance_for
    monkeypatch.setattr(
        descriptor, "_instance_for", lambda key: calls.append(key) or original(key)
    )
    SchemaDescriptor().types("script")

    assert calls == []
