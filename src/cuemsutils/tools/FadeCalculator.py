from collections.abc import Callable

from .CTimecode import CTimecode


class FadeCalculator:
    TIMELINE_PARAMS = [
        'start_time',
        'end_time',
        'framerate',
        'drop_frame'
    ]

    TRANSITION_DURATION_MILLISECONDS = 20

    @staticmethod
    def calculate(fade_function: Callable | str, **kwargs) -> dict[str, float]:
        """
        Calculate a timeline of timecodes between start_time and end_time.

        Args:
            fade_function: The fade function to apply to the timeline.
            **kwargs: Additional keyword arguments to pass to the timeline calculation and the fade function.

        Returns:
            A list of tuples, each containing a timecode and the value of the fade function at that timecode.

        Raises:
            ValueError: If fade_function is a string and not a valid function name of FadeCalculator.
        """
        timeline_args = {k: v for k,v in kwargs.items() if k in FadeCalculator.TIMELINE_PARAMS}
        for k in timeline_args.keys():
            kwargs.pop(k)
        if isinstance(fade_function, str):
            if not hasattr(FadeCalculator, fade_function):
                raise ValueError(f"Invalid fade function name: {fade_function}")
            fade_function = getattr(FadeCalculator, fade_function)
        if not callable(fade_function):
            raise ValueError(f"Invalid fade function: {fade_function}")
        timeline = FadeCalculator.calculate_timeline(**timeline_args)
        return zip(timeline, fade_function(**kwargs), strict=True)

    @staticmethod
    def calculate_timeline(start_time: CTimecode, end_time: CTimecode, **kwargs) -> list[str]:
        """
        Calculate a timeline of timecodes between start_time and end_time. It does not allow for a zero duration resulting timeline.

        Args:
            start_time: The start timecode.
            end_time: The end timecode.
            **kwargs: Additional keyword arguments to pass to the CTimecode constructor.

        Returns:
            A list of timecodes as strings.

        Raises:
            ValueError: If start_time or end_time are not of type CTimecode.
            ValueError: If the duration is less than or equal to 0.
        """
        if not (isinstance(start_time, CTimecode) and isinstance(end_time, CTimecode)):
            raise ValueError("start_time and end_time must be of type CTimecode")
        if start_time.milliseconds >= end_time.milliseconds:
            raise ValueError("start_time must be before end_time")
        duration = (end_time.milliseconds - start_time.milliseconds)
        steps = duration // FadeCalculator.TRANSITION_DURATION_MILLISECONDS
        out = [
            str(
                CTimecode(
                    start_seconds=(
                        start_time.milliseconds
                        + i * FadeCalculator.TRANSITION_DURATION_MILLISECONDS
                    ),
                    **kwargs,
                )
            )
            for i in range(int(steps))
        ]
        out[-1] = str(end_time)
        return out

    # --- Fade curve functions ---
    @staticmethod
    def linear(length: int, start_value: float, end_value: float) -> dict[str, float]:
        slope = (end_value - start_value) / (length - 1)

        def fn(x: float) -> float:
            return start_value + slope * x

        return FadeCalculator._apply_function_to_range(length, fn)

    @staticmethod
    def sigmoid(length: int, start_value: float, end_value: float, inflec: float, growth: float) -> float:

        def fn(x: float) -> float:
            return (start_value - end_value) / (1 + (x / inflec) ** growth) + end_value

        return FadeCalculator._apply_function_to_range(length, fn)

    # --- Internal helper methods ---
    @staticmethod
    def _apply_to_100(function: Callable, **kwargs) -> list[float]:
        return [function(i, **kwargs) for i in range(100)]

    @staticmethod
    def _apply_to_list(x: list[float|int], function: Callable, **kwargs) -> list[float]:
        return [function(i, **kwargs) for i in x]

    @staticmethod
    def _apply_function_to_range(length: int, function: Callable, **kwargs) -> list[float]:
        return [function(i, **kwargs) for i in range(length)]

    @staticmethod
    def _rescale(x: list[float|int], in_min: float | int, in_max: float | int, out_min: float | int, out_max: float | int) -> list[float]:

        def fn(xv: float | int) -> float:
            return (out_max - out_min) * (xv - in_min) / (in_max - in_min) + out_min

        return FadeCalculator._apply_to_list(x, fn)

    @staticmethod
    def _sample_values(x: list[float|int], n: int) -> list:
        if n < 0:
            raise ValueError("n must be >= 0")
        if n == 0:
            return []
        if len(x) == 0:
            return []

        # Map n evenly-spaced indices over [0, len(x)-1]
        idx = FadeCalculator._rescale(
            list(range(n)),
            0,
            max(1, n - 1),
            0,
            len(x) - 1,
        )
        return [x[round(i)] for i in idx]
