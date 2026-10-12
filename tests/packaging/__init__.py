# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Packaging-level tests (feature 011): the maintainer scripts run against temp
directories through path overrides, the built ``.deb`` is inspected when one
exists, and the lifecycle is exercised in an unprivileged chroot when
``CUEMS_CHROOT_TAR`` points at one. See ``conftest.py`` for the fixtures and the
skip rules."""
