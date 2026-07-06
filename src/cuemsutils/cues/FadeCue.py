from enum import Enum

from ..helpers import ensure_items, format_timecode
from ..tools.CTimecode import CTimecode
from .ActionCue import ActionCue

_ZERO_TC = CTimecode('00:00:00.000')


class FadeCurveType(Enum):
    """Enumeration of supported fade curve shapes."""

    linear = 'linear'
    exponential = 'exponential'
    logarithmic = 'logarithmic'
    sigmoid = 'sigmoid'

    def __str__(self):
        return self.value

    def __json__(self):
        return self.value


REQ_ITEMS = {
    'action_type': 'fade_action',
    'curve_type': FadeCurveType.linear,
    'duration': None,
    'target_value': 0,
}


class FadeCue(ActionCue):
    """A cue that fades a target cue's level to a specified value over a duration.

    FadeCue stores all parameters needed by the show engine to execute a smooth
    level transition: the target cue identifier (inherited from ActionCue),
    the curve shape, the fade duration, and the destination level.

    The starting level is recovered from the live runtime state by the engine;
    FadeCue does not store it.
    """

    def __init__(self, init_dict: dict = None):
        """Initialise a FadeCue.

        Args:
            init_dict (dict, optional): Initialisation values. When omitted,
                defaults from REQ_ITEMS are used.

        Raises:
            ValueError: If init_dict explicitly sets action_target to None.
            ValueError: If init_dict sets action_type to a value other than
                'fade_action'.
        """
        if init_dict:
            if init_dict.get('action_type', 'fade_action') != 'fade_action':
                raise ValueError(
                    "action_type must be 'fade_action' for FadeCue"
                )
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            super().__init__(init_dict)
        else:
            # No-args construction: delegate to ActionCue with no dict so all
            # Cue defaults are applied without triggering the action_target guard.
            # Then set FadeCue-specific defaults directly in the underlying dict
            # to avoid calling property setters while _initialized is True.
            super().__init__(None)
            dict.__setitem__(self, 'action_type', 'fade_action')
            dict.__setitem__(self, 'curve_type', FadeCurveType.linear)
            dict.__setitem__(self, 'duration', None)
            dict.__setitem__(self, 'target_value', 0)

    # ------------------------------------------------------------------ #
    # action_type — fixed to 'fade_action'                                #
    # ------------------------------------------------------------------ #

    def get_action_type(self) -> str:
        """Return the action type (always 'fade_action').

        Returns:
            str: 'fade_action'
        """
        return super().get_action_type()

    def set_action_type(self, action_type: str) -> None:
        """Set the action type.

        Args:
            action_type (str): Must be 'fade_action'.

        Raises:
            ValueError: If action_type is not 'fade_action' and the object is
                fully initialised (post-construction assignment).
        """
        if getattr(self, '_initialized', False) and action_type != 'fade_action':
            raise ValueError(
                f"action_type must be 'fade_action' for FadeCue, got '{action_type}'"
            )
        super().set_action_type(action_type)

    action_type = property(get_action_type, set_action_type)

    # ------------------------------------------------------------------ #
    # curve_type                                                           #
    # ------------------------------------------------------------------ #

    def get_curve_type(self) -> FadeCurveType:
        """Return the fade curve type.

        When the underlying dict holds a plain string (e.g. after deserialization
        via GenericParser which bypasses the property setter), it is coerced to the
        correct FadeCurveType member on read so callers always get an enum value.

        Returns:
            FadeCurveType: The current curve type.
        """
        value = super(ActionCue, self).__getitem__('curve_type')
        if isinstance(value, FadeCurveType):
            return value
        return FadeCurveType(value)

    def set_curve_type(self, curve_type) -> None:
        """Set the fade curve type.

        Args:
            curve_type (FadeCurveType | str): A FadeCurveType member or its
                string value ('linear', 'exponential', 'logarithmic', 'sigmoid').

        Raises:
            ValueError: If curve_type is not a recognised value.
        """
        if isinstance(curve_type, FadeCurveType):
            super(ActionCue, self).__setitem__('curve_type', curve_type)
            return
        try:
            super(ActionCue, self).__setitem__('curve_type', FadeCurveType(curve_type))
        except ValueError:
            valid = [e.value for e in FadeCurveType]
            raise ValueError(
                f"curve_type must be one of {valid}, got '{curve_type}'"
            )

    curve_type = property(get_curve_type, set_curve_type)

    # ------------------------------------------------------------------ #
    # duration                                                             #
    # ------------------------------------------------------------------ #

    def get_duration(self):
        """Return the fade duration as a CTimecode.

        Returns:
            CTimecode | None: The fade duration, or None if not yet set.
        """
        return super(ActionCue, self).__getitem__('duration')

    def set_duration(self, duration) -> None:
        """Set the fade duration.

        None is accepted during construction (GenericParser pattern).  Any
        explicit non-None value that resolves to zero or negative is rejected.

        Args:
            duration (str | CTimecode | float | int | None): Timecode-compatible
                value, or None to clear.

        Raises:
            ValueError: If duration is a non-None value that is zero or negative.
        """
        if duration is None:
            super(ActionCue, self).__setitem__('duration', None)
            return
        result = format_timecode(duration)
        if result <= _ZERO_TC:
            raise ValueError('duration must be positive and non-zero')
        super(ActionCue, self).__setitem__('duration', result)

    duration = property(get_duration, set_duration)

    # ------------------------------------------------------------------ #
    # target_value                                                         #
    # ------------------------------------------------------------------ #

    def get_target_value(self) -> int:
        """Return the destination level (0–100 inclusive).

        Returns:
            int: The target level.
        """
        return super(ActionCue, self).__getitem__('target_value')

    def set_target_value(self, target_value: int) -> None:
        """Set the destination level.

        Args:
            target_value (int): Destination level in the range 0–100 inclusive.

        Raises:
            ValueError: If target_value is outside [0, 100].
        """
        value = int(target_value)
        if not (0 <= value <= 100):
            raise ValueError(
                f'target_value must be between 0 and 100, got {value}'
            )
        super(ActionCue, self).__setitem__('target_value', value)

    target_value = property(get_target_value, set_target_value)

    # ------------------------------------------------------------------ #
    # items()                                                              #
    # ------------------------------------------------------------------ #

    def items(self):
        """Return all items with own REQ_ITEMS appended in XSD sequence order.

        The XSD sequence for FadeCueType (extending ActionCueType) is:
        ...CommonProperties..., action_target, action_type,
        curve_type, duration, target_value.

        Returns:
            dict_items: Ordered items suitable for XML serialisation.
        """
        x = dict(super().items())
        for k in ('curve_type', 'duration', 'target_value'):
            x[k] = self[k]
        return x.items()
