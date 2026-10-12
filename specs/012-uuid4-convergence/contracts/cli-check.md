<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the identity check (read-only)

**Surface**: the existing identity tool's `--check` mode, extended. No new entry point
(clarification Q1). **Writes nothing, ever** (FR-003).

## Invocation

```
cuems-init-node --check [--json] [--conf-dir DIR] [--library PATH] [--avahi-service FILE]
```

`--library` overrides the library path; by default it is read from the configuration document,
and its absence degrades to a configuration-only survey that says so (R9, FR-005).

## Exit classes

The existing vocabulary, **extended rather than replaced** (Principle III). Precedence is
highest-numbered wins, as today.

| Code | Meaning | Introduced |
|---|---|---|
| 0 | coherent, provisioned, and every identity converged | existing, narrowed |
| 1 | at least one mirror disagrees with the source **or** at least one identity is not converged | existing, widened |
| 2 | at least one location absent or unreadable | existing |
| 3 | the source carries the sentinel — NOT PROVISIONED | existing |

**The widening of 1 is the compatibility question to watch.** A consumer treating 1 as "mirrors
disagree" will now also see it for "migration needed". Both mean *actionable, run the tool named
in `fix`*, so the semantics hold; the `verdict` field distinguishes them for anything that needs
to.

The verdict vocabulary is the shipped one **extended**, not replaced: `ok`, `mismatch`, `absent`
and `not-provisioned` keep their meanings and `migration-needed` joins them. The tool's existing
contract test asserts against these values and is extended in step with the widening, not
rewritten around it.

## Output

Human-readable by default; one JSON object under `--json`. Both carry, per occurrence: the file
path, the location within it, the value, its classification (§1.3 of the data model), and whether
it was found embedded in a compound string.

## Guarantees

| | |
|---|---|
| No writes | no file created, modified, moved or deleted; no backup taken; no modification time changed |
| Survives invalid documents | reads with stdlib XML only, never through the validating load path — this is what makes it usable when it is needed |
| Partial failure is reported, not fatal | an unreadable or unrecognised document is named and the survey continues (FR-005) |
| Shared with the re-mint | the re-mint's pre-write paths carry the same stdlib-only property, for two further reasons of their own (FR-006a) — so this is a property of the feature, not a quirk of the check |
| No dependency on the conversion tool | reporting a document's *version* and classifying an identity's *shape* are separate questions (FR-001a). Satisfied **by design** — stdlib XML only, never the validating load path — rather than by a dedicated test; reversing it requires a stated justification in the plan |
