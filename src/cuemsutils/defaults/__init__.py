# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Package data: the upstream seed values (``system-defaults.toml``).

The one copy code reads (feature 011, research R4) — the build-time generator
and ``cuems-init-node`` both load it through ``importlib.resources``. The same
bytes are installed to ``/usr/share/cuems/defaults/system-defaults.toml`` as the
operator-visible reference; a test pins the two identical.
"""
