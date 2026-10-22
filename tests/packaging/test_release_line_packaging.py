# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Two packaging fixes the release line shipped, pinned (feature 017, A-5, FR-028, FR-034).

* **rc15** (``6a9d1d8``, PR #14): ``Replaces: cuems-engine (<< 0.1.0rc6-2~)``.
  ``/usr/lib/cuems/bin/cffi-gen-src`` moved from the engine to this package. Without
  ``Replaces:``, dpkg aborts on the file conflict whenever an older engine is installed.
  Relation row 26 (``specs/017-release-line-reconciliation/contracts/relation-row-26.md``).
* **rc16+1** (``c01ca36``, PR #18): no ``/usr/lib/cuems/CACHEDIR.TAG``. Newer virtualenv writes
  it, other packages ship the same path, and dpkg refuses to overwrite it. ``debian/rules`` strips
  it right after ``dh_virtualenv``. 016's ``.deb`` lacked the file only because the bookworm
  chroot's virtualenv does not write one, so nothing pinned the strip until now.

Neither was in the refactor's ``debian/`` before 017's merge, so these fail on ``5e4c637``. That
is their purpose: they are what makes a later merge that drops one of them visible.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "debian" / "control"
RULES = ROOT / "debian" / "rules"


def _binary_stanza() -> dict[str, str]:
    """The ``Package: cuems-utils`` stanza's fields (comments dropped)."""
    text = CONTROL.read_text()
    for stanza in re.split(r"\n\s*\n", text):
        lines = [line for line in stanza.splitlines() if not line.startswith("#")]
        fields = dict(
            (m.group(1), m.group(2).strip())
            for m in (re.match(r"^([A-Za-z-]+):\s*(.*)$", line) for line in lines)
            if m
        )
        if fields.get("Package") == "cuems-utils":
            return fields
    raise AssertionError("debian/control has no Package: cuems-utils stanza")


def _override_dh_virtualenv() -> list[str]:
    """The recipe lines of ``override_dh_virtualenv``, in order."""
    lines = RULES.read_text().splitlines()
    start = lines.index("override_dh_virtualenv:")
    recipe = []
    for line in lines[start + 1:]:
        if line and not line.startswith("\t"):
            break
        recipe.append(line)
    return recipe


def test_cuems_utils_replaces_the_old_engine_for_cffi_gen_src():
    fields = _binary_stanza()
    assert fields.get("Replaces") == "cuems-engine (<< 0.1.0rc6-2~)"


def test_the_cuems_common_breaks_is_unchanged():
    """Relation row 1: it must survive the merge that brought row 26."""
    assert _binary_stanza().get("Breaks") == "cuems-common (<< 1.3.1~)"


def test_the_control_comment_no_longer_says_replaces_is_absent():
    """A-5: the comment above the relations used to say *"Replaces is deliberately absent"*,
    which stopped being true when rc15's ``Replaces:`` arrived. Each relation now states its
    own reason."""
    assert "deliberately absent" not in CONTROL.read_text()


def test_rules_strips_cachedir_tag_right_after_dh_virtualenv():
    recipe = [line.strip() for line in _override_dh_virtualenv() if line.strip()
              and not line.strip().startswith("#")]
    assert recipe[0].startswith("dh_virtualenv "), recipe[:2]
    assert recipe[1] == "rm -f debian/cuems-utils/usr/lib/cuems/CACHEDIR.TAG", recipe[:2]


def test_rules_carries_all_four_required_items():
    """FR-034: the interpreter pin, the strip, 011's schema/defaults install and the
    ``override_dh_installdeb`` relabel all have to be present at once. Each came from a
    different line of history, and a merge can drop any one of them."""
    text = RULES.read_text()
    assert "dh_virtualenv --python /usr/bin/python3" in text
    assert "rm -f debian/cuems-utils/usr/lib/cuems/CACHEDIR.TAG" in text
    assert "debian/cuems-utils/usr/share/cuems/schemas" in text
    assert "-m cuemsutils.xml.make_defaults" in text
    assert re.search(r"^override_dh_installdeb:", text, re.M)
