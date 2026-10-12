# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T041 — OPEN-3, pinned from this side (research R16, FR-022): the tool runs
in this package's postinst after dh-virtualenv's autoscript and before the
final exit, and cuems-common still configures after cuems-utils (Depends) with
no service start injected into its postinst."""

from __future__ import annotations

import re

import pytest

from tests.packaging.conftest import DEBIAN, REPO_ROOT

COMMON = REPO_ROOT.parent / "cuems-common"


def test_postinst_runs_the_tool_after_the_token_and_before_exit():
    text = (DEBIAN / "cuems-utils.postinst").read_text(encoding="utf-8")
    token = text.index("#DEBHELPER#")
    set_plus_e = text.index("set +e")
    tool = text.index("$CUEMS_INIT_NODE")
    final_exit = text.rindex("exit 0")
    assert token < set_plus_e < tool < final_exit


@pytest.mark.skipif(not (COMMON / "debian" / "control").exists(), reason="cuems-common sibling checkout not found")
def test_cuems_common_still_configures_after_this_package():
    control = (COMMON / "debian" / "control").read_text(encoding="utf-8")
    assert re.search(r"^\s*cuems-utils \(>= 0\.1\.0rc16\)", control, re.M), "cuems-common must depend on cuems-utils"
    postinst = (COMMON / "debian" / "postinst").read_text(encoding="utf-8")
    assert "#DEBHELPER" + "#" not in postinst, "cuems-common's postinst would inject service starts"
