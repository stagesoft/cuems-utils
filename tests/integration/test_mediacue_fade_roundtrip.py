"""Integration: MediaCue round-trip through XML.

The fade-profile round-trip assertions this file used to carry are retired
(feature 008, FR-007a, T021) — the surface they exercised (``FadeProfile``,
``fade_profiles``) no longer exists anywhere in the schema or the model.
"""

import pytest

from cuemsutils.create_script import create_script, validate_template
from cuemsutils.helpers import new_datetime, new_uuid


def test_create_script_template_validates_with_schema():
    """Mirror create_script validation window (ids and dates set)."""
    script = create_script()
    now = new_datetime()
    script.created = now
    script.modified = now
    script['id'] = new_uuid()
    script['CueList']['id'] = new_uuid()
    for i in range(len(script.cuelist.contents)):
        script.cuelist.contents[i]['id'] = new_uuid()
    script['ui_properties'] = {'warning': 0}
    validate_template(script)
