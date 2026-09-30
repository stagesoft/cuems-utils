# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T076c — the migration guide is **checked**, not just written (US5's Independent Test).

Not optional. The constitution requires testing work and verification steps
**per story**, and Phase 7 was six writing tasks with nothing that checked the
result — which the second `/speckit.analyze` pass recorded as a Delivery
Workflow violation rather than a gap.

Two kinds of assertion, and the second is the one that earns its keep:

1. **Presence** — every item FR-033 through FR-036c requires is in the document.
   A checklist, and worth having, but it only catches an omission.
2. **Resolution** — every version and component the guide names exists in the
   actual trees, and every path it tells an operator to type is a path this
   library really uses. **A guide whose named version has moved is worse than no
   guide, because an operator follows it.**

The second kind reaches outside this repository, to the sibling checkouts. Where
a sibling is not present the check **skips with a reason** rather than passing:
a green run on a machine with no siblings must not be read as evidence that the
cross-repository facts hold.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDE = REPO_ROOT / "specs" / "012-uuid4-convergence" / "migration-guide.md"
SIBLINGS = REPO_ROOT.parent


def _words(text: str) -> str:
    """``text`` reduced to lower-case words.

    Markdown emphasis, blockquote markers, backticks and line wrapping are all
    removed. Every presence check below is about **words**, not about where the
    80th column fell or whether a phrase happens to be bolded — matching raw
    text makes a re-wrap look like a deleted warning, which is the kind of
    failure that gets a checking test deleted rather than fixed.
    """
    stripped = re.sub(r"[*`>#|]", " ", text.lower())
    return re.sub(r"\s+", " ", stripped)


@pytest.fixture(scope="module")
def guide() -> str:
    """The guide, reduced to words (see :func:`_words`)."""
    assert GUIDE.is_file(), f"{GUIDE} does not exist"
    return _words(GUIDE.read_text())


# --- 1. presence: every requirement's item -----------------------------------

#: ``requirement -> substrings that must all appear``. Phrased as the operator
#: would recognise them, not as the requirement's own wording: the guide is for
#: an operator, and a checklist of internal identifiers would pass on a document
#: that quoted the spec back at them.
REQUIRED = {
    "FR-033 (the reimage property)": [
        "re-imaged node",
        "no longer regenerates",
        "must be re-adopted",
    ],
    "FR-033a (the backup hazard)": [
        "Backups are not rewritten",
        "reintroduces a stale identity",
    ],
    "FR-034 (what must be stopped, and the table copy)": [
        "cuems-nodeconf.service",
        "writes network_map.xml",
        "substitution-table.json",
    ],
    "FR-035 (the coupled consumer version)": [
        "cuems-engine 0.1.0rc7",
        "cluster_status",
    ],
    "FR-036 (the incomplete-re-mint detector)": [
        "cluster_warning",
        '"missing"',
    ],
    "FR-036a (the four collision routes)": [
        "four collision routes",
        "Cloning a provisioned disk",
    ],
    "FR-036b (the pre-existing-collision procedure)": [
        "pre-existing collision must be resolved first",
        "while the map still loads",
        "--force-new-identity",
    ],
    "FR-036c (the roll-call)": [
        "roll-call",
        "one record per row",
        "not a node that is probably fine",
    ],
    "FR-011a (the scope split and its ordering)": [
        "scope split",
        "the controller, once",
        "replication",
        "re-minted in place",
    ],
    "FR-007 (the table copy as a numbered step)": [
        "adds no transport",
        "refuses, and that refusal is the design working",
        "numbered step, not a detail",
    ],
}


@pytest.mark.parametrize("requirement,needles", sorted(REQUIRED.items()))
def test_every_required_item_is_present(guide, requirement, needles):
    missing = [n for n in needles if _words(n) not in guide]
    assert not missing, f"{requirement}: the guide does not say {missing}"


def test_the_guide_names_its_audience():
    """It is written for an operator, not for a reviewer of this feature."""
    assert "Written for:" in GUIDE.read_text()


def test_the_normaliser_does_not_make_every_check_vacuous():
    """The control. A normaliser aggressive enough to erase the difference
    between phrases would make every presence check above pass."""
    assert _words("a phrase this guide does not contain") not in _words(GUIDE.read_text())


# --- 2. resolution: the facts the guide asserts about other trees ------------


def _sibling(name: str) -> Path:
    path = SIBLINGS / name
    if not path.is_dir():
        pytest.skip(
            f"{path} is not checked out; the cross-repository facts this guide "
            "names cannot be verified here. Skipped rather than passed, so a "
            "machine with no siblings does not read as evidence."
        )
    return path


def test_the_coupled_engine_version_resolves(guide):
    """FR-035's precondition names a version. If the engine has moved past it
    the guide is still right (it is a floor), but if the engine has **not
    reached** it the guide names a release that does not exist."""
    engine = _sibling("cuems-engine")
    declared = re.search(
        r'__version__\s*=\s*"([^"]+)"',
        (engine / "src" / "cuemsengine" / "__init__.py").read_text(),
    )
    assert declared, "cuems-engine declares no __version__"

    named = re.search(r"cuems-engine (\d[^\s`*]+)", GUIDE.read_text())
    assert named, "the guide names no cuems-engine version"
    assert named.group(1) == declared.group(1), (
        f"the guide names cuems-engine {named.group(1)} but the tree is at "
        f"{declared.group(1)}. FR-035 couples the re-mint to a specific release; "
        "a guide naming a different one sends an operator to check the wrong thing."
    )


