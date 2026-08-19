"""``tests.support.roundtrip.wire_diff``/``wire_equal`` — contracts §W1a (T003a).

The one predicate every byte-equality test in feature 006 shares (T005, T030,
T043a). Tested here in isolation, against synthetic payloads, so a defect in
the comparator itself cannot hide behind a real document's complexity.
"""

from __future__ import annotations

from tests.support.roundtrip import wire_diff, wire_equal


def test_equal_payloads_produce_no_diff():
    payload = {"a": 1, "b": [1, 2, {"c": "x"}]}
    assert wire_equal(payload, payload) is True
    assert wire_diff(payload, payload) == []


def test_bool_is_not_int_even_though_they_compare_equal():
    assert True == 1  # noqa: E712 - the premise this test exists to guard
    assert not wire_equal({"a": True}, {"a": 1})
    assert not wire_equal({"a": 1}, {"a": True})


def test_int_is_not_float():
    assert not wire_equal({"a": 1}, {"a": 1.0})


def test_key_order_is_significant():
    assert not wire_equal({"a": 1, "b": 2}, {"b": 2, "a": 1})


def test_list_order_and_length_are_significant():
    assert not wire_equal([1, 2, 3], [3, 2, 1])
    assert not wire_equal([1, 2], [1, 2, 3])


def test_nested_structure_mismatch_is_reported_with_a_path():
    diffs = wire_diff({"a": {"b": [1, {"c": "x"}]}}, {"a": {"b": [1, {"c": "y"}]}})
    assert len(diffs) == 1
    assert diffs[0].startswith("$.a.b[1].c:")


def test_text_compares_as_str_codepoints():
    assert wire_equal({"a": "café"}, {"a": "café"})
