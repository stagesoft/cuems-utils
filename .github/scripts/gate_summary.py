# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the pre-publication gate's summary (feature 017, FR-074) and say whether it holds.

Stdlib only. Run by tests.yml's ``gate-summary`` job over the artefacts the other jobs upload::

    python gate_summary.py <artefacts dir>   # env: NEEDS_JSON, GATE_SHA, SIBLINGS_REF

Every field of ``specs/017-release-line-reconciliation/evidence/ci-gate.md`` comes from here:
counts per job from each job's JUnit XML; the strict xfails (an ``XPASS(strict)`` is a failure,
and the reason names it); the ``reads_siblings`` tests that ran versus skipped (the marker reaches
the XML as a test property, see ``tests/conftest.py``); each sibling's resolved commit; the
``xmlschema``/``lxml`` versions the test environment resolved; and every job's result.
The exit status is not the gate: the workflow's own failing step is (it names the blocking set).
"""
from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _outcome(case: ET.Element) -> str:
    kinds = {child.tag for child in case}
    if "failure" in kinds or "error" in kinds:
        return "failed"
    if "skipped" in kinds:
        skipped = case.find("skipped")
        return "xfailed" if skipped is not None and skipped.get("type") == "pytest.xfail" else "skipped"
    return "passed"


def _junit(path: Path) -> dict:
    counts = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0}
    siblings = {"ran": 0, "skipped": 0}
    strict = []
    for case in ET.parse(path).iter("testcase"):
        outcome = _outcome(case)
        counts[outcome] += 1
        name = f"{case.get('classname')}::{case.get('name')}"
        failure = case.find("failure")
        if failure is not None and "XPASS(strict)" in (failure.get("message") or ""):
            strict.append(name)
        props = {p.get("name"): p.get("value") for p in case.iter("property")}
        if props.get("reads_siblings") == "true":
            siblings["skipped" if outcome == "skipped" else "ran"] += 1
    return {"counts": counts, "siblings": siblings, "strict_xpass": strict}


def main(argv: list[str]) -> int:
    root = Path(argv[1])
    needs = json.loads(os.environ.get("NEEDS_JSON", "{}"))
    out = [
        "# Pre-publication gate",
        "",
        f"- **cuems-utils SHA**: `{os.environ.get('GATE_SHA', '?')}`",
        f"- **siblings_ref**: `{os.environ.get('SIBLINGS_REF', '?')}`",
        "",
        "| Job | Result |",
        "|---|---|",
        *(f"| {job} | {info.get('result', '?')} |" for job, info in sorted(needs.items())),
        "",
        "## Tests per job",
        "",
        "| Job | passed | failed | skipped | xfailed | reads_siblings ran | reads_siblings skipped |",
        "|---|---|---|---|---|---|---|",
    ]
    strict: list[str] = []
    for xml in sorted(root.glob("**/junit-*.xml")):
        data = _junit(xml)
        c, s = data["counts"], data["siblings"]
        job = xml.stem.removeprefix("junit-")
        out.append(f"| {job} | {c['passed']} | {c['failed']} | {c['skipped']} | {c['xfailed']} "
                   f"| {s['ran']} | {s['skipped']} |")
        strict += [f"{job}: {n}" for n in data["strict_xpass"]]
    out += ["", "## Strict xfails that passed (XPASS(strict))", ""]
    out += [f"- `{n}`" for n in strict] or ["- none"]
    for title, pattern in (("Sibling commits", "**/sibling-commits.txt"),
                           ("Resolved versions", "**/versions-*.txt")):
        out += ["", f"## {title}", ""]
        files = sorted(root.glob(pattern))
        out += [f"- `{line.strip()}` ({f.parent.name})" for f in files
                for line in f.read_text(encoding="utf-8").splitlines() if line.strip()] or ["- none recorded"]
    text = "\n".join(out) + "\n"
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
