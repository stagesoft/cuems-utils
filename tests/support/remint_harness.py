# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Driving ``--remint`` from a test — feature 012, US2.

One place that knows how the flags go together, so nineteen test files do not
each rediscover it. Runs through ``init_node.main`` rather than calling
``remint.run`` directly: the flags, the dispatch and the refusal-to-exit-code
translation are part of what US2 delivers, and a harness that bypassed them
would leave the only path an operator actually uses untested.
"""

from __future__ import annotations

import io
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from cuemsutils.tools import init_node


def run_remint(cluster, state, *, extra=(), library=True, yes=True,
               conf=None) -> tuple[int, str]:
    """``(exit code, combined output)``.

    ``--systemctl`` is pointed at a path that does not exist so the
    nodeconf-active guard answers "not active" without consulting the host's
    systemd — a test must not depend on what is running on the machine.
    """
    argv = [
        "--remint",
        "--conf-dir", str(conf or cluster.conf),
        "--state-dir", str(state),
        "--systemctl", "/nonexistent/systemctl",
    ]
    if library:
        argv += ["--library", str(cluster.library)]
    if yes:
        argv.append("--yes")
    argv += list(extra)

    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = init_node.main(argv)
    return code, out.getvalue() + err.getvalue()


def state_dir(tmp_path) -> Path:
    return Path(tmp_path) / "var" / "lib" / "cuems-utils"


def snapshot(root) -> dict[str, tuple[bytes, int, int]]:
    """``path -> (bytes, size, mtime_ns)`` for every file under ``root``.

    All three, because this feature has a requirement in each direction: the
    check must change none of them (FR-003), a converged re-run must change
    none of them (FR-013), and a rewritten library file must change the
    **time** while keeping the **size** (FR-011b).
    """
    out = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            stat = os.stat(path)
            out[path] = (Path(path).read_bytes(), stat.st_size, stat.st_mtime_ns)
    return out


def documents_snapshot(cluster) -> dict[str, tuple[bytes, int, int]]:
    """:func:`snapshot` over the **documents** — the configuration directory and
    the library — and not over the tool's own state.

    FR-013's "changes zero bytes in zero files" is about the documents. The
    completion record is *meant* to change on every run: it is this node's
    evidence that it was reached, and a run that found nothing to do is still
    evidence (FR-017a). Folding the state directory into an idempotence
    assertion would make that correct behaviour look like a violation.
    """
    out = {}
    out.update(snapshot(cluster.conf))
    out.update(snapshot(cluster.library))
    return out


def all_text(root) -> str:
    """Every file under ``root`` concatenated — for "does this token survive
    anywhere" questions, which is what FR-016 asks."""
    chunks = []
    for base, _dirs, files in os.walk(root):
        for name in files:
            try:
                chunks.append(Path(base, name).read_text(encoding="utf-8", errors="surrogateescape"))
            except OSError:
                pass
    return "".join(chunks)
