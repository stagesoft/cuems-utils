# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Judge every verdict of contracts/relation-matrix.md against the CURRENT files.

Run through verdicts.sh (uvx supplies `packaging`). Debian relations are judged by
`dpkg --compare-versions`, Python bounds by `packaging.specifiers.SpecifierSet`.
Prints `rows edge where candidate expected observed OK|FAIL`; exits 1 on any FAIL.
A relation that is absent from its file is a FAIL for every candidate.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/disk/Projects/StageLab")
OPS = {">=": "ge", "<<": "lt", "<=": "le", ">>": "gt", "=": "eq"}


def stanza_field(repo: str, package: str, field: str) -> str:
    text = (ROOT / repo / "debian/control").read_text(encoding="utf-8")
    lines = [l for l in text.splitlines() if not l.lstrip().startswith("#")]
    stanzas, cur = [], []
    for l in lines:
        if not l.strip():
            if cur:
                stanzas.append(cur)
            cur = []
        else:
            cur.append(l)
    if cur:
        stanzas.append(cur)
    for st in stanzas:
        if any(re.fullmatch(rf"Package:\s*{re.escape(package)}\s*", l) for l in st):
            value, inside = [], False
            for l in st:
                if re.match(rf"^{field}:", l):
                    inside = True
                    value.append(l.split(":", 1)[1])
                elif inside and l[:1] in (" ", "\t"):
                    value.append(l)
                elif inside:
                    break
            return " ".join(value)
    raise SystemExit(f"no stanza Package: {package} in {repo}/debian/control")


def relations(repo: str, package: str, field: str, target: str) -> list[tuple[str, str]]:
    out = []
    for item in stanza_field(repo, package, field).split(","):
        m = re.fullmatch(rf"\s*{re.escape(target)}\s*\(\s*(>=|<<|<=|>>|=)\s*([^)\s]+)\s*\)\s*", item)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def dpkg(a: str, op: str, b: str) -> bool:
    return subprocess.run(["dpkg", "--compare-versions", a, OPS[op], b]).returncode == 0


def py_bound(repo: str) -> str | None:
    d = tomllib.loads((ROOT / repo / "pyproject.toml").read_text(encoding="utf-8"))
    poetry = d.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if "cuemsutils" in poetry:
        v = poetry["cuemsutils"]
        return v if isinstance(v, str) else v.get("version")
    for dep in d.get("project", {}).get("dependencies", []):
        m = re.match(r"\s*cuemsutils\s*(.*)$", dep)
        if m:
            return m.group(1)
    return None


results: list[tuple[str, str, str, str, str, str]] = []


def judge(rows, edge, where, rels, kind, refused, admitted):
    """kind 'depends': admitted = satisfies all; kind 'breaks': 'broken' = satisfies any."""
    for cand, expected in [(c, "R") for c in refused] + [(c, "A") for c in admitted]:
        if not rels:
            obs = "absent"
        elif kind == "depends":
            obs = "A" if all(dpkg(cand, op, b) for op, b in rels) else "R"
        else:  # breaks: R means "this version is broken (refused)"
            obs = "R" if any(dpkg(cand, op, b) for op, b in rels) else "A"
        results.append((rows, edge, where, cand, expected, obs))


UTILS_R = ["0.1.0rc16", "0.1.0rc16+1", "0.1.0rc17", "0.1.0", "0.1.1~rc1", "0.1.2~rc1", "0.1.2", "0.2.0"]
UTILS_A = ["0.1.1", "0.1.1-1", "0.1.1+b1"]
for rows, repo, pkg in [("2-3", "cuems-common", "cuems-common"), ("6-7", "cuems-engine", "cuems-engine"),
                        ("11-12", "cuems-editor", "cuems-editor"), ("15-16", "cuems-nodeconf", "cuems-nodeconf"),
                        ("20-21", "cuems-power-bridge", "cuems-power-bridge")]:
    judge(rows, "-> cuems-utils", f"{repo}:Depends", relations(repo, pkg, "Depends", "cuems-utils"),
          "depends", UTILS_R, UTILS_A)

judge("1", "Breaks cuems-common", "cuems-utils:Breaks",
      relations("cuems-utils", "cuems-utils", "Breaks", "cuems-common"),
      "breaks", ["1.3.0-22", "1.3.0-23", "1.3.0-24", "1.3.0-25"], ["1.3.1~rc1", "1.3.1-1"])

for rows, repo in [("8", "cuems-engine"), ("13", "cuems-editor"), ("17", "cuems-nodeconf"), ("22", "cuems-power-bridge")]:
    judge(rows, "-> cuems-common", f"{repo}:Depends", relations(repo, repo, "Depends", "cuems-common"),
          "depends", ["1.0.0", "1.3.0-23", "1.3.0-25"], ["1.3.1-1"])

for rows, repo in [("18", "cuems-nodeconf"), ("23", "cuems-power-bridge")]:
    judge(rows, "Breaks cuems-common", f"{repo}:Breaks", relations(repo, repo, "Breaks", "cuems-common"),
          "breaks", ["1.3.0-25"], ["1.3.1-1"])

judge("4", "Breaks cuems-nodeconf", "cuems-common:Breaks",
      relations("cuems-common", "cuems-common", "Breaks", "cuems-nodeconf"),
      "breaks", ["0.1.0-8", "0.1.0-9"], ["0.1.1~rc1", "0.1.1-1"])
judge("5", "Breaks cuems-power-bridge", "cuems-common:Breaks",
      relations("cuems-common", "cuems-common", "Breaks", "cuems-power-bridge"),
      "breaks", ["0.3.0-11", "0.3.1-1", "0.3.1-2", "0.3.2-1", "0.3.2-2"], ["0.4.0-1"])
judge("9", "-mock -> cuems-engine", "cuems-engine-mock:Depends",
      relations("cuems-engine", "cuems-engine-mock", "Depends", "cuems-engine"),
      "depends", ["0.1.0rc6-5"], ["0.1.1-1"])
judge("25", "-> libmtcmaster", "cuems-engine:Depends",
      relations("cuems-engine", "cuems-engine", "Depends", "libmtcmaster"),
      "depends", ["0.0.1-1", "0.0.2~rc1"], ["0.0.2-0", "0.0.2-1"])

for rows, repo in [("10", "cuems-engine"), ("14", "cuems-editor"), ("19", "cuems-nodeconf"), ("24", "cuems-power-bridge")]:
    spec = py_bound(repo)
    for cand, expected in [("0.1.0rc16", "R"), ("0.1.0rc17", "R"), ("0.1.2rc1", "R"), ("0.1.2", "R"),
                           ("0.1.1", "A"), ("0.1.1.post1", "A")]:
        if not spec:
            obs = "absent"
        else:
            obs = "A" if SpecifierSet(spec).contains(Version(cand)) else "R"
        results.append((rows, "py cuemsutils", f"{repo}:pyproject ({spec})", cand, expected, obs))

fails = 0
for rows, edge, where, cand, expected, obs in results:
    ok = obs == expected
    fails += not ok
    print(f"row {rows:<6} {edge:<26} {where:<46} {cand:<12} expected {expected} observed {obs:<6} {'OK' if ok else 'FAIL'}")
print(f"# {len(results)} verdicts, {fails} FAIL")
sys.exit(1 if fails else 0)
