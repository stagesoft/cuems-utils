"""Rough parse/serialize budget check (<= ~15% median overhead; allows CI noise)."""

import statistics
import time

import pytest

from cuemsutils.cues.FadeProfile import FadeFunctionParameter, FadeProfile
from cuemsutils.xml.XmlReaderWriter import XmlReaderWriter
from tests.test_xml import create_dummy_script


def _time_validate_object(script, iterations: int = 40) -> float:
    w = XmlReaderWriter(schema_name='script', xmlfile=None)
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        w.validate_object(script)
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


@pytest.mark.slow
def test_fade_profiles_parse_serialize_overhead_budget():
    base_script, _ = create_dummy_script()
    faded, _ = create_dummy_script()
    ac = faded.cuelist.contents[2]
    ac.fade_profiles = [
        FadeProfile(
            {
                'type': 'in',
                'mode': 'preset',
                'function_id': 'linear_in_out',
                'parameters': None,
            }
        ),
        FadeProfile(
            {
                'type': 'out',
                'mode': 'parametric',
                'function_id': 'bezier',
                'parameters': [
                    FadeFunctionParameter(
                        {'parameter_name': 'p1', 'parameter_value': 0.5}
                    )
                ],
            }
        ),
    ]
    m_base = _time_validate_object(base_script)
    m_fade = _time_validate_object(faded)
    assert m_fade <= m_base * 1.15, (
        f"median validate_object too slow with fades: base={m_base:.4f}s "
        f"fade={m_fade:.4f}s ratio={m_fade/m_base:.3f}"
    )
