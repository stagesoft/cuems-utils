<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 011, `/etc/cuems` first install

**Audience**: operators of existing hosts, and the maintainers of `cuems-common` and
`cuems-nodeconf`. Written as the stories land (FR-045); each section is filled by the task that
delivers it and says so.

## 1. Upgraded hosts — what changes and what to run (US1, US3)

*Filled by T025 and T050.*

## 2. The pristine copies and the install-if-absent rule (US2)

*Filled by T034.*

## 3. Purge destroys identity; remove does not (US5)

*Filled by T060.*

## 4. Disk imaging after install (US3)

*Filled by T050.*

## 5. `cuems-init-node --check` — the four locations and the four exit codes (US6)

*Filled by T064.*

## 6. Site overlays and operator edits (US4)

*Filled by T056.*

## 7. The `cuems-common` handover — order, versions, announced re-cuts

*Filled by T025 and T080.*

## 8. Hardware verification — the pointer

The one record of the manual per-node verification is entry §5 of `cuems-nodeconf`'s
hardware-verification ledger (`specs/002-public-network-map-path/checklists/hardware-verification.md`
in that repository; decision D3, 2026-09-28). Acceptance, per node class: unmask, enable and start
`cuems-nodeconf`; `cuems-init-node --check` exits **0** after the unmask and again after a reboot;
a second node lists this one exactly once with the `settings.xml` uuid.
