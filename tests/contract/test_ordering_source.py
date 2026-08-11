"""Contract C6 (T036) — where element order comes from.

The feature's central claim, asserted structurally rather than through output.
A golden can tell you the bytes are right; only this can tell you they are right
*for the right reason*. Pre-refactor, ``master_vol`` preceded ``fade_profiles``
because a branch in ``MediaCueXmlBuilder.build`` said so by name:

    if key == 'master_vol' or (key == 'opacity' and cls_name == 'VideoCue'):

Both orderings produce identical output on today's corpus. What separates them
is what happens to a field the hardcoded branch has never heard of — which is
why ``test_a_field_declared_out_of_alphabetical_position_still_orders``
exercises the general rule rather than the special case.

**Fail-before-pass**: ``test_engine_contains_no_field_name_ordering_literals``
fails against pre-refactor code, because that branch is precisely a field-name
string comparison used to order output (plan §II).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from cuemsutils.xml import spec as spec_module
from cuemsutils.xml.spec import derive_named, derive_path

#: The engine's live modules. The frozen shims (``Parsers.py``, ``XmlBuilder.py``)
#: are deliberately excluded: they still *contain* the hack, unreachable, until
#: feature 007 removes them. T049 asserts no live path reaches it.
ENGINE_MODULES = (
    "schema.py",
    "spec.py",
    "adapters.py",
    "registry.py",
    "converter.py",
    "mapper.py",
    "xml_reader_writer.py",
    "settings.py",
)

#: Field names that must never appear as ordering literals in engine source.
ORDERING_SENTINELS = ("master_vol", "fade_profiles", "opacity")

ENGINE_DIR = Path(spec_module.__file__).parent


def _existing_engine_sources():
    for name in ENGINE_MODULES:
        path = ENGINE_DIR / name
        if path.exists():
            yield name, path.read_text(encoding="utf-8")


def test_master_vol_precedes_fade_profiles():
    """The ordering itself — necessary, and nowhere near sufficient."""
    spec = derive_named("script", "AudioCueType")
    names = list(spec.field_names)
    assert names.index("master_vol") < names.index("fade_profiles")


def test_the_order_survives_a_shuffled_input():
    """The engine reorders; it does not merely preserve what it was handed."""
    spec = derive_named("script", "AudioCueType")
    assert spec.order_keys(["fade_profiles", "master_vol"]) == [
        "master_vol",
        "fade_profiles",
    ]


def test_engine_contains_no_field_name_ordering_literals():
    """FR-002 — the hack must not exist anywhere in the engine.

    "Not relocated to another module, not re-expressed as a data table."
    Searching the source is crude, and it is exactly right here: the
    requirement is about the *absence* of a construct, which no behavioural
    test can demonstrate.

    This fails against pre-refactor code — ``XmlBuilder.py`` compares ``key``
    to ``'master_vol'`` and ``'opacity'`` to decide emission order.
    """
    offenders = []
    for name, source in _existing_engine_sources():
        for lineno, line in enumerate(source.splitlines(), start=1):
            code = line.split("#", 1)[0]
            for sentinel in ORDERING_SENTINELS:
                if f"'{sentinel}'" in code or f'"{sentinel}"' in code:
                    offenders.append(f"{name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "engine source compares field names as string literals:\n"
        + "\n".join(offenders)
    )


def test_ordering_is_decided_in_exactly_one_place():
    """One rule, one implementation.

    ``TypeSpec.order_keys`` is the only thing that may decide element order.
    Two implementations would drift, and the second would be found by a golden
    failure months later.
    """
    source = inspect.getsource(spec_module.TypeSpec.order_keys)
    assert "self.ordered" in source

    # Every sort in the two modules that shape output must live inside
    # ``order_keys`` — the declared rule. One elsewhere is a second ordering
    # implementation, and two will drift.
    #
    # ``registry.py`` sorts type *names* for error messages, and
    # ``schema.py``/``settings.py`` do not order output at all, so only
    # ``spec.py`` and ``mapper.py`` are in scope.
    offenders = []
    for name, text in _existing_engine_sources():
        if name not in ("spec.py", "mapper.py"):
            continue
        tree = ast.parse(text)
        for parent in ast.walk(tree):
            if not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(parent):
                if not isinstance(node, ast.Call):
                    continue
                target = getattr(node.func, "id", None) or getattr(
                    node.func, "attr", None
                )
                if target in ("sorted", "sort") and parent.name != "order_keys":
                    offenders.append(f"{name}:{node.lineno} in {parent.name}()")

    assert not offenders, (
        "output ordering decided outside TypeSpec.order_keys: " + ", ".join(offenders)
    )


def test_a_field_declared_out_of_alphabetical_position_still_orders():
    """The general rule, not the one pair everyone remembers.

    ``AudioCueType`` has several fields whose declaration order differs from
    alphabetical. All of them must come out in schema order — a hardcoded
    branch would only ever fix the pair it names.
    """
    spec = derive_named("script", "AudioCueType")
    names = list(spec.field_names)
    assert names != sorted(names)

    shuffled = sorted(names)
    assert spec.order_keys(shuffled) == names


@pytest.mark.parametrize(
    "type_name",
    ["AudioCueType", "VideoCueType", "CueListType", "MediaType", "DmxCueType"],
)
def test_order_comes_from_the_schema_for_every_ordered_type(type_name):
    spec = derive_named("script", type_name)
    assert spec.ordered
    assert spec.order_keys(sorted(spec.field_names)) == list(spec.field_names)


def test_order_free_types_are_the_only_exception():
    """FR-001a — arrival order reaches the output nowhere else.

    If an ordered type also passed its keys through untouched, dict iteration
    order would be deciding the bytes and nobody would notice until a
    hand-authored file round-tripped differently.
    """
    order_free = derive_path("script", "CuemsProject/CuemsScript")
    assert not order_free.ordered

    arbitrary = ["ui_properties", "CueList", "id"]
    assert order_free.order_keys(arbitrary) == arbitrary

    ordered = derive_named("script", "AudioCueType")
    assert ordered.order_keys(["ui_properties", "id", "autoload"]) == [
        "autoload",
        "id",
        "ui_properties",
    ]
