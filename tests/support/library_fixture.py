# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The named performance fixtures — feature 012, T002.

A generator parameterised by project count and node count, plus one **named**
instance: :func:`remint_200`, fixed at 200 projects and about 4 MB (research
R8).

**The scale is part of the budget, not a detail of the fixture.** SC-PERF-001's
wall-clock ceiling is stated *for `remint_200`*, so a fixture that quietly grew
or shrank would move the ceiling without anybody deciding to. :data:`REMINT_200`
records the two numbers and :func:`remint_200` asserts the byte total lands in
the recorded band, which is what keeps the name meaning one thing.

Grounding, from research R8: the largest corpus script is ~24 KB and the whole
corpus is 504 KB. A 200-project library is therefore single-digit megabytes —
I/O-trivial in absolute terms, which is exactly why the budget is shaped to
catch an algorithmic regression (a per-node pass) rather than to police absolute
time.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.support.cluster_fixture import (
    NodeSpec,
    _common,
    _video_output,
    mac_for,
    project_mappings_xml,
)

#: ``remint_200``'s two fixed numbers, and the band its byte total must land in.
#: The band is ±15% of the nominal 4 MB — wide enough to survive an incidental
#: change to a cue's markup, narrow enough that doubling the fixture fails here
#: rather than silently doubling every timing.
REMINT_200 = {
    "projects": 200,
    "nominal_bytes": 4_000_000,
    "band": (3_400_000, 4_600_000),
}

#: Cues per script, chosen so 200 projects land on the nominal byte total. Each
#: cue is ~1 KB of markup carrying two compound output names.
CUES_PER_SCRIPT = 13


@dataclass
class Library:
    """A generated library and the numbers a timing test needs from it."""

    root: Path
    nodes: list[NodeSpec]
    projects: list[str]
    total_bytes: int

    @property
    def files(self) -> list[Path]:
        return sorted(p for p in self.root.rglob("*.xml") if p.is_file())

    @property
    def identities(self) -> list[str]:
        return [n.uuid for n in self.nodes]


def nodes_for(count: int) -> list[NodeSpec]:
    """``count`` node rows carrying **non-converged** (uuid1-shaped) identities.

    Non-converged on purpose: a performance fixture must give the substitution
    something to *do*, and a converged library is the case FR-014 says is
    skipped entirely — timing that would measure the skip, not the rewrite.

    The identities are generated rather than drawn from ``SHAPES`` so a ten-node
    cluster has ten distinct ones. The version nibble is pinned to ``1`` and the
    variant to ``9``, which is a real uuid1 shape and one the narrowed pattern
    refuses.

    **Passing the same rows to two libraries is how "identical library bytes"
    is arranged** (T077): a script's length does not depend on how many nodes
    exist — every identity is 36 characters — but ``mappings.xml`` lists one
    entry per node, so it does. A timing comparison across node counts holds
    the rows fixed and varies the *table*, which is where the per-node-pass
    defect would show.
    """
    return [
        NodeSpec(
            uuid=f"{i:08x}-ebf4-11b2-9f26-{i:012x}",
            mac=mac_for(i),
            role="controller" if i == 0 else "node",
            name=f"node{i}",
            ip=f"10.0.0.{i + 1}",
        )
        for i in range(count)
    ]


def _script(name: str, nodes: list[NodeSpec], cues: int) -> str:
    """A script with ``cues`` video cues, each naming one node's outputs.

    Outputs cycle through the nodes so a ten-node library carries every
    identity in every script — which is what makes the 2-node and 10-node runs
    comparable over the *same* total bytes rather than over different work.
    """
    body = "".join(
        "<VideoCue>"
        + _common(f"{i:08x}-bbbb-4bbb-abcd-{i:012x}", f"cue {i}")
        + "<Media><file_name>v.mp4</file_name><id />"
        "<duration><CTimecode>00:00:10.000</CTimecode></duration>"
        "<regions><Region><id>0</id><loop>0</loop>"
        "<in_time><CTimecode>00:00:00.000</CTimecode></in_time>"
        "<out_time><CTimecode>00:00:10.000</CTimecode></out_time></Region></regions></Media>"
        "<outputs>"
        + _video_output(f"{nodes[i % len(nodes)].uuid}_0")
        + _video_output(f"{nodes[i % len(nodes)].uuid}_custom_1")
        + "</outputs></VideoCue>"
        for i in range(cues)
    )
    root_id = "12345678-aaaa-4aaa-abcd-123456789000"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<cms:CuemsProject xmlns:cms="https://stagelab.coop/cuems/" doc_version="2">'
        "<CuemsScript>"
        f"<CueList>{_common(root_id, 'main')}<contents>{body}</contents></CueList>"
        f"<description /><id>{root_id}</id><name>{name}</name>"
        "<created>2026-09-30T00:00:00</created><modified>2026-09-30T00:00:00</modified>"
        "<ui_properties />"
        "</CuemsScript></cms:CuemsProject>\n"
    )


def build_library(
    root: Path,
    *,
    projects: int,
    node_count: int,
    cues_per_script: int = CUES_PER_SCRIPT,
    script_name: str = "script.xml",
    nodes: list[NodeSpec] | None = None,
) -> Library:
    """Generate ``projects`` project directories under ``root``.

    ``nodes`` may be passed so two libraries at *different* node counts can be
    built over the same identities where a test needs that; by default the rows
    are generated from ``node_count``.
    """
    root = Path(root)
    rows = nodes if nodes is not None else nodes_for(node_count)
    (root / "projects").mkdir(parents=True, exist_ok=True)
    (root / "trash" / "projects").mkdir(parents=True, exist_ok=True)

    names = []
    total = 0
    mappings = project_mappings_xml(rows)
    for index in range(projects):
        name = f"project_{index:04d}"
        names.append(name)
        directory = root / "projects" / name
        directory.mkdir(parents=True, exist_ok=True)
        script = _script(name, rows, cues_per_script)
        (directory / script_name).write_text(script, encoding="utf-8")
        (directory / "mappings.xml").write_text(mappings, encoding="utf-8")
        total += len(script.encode()) + len(mappings.encode())

    return Library(root=root, nodes=rows, projects=names, total_bytes=total)


def remint_200(root: Path, *, node_count: int = 2, nodes: list[NodeSpec] | None = None) -> Library:
    """**The named fixture** SC-PERF-001's ceiling is stated for.

    Raises:
        AssertionError: the generated byte total left :data:`REMINT_200`'s
            recorded band. That is deliberately an assertion and not a warning:
            the ceiling is meaningless if the fixture it names has drifted, and
            a drifted fixture is a decision somebody has to make rather than a
            number to re-fit.
    """
    library = build_library(
        root, projects=REMINT_200["projects"], node_count=node_count, nodes=nodes
    )
    low, high = REMINT_200["band"]
    assert low <= library.total_bytes <= high, (
        f"remint_200 generated {library.total_bytes} bytes, outside the recorded "
        f"band {low}–{high} (nominal {REMINT_200['nominal_bytes']}). The fixture's "
        "scale is part of SC-PERF-001's budget: either restore it, or change "
        "REMINT_200 and the ceiling together, deliberately."
    )
    return library
