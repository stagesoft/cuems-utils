import math

from ..helpers import CuemsDict, ensure_items

FADE_PARAM_REQ_ITEMS = {
    'parameter_name': '',
    'parameter_value': 0.0,
}

FADE_PROFILE_REQ_ITEMS = {
    'type': 'in',
    'mode': 'preset',
    'function_id': '',
    'parameters': None,
}

VALID_FADE_TYPES = ('in', 'out')
VALID_FADE_MODES = ('preset', 'parametric')


class FadeFunctionParameter(CuemsDict):
    """A named numeric parameter for a parametric fade function."""

    def __init__(self, init_dict=None):
        if not init_dict:
            init_dict = FADE_PARAM_REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, FADE_PARAM_REQ_ITEMS)
        if init_dict:
            self.setter(init_dict)

    def get_parameter_name(self):
        return super().__getitem__('parameter_name')

    def set_parameter_name(self, value):
        super().__setitem__('parameter_name', str(value))

    parameter_name = property(get_parameter_name, set_parameter_name)

    def get_parameter_value(self):
        return super().__getitem__('parameter_value')

    def set_parameter_value(self, value):
        try:
            v = float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"parameter_value must be numeric, got {value!r}"
            ) from e
        if math.isnan(v) or math.isinf(v):
            raise ValueError("parameter_value must be a finite number")
        super().__setitem__('parameter_value', v)

    parameter_value = property(get_parameter_value, set_parameter_value)

    def __json__(self):
        return {type(self).__name__: dict(self.items())}


class FadeProfile(CuemsDict):
    """Typed fade profile (``in`` or ``out``) attached to a MediaCue.

    Supports two modes:
    - ``preset``: system-defined function, no user parameters required.
    - ``parametric``: user-supplied parameters control the fade curve.
    """

    def __init__(self, init_dict=None):
        if not init_dict:
            init_dict = FADE_PROFILE_REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, FADE_PROFILE_REQ_ITEMS)
        if init_dict:
            self.setter(init_dict)

    # -- type ----------------------------------------------------------

    def get_type(self):
        return super().__getitem__('type')

    def set_type(self, value):
        if value not in VALID_FADE_TYPES:
            raise ValueError(
                f"Invalid fade type '{value}'. Must be one of {VALID_FADE_TYPES}"
            )
        super().__setitem__('type', value)

    type = property(get_type, set_type)

    # -- mode ----------------------------------------------------------

    def get_mode(self):
        return super().__getitem__('mode')

    def set_mode(self, value):
        if value not in VALID_FADE_MODES:
            raise ValueError(
                f"Invalid fade mode '{value}'. Must be one of {VALID_FADE_MODES}"
            )
        super().__setitem__('mode', value)

    mode = property(get_mode, set_mode)

    # -- function_id ---------------------------------------------------

    def get_function_id(self):
        return super().__getitem__('function_id')

    def set_function_id(self, value):
        super().__setitem__('function_id', str(value))

    function_id = property(get_function_id, set_function_id)

    # -- parameters ----------------------------------------------------

    def get_parameters(self):
        return super().__getitem__('parameters')

    def set_parameters(self, value):
        if value is None:
            super().__setitem__('parameters', None)
            return
        if not isinstance(value, list):
            value = [value]
        converted = []
        seen_names: set[str] = set()
        for item in value:
            if not isinstance(item, FadeFunctionParameter):
                item = FadeFunctionParameter(item)
            name = item.parameter_name
            if name in seen_names:
                raise ValueError(
                    f"Duplicate parameter_name {name!r} in fade profile"
                )
            seen_names.add(name)
            converted.append(item)
        super().__setitem__('parameters', converted)

    parameters: list[FadeFunctionParameter] | None = property(
        get_parameters, set_parameters
    )

    def __json__(self):
        return {type(self).__name__: dict(self.items())}
