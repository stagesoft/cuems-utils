# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T037a — convert-on-read, verified at library scale (FR-095a).

FR-095 leaves a library unconverted until an operator runs the conversion, and
FR-095a says what makes that safe: the load path converts an older document in
memory, so it still opens. This verifies it over a library rather than a single
file, with the disk compared byte for byte afterwards.

It also pins what convert-on-read does **not** cover, because the measurement
found it (2026-10-16): 013's device-class reshape has no version step
(``doc_version`` does not move), so there is no conversion for the load path to
run. A pre-013-shape document is **refused**, naming ``cuems-reshape-devices``.
"Unconverted still opens" therefore holds for the version axis only. An
un-reshaped library does not open until the reshape has run (FR-095a as
amended, T040).
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome, SchemaError
from cuemsutils.tools import validate_config_document
from tests.support.corpus import REPO_ROOT

CORPUS = REPO_ROOT / "tests" / "data" / "corpus"
VERSION_OLD = CORPUS / "pre-008" / "script_v1_all_transforms.xml"
PRE_013 = CORPUS / "pre-013"


def _digests(directory: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir())}


def test_an_unconverted_library_opens_and_its_disk_is_untouched(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    for n in range(5):
        shutil.copyfile(VERSION_OLD, library / f"show{n}.xml")
    before = _digests(library)

    outcomes = [CuemsScript.load_with_report(path)[1].outcome for path in sorted(library.iterdir())]

    assert outcomes == [Outcome.CONVERTED] * 5
    assert _digests(library) == before, "convert-on-read must write nothing, not even a backup"


@pytest.mark.parametrize("name", ["settings.xml", "project_mappings.xml"])
def test_convert_on_read_does_not_reshape_a_configuration_document(name):
    with pytest.raises(SchemaError, match="cuems-reshape-devices"):
        validate_config_document(PRE_013 / name)


def test_convert_on_read_does_not_reshape_a_show_document():
    with pytest.raises(SchemaError, match="cuems-reshape-devices"):
        CuemsScript.load(PRE_013 / "script.xml")
