from __future__ import annotations

from dataclasses import dataclass

import pytest

from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.tools.FadeCalculator import FadeCalculator


@dataclass(frozen=True, slots=True)
class CurveSpec:
    id: str
    method: str
    kwargs: dict
    monotonic: str | None  # "non_decreasing" | "non_increasing" | None
    expected_bounds: tuple[float, float] | None  # (first, last)


CURVE_REGISTRY: list[CurveSpec] = [
    CurveSpec(
        "linear_up",
        "linear",
        dict(length=50, start_value=0.0, end_value=1.0),
        monotonic="non_decreasing",
        expected_bounds=(0.0, 1.0),
    ),
    CurveSpec(
        "linear_down",
        "linear",
        dict(length=50, start_value=1.0, end_value=0.0),
        monotonic="non_increasing",
        expected_bounds=(1.0, 0.0),
    ),
    CurveSpec(
        "sigmoid_up",
        "sigmoid",
        dict(length=101, start_value=0.0, end_value=1.0, inflec=50.0, growth=4.0),
        monotonic="non_decreasing",
        expected_bounds=None,
    ),
    CurveSpec(
        "sigmoid_down",
        "sigmoid",
        dict(length=101, start_value=1.0, end_value=0.0, inflec=50.0, growth=4.0),
        monotonic="non_increasing",
        expected_bounds=None,
    ),
]


def _call(spec: CurveSpec) -> list[float]:
    fn = getattr(FadeCalculator, spec.method)
    out = fn(**spec.kwargs)
    assert isinstance(out, list)
    return out


@pytest.mark.parametrize("spec", CURVE_REGISTRY, ids=lambda s: s.id)
def test_output_length(spec: CurveSpec):
    out = _call(spec)
    assert len(out) == spec.kwargs["length"]


@pytest.mark.parametrize("spec", CURVE_REGISTRY, ids=lambda s: s.id)
def test_boundary_values(spec: CurveSpec):
    out = _call(spec)
    if spec.expected_bounds is None:
        assert out[0] == pytest.approx(spec.kwargs["start_value"])
        return
    first, last = spec.expected_bounds
    assert out[0] == pytest.approx(first)
    assert out[-1] == pytest.approx(last)


@pytest.mark.parametrize("spec", CURVE_REGISTRY, ids=lambda s: s.id)
def test_value_containment(spec: CurveSpec):
    out = _call(spec)
    lo = min(spec.kwargs["start_value"], spec.kwargs["end_value"])
    hi = max(spec.kwargs["start_value"], spec.kwargs["end_value"])
    eps = 1e-12
    assert min(out) >= lo - eps
    assert max(out) <= hi + eps


@pytest.mark.parametrize("spec", CURVE_REGISTRY, ids=lambda s: s.id)
def test_monotonicity(spec: CurveSpec):
    out = _call(spec)
    if spec.monotonic is None:
        return
    diffs = [b - a for a, b in zip(out, out[1:])]
    eps = 1e-12
    if spec.monotonic == "non_decreasing":
        assert min(diffs) >= -eps
    elif spec.monotonic == "non_increasing":
        assert max(diffs) <= eps
    else:
        raise AssertionError(f"Unknown monotonic spec: {spec.monotonic!r}")


@pytest.mark.parametrize("spec", CURVE_REGISTRY, ids=lambda s: s.id)
def test_deterministic(spec: CurveSpec):
    assert _call(spec) == _call(spec)


def test_linear_midpoint():
    length = 51
    start_value = 10.0
    end_value = 20.0
    out = FadeCalculator.linear(length=length, start_value=start_value, end_value=end_value)
    mid = (length - 1) // 2
    assert out[mid] == pytest.approx((start_value + end_value) / 2.0)


def test_linear_exact_values():
    out = FadeCalculator.linear(length=5, start_value=0.0, end_value=1.0)
    assert out == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])


def test_sigmoid_inflection_point_is_midpoint():
    start_value = 0.0
    end_value = 1.0
    inflec = 50.0
    out = FadeCalculator.sigmoid(
        length=101,
        start_value=start_value,
        end_value=end_value,
        inflec=inflec,
        growth=4.0,
    )
    assert out[int(inflec)] == pytest.approx((start_value + end_value) / 2.0)


def test_sigmoid_growth_steepness():
    low = FadeCalculator.sigmoid(
        length=101, start_value=0.0, end_value=1.0, inflec=50.0, growth=2.0
    )
    high = FadeCalculator.sigmoid(
        length=101, start_value=0.0, end_value=1.0, inflec=50.0, growth=8.0
    )
    # A steeper curve should be closer to 0 before inflection and closer to 1 after.
    assert high[30] < low[30]
    assert high[70] > low[70]


def test_sigmoid_endpoints_are_near_end_value():
    up = FadeCalculator.sigmoid(
        length=101, start_value=0.0, end_value=1.0, inflec=50.0, growth=4.0
    )
    down = FadeCalculator.sigmoid(
        length=101, start_value=1.0, end_value=0.0, inflec=50.0, growth=4.0
    )
    # Implementation is asymptotic; it won't hit end_value exactly for finite length.
    assert up[-1] >= 0.90
    assert down[-1] <= 0.10


