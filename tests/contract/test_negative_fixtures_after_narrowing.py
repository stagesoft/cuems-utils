# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T050 — **which** error each negative fixture now raises (FR-027, trap 7.3).

A negative fixture fails for a reason, and the reason is the assertion. After a
tightening, one that still fails while testing the wrong thing keeps the suite
green and the coverage gone — which is worse than a fixture that started
passing, because nothing anywhere reports it.

The three fixtures in ``tests/data/corpus/negative/`` are ``settings``
documents, and all three carry identities that are **already converged**
(``0367f391-ebf4-48b2-9f26-0000000000NN`` — version nibble 4, variant 9,
lowercase). So the narrowing must **not** change why any of them fails, and
that is what is asserted: the recorded error type, unchanged, plus the positive
statement that the failure is not about the identity.

Recording "unchanged" is the point. It is the measured result, and a later
reader needs to know it was measured rather than assumed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cuemsutils.tools import ids
from cuemsutils.xml.schema import get_schema
from tests.support.corpus import CORPUS_ROOT, GOLDEN_ROOT

#: The recorded pre-narrowing verdict per fixture, from ``outcomes.json``. Read
#: rather than restated, so the two cannot disagree — and **never regenerated**
#: (quickstart, "Do not").
OUTCOMES = json.loads((GOLDEN_ROOT / "outcomes.json").read_text())

NEGATIVE = sorted(
    p.name for p in (CORPUS_ROOT / "negative").iterdir() if p.suffix == ".xml"
)


def test_the_fixture_set_is_what_this_file_thinks_it_is():
    """A corpus can lose a file and a parametrisation shrinks silently."""
    assert NEGATIVE == [
        "settings-utils-v0.1.0rc2.xml",
        "settings-utils-v0.1.0rc7.xml",
        "settings_bad_dmx_auto.xml",
    ]


@pytest.mark.parametrize("name", NEGATIVE)
def test_each_fixture_still_fails_for_its_recorded_reason(name):
    path = CORPUS_ROOT / "negative" / name
    recorded = OUTCOMES[f"negative/{name}"]["read"]
    assert recorded["ok"] is False

    with pytest.raises(Exception) as raised:
        get_schema("settings").validate(str(path))
    assert type(raised.value).__name__ == recorded["error_type"], (
        f"{name} now fails with {type(raised.value).__name__}, not the recorded "
        f"{recorded['error_type']}. Either the tightening changed why it fails — in "
        "which case this fixture no longer covers what it was written to cover — or "
        "something else moved."
    )


@pytest.mark.parametrize("name", NEGATIVE)
def test_no_fixture_fails_because_of_its_identity(name):
    """The positive half. All three carry converged identities, so the
    narrowing is not what rejects them — and if that ever stops being true, the
    fixture has silently been repurposed."""
    path = CORPUS_ROOT / "negative" / name
    import re

    identities = re.findall(r"<uuid>([^<]*)</uuid>", path.read_text())
    assert identities, f"{name} carries no identity; this test is about the wrong file"
    for value in identities:
        assert ids.classify(value.strip()) == ids.CONVERGED, (
            f"{name} carries a {ids.classify(value.strip())} identity, so the "
            "narrowing may now be the reason it fails rather than the fault it "
            "was authored for."
        )


@pytest.mark.parametrize("name", NEGATIVE)
def test_the_fixture_is_not_accidentally_repaired_by_the_narrowing(name):
    """The other failure mode: a tightening that made a fixture *valid* would
    be a hole in the corpus with nothing to report it."""
    path = CORPUS_ROOT / "negative" / name
    with pytest.raises(Exception):
        get_schema("settings").validate(str(path))


def test_the_pre_008_mirror_is_unchanged_too():
    """``tests/data/corpus/pre-008/`` exists to hold documents in their
    pre-refactor shape. A narrowing that changed their verdicts would make that
    record mean something different."""
    mirror = CORPUS_ROOT / "pre-008" / "negative"
    assert mirror.is_dir()
    for name in NEGATIVE:
        assert (mirror / name).is_file()
        with pytest.raises(Exception):
            get_schema("settings").validate(str(mirror / name))
