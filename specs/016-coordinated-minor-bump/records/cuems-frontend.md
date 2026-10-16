# Repository record — cuems-frontend

Fields per [data-model.md](../data-model.md). Filled as the phase runs.

| Field | Value |
|---|---|
| start_commit | `6b69b41` |
| measured_versions | `package.json:3`, `package-lock.json:3` and `:9` → `0.0.0` |
| release_line / released_high_water | no package. ⚠ **`v0.1.0-rc1`** tagged on `origin/dev` (`6dc775c`) on **2026-10-16** by the frontend line (`package.json` there still `0.0.0`); not an ancestor of the refactor → target moved `0.1.0` → **`0.2.0`** (research R2b) |
| release_gap_start | n/a (no packaging release line); `origin/dev` carries its own work (the stop-project show badge) not in the refactor |
| target | **`0.2.0`** (FR-014, R2b) |
| bump_commit (replaced) | `9e91464` on `feat/xml-refactor` (signed, unpushed). The uncommitted `0.1.0` edit was discarded before committing, so nothing was replaced. `npm version --no-git-tag-version` created no tag (tag list unchanged) |
| release_gap_bump | n/a |
| relations | none (not packaged); compatibility contract = payload handshake `payload_version: 1` |
| literals_reviewed | only the three version fields changed (`git diff -U0`) |
| suite_start | 288 SUCCESS (`suite-start.txt`) |
| suite_A / suite_B | `CHROME_BIN=/usr/bin/google-chrome npm run test:ci` ×3 interleaved: A (`6b69b41`) 288 SUCCESS, B (`9e91464`) 288 SUCCESS |
| library_effect | n/a — the frontend does not import `cuemsutils` |
| reruns | — |
| new_failures | none |
| build | `npm run build` at `9e91464`: OK (`evidence/cuems-frontend/build.txt`; FR-006 n/a) |
| demo | n/a (no package) |
| tag_message | `../.xml-refactor-tag-messages/cuems-frontend.txt`. Verified: `Tag:` = `9e91464…` = head; `package.json` `0.2.0`; pairs editor/common/nodeconf/power-bridge/engine match; utils pending (T121) |
| go_ahead | ✅ 2026-10-16 — maintainer: "go" |