@pytest.mark.parametrize("method", ["linear", "sigmoid"])
def test_flat_line(method: str):
    if method == "linear":
        out = FadeCalculator.linear(length=20, start_value=0.5, end_value=0.5)
    else:
        out = FadeCalculator.sigmoid(
            length=101, start_value=0.5, end_value=0.5, inflec=50.0, growth=4.0
        )
    assert out == pytest.approx([0.5] * len(out))


@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("linear", dict(length=2, start_value=0.0, end_value=1.0)),
    ],
)
def test_length_2(method: str, kwargs: dict):
    out = getattr(FadeCalculator, method)(**kwargs)
    assert out[0] == pytest.approx(kwargs["start_value"])
    assert out[-1] == pytest.approx(kwargs["end_value"])


@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("linear", dict(length=1, start_value=0.0, end_value=1.0)),
    ],
)
def test_length_1_is_rejected(method: str, kwargs: dict):
    # Define "length=1" as invalid for fade curves (no transition).
    with pytest.raises(Exception):
        getattr(FadeCalculator, method)(**kwargs)


def test_sigmoid_length_1_returns_start_value():
    out = FadeCalculator.sigmoid(
        length=1, start_value=0.25, end_value=1.0, inflec=1.0, growth=4.0
    )
    assert out == pytest.approx([0.25])


def test_large_length():
    out = FadeCalculator.linear(length=10_000, start_value=0.0, end_value=1.0)
    assert out[0] == pytest.approx(0.0)
    assert out[-1] == pytest.approx(1.0)


def test_apply_function_to_range_identity():
    out = FadeCalculator._apply_function_to_range(5, lambda i: i)
    assert out == [0, 1, 2, 3, 4]


def test_apply_to_100_size():
    out = FadeCalculator._apply_to_100(lambda i: i)
    assert len(out) == 100
    assert out[0] == 0
    assert out[-1] == 99


def test_apply_to_list():
    out = FadeCalculator._apply_to_list([1, 2, 3], lambda i: i * 2)
    assert out == [2, 4, 6]


def test_rescale_known_mapping():
    out = FadeCalculator._rescale([0, 50, 100], 0, 100, 0.0, 1.0)
    assert out == pytest.approx([0.0, 0.5, 1.0])


def test_sample_values_preserves_endpoints():
    x = list(range(100))
    out = FadeCalculator._sample_values(x, 5)
    assert out[0] == 0
    assert out[-1] == 99
    assert len(out) == 5


def test_calculate_timeline_step_count_and_boundaries():
    start = CTimecode(start_timecode="00:00:00.000", framerate="ms")
    end = CTimecode(start_timecode="00:00:00.100", framerate="ms")
    tl = FadeCalculator.calculate_timeline(start, end, framerate="ms")

    expected_steps = (end.milliseconds - start.milliseconds) // FadeCalculator.TRANSITION_DURATION_MILLISECONDS
    assert len(tl) == expected_steps
    assert tl[0] == str(start)
    assert tl[-1] == str(end)


def test_calculate_timeline_rejects_equal_or_reversed():
    t = CTimecode(start_timecode="00:00:00.100", framerate="ms")
    with pytest.raises(ValueError):
        FadeCalculator.calculate_timeline(t, t, framerate="ms")
    with pytest.raises(ValueError):
        FadeCalculator.calculate_timeline(
            t,
            CTimecode(start_timecode="00:00:00.000", framerate="ms"),
            framerate="ms",
        )


def test_calculate_timeline_rejects_non_ctimecode():
    start = "00:00:00.000"
    end = "00:00:00.100"
    with pytest.raises(ValueError):
        FadeCalculator.calculate_timeline(start, end, framerate="ms")


def test_calculate_with_string_name():
    start = CTimecode(start_timecode="00:00:00.000", framerate="ms")
    end = CTimecode(start_timecode="00:00:00.100", framerate="ms")
    out = list(
        FadeCalculator.calculate(
            "linear",
            start_time=start,
            end_time=end,
            framerate="ms",
            length=5,
            start_value=0.0,
            end_value=1.0,
        )
    )
    assert len(out) == 5
    assert out[0][1] == pytest.approx(0.0)
    assert out[-1][1] == pytest.approx(1.0)


def test_calculate_with_callable():
    start = CTimecode(start_timecode="00:00:00.000", framerate="ms")
    end = CTimecode(start_timecode="00:00:00.100", framerate="ms")

    def fn(length: int, start_value: float, end_value: float):
        return FadeCalculator.linear(length=length, start_value=start_value, end_value=end_value)

    out = list(
        FadeCalculator.calculate(
            fn,
            start_time=start,
            end_time=end,
            framerate="ms",
            length=5,
            start_value=0.0,
            end_value=1.0,
        )
    )
    assert len(out) == 5


def test_calculate_invalid_name():
    start = CTimecode(start_timecode="00:00:00.000", framerate="ms")
    end = CTimecode(start_timecode="00:00:00.100", framerate="ms")
    with pytest.raises(ValueError, match="Invalid fade function name"):
        list(
            FadeCalculator.calculate(
                "nope",
                start_time=start,
                end_time=end,
                framerate="ms",
                length=5,
                start_value=0.0,
                end_value=1.0,
            )
        )


def test_calculate_non_callable():
    with pytest.raises(ValueError, match="Invalid fade function"):
        FadeCalculator.calculate(123)

