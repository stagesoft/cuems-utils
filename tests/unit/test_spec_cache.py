"""Derivation count (T064) — SC-PERF-002.

"Derivation does not grow with object count", expressed as something countable
rather than as a timing. A clock would measure the machine; a count measures
the design.

This is also the assertion that keeps the cyclic content models terminating:
``CueListType`` → ``CueListContentsType`` → ``CueListType`` is a real cycle, and
the memo is what makes derivation both finite and bounded. One mechanism,
two guarantees (research R8).
"""

from __future__ import annotations

import warnings

import pytest

from cuemsutils.xml import schema as schema_module
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import clear_cache, derivation_count, derive_named
from tests.support import roundtrip as rt
from tests.support.corpus import by_relpath

SCRIPT = "cuems-editor/script_minimal.xml"
COMPLEX = "cuems-engine/projects/complex_test/script.xml"

def _total_complex_types() -> int:
    """Every ``TypeKey`` derivation could reach, across all six schemas.

    **Computed, not written down.** It used to be the literal ``56``, carried
    from feature 004's plan ("6 schemas, 56 complex types") and never updated —
    008's plan had already hedged it to "~56". Measured 2026-09-04 the real
    figure is **58** (50 named types + 8 path-bound), so the constant had been
    two low for some time.

    That staleness was invisible because every assertion using it is ``<=``, and
    the two fixture documents never derive the whole set. It was still a trap: a
    document reaching 57 or 58 types would have failed these tests as a
    *performance regression* when the behaviour was correct.

    Deriving it removes the trap without weakening SC-PERF-002. The bound was
    only ever a sanity check; the requirement — "derivation does not grow with
    object count" — is carried by
    :func:`test_derivation_does_not_grow_with_object_count` and
    :func:`test_a_thousand_cues_derive_no_more_than_one`, which compare counts
    against each other rather than against a ceiling.
    """
    from cuemsutils.xml.registry import get_registry

    return sum(
        len(get_registry(name).bound_type_names) + len(get_registry(name).bound_path_names)
        for name in SCHEMA_NAMES
    )


TOTAL_COMPLEX_TYPES = _total_complex_types()


def test_the_ceiling_is_not_vacuous():
    """Guards the computation above.

    A derived bound that silently became huge — or zero — would make every
    ``<=`` assertion in this file pass while measuring nothing. The floor is the
    count at the time of writing; the ceiling catches a registry that started
    reporting nonsense.
    """
    assert 50 <= TOTAL_COMPLEX_TYPES <= 200, TOTAL_COMPLEX_TYPES


def _load(relpath):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = by_relpath(relpath)
        return rt.write_bytes(doc, rt.read_objects(doc))


def test_derivation_count_is_bounded_by_distinct_types():
    clear_cache()
    _load(SCRIPT)
    assert derivation_count() <= TOTAL_COMPLEX_TYPES


def test_derivation_does_not_grow_with_object_count():
    """The requirement itself.

    ``complex_test/script.xml`` holds many more cues than
    ``script_minimal.xml`` and reaches roughly the same set of *types*. If
    derivation ran per object the two counts would diverge sharply.
    """
    clear_cache()
    _load(SCRIPT)
    after_small = derivation_count()

    clear_cache()
    _load(COMPLEX)
    after_large = derivation_count()

    assert after_large <= TOTAL_COMPLEX_TYPES
    assert abs(after_large - after_small) <= 6, (after_small, after_large)


def test_reprocessing_the_same_document_derives_nothing_new():
    """The cache is a cache, not a per-call table."""
    clear_cache()
    _load(SCRIPT)
    baseline = derivation_count()
    for _ in range(5):
        _load(SCRIPT)
    assert derivation_count() == baseline


def test_a_thousand_cues_derive_no_more_than_one():
    """The scale the requirement is really about.

    A per-object derivation would be invisible on a five-cue fixture and fatal
    on a real show file.
    """
    from cuemsutils.cues.ActionCue import ActionCue

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = by_relpath(SCRIPT)
        obj = rt.read_objects(doc)

    clear_cache()
    rt.write_bytes(doc, obj)
    baseline = derivation_count()

    contents = obj["CueList"]["contents"]
    template = next(c for c in contents if type(c) is ActionCue)
    for _ in range(1000):
        contents.append(template)

    rt.write_bytes(doc, obj)
    assert derivation_count() == baseline


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_schema_loads_once_per_process(schema_name):
    """Parsing an XSD is expensive and its result is immutable in use."""
    first = schema_module.get_schema(schema_name)
    for _ in range(10):
        assert schema_module.get_schema(schema_name) is first


def test_derive_returns_the_identical_spec_object():
    clear_cache()
    first = derive_named("script", "AudioCueType")
    assert derive_named("script", "AudioCueType") is first


def test_clearing_the_cache_resets_the_count():
    """Without this the assertions above could pass on a stale count."""
    _load(SCRIPT)
    assert derivation_count() > 0
    clear_cache()
    assert derivation_count() == 0
