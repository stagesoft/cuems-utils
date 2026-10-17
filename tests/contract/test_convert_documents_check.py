# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T035 — ``cuems-convert-documents --check`` reports and writes nothing (FR-103).

The post-conversion rollback begins "if you converted", so an operator must be
able to answer that without inspecting documents by hand (research R4). The
check mode is that answer: one line per document with its version, a library
summary, and not one byte or file changed. Exit codes follow
``cuems-reshape-devices --check``: 0 when everything is current, 1 when
anything needs conversion or was skipped, 2 for usage.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from cuemsutils.xml.convert_documents import main
from cuemsutils.xml.versioning import CURRENT_VERSION
from tests.support.corpus import REPO_ROOT

PRE_008 = REPO_ROOT / "tests" / "data" / "corpus" / "pre-008" / "script_v1_all_transforms.xml"


def _state(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
    }


def _library(tmp_path: Path) -> tuple[Path, Path]:
    old = tmp_path / "old.xml"
    current = tmp_path / "current.xml"
    shutil.copyfile(PRE_008, old)
    shutil.copyfile(PRE_008, current)
    assert main([str(current)]) == 0  # converted, and backed up beside itself
    return old, current


def test_check_writes_nothing(tmp_path):
    old, current = _library(tmp_path)
    before = _state(tmp_path)
    main(["--check", str(old), str(current)])
    assert _state(tmp_path) == before, "the check mode must not write, back up or rewrite"


def test_check_reports_each_document_version(tmp_path, capsys):
    old, current = _library(tmp_path)
    capsys.readouterr()
    main(["--check", str(old), str(current)])
    out = capsys.readouterr().out
    now = CURRENT_VERSION["script"]
    assert f"{old}: version 1, current {now} — needs conversion" in out
    assert f"{current}: already current (version {now})" in out


def test_check_summarises_the_library(tmp_path, capsys):
    old, current = _library(tmp_path)
    capsys.readouterr()
    main(["--check", str(old), str(current)])
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last == "2 documents: 1 current, 1 needs conversion"


def test_check_exit_codes(tmp_path):
    old, current = _library(tmp_path)
    assert main(["--check", str(current)]) == 0
    assert main(["--check", str(old), str(current)]) == 1


def test_check_names_a_document_it_cannot_classify(tmp_path, capsys):
    stranger = tmp_path / "stranger.xml"
    stranger.write_text("<notcuems/>", encoding="utf-8")
    assert main(["--check", str(stranger)]) == 1
    captured = capsys.readouterr()
    assert f"{stranger}: skipped (root element names no bundled schema)" in captured.err
    assert captured.out.strip().splitlines()[-1] == "1 document: 1 skipped"