def test_the_engine_really_broadcasts_the_status_the_guide_tells_you_to_watch(guide):
    """§8c tells an operator to watch ``cluster_warning`` and to read
    ``missing`` out of it. Both must exist, and the channel name must be the one
    the engine actually publishes on."""
    engine = _sibling("cuems-engine")
    controller = (engine / "src" / "cuemsengine" / "ControllerEngine.py").read_text()
    assert "cluster_warning" in controller
    assert '"missing"' in controller
    assert "/engine/status/cluster_warning" in GUIDE.read_text()
    assert "/engine/status/" in controller


@pytest.mark.parametrize("unit", [
    "cuems-nodeconf.service",
    "cuems-controller-engine.service",
    "cuems-node-engine.service",
    "cuems-editor.service",
    "cuems-videocomposer.service",
])
def test_every_unit_on_the_stop_list_is_a_unit_that_exists(guide, unit):
    """A stop list naming a unit that does not exist teaches an operator to
    ignore the errors from the ones that do."""
    assert unit in GUIDE.read_text(), f"the guide does not name {unit}"
    common = _sibling("cuems-common")
    assert (common / "etc" / "systemd" / "system" / unit).is_file(), (
        f"{unit} is on the guide's stop list and is shipped by no package"
    )


def test_the_power_bridge_unit_exists_where_its_own_package_ships_it(guide):
    """The one unit not in ``cuems-common``: the bridge ships its own."""
    assert "cuems-power-bridge.service" in GUIDE.read_text()
    bridge = _sibling("cuems-power-bridge")
    assert (bridge / "debian" / "cuems-power-bridge.service").is_file()


def test_nodeconf_really_writes_the_map(guide):
    """The stop list's whole justification. If nodeconf stopped writing the map,
    the most emphatic warning in this document would be false."""
    nodeconf = _sibling("cuems-nodeconf")
    source = (nodeconf / "cuemsnodeconf" / "CuemsNodeConf.py").read_text()
    assert "network_map.xml" in source
    assert re.search(r"\.save\(|write_network_map|save_network_map", source), (
        "cuems-nodeconf no longer appears to write the map; the guide's central "
        "warning needs re-checking"
    )


# --- 2b. the paths and commands an operator types ---------------------------


def test_the_table_path_is_the_one_the_tool_writes(guide):
    from cuemsutils.tools import remint

    written = remint.table_path("/var/lib/cuems-utils")
    assert str(written) in GUIDE.read_text(), (
        f"the guide tells an operator to copy {re.findall(r'/var/lib[^ `]*', guide)[:2]} "
        f"but the tool writes {written}"
    )


def test_the_completion_record_path_pattern_matches_the_tool(guide):
    from cuemsutils.tools import remint

    path = remint.completion_record_path("/var/lib/cuems-utils", "SOMEUUID")
    raw = GUIDE.read_text()
    assert str(path.parent) in raw
    assert "completion-" in raw and "completion-" in path.name


@pytest.mark.parametrize("flag", ["--check", "--json", "--remint", "--dry-run",
                                  "--yes", "--table", "--resume", "--library",
                                  "--force-new-identity", "--mac"])
def test_every_flag_the_guide_tells_you_to_type_exists(guide, flag):
    from cuemsutils.tools import init_node

    assert flag in GUIDE.read_text() or flag in ("--resume", "--library"), (
        f"the guide does not mention {flag}"
    )
    actions = {a for action in init_node._parser()._actions
               for a in action.option_strings}
    assert flag in actions, f"the guide names {flag} and the parser has no such flag"


def test_the_exit_codes_the_guide_tabulates_are_the_tools(guide):
    """Both tables: the check's four classes and the re-mint's three."""
    raw = GUIDE.read_text()
    for line in ("| 0 |", "| 1 |", "| 2 |", "| 3 |"):
        assert line in raw
    assert _words("rewritten but the verification failed") in guide, (
        "the guide's exit table does not distinguish exit 2 from exit 1. "
        "\"we changed your cluster and cannot prove it is right\" is not the "
        "same news as \"we changed nothing\"."
    )


def test_the_three_version_steps_the_guide_states_match_the_registry(guide):
    from cuemsutils.xml.versioning import CURRENT_VERSION

    raw = GUIDE.read_text()
    assert f"`network_map` 1\u2192{CURRENT_VERSION['network_map']}" in raw
    assert f"`project_mappings` 1\u2192{CURRENT_VERSION['project_mappings']}" in raw
    assert f"`settings` 2\u2192{CURRENT_VERSION['settings']}" in raw


def test_the_library_path_default_the_guide_uses_is_the_shipped_one(guide):
    """§5's replication check tells an operator to `grep` a directory. If the
    shipped default moved, the command finds nothing and reads as "replication
    has not run"."""
    from cuemsutils.xml import seed_values

    tables = seed_values.load_seed_values()
    shipped = tables["settings"]["SettingsType"]["library_path"]
    assert shipped in GUIDE.read_text(), (
        f"the guide's example paths do not use the shipped library_path {shipped!r}"
    )


def test_the_interface_the_guide_tells_you_to_read_is_the_one_the_tool_prefers(guide):
    from cuemsutils.tools import init_node

    assert "/sys/class/net/ethernet0/address" in GUIDE.read_text()
    assert init_node.DEFAULT_SYSFS == "/sys/class/net"


def test_systemctl_is_available_where_the_guide_assumes_it(guide):
    """Not a check of this library — a check that the guide's commands are the
    ones this platform has. Debian bookworm nodes, systemd."""
    assert "systemctl" in GUIDE.read_text()
    if shutil.which("systemctl") is None:
        pytest.skip("no systemd on this machine; the guide targets Debian nodes")
