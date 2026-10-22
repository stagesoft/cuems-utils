# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``python -m cuemsutils.xml.reshape_devices`` runs the tool (feature 017, S-4, FR-029a).

The console script ``cuems-reshape-devices`` always worked, and ``postinst`` uses it. But the
module had no ``__main__`` guard, so ``python -m`` exited 0 having done nothing: a silent
success. ``cuems-convert-documents`` already had the guard. Both tools now behave alike.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from cuemsutils.xml import reshape_devices

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "rc17" / "stop_control.xml"


def test_python_dash_m_runs_the_tool_like_its_main(tmp_path, capsys):
    by_m, by_main = tmp_path / "by_m.xml", tmp_path / "by_main.xml"
    shutil.copy(FIXTURE, by_m)
    shutil.copy(FIXTURE, by_main)

    run = subprocess.run(
        [sys.executable, "-m", "cuemsutils.xml.reshape_devices", "--check", str(by_m)],
        capture_output=True, text=True,
    )
    expected_code = reshape_devices.main(["--check", str(by_main)])
    expected_out = capsys.readouterr().out

    assert run.returncode == expected_code
    assert f"{by_m}: old-shape" in run.stdout, run.stdout + run.stderr
    assert expected_out.replace(str(by_main), str(by_m)) == run.stdout
