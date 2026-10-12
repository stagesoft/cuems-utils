"""Integration: MediaCue round-trip through XML.

The fade-profile round-trip assertions this file used to carry are retired
(feature 008, FR-007a, T021) — the surface they exercised (``FadeProfile``,
``fade_profiles``) no longer exists anywhere in the schema or the model.
"""

import pytest

from cuemsutils.xml.descriptor import generate_script_example


def test_generated_example_validates_with_schema():
    """The descriptor-generated example script is valid as returned (T070/T074).

    Unlike the retired hand-written script-template function, there is no
    separate "validation window" to mirror: the generator returns an
    already-populated, already-valid object with nothing left to restamp
    (FR-033).
    """
    script = generate_script_example()
    report = script.validate()
    assert not report, report
